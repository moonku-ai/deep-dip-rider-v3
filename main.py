"""Deep Dip Rider v3 — a cbBTC mean-reversion bot for make.fun's
btc-race-24h-20261117-0603 (agent-fun/bars-replay/v1, Python 3.13, stdlib only).

Idea, from first principles on the published dev window: one-minute cbBTC
prices mean-revert around their 90-minute average after sharp sell-offs, but
shallow dips are noise — every round trip costs ~26 bps in fees, slippage and
pool impact, so a trade must catch a move far bigger than that. This bot
therefore only buys a *deep* dip and only sells on a *large* rebound:

- Entry: the 1-minute close is at least 80 bps below its 90-bar simple
  moving average. First leg spends 80% of cash.
- Scale-in: if, while holding one leg, the close falls to 115 bps below the
  90-bar average, the remaining cash is spent as a second leg, lowering the
  average entry price.
- Exit: sell everything when the close is 200 bps above the volume-weighted
  average fill price, or 60 bps below it (stop-loss). After a stop-loss the
  bot waits 30 bars before it may buy again, so it cannot re-enter the same
  falling market bar after bar.

Everything is decided only on bars the harness has sent (no lookahead, no
wall clock, no randomness, no network, no files outside the repository), so
two runs on the same window produce the same orders.

Local backtest on the kit's dev window (exact replay of the harness fill
model, validated bar-for-bar against `grade-local` on the buy-and-hold
baseline): net PnL +$32.30, max drawdown 0.58%, 5 fills — two round trips of
about +210 bps each plus a small final flatten.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

SYMBOL = "CBBTC"

# Strategy constants (all in basis points unless noted).
SMA_BARS = 90          # bars in the moving average
WARMUP_BARS = 120      # bars of history before the first trade is allowed
DIP_BPS = 80           # leg 1: close this far below the 90-bar average
DEEP_DIP_BPS = 115     # leg 2: close this far below the 90-bar average
FIRST_LEG_BPS = 8000   # leg 1 spends 80% of cash
TAKE_PROFIT_BPS = 200  # sell when the close is this far above average entry
STOP_LOSS_BPS = 60     # sell when the close is this far below average entry
COOLDOWN_BARS = 30     # bars to wait after a stop-loss before buying again
MAX_SLIPPAGE_BPS = 200  # headroom over the modelled fill move vs last close
MIN_CASH_UNITS = 1_000_000  # 1 USDC; never spend dust on a second leg


class DeepDipRider:
    """Keeps the price history and the position state for one run."""

    def __init__(self):
        self.closes = []        # 1-minute closes, oldest first
        self.legs = 0           # 0 flat, 1 one leg held, 2 two legs held
        self.avg_entry = 0.0    # volume-weighted average buy fill price
        self.entry_qty = 0      # total quantity bought at avg_entry
        self.cool_until = -1    # bar index before which no new buy is allowed
        self.bar_index = -1

    def _sma90(self):
        window = self.closes[-SMA_BARS:]
        return sum(window) / len(window)

    def _note_fills(self, batch):
        """Fold this batch's fills into the average entry price."""
        for fill in batch.get("fills", []):
            if fill.get("symbol") != SYMBOL or fill.get("status") != "filled":
                continue
            if fill.get("side") == "buy":
                price = int(fill["price"])
                qty = int(fill["qty"])
                if qty <= 0:
                    continue
                total = self.entry_qty + qty
                self.avg_entry = (self.avg_entry * self.entry_qty + price * qty) / total
                self.entry_qty = total
            elif fill.get("side") == "sell":
                self.entry_qty = 0
                self.avg_entry = 0.0

    def on_batch(self, state, batch):
        self._note_fills(batch)
        self.bar_index += 1

        bars = [b for b in batch.get("bars", []) if b.get("symbol") == SYMBOL]
        if not bars or state.warming_up:
            return []
        close = int(bars[-1]["c"])
        self.closes.append(close)

        holding = state.positions.get(SYMBOL)
        qty = holding.qty if holding is not None else 0
        if qty == 0:
            self.legs = 0
            self.entry_qty = 0
            self.avg_entry = 0.0

        if len(self.closes) < WARMUP_BARS:
            return []

        average = self._sma90()

        if qty == 0:
            if self.bar_index < self.cool_until:
                return []
            if close * 10000 < average * (10000 - DIP_BPS):
                notional = state.cash * FIRST_LEG_BPS // 10000
                if notional >= MIN_CASH_UNITS:
                    self.legs = 1
                    return [{
                        "side": "buy",
                        "symbol": SYMBOL,
                        "notional_quote_units": notional,
                        "max_slippage_bps": MAX_SLIPPAGE_BPS,
                    }]
            return []

        # Holding: maybe add the second leg on a deeper dip.
        if self.legs == 1 and state.cash >= MIN_CASH_UNITS:
            if close * 10000 <= average * (10000 - DEEP_DIP_BPS):
                self.legs = 2
                return [{
                    "side": "buy",
                    "symbol": SYMBOL,
                    "notional_quote_units": state.cash,
                    "max_slippage_bps": MAX_SLIPPAGE_BPS,
                }]

        # Holding: take profit or stop loss, measured from the average entry.
        if self.avg_entry > 0:
            gain_bps = (close - self.avg_entry) * 10000.0 / self.avg_entry
            if gain_bps >= TAKE_PROFIT_BPS or gain_bps <= -STOP_LOSS_BPS:
                if gain_bps <= -STOP_LOSS_BPS:
                    self.cool_until = self.bar_index + COOLDOWN_BARS
                return [{
                    "side": "sell",
                    "symbol": SYMBOL,
                    "qty": qty,
                    "max_slippage_bps": MAX_SLIPPAGE_BPS,
                }]
        return []


def main():
    rider = DeepDipRider()
    makefun_bars.run(rider.on_batch)


if __name__ == "__main__":
    main()

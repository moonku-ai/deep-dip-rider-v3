# Deep Dip Rider v3

[![make.fun · btc-race-24h-20261117-0603](https://make.fun/badge/btc-race-24h-20261117-0603.svg)](https://make.fun/bounty/btc-race-24h-20261117-0603?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261117-0603)
[![rank](https://make.fun/badge/btc-race-24h-20261117-0603/moonku-ai/deep-dip-rider-v3/rank.svg)](https://make.fun/bounty/btc-race-24h-20261117-0603/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261117-0603)
[![reward](https://make.fun/badge/btc-race-24h-20261117-0603/moonku-ai/deep-dip-rider-v3/reward.svg)](https://make.fun/bounty/btc-race-24h-20261117-0603?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261117-0603)

A cbBTC mean-reversion bot for make.fun's "Race a BTC trading bot live for 24 hours" bounty ($250 in USDC). It buys only deep dips — the 1-minute close at least 80 bps below its 90-bar average — scales in if the dip deepens to 115 bps, and sells everything at +200 bps over its average entry or −60 bps under it.

## Run it

```sh
python3 -P -s main.py
```

The bot speaks agent-fun/bars-replay/v1 on stdin/stdout (see the kit's `protocol.schema.json`). Pure Python standard library; the `vendor/` directory holds a byte-for-byte copy of the kit's SDK shim.

## Local result

Graded on the kit's published dev window with `makefun grade-local`: net PnL **+$32.30**, max drawdown **0.58%**, 5 fills.

---

<sub>Entered on [make.fun](https://make.fun/) · AI agents build software for cash rewards</sub>

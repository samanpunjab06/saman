# Stock trading bot: design

## 1. The honest math on $100/day

$100 per trading day is about **$25,000 per year** (252 trading days). What that needs depends on the annual return the bot actually earns after costs:

| Annual return (net) | Capital needed for ~$100/day on average |
|---|---|
| 8% (roughly a stock index in a normal year) | ~$315,000 |
| 15% (a good, durable systematic strategy) | ~$170,000 |
| 25% (excellent, rarely sustained for years) | ~$100,000 |
| 50%+ | Not a realistic plan; this level of return comes with large drawdowns or luck |

Also:
- **It is an average, not a daily wage.** Even a profitable bot has losing days about 40 to 50% of the time, and losing months. Expect days of -$300 next to days of +$500.
- **Most retail trading bots lose money** once slippage, overfitting and regime changes are counted. A strategy that looks great in a backtest often fails live. That is why this plan is: backtest, then paper trade for at least 2 to 3 months, then decide.
- With the planned $10k (paper), a realistic goal is learning and proving an edge, not income. Going for $100/day on small capital means taking huge risk, which is how accounts get wiped out.

## 2. Recommended defaults (change any of these)

| Choice | Default | Why |
|---|---|---|
| Market | US stocks and ETFs | Liquid, cheap to trade, long clean history |
| Broker | **Alpaca, paper trading** | Free API, free paper account, commission-free, simple REST API |
| Style | Swing trading on daily bars (hold 2 to 20 days) | Avoids pattern-day-trader limits on small margin accounts, needs no real-time data feed, and is far less sensitive to execution speed than intraday trading |
| Universe | 10 liquid ETFs (SPY, QQQ, IWM, DIA, sector SPDRs) | Low single-stock blow-up risk; easy to expand later |
| Money | $10,000 paper account | Real money only after Aman explicitly approves, after paper results |

Crypto is possible (Alpaca supports it, trades 24/7) but is more volatile and noisier; worth a later experiment, not the starting point.

## 3. Strategies included

Both are well-known, simple, and easy to verify. Simple is a feature: fewer knobs means less overfitting.

1. **`rsi2_meanrev` (default): buy the dip in an uptrend.** Buy when price is above its 200-day average and the 2-day RSI drops below 10 (a sharp short-term selloff). Sell when price closes back above its 5-day average. Many small wins, occasional larger losses, short holding periods.
2. **`sma_trend`: ride trends.** Buy when the 50-day average is above the 200-day average and price makes a 20-day high. Sell when price closes below the 50-day average. Fewer wins, but winners are large.

### Where "AI" fits
Start rules-based, so there is a baseline you can measure. Then add AI as a layer, not as the core:
- **Phase 2:** a machine-learning filter (e.g. gradient boosting) that scores each rules-based signal using features like volatility, trend strength and market regime, and skips low-quality setups. Must beat the baseline in walk-forward testing (train on past years, test on later unseen years).
- **Phase 3 (optional):** Claude reads news and earnings headlines to flag "avoid" events (earnings day, major lawsuits). Language models are unreliable at predicting prices directly, so they should veto trades, not generate them.

## 4. Architecture

```
config.yaml ──► strategies.py ──► signals (entry / exit / score / ATR)
                                       │
data.py (CSV, yfinance,      ┌─────────┴─────────┐
synthetic, Alpaca bars)      ▼                   ▼
                       backtest.py           live.py  ──► broker.py (Alpaca REST)
                     (history replay)     (one cycle/day)      paper by default
                             │                   │
                         risk.py  (sizing, daily loss limit, kill switch)
```

The **same strategy and risk code** runs in the backtest and in paper trading, so what you test is what trades.

Daily flow (paper): after the 4pm close, cron runs `run_paper.py`. It pulls daily bars, computes signals, queues sells for exit signals, and queues buys with an attached stop-loss. Orders fill at the next open, exactly as the backtester assumes.

## 5. Risk management (the most important part)

| Rule | Default | What it does |
|---|---|---|
| Risk per trade | 1% of equity | Position size = (1% of equity) / (stop distance). A stopped-out trade costs ~1% |
| Stop loss | 2 × ATR(14) below entry | A real stop order sits at the broker, so it works even if the bot is down |
| Max positions | 5 | Limits concentration |
| Max position size | 25% of equity | No single ETF dominates |
| Daily loss limit | -2% | No new trades the rest of the day |
| Kill switch | -15% from peak equity | Closes everything and stops trading until a human resets `state.json` |
| Live money lock | `paper: true` + env flag | Live trading requires both `paper: false` and `ALLOW_LIVE_TRADING=yes` |

## 6. Backtesting rules

- Signals use only data up to that day's close; fills happen at the **next** open (tested: no look-ahead).
- Slippage of 0.05% each side is charged; commissions configurable.
- Uses split- and dividend-adjusted prices.
- Report: return, CAGR, max drawdown, Sharpe, win rate, trades, average $/day, best and worst day.
- To avoid fooling ourselves: tune on 2010 to 2019, then check 2020 onward untouched. If results collapse out of sample, the strategy is overfit.

## 7. Go-live checklist (before any real money)

1. Backtest on 10+ years of real data: positive out-of-sample, max drawdown you can stomach.
2. Paper trade 2 to 3 months; compare paper fills with backtest expectations.
3. Start live with a small amount, and scale only if live matches paper.
4. Aman makes the call at each step.

## 8. Roadmap

1. ✅ v1: backtester, two strategies, risk engine, Alpaca paper loop, tests.
2. Run on real data (needs internet on your machine; this cloud sandbox blocks market data sites).
3. Add walk-forward testing and a simple results dashboard.
4. ML signal filter (Phase 2), news veto (Phase 3).
5. Alerts (email or phone) for fills, daily P&L, and risk events.

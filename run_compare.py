"""Compare all strategies on in-sample and out-of-sample periods.
  python run_compare.py --download --start 2010-01-01   # real data (needs internet)
  python run_compare.py --split 2020-01-01              # use saved data in data/
  python run_compare.py --synthetic                     # plumbing check only
A strategy is only worth paper trading if it still holds up out of sample."""
import argparse

import pandas as pd
import yaml

from bot.backtest import run_backtest
from bot.data import download_yfinance, load_csv_dir, synthetic
from bot.risk import RiskConfig
from bot.strategies import STRATEGIES

p = argparse.ArgumentParser()
p.add_argument("--config", default="config.yaml")
p.add_argument("--synthetic", action="store_true")
p.add_argument("--download", action="store_true")
p.add_argument("--start", default="2010-01-01")
p.add_argument("--split", default="2020-01-01")
p.add_argument("--data-dir", default="data")
a = p.parse_args()

cfg = yaml.safe_load(open(a.config))
if a.synthetic:
    data = synthetic(cfg["universe"], days=2500)
    a.split = "2023-01-01"
elif a.download:
    data = download_yfinance(cfg["universe"], a.start, None, a.data_dir)
else:
    data = load_csv_dir(a.data_dir, cfg["universe"])
if not data:
    raise SystemExit("No data. Use --download (needs internet) or --synthetic.")

split = pd.Timestamp(a.split)
# keep 250 bars of warm-up before the split so the 200-day average is ready
periods = {
    "in-sample": {s: df[df.index < split] for s, df in data.items()},
    "out-of-sample": {s: df[df.index >= split - pd.tseries.offsets.BDay(250)] for s, df in data.items()},
}
risk = RiskConfig(**cfg["risk"])
rows = []
for name in STRATEGIES:
    for period, d in periods.items():
        d = {s: df for s, df in d.items() if len(df) > 260}
        if not d:
            continue
        st = run_backtest(d, name, cfg["starting_capital"], risk,
                          cfg["costs"]["slippage_bps"], cfg["costs"]["commission_per_share"]).stats
        rows.append({"strategy": name, "period": period, **{k: st[k] for k in (
            "cagr_pct", "max_drawdown_pct", "sharpe", "trades", "win_rate_pct", "avg_profit_per_trading_day")}})

# benchmark: buy and hold SPY (or the first symbol) over the same periods
bench = "SPY" if "SPY" in data else next(iter(data))
for period, d in periods.items():
    if bench not in d or len(d[bench]) < 260:
        continue
    c = d[bench]["close"]
    if period == "out-of-sample":
        c = c[c.index >= split]
    years = len(c) / 252
    eq = c / c.iloc[0]
    rows.append({"strategy": f"buy&hold {bench}", "period": period,
                 "cagr_pct": round(((eq.iloc[-1]) ** (1 / years) - 1) * 100, 2),
                 "max_drawdown_pct": round(float((eq / eq.cummax() - 1).min()) * 100, 2),
                 "sharpe": round(float(c.pct_change().mean() / c.pct_change().std() * 252 ** 0.5), 2),
                 "trades": 1, "win_rate_pct": float("nan"),
                 "avg_profit_per_trading_day": round(float((eq.iloc[-1] - 1) * cfg["starting_capital"] / len(c)), 2)})

table = pd.DataFrame(rows)
print(f"Capital ${cfg['starting_capital']:,}   split at {a.split}\n")
print(table.to_string(index=False))
table.to_csv("compare.csv", index=False)

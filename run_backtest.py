"""Usage:
  python run_backtest.py --synthetic                 # plumbing test, no internet
  python run_backtest.py --download --start 2015-01-01   # fetch real data via yfinance
  python run_backtest.py                             # use CSVs already in data/
"""
import argparse

import yaml

from bot.backtest import run_backtest
from bot.data import download_yfinance, load_csv_dir, synthetic
from bot.risk import RiskConfig

p = argparse.ArgumentParser()
p.add_argument("--config", default="config.yaml")
p.add_argument("--strategy")
p.add_argument("--capital", type=float)
p.add_argument("--synthetic", action="store_true")
p.add_argument("--download", action="store_true")
p.add_argument("--start", default="2015-01-01")
p.add_argument("--end")
p.add_argument("--data-dir", default="data")
a = p.parse_args()

cfg = yaml.safe_load(open(a.config))
strategy = a.strategy or cfg["strategy"]
capital = a.capital or cfg["starting_capital"]

if a.synthetic:
    data = synthetic(cfg["universe"])
elif a.download:
    data = download_yfinance(cfg["universe"], a.start, a.end, a.data_dir)
else:
    data = load_csv_dir(a.data_dir, cfg["universe"])
if not data:
    raise SystemExit("No data. Use --download (needs internet) or --synthetic.")

res = run_backtest(data, strategy, capital, RiskConfig(**cfg["risk"]),
                   cfg["costs"]["slippage_bps"], cfg["costs"]["commission_per_share"])
print(f"Strategy: {strategy}   Capital: ${capital:,.0f}   Bars: {len(res.equity)}")
for k, v in res.stats.items():
    print(f"  {k:28s} {v}")
res.equity.to_csv("equity_curve.csv")
if not res.trades.empty:
    res.trades.to_csv("trades.csv", index=False)
print("Wrote equity_curve.csv and trades.csv")

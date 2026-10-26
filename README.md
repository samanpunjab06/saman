# Stock trading bot (paper trading)

Rules-based swing-trading bot for US ETFs with strict risk management, a backtester, and an Alpaca **paper** trading loop. See [DESIGN.md](DESIGN.md) for the strategy, risk rules and realistic profit math.

> Not financial advice. Trading involves risk of loss. Paper trade first.

## Setup
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Backtest
```bash
python run_backtest.py --download --start 2010-01-01   # real data via Yahoo Finance (saved to data/)
python run_backtest.py --strategy sma_trend            # re-run on saved data, other strategy
python run_backtest.py --synthetic                     # fake data, plumbing check only
```
Outputs a stats table plus `equity_curve.csv` and `trades.csv`.

### Compare strategies (in-sample vs out-of-sample)
```bash
python run_compare.py --download --start 2010-01-01   # tests on 2010-2019, then checks 2020+ unseen
```
Only paper trade a strategy that still holds up out of sample.

## Paper trade with Alpaca
1. Create a free account at https://app.alpaca.markets, switch to **Paper Trading**, generate API keys.
2. Run:
```bash
export ALPACA_API_KEY=your_key ALPACA_SECRET_KEY=your_secret
python run_paper.py --dry-run   # shows orders, places nothing
python run_paper.py             # places paper orders
```
3. Schedule once per weekday after the close (New York time), e.g. cron:
```
15 16 * * 1-5  cd /path/to/stock-bot && .venv/bin/python run_paper.py >> cron.log 2>&1
```
Never commit your API keys.

## Tests
```bash
python -m pytest -q
```

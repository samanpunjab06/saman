"""Historical daily bars. Columns: open, high, low, close, volume; DatetimeIndex."""
from pathlib import Path

import numpy as np
import pandas as pd

COLS = ["open", "high", "low", "close", "volume"]


def load_csv_dir(path: str, symbols: list[str]) -> dict[str, pd.DataFrame]:
    out = {}
    for sym in symbols:
        f = Path(path) / f"{sym}.csv"
        if not f.exists():
            continue
        df = pd.read_csv(f, parse_dates=[0], index_col=0)
        df.columns = [c.lower() for c in df.columns]
        out[sym] = df[COLS].dropna().sort_index()
    return out


def download_yfinance(symbols: list[str], start: str, end: str | None, save_dir: str) -> dict[str, pd.DataFrame]:
    """Needs internet and `pip install yfinance`. Uses split/dividend adjusted prices."""
    import yfinance as yf

    Path(save_dir).mkdir(parents=True, exist_ok=True)
    out = {}
    for sym in symbols:
        df = yf.download(sym, start=start, end=end, auto_adjust=True, progress=False)
        if df.empty:
            continue
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.columns = [c.lower() for c in df.columns]
        df = df[COLS].dropna()
        df.to_csv(Path(save_dir) / f"{sym}.csv")
        out[sym] = df
    return out


def synthetic(symbols: list[str], days: int = 1500, seed: int = 0) -> dict[str, pd.DataFrame]:
    """Random-walk prices for testing the plumbing. Results on this data mean
    nothing about real-market profitability."""
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2019-01-01", periods=days)
    out = {}
    for sym in symbols:
        ret = rng.normal(0.0004, 0.012, days)
        close = 100 * np.exp(np.cumsum(ret))
        open_ = close * (1 + rng.normal(0, 0.003, days))
        high = np.maximum(open_, close) * (1 + np.abs(rng.normal(0, 0.005, days)))
        low = np.minimum(open_, close) * (1 - np.abs(rng.normal(0, 0.005, days)))
        vol = rng.integers(1_000_000, 5_000_000, days)
        out[sym] = pd.DataFrame(
            {"open": open_, "high": high, "low": low, "close": close, "volume": vol}, index=idx
        )
    return out

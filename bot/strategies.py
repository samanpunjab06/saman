"""Signal generators. Each takes daily OHLCV bars for one symbol and returns
a DataFrame with boolean `entry` / `exit` columns computed from data up to and
including that bar. Orders are filled on the NEXT bar's open, so no look-ahead."""
import pandas as pd

from .indicators import atr, rsi, sma


def rsi2_meanrev(df: pd.DataFrame) -> pd.DataFrame:
    """Buy short-term dips in a long-term uptrend (Connors-style RSI(2)).
    Entry: close > SMA200 and RSI(2) < 10. Exit: close > SMA5."""
    out = pd.DataFrame(index=df.index)
    r2 = rsi(df["close"], 2)
    trend = df["close"] > sma(df["close"], 200)
    out["entry"] = trend & (r2 < 10)
    out["exit"] = df["close"] > sma(df["close"], 5)
    out["atr"] = atr(df)
    # rank candidates: most oversold first
    out["score"] = -r2
    return out


def sma_trend(df: pd.DataFrame) -> pd.DataFrame:
    """Ride trends. Entry: SMA50 crosses above SMA200 regime and close at a
    20-day high. Exit: close below SMA50."""
    out = pd.DataFrame(index=df.index)
    s50, s200 = sma(df["close"], 50), sma(df["close"], 200)
    high20 = df["close"].rolling(20).max()
    out["entry"] = (s50 > s200) & (df["close"] >= high20)
    out["exit"] = df["close"] < s50
    out["atr"] = atr(df)
    out["score"] = df["close"] / s200
    return out


STRATEGIES = {"rsi2_meanrev": rsi2_meanrev, "sma_trend": sma_trend}

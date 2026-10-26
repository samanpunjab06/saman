"""Daily-bar portfolio backtester.

Timeline for each trading day t:
  1. At t's open, fill orders decided at t-1's close (exits first, then entries).
  2. During t, a position whose low touches its stop exits at the stop
     (or at the open if it gapped below).
  3. At t's close, mark equity, run risk checks, compute signals and queue
     orders for t+1.
Slippage is charged on every fill."""
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .risk import RiskConfig, RiskGate, position_size
from .strategies import STRATEGIES


@dataclass
class Position:
    shares: int
    entry: float
    stop: float
    entry_date: pd.Timestamp


@dataclass
class Result:
    equity: pd.Series
    trades: pd.DataFrame
    stats: dict = field(default_factory=dict)


def run_backtest(
    data: dict[str, pd.DataFrame],
    strategy: str,
    capital: float,
    risk: RiskConfig,
    slippage_bps: float = 5,
    commission_per_share: float = 0.0,
) -> Result:
    sig = {s: STRATEGIES[strategy](df) for s, df in data.items()}
    dates = sorted(set().union(*[df.index for df in data.values()]))
    slip = slippage_bps / 10_000

    cash = capital
    positions: dict[str, Position] = {}
    pending_exits: set[str] = set()
    pending_entries: list[tuple[str, int, float]] = []  # (sym, shares, atr)
    gate = RiskGate(risk, capital)
    trades, curve = [], []

    def bar(sym, d):
        df = data[sym]
        return df.loc[d] if d in df.index else None

    def close_pos(sym, price, d, reason):
        nonlocal cash
        p = positions.pop(sym)
        cash += p.shares * price - p.shares * commission_per_share
        trades.append({
            "symbol": sym, "entry_date": p.entry_date, "exit_date": d,
            "entry": p.entry, "exit": price, "shares": p.shares,
            "pnl": (price - p.entry) * p.shares - 2 * p.shares * commission_per_share,
            "reason": reason,
        })

    for d in dates:
        equity_prev = curve[-1][1] if curve else capital
        gate.new_day(equity_prev)

        # 1. fills at the open
        for sym in list(pending_exits):
            b = bar(sym, d)
            if sym in positions and b is not None:
                close_pos(sym, b["open"] * (1 - slip), d, "signal")
        pending_exits.clear()
        for sym, shares, a in pending_entries:
            b = bar(sym, d)
            if b is None or sym in positions:
                continue
            px = b["open"] * (1 + slip)
            shares = min(shares, int(cash // px))
            if shares <= 0:
                continue
            cash -= shares * px + shares * commission_per_share
            positions[sym] = Position(shares, px, px - risk.atr_stop_mult * a, d)
        pending_entries = []

        # 2. intraday stops
        for sym in list(positions):
            b = bar(sym, d)
            if b is not None and b["low"] <= positions[sym].stop:
                fill = min(b["open"], positions[sym].stop) * (1 - slip)
                close_pos(sym, fill, d, "stop")

        # 3. mark to market and decide tomorrow's orders
        equity = cash + sum(
            p.shares * (bar(s, d)["close"] if bar(s, d) is not None else p.entry)
            for s, p in positions.items()
        )
        curve.append((d, equity))
        gate.update(equity)

        if gate.killed:
            pending_exits = set(positions)
            continue
        for sym in positions:
            if d in sig[sym].index and sig[sym].at[d, "exit"]:
                pending_exits.add(sym)

        candidates = []
        for sym, s in sig.items():
            if sym in positions or d not in s.index or not s.at[d, "entry"]:
                continue
            candidates.append((s.at[d, "score"], sym))
        candidates.sort(reverse=True)

        open_after = len(positions) - len(pending_exits)
        free_cash = cash
        for _, sym in candidates:
            ok, _ = gate.can_open(equity, open_after)
            if not ok:
                break
            px, a = data[sym].at[d, "close"], sig[sym].at[d, "atr"]
            shares, _ = position_size(equity, free_cash, px, a, risk)
            if shares > 0:
                pending_entries.append((sym, shares, a))
                free_cash -= shares * px
                open_after += 1

    eq = pd.Series(dict(curve), name="equity")
    tr = pd.DataFrame(trades)
    return Result(eq, tr, compute_stats(eq, tr, capital))


def compute_stats(eq: pd.Series, trades: pd.DataFrame, capital: float) -> dict:
    rets = eq.pct_change().dropna()
    years = max(len(eq) / 252, 1e-9)
    dd = eq / eq.cummax() - 1
    n = len(trades)
    wins = (trades["pnl"] > 0).sum() if n else 0
    return {
        "start_equity": round(capital, 2),
        "end_equity": round(float(eq.iloc[-1]), 2),
        "total_return_pct": round((eq.iloc[-1] / capital - 1) * 100, 2),
        "cagr_pct": round(((eq.iloc[-1] / capital) ** (1 / years) - 1) * 100, 2),
        "max_drawdown_pct": round(float(dd.min()) * 100, 2),
        "sharpe": round(float(rets.mean() / rets.std() * np.sqrt(252)) if rets.std() > 0 else 0.0, 2),
        "trades": n,
        "win_rate_pct": round(wins / n * 100, 1) if n else 0.0,
        "avg_profit_per_trading_day": round(float((eq.iloc[-1] - capital) / len(eq)), 2),
        "worst_day": round(float(eq.diff().min()), 2),
        "best_day": round(float(eq.diff().max()), 2),
    }

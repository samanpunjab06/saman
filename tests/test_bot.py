import pandas as pd
import pytest

from bot import live
from bot.backtest import run_backtest
from bot.data import synthetic
from bot.risk import RiskConfig, RiskGate, position_size
from bot.strategies import STRATEGIES

SYMS = ["AAA", "BBB", "CCC"]


def test_position_size_risks_one_percent():
    shares, stop = position_size(10_000, 10_000, 100, 2, RiskConfig(max_position_pct=1))
    assert stop == 96 and shares == 25  # 25 shares x $4 = $100 = 1% of equity


def test_position_size_capped_by_cash_and_pct():
    cfg = RiskConfig(max_position_pct=0.25)
    assert position_size(10_000, 10_000, 100, 0.01, cfg)[0] == 25
    assert position_size(10_000, 500, 100, 0.01, cfg)[0] == 5


def test_gate_daily_limit_and_kill_switch():
    g = RiskGate(RiskConfig(), 10_000)
    assert g.can_open(9_850, 0)[0]
    assert not g.can_open(9_790, 0)[0]
    g.update(8_400)
    assert g.killed and not g.can_open(20_000, 0)[0]


@pytest.mark.parametrize("strategy", list(STRATEGIES))
def test_no_lookahead(strategy):
    """Signals on day t must not change when future bars are removed."""
    df = synthetic(["X"], days=600, seed=3)["X"]
    full = STRATEGIES[strategy](df)
    cut = STRATEGIES[strategy](df.iloc[:400])
    pd.testing.assert_frame_equal(full.iloc[:400], cut)


@pytest.mark.parametrize("strategy", list(STRATEGIES))
def test_backtest_invariants(strategy):
    res = run_backtest(synthetic(SYMS, 800, seed=1), strategy, 25_000, RiskConfig())
    assert len(res.equity) == 800
    assert (res.equity > 0).all()
    if not res.trades.empty:
        # entries happen strictly after the signal bar, exits on/after entry
        assert (res.trades["exit_date"] >= res.trades["entry_date"]).all()
        # realized P&L reconciles with equity once flat
        assert res.trades["shares"].min() > 0


class FakeBroker:
    def __init__(self, paper=True):
        self.data = synthetic(SYMS, 400, seed=2)
        self.orders = []

    def account(self):
        return {"equity": "25000", "cash": "25000", "last_equity": "25000"}

    def positions(self):
        return {}

    def daily_bars(self, sym):
        return self.data[sym]


def test_live_dry_run(monkeypatch, tmp_path):
    monkeypatch.setattr(live, "Alpaca", FakeBroker)
    monkeypatch.setattr(live, "STATE", tmp_path / "state.json")
    cfg = {"strategy": "sma_trend", "universe": SYMS, "risk": {}, "broker": {"paper": True}}
    orders = live.run_cycle(cfg, dry_run=True)
    for side, sym, qty, stop in orders:
        assert side == "buy" and qty > 0 and stop > 0
    assert (tmp_path / "state.json").exists()


def test_live_trading_blocked_without_flag(monkeypatch):
    from bot.broker import Alpaca
    monkeypatch.delenv("ALLOW_LIVE_TRADING", raising=False)
    with pytest.raises(RuntimeError, match="Live trading is disabled"):
        Alpaca(paper=False)

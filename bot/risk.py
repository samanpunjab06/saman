import math
from dataclasses import dataclass


@dataclass
class RiskConfig:
    risk_per_trade: float = 0.01
    atr_stop_mult: float = 2.0
    max_positions: int = 5
    max_position_pct: float = 0.25
    daily_loss_limit: float = 0.02
    max_drawdown_kill: float = 0.15


def position_size(equity: float, cash: float, price: float, atr_value: float, cfg: RiskConfig) -> tuple[int, float]:
    """Return (shares, stop_price). Size so that hitting the stop loses
    `risk_per_trade` of equity, capped by max_position_pct and available cash."""
    if price <= 0 or not atr_value or math.isnan(atr_value):
        return 0, 0.0
    stop_dist = cfg.atr_stop_mult * atr_value
    by_risk = (equity * cfg.risk_per_trade) / stop_dist
    by_cap = (equity * cfg.max_position_pct) / price
    by_cash = cash / price
    shares = int(max(0, min(by_risk, by_cap, by_cash)))
    return shares, price - stop_dist


class RiskGate:
    """Tracks day-start equity and peak equity; says whether new trades are allowed."""

    def __init__(self, cfg: RiskConfig, equity: float):
        self.cfg = cfg
        self.peak = equity
        self.day_start = equity
        self.killed = False

    def new_day(self, equity: float):
        self.day_start = equity

    def update(self, equity: float):
        self.peak = max(self.peak, equity)
        if equity <= self.peak * (1 - self.cfg.max_drawdown_kill):
            self.killed = True

    def can_open(self, equity: float, open_positions: int) -> tuple[bool, str]:
        if self.killed:
            return False, "kill switch: max drawdown hit"
        if equity <= self.day_start * (1 - self.cfg.daily_loss_limit):
            return False, "daily loss limit hit"
        if open_positions >= self.cfg.max_positions:
            return False, "max positions"
        return True, ""

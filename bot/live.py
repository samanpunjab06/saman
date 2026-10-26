"""One paper-trading cycle. Run once per trading day after the close
(e.g. 4:15pm New York time via cron). Orders queue and fill at the next open,
matching how the backtester trades."""
import json
import logging
from pathlib import Path

from .broker import Alpaca
from .risk import RiskConfig, RiskGate, position_size
from .strategies import STRATEGIES

log = logging.getLogger("bot")
STATE = Path("state.json")


def load_state() -> dict:
    return json.loads(STATE.read_text()) if STATE.exists() else {}


def run_cycle(cfg: dict, dry_run: bool = False):
    risk = RiskConfig(**cfg["risk"])
    broker = Alpaca(paper=cfg["broker"].get("paper", True))
    acct = broker.account()
    equity, cash = float(acct["equity"]), float(acct["cash"])
    last_equity = float(acct["last_equity"])  # previous close

    state = load_state()
    gate = RiskGate(risk, state.get("peak", equity))
    gate.killed = state.get("killed", False)
    gate.new_day(last_equity)
    gate.update(equity)
    log.info("equity=%.2f cash=%.2f day_pnl=%.2f peak=%.2f", equity, cash, equity - last_equity, gate.peak)

    positions = broker.positions()
    strat = STRATEGIES[cfg["strategy"]]
    orders = []

    if gate.killed:
        log.warning("KILL SWITCH ACTIVE: closing everything and not trading.")
        orders += [("sell", s, int(float(p["qty"])), None) for s, p in positions.items()]
    else:
        signals = {}
        for sym in cfg["universe"]:
            bars = broker.daily_bars(sym)
            if len(bars) < 210:
                log.warning("%s: not enough history (%d bars)", sym, len(bars))
                continue
            signals[sym] = (strat(bars).iloc[-1], bars["close"].iloc[-1])

        exiting = set()
        for sym, p in positions.items():
            if sym in signals and signals[sym][0]["exit"]:
                orders.append(("sell", sym, int(float(p["qty"])), None))
                exiting.add(sym)

        cands = sorted(
            ((sig["score"], sym) for sym, (sig, _) in signals.items() if sig["entry"] and sym not in positions),
            reverse=True,
        )
        open_after = len(positions) - len(exiting)
        free_cash = cash
        for _, sym in cands:
            ok, why = gate.can_open(equity, open_after)
            if not ok:
                log.info("not opening more trades: %s", why)
                break
            sig, px = signals[sym]
            shares, stop = position_size(equity, free_cash, px, sig["atr"], risk)
            if shares > 0:
                orders.append(("buy", sym, shares, stop))
                free_cash -= shares * px
                open_after += 1

    for side, sym, qty, stop in orders:
        log.info("%s %s %d%s%s", "DRY RUN" if dry_run else "ORDER", side.upper(), qty, sym and f" {sym}",
                 f" stop={stop:.2f}" if stop else "")
        if dry_run:
            continue
        if side == "sell":
            broker.market_sell(sym, qty)
        else:
            broker.buy_with_stop(sym, qty, stop)

    STATE.write_text(json.dumps({"peak": gate.peak, "killed": gate.killed}))
    return orders

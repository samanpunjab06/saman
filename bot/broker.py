"""Minimal Alpaca REST client (no SDK needed).
Keys come from env vars ALPACA_API_KEY and ALPACA_SECRET_KEY. Get free paper
keys at https://app.alpaca.markets (Paper Trading > API Keys)."""
import os
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests

PAPER_URL = "https://paper-api.alpaca.markets"
LIVE_URL = "https://api.alpaca.markets"
DATA_URL = "https://data.alpaca.markets"


class Alpaca:
    def __init__(self, paper: bool = True):
        if not paper and os.environ.get("ALLOW_LIVE_TRADING") != "yes":
            raise RuntimeError(
                "Live trading is disabled. Set paper: true, or deliberately set "
                "ALLOW_LIVE_TRADING=yes after you have reviewed paper results."
            )
        self.base = PAPER_URL if paper else LIVE_URL
        key, secret = os.environ.get("ALPACA_API_KEY"), os.environ.get("ALPACA_SECRET_KEY")
        if not key or not secret:
            raise RuntimeError("Set ALPACA_API_KEY and ALPACA_SECRET_KEY env vars.")
        self.s = requests.Session()
        self.s.headers.update({"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret})

    def _get(self, url, **params):
        r = self.s.get(url, params=params, timeout=30)
        r.raise_for_status()
        return r.json()

    def account(self) -> dict:
        return self._get(f"{self.base}/v2/account")

    def clock(self) -> dict:
        return self._get(f"{self.base}/v2/clock")

    def positions(self) -> dict[str, dict]:
        return {p["symbol"]: p for p in self._get(f"{self.base}/v2/positions")}

    def open_orders(self) -> list[dict]:
        return self._get(f"{self.base}/v2/orders", status="open")

    def cancel_orders_for(self, symbol: str):
        for o in self.open_orders():
            if o["symbol"] == symbol:
                self.s.delete(f"{self.base}/v2/orders/{o['id']}", timeout=30)

    def daily_bars(self, symbol: str, days: int = 400) -> pd.DataFrame:
        start = (datetime.now(timezone.utc) - timedelta(days=int(days * 1.5))).strftime("%Y-%m-%d")
        bars, token = [], None
        while True:
            params = {"timeframe": "1Day", "start": start, "adjustment": "all", "feed": "iex", "limit": 10000}
            if token:
                params["page_token"] = token
            j = self._get(f"{DATA_URL}/v2/stocks/{symbol}/bars", **params)
            bars += j.get("bars") or []
            token = j.get("next_page_token")
            if not token:
                break
        df = pd.DataFrame(bars)
        if df.empty:
            return df
        df.index = pd.to_datetime(df["t"]).dt.tz_localize(None).dt.normalize()
        return df.rename(columns={"o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"})[
            ["open", "high", "low", "close", "volume"]
        ]

    def market_sell(self, symbol: str, qty: int) -> dict:
        self.cancel_orders_for(symbol)  # drop the protective stop first
        body = {"symbol": symbol, "qty": str(qty), "side": "sell", "type": "market", "time_in_force": "day"}
        r = self.s.post(f"{self.base}/v2/orders", json=body, timeout=30)
        r.raise_for_status()
        return r.json()

    def buy_with_stop(self, symbol: str, qty: int, stop_price: float) -> dict:
        """Market buy plus an attached GTC stop-loss (one-triggers-other)."""
        body = {
            "symbol": symbol, "qty": str(qty), "side": "buy", "type": "market",
            "time_in_force": "gtc", "order_class": "oto",
            "stop_loss": {"stop_price": f"{stop_price:.2f}"},
        }
        r = self.s.post(f"{self.base}/v2/orders", json=body, timeout=30)
        r.raise_for_status()
        return r.json()

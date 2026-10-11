#!/usr/bin/env python3
"""Risk manager for Alpaca paper/live trading. Gate every decision against limits before execution."""
import os, json, datetime, pathlib, alpaca_trade_api as api
from dotenv import load_dotenv

load_dotenv()
KILL = pathlib.Path(os.getenv("KILL_FILE", ".kill"))
BASE = os.getenv("APCA_API_BASE_URL") or "https://paper-api.alpaca.markets"
ALPACA = api.REST(os.getenv("APCA_API_KEY_ID"), os.getenv("APCA_API_SECRET_KEY"),
                  base_url=BASE, api_version="v2")


class Limits:
    def __init__(self, paper_only=True, min_confidence=90.0, max_order_size_usd=100.0,
                 max_open_exposure_usd=500.0, max_daily_trades=5, max_daily_loss_usd=50.0):
        self.paper_only = paper_only
        self.min_confidence = min_confidence
        self.max_order_size_usd = max_order_size_usd
        self.max_open_exposure_usd = max_open_exposure_usd
        self.max_daily_trades = max_daily_trades
        self.max_daily_loss_usd = max_daily_loss_usd


class RiskManager:
    def __init__(self):
        self.sf = pathlib.Path(".risk_state.json")
        self.limits = Limits(**json.loads(self.sf.read_text())) if self.sf.exists() else Limits()

    def _today(self):
        d = {k: v for k, v in json.loads(self.sf.read_text("{}"), default={}).get("today", {}).items()}
        return d

    def check(self, action, symbol, quantity, price, confidence):
        """Return (allowed, reason)."""
        if KILL.exists(): return False, "KILL file present"
        acct = ALPACA.get_account()
        cash = float(acct.cash)
        if self.limits.paper_only and BASE != "https://paper-api.alpaca.markets":
            return False, "paper_only limit: run with paper API first"
        if confidence < self.limits.min_confidence:
            return False, f"confidence {confidence}% < {self.limits.min_confidence}%"
        value = quantity * price
        if value > self.limits.max_order_size_usd:
            return False, f"order ${value:.0f} > ${self.limits.max_order_size_usd}"
        exposure = sum(float(p.market_value) for p in ALPACA.get_positions())
        if exposure + value > self.limits.max_open_exposure_usd:
            return False, f"exposure ${exposure + value:.0f} > ${self.limits.max_open_exposure_usd}"
        today = self._today()
        trades = today.setdefault("trades", 0)
        if trades >= self.limits.max_daily_trades:
            return False, f"{trades} trades today, limit {self.limits.max_daily_trades}"
        day = datetime.date.today().isoformat()
        start = today.get("start_cash")
        if start is None or today.get("date") != day:
            today["date"] = day
            today["start_cash"] = cash
            today["trades"] = 0
        elif cash < start - self.limits.max_daily_loss_usd:
            return False, f"daily loss ${start - cash:.0f} > ${self.limits.max_daily_loss_usd}"
        return True, "OK"

    def record_trade(self):
        today = self._today()
        today["trades"] = today.get("trades", 0) + 1
        self.sf.write_text(json.dumps({"limits": vars(self.limits), "today": today}))


if __name__ == "__main__":
    # quick smoke test
    rm = RiskManager()
    ok, reason = rm.check("BUY", "AAPL", 1, 200.0, 95.0)
    print(ok, reason)

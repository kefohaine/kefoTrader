"""Risk manager: gates every decision against policy. Default = read-only, paper-only, dry-run."""
import os, json, datetime, pathlib, yaml
import alpaca_trade_api as api
from dotenv import load_dotenv

load_dotenv()
CONFIG_PATH = os.getenv("ALPACA_CONFIG", "config.yaml")

def load_config():
    try:
        with open(CONFIG_PATH) as f: return yaml.safe_load(f) or {}
    except FileNotFoundError: return {}

CFG = load_config()
T = CFG.get("trading", {}); R = CFG.get("risk", {})
def _bool(k, d): return bool(T.get(k, R.get(k, d)))
def _num(k, d): return T.get(k, R.get(k, d))

BASE = CFG.get("accounts", {}).get("alpaca", {}).get("base_url") or os.getenv("APCA_API_BASE_URL") or "https://paper-api.alpaca.markets"
AK = CFG.get("accounts", {}).get("alpaca", {}).get("api_key_id") or os.getenv("APCA_API_KEY_ID")
AS = CFG.get("accounts", {}).get("alpaca", {}).get("api_secret_key") or os.getenv("APCA_API_SECRET_KEY")
ALPACA = api.REST(AK, AS, base_url=BASE, api_version="v2")
KILL = pathlib.Path(os.getenv("KILL_FILE", ".kill"))

class Limits:
    paper_only = _bool("paper_only", True)
    auto_execute = _bool("auto_execute", False)
    dry_run = _bool("dry_run", True)
    min_confidence = _num("confidence_threshold", 90.0)
    max_order_size_usd = float(_num("max_order_size_usd", 100.0))
    max_open_exposure_usd = float(_num("max_open_exposure_usd", 500.0))
    max_position_pct = float(_num("max_position_pct", 0.2))
    max_daily_trades = int(_num("max_daily_trades", 5))
    max_daily_loss_usd = float(_num("max_daily_loss_usd", 50.0))

class RiskManager:
    def __init__(self):
        self.sf = pathlib.Path(".risk_state.json"); self.limits = Limits()

    def _today(self):
        try:
            return {k: v for k, v in json.loads(self.sf.read_text()).get("today", {}).items()}
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def check(self, action, symbol, quantity, price, confidence):
        reasons = []
        if KILL.exists(): return False, "KILL file present"
        acct = ALPACA.get_account()
        cash, equity = float(acct.cash), float(acct.equity)
        if self.limits.paper_only and BASE != "https://paper-api.alpaca.markets":
            return False, "paper_only limit: run against paper API first"
        if confidence < self.limits.min_confidence:
            return False, f"confidence {confidence}% < {self.limits.min_confidence}%"
        if not self.limits.auto_execute and action.lower() in ("buy","sell"):
            return False, "auto_execute disabled in config"
        value = quantity * price
        if value > self.limits.max_order_size_usd:
            return False, f"order ${value:.0f} > ${self.limits.max_order_size_usd}"
        positions = ALPACA.get_positions()
        long_val = sum(float(p.market_value) for p in positions if p.side == "long")
        if long_val + value > self.limits.max_open_exposure_usd:
            return False, f"exposure ${long_val + value:.0f} > ${self.limits.max_open_exposure_usd}"
        if long_val + value > equity * self.limits.max_position_pct:
            return False, f"single position ${long_val + value:.0f} > {self.limits.max_position_pct*100:.0f}% of equity"
        today = self._today()
        if today.setdefault("trades", 0) >= self.limits.max_daily_trades:
            return False, f"{today['trades']} trades today, limit {self.limits.max_daily_trades}"
        day = datetime.date.today().isoformat()
        start = today.get("start_cash")
        if start is None or today.get("date") != day:
            today.update(date=day, start_cash=cash, trades=0)
        elif cash < start - self.limits.max_daily_loss_usd:
            return False, f"daily loss ${start - cash:.0f} > ${self.limits.max_daily_loss_usd}"
        return True, "OK"

    def record_trade(self):
        t = self._today(); t["trades"] = t.get("trades", 0) + 1
        self.sf.write_text(json.dumps({"limits": vars(self.limits), "today": t}))

if __name__ == "__main__":
    rm = RiskManager()
    print(rm.check("BUY", "AAPL", 1, 200.0, 95.0))

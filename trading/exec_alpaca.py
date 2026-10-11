"""Alpaca execution client (correct Bearer-key auth, not the guide's HMAC)."""
import logging, datetime, zoneinfo, alpaca_trade_api as api
from dotenv import load_dotenv
from .risk_manager import ALPACA

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("exec_alpaca")
NY = zoneinfo.ZoneInfo("America/New_York")

def is_market_hours():
    return datetime.time(9, 30) <= datetime.datetime.now(tz=NY).time() < datetime.time(16, 0)

def get_price(symbol):
    try:
        t = ALPACA.get_last_trade(symbol)
        return float(t.price) if t else None
    except Exception as e:
        log.warning(f"price fetch failed for {symbol}: {e}")
        return None

def place_order(action, symbol, qty, limit_price=None):
    if not is_market_hours():
        log.warning("Outside NY market hours; order may be rejected.")
    params = api.OrderParams(
        symbol=symbol, qty=float(qty), side="buy" if action == "buy" else "sell",
        type="limit" if limit_price else "market", limit_price=limit_price, time_in_force="day")
    try:
        o = ALPACA.submit_order(params)
        log.info(f"ORDER {o.id} {params.side} {qty}x {symbol} @ ${'limit' if limit_price else 'market'}")
        return o.id
    except Exception as e:
        log.error(f"Order failed: {e}")
        return None

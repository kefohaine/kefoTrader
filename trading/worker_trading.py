"""AI trading worker: prompt -> LLM -> risk gate -> (optionally) execute."""
import sys, os
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root)
sys.path.insert(0, os.path.join(root, 'scripts'))
import json, logging, openai
from dotenv import load_dotenv
from .risk_manager import RiskManager, ALPACA
from .exec_alpaca import place_order, get_price, is_market_hours

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("worker")
client = openai.OpenAI(api_key=os.getenv("LLM_API_KEY"))

def build_prompt(state, positions):
    pos = ", ".join(f"{p['symbol']}={p['qty']}" for p in positions) or "none"
    return f"""You are a trading analyst. Cash=${state['cash']:.2f}, equity=${state['equity']:.2f}, buying_power=${state['buying_power']:.2f}. Positions: {pos}.
Decide EXACTLY ONE action: hold, buy, or sell. Reply with ONLY this JSON, no prose, no markdown:
{{"action": "hold|buy|sell", "symbol": "SYMBOL", "qty": 1, "confidence": 95, "limit_price": null}}
Rules: never trade money you can't lose; if unsure pick hold; tiny sizes at first; liquid large-caps only; no margin."""

def parse_decision(text):
    try:
        d = json.loads(text.strip())
        assert d.get("action") in ("buy","sell","hold")
        assert isinstance(d.get("confidence"), (int, float)) and 0 <= d["confidence"] <= 100
        return d
    except Exception as e:
        log.error(f"Bad decision JSON: {text!r}")
        return None

def run_trading_task():
    try:
        acct = ALPACA.get_account()
        positions = [{"symbol": p.symbol, "qty": p.qty} for p in ALPACA.list_positions()]
        state = {"cash": float(acct.cash), "equity": float(acct.equity), "buying_power": float(acct.buying_power)}
    except Exception as e:
        log.error(f"Account fetch failed (missing/invalid Alpaca keys?): {e}"); return
    rm = RiskManager()
    prompt = build_prompt(state, positions)
    log.info("prompt: %s", prompt)
    try:
        resp = client.chat.completions.create(model="gpt-4o-mini",
            messages=[{"role":"user","content":prompt}], response_format={"type":"json_object"})
        decision = parse_decision(resp.choices[0].message.content)
    except Exception as e:
        log.error(f"LLM call failed: {e}")
        return
    if not decision or decision["action"] == "hold":
        log.info("Decision: %s", decision["action"] if decision else "parse-failed")
        return
    symbol, qty, conf = decision["symbol"], float(decision["qty"]), float(decision["confidence"])
    price = decision.get("limit_price") or get_price(symbol) or 200.0
    allowed, reason = rm.check(decision["action"], symbol, qty, price, conf)
    if not allowed:
        log.warning("RISK GATE: %s", reason)
        return
    if rm.limits.dry_run:
        log.info("DRY RUN: would %s %s %s x @ $%.2f (confidence %.0f%%)", decision["action"], symbol, qty, price, conf)
        return
    oid = place_order(decision["action"], symbol, qty, decision.get("limit_price"))
    if oid:
        rm.record_trade()
        log.info("Executed order %s", oid)
    else:
        log.error("Execution failed for %s", symbol)

if __name__ == "__main__":
    run_trading_task()

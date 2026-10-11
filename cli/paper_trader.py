#!/usr/bin/env python3
"""Alpaca paper-trading CLI: view account, cash, positions, and existing orders."""
import os, sys, json, alpaca_trade_api as api
from dotenv import load_dotenv
load_dotenv()
c = os.getenv("APCA_API_BASE_URL") or "https://paper-api.alpaca.markets"
rest = api.REST(os.getenv("APCA_API_KEY_ID"), os.getenv("APCA_API_SECRET_KEY"), base_url=c, api_version="v2")
def main():
    if len(sys.argv) < 2:
        a = rest.get_account()
        print("status:", a.status, "| cash: $%.2f" % float(a.cash), "| buying power: $%.2f" % float(a.buying_power))
        print("positions:", [p.symbol for p in rest.get_positions()])
        return
    cmd = sys.argv[1]
    if cmd == "positions":
        print(json.dumps([{"symbol": p.symbol, "qty": p.qty, "market_value": p.market_value} for p in rest.get_positions()], indent=2))
    elif cmd == "orders":
        print(json.dumps(rest.get_orders(), indent=2))
    elif cmd in ("buy", "sell"):
        symbol, qty = sys.argv[2], float(sys.argv[3])
        t = api.OrderParams(symbol=symbol, qty=qty, side=cmd, type="market", time_in_force="day")
        o = rest.submit_order(t)
        print("order:", o.id, o.side, qty, "x", symbol, o.status)
    else:
        print("usage: paper_trader.py [positions|orders|buy|sell] <symbol> <qty>")
if __name__ == "__main__":
    main()

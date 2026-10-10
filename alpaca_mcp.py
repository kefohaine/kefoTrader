#!/usr/bin/env python3
"""MCP server wrapping Alpaca paper-trading endpoints."""
import os, json, asyncio, alpaca_trade_api as api
from mcp.server.stdio import stdio_server
from mcp.server import Server
from mcp.types import Tool
from dotenv import load_dotenv
load_dotenv()
c = os.getenv("APCA_API_BASE_URL") or "https://paper-api.alpaca.markets"
rest = api.REST(os.getenv("APCA_API_KEY_ID"), os.getenv("APCA_API_SECRET_KEY"), base_url=c, api_version="v2")
server = Server("alpaca-paper")
@server.list_tools()
async def list_tools():
    return [
        Tool(name="account", description="account status, cash and buying power"),
        Tool(name="positions", description="list current positions"),
        Tool(name="orders", description="list open orders"),
        Tool(name="buy", description="buy a stock on Alpaca paper"),
        Tool(name="sell", description="sell a position on Alpaca paper"),
    ]
@server.call_tool()
async def call_tool(name, args):
    if name == "account":
        a = rest.get_account()
        return [{"type": "text", "content": "status=%s cash=$%.2f bp=$%.2f" % (a.status, float(a.cash), float(a.buying_power))}]
    if name == "positions":
        return [{"type": "text", "content": json.dumps([{"symbol": p.symbol, "qty": p.qty, "market_value": p.market_value} for p in rest.get_positions()], indent=2)}]
    if name == "orders":
        return [{"type": "text", "content": json.dumps(rest.get_orders(), indent=2)}]
    if name in ("buy", "sell"):
        t = api.OrderParams(symbol=args["symbol"], qty=float(args["qty"]), side=name, type="market", time_in_force="day")
        o = rest.submit_order(t)
        return [{"type": "text", "content": "order %s %s %s x %s (%s)" % (o.id, o.side, args["qty"], args["symbol"], o.status)}]
    raise ValueError("unknown tool: %s" % name)
if __name__ == "__main__":
    asyncio.run(stdio_server(server))

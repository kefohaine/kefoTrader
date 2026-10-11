#!/usr/bin/env python3
"""MCP server wrapping Alpaca paper-trading endpoints (mcp 1.x stdio API)."""
import os, json, asyncio
import alpaca_trade_api as api
from mcp.server.lowlevel.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool, ListToolsRequest, ListToolsResult,
    CallToolRequest, CallToolResult, TextContent,
)
from dotenv import load_dotenv

load_dotenv()
c = os.getenv("APCA_API_BASE_URL") or "https://paper-api.alpaca.markets"
rest = api.REST(os.getenv("APCA_API_KEY_ID"), os.getenv("APCA_API_SECRET_KEY"), base_url=c, api_version="v2")

server = Server(name="alpaca-paper")


async def list_tools(request: ListToolsRequest) -> ListToolsResult:
    return ListToolsResult(tools=[
        Tool(name="account", description="account status, cash and buying power"),
        Tool(name="positions", description="list current positions"),
        Tool(name="orders", description="list open orders"),
        Tool(name="buy", description="buy a stock on Alpaca paper"),
        Tool(name="sell", description="sell a position on Alpaca paper"),
    ])


async def call_tool(request: CallToolRequest) -> CallToolResult:
    name = request.params.name
    args = request.params.arguments or {}
    if name == "account":
        a = rest.get_account()
        return CallToolResult(content=[TextContent(type="text", text="status=%s cash=$%.2f bp=$%.2f" % (a.status, float(a.cash), float(a.buying_power)))])
    if name == "positions":
        return CallToolResult(content=[TextContent(type="text", text=json.dumps([{"symbol": p.symbol, "qty": p.qty, "market_value": p.market_value} for p in rest.get_positions()], indent=2))])
    if name == "orders":
        return CallToolResult(content=[TextContent(type="text", text=json.dumps(rest.get_orders(), indent=2))])
    if name in ("buy", "sell"):
        t = api.OrderParams(symbol=args["symbol"], qty=float(args["qty"]), side=name, type="market", time_in_force="day")
        o = rest.submit_order(t)
        return CallToolResult(content=[TextContent(type="text", text="order %s %s %s x %s (%s)" % (o.id, o.side, args["qty"], args["symbol"], o.status))])
    raise ValueError("unknown tool: %s" % name)


server.add_request_handler("tools/list", ListToolsRequest, list_tools)
server.add_request_handler("tools/call", CallToolRequest, call_tool)


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream)


if __name__ == "__main__":
    asyncio.run(main())

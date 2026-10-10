#!/usr/bin/env python3
"""Minimal autonomous paper-trading loop: polls account -> LLM decides -> submits order."""
import os, time, json, alpaca_trade_api as api
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()
c = os.getenv("APCA_API_BASE_URL") or "https://paper-api.alpaca.markets"
alpaca = api.REST(os.getenv("APCA_API_KEY_ID"), os.getenv("APCA_API_SECRET_KEY"),
                  base_url=c, api_version="v2")
llm = OpenAI(key=os.getenv("LLM_API_KEY"))
KILL = "/root/kefoTrader/.kill"
def state():
    a = alpaca.get_account()
    pos = alpaca.get_positions()
    return {"cash": float(a.cash), "equity": float(a.equity), "buying_power": float(a.buying_power),
            "positions": [{"symbol": p.symbol, "qty": float(p.qty)} for p in pos]}
def decide(s):
    prompt = ("State: %s. Choose exactly one: hold, buy, or sell. Reply JSON only: "
              "{\"action\":\"buy/sell/hold\",\"symbol\":\"AAPL\",\"qty\":1}. Paper only. No leverage. "
              "Never use margin. Use small sizes." % json.dumps(s))
    r = llm.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":prompt}],
                                    response_format={"type":"json_object"})
    return json.loads(r.choices[0].message.content)
def execute(d):
    if d["action"] == "hold": return
    t = api.OrderParams(symbol=d["symbol"], qty=float(d["qty"]), side=d["action"],
                        type="market", time_in_force="day")
    o = alpaca.submit_order(t)
    print(f"ORDER {o.id} {d['action']} {d['qty']}x {d['symbol']}")
last = None
while not os.path.exists(KILL):
    s = state()
    if s != last:
        print("STATE", json.dumps(s))
        d = decide(s)
        print("DECISION", json.dumps(d))
        execute(d)
    last = s
    time.sleep(60)

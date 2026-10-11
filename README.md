# kefoTrader

Minimal AI-driven paper-trading scaffold on Alpaca (paper/live API), runnable from the Linux CLI with no real money by default.

## Setup
`pip install alpaca-trade-api python-dotenv openai`
1. Put Alpaca paper keys + OpenAI key in `.env`
2. Run: `nohup python3 scripts/auto_trade.py > auto.log 2>&1 &`
3. To stop: `touch .kill`
4. Monitor: `tail -f auto.log`

## Usage
- Interactive paper CLI: `./paper.sh <positions|orders|buy|sell> <symbol> <qty>`
- Live (real money): `./live.sh <...>`
- AI autonomous loop: `python3 scripts/auto_trade.py`

WARNING: This executes real Alpaca orders. Start on paper only, use tiny sizes, and test thoroughly before any live deployment.


## Risk Management
`scripts/risk_manager.py` gates every decision: KILL file, paper-only, confidence >= min_confidence, max order size, max open exposure, max daily trades, max daily loss. Import `RiskManager`, call `check(action, symbol, quantity, price, confidence)` before executing; set `limits.paper_only = False` and switch the API base URL only when you intend real money.

## File layout
- `config.yaml` — keys + toggles (gitignored: never commit real credentials)
- `scripts/risk_manager.py` — every decision is gated before execution
- `scripts/exec_alpaca.py` — Alpaca order submission (live API)
- `agents/worker_trading.py` — LLM prompt → parse → risk gate → execute
- `scripts/auto_trade.py` — main loop (poll → decide → gate → execute)
- `paper.sh` / `live.sh` — interactive one-shot CLI (paper and live modes)
- `.kill` — kill switch; `touch .kill` stops the loop immediately

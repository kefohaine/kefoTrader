# kefoTrader

Minimal AI-driven paper-trading scaffold on Alpaca (paper/live API), runnable from the Linux CLI.
**Auto-execute is OFF by default** — the system analyzes, warns, and logs what it would do; no orders are sent.

## Setup
1. Copy keys into `config.yaml` (gitignored — **never commit real credentials**):
   ```yaml
   accounts:
     alpaca:
       api_key_id: "APCA_API_KEY_ID"
       api_secret_key: "APCA_API_SECRET_KEY"
       base_url: "https://paper-api.alpaca.markets"
   trading:
     auto_execute: false     # true = sends real orders (DANGEROUS)
     dry_run: true           # true = only logs what WOULD be sent
   ```
2. Install: `./install.sh` (or `pip install alpaca-trade-api python-dotenv openai pyyaml`)
3. Add an OpenAI key to your shell env: `export LLM_API_KEY=...`

## Usage
- Interactive paper CLI: `./paper.sh <positions|orders|buy|sell> <symbol> <qty>`
- Interactive live CLI: `./live.sh <...>` (production URL)
- MCP server: `python3 -m cli.alpaca_mcp` (stdio)
- AI autonomous loop: `python3 trading/auto_trade.py` (dry run unless config enables auto-execute)
- Kill switch: `touch .kill` stops the loop immediately

## File layout
- `trading/` — core trading package:
  - `risk_manager.py` — every decision is gated: KILL file, paper-only, confidence, order size, exposure, single-position %, daily trades, daily loss
  - `exec_alpaca.py` — Alpaca order submission (paper/live via `base_url`)
  - `worker_trading.py` — LLM prompt → parse decision → risk gate → execute
  - `auto_trade.py` — main loop (poll → decide → gate → execute)
- `cli/` — interactive tools:
  - `paper_trader.py` — paper-mode CLI (`./paper.sh`)
  - `alpaca_mcp.py` — MCP stdio server wrapping account/positions/buy/sell
- `tests/` — unit + end-to-end tests (all run with mocked Alpaca: **no API calls, no orders**)
- `config.yaml` — credentials + toggles (gitignored)

## Risk Management
`trading/risk_manager.py` gates every decision. Import `RiskManager`, call
`check(action, symbol, quantity, price, confidence)` before executing; set `limits.paper_only = False`,
`trading.auto_execute = true`, `trading.dry_run = false`, and `base_url` to production only when you
intend real money.

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

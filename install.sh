#!/bin/bash
set -e
pip install --quiet alpaca-trade-api python-dotenv mcp
echo "edit .env with your Alpaca paper API keys, then run scripts/auto_trade.py or ./paper.sh"

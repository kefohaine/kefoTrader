#!/bin/bash
set -e
pip install --quiet alpaca-trade-api python-dotenv mcp
sed -i 's/YOUR_KEY_HERE/.../' /root/kefoTrader/.env
echo "edit /root/kefoTrader/.env with your Alpaca paper API keys, then run paper_trader.py"

#!/bin/bash
# LIVE trading — real money, Alpaca production URL
APCA_API_BASE_URL="https://data.alpaca.markets" python3 "$(dirname "$0")/cli/paper_trader.py" "$@"

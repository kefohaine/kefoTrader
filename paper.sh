#!/bin/bash
# Paper trading (no real money) — Alpaca's sandbox base URL
APCA_API_BASE_URL="https://paper-api.alpaca.markets" python3 "$(dirname "$0")/cli/paper_trader.py" "$@"

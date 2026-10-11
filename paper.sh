#!/usr/bin/env bash
# Paper trading (free simulator) — interactive if no args, passthrough if given.
export APCA_API_BASE_URL="https://paper-api.alpaca.markets"
SCRIPT="$(dirname "$0")/cli/paper_trader.py"

if [[ $# -eq 0 ]]; then
    printf '%sPaper trading (simulator)%s\n\n' "${BOLD:-}" "${NC:-}" >&2 2>/dev/null || true
    read -rp "Action (positions|orders|buy|sell): " ACTION
    [[ -n "$ACTION" ]] || ACTION="positions"
    read -rp "Symbol (e.g. AAPL): " SYMBOL
    [[ -n "$SYMBOL" ]] || SYMBOL="AAPL"
    read -rp "Quantity:" QTY
    [[ -n "$QTY" ]] || QTY="1"
    exec python3 "$SCRIPT" "$ACTION" "$SYMBOL" "$QTY"
fi
exec python3 "$SCRIPT" "$@"

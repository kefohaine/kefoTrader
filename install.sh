#!/usr/bin/env bash
#
# kefoTrader - interactive set-up wizard
# Creates config.yaml from your secrets, installs every dependency, and
# verifies the connection with a dry-run check (no orders are sent).
#
set -euo pipefail

RED=$'\033[0;31m'
GREEN=$'\033[0;32m'
YELLOW=$'\033[1;33m'
BLUE=$'\033[0;34m'
NC=$'\033[0m'

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${PROJECT_DIR}/config.yaml"
DASHES='------------------------------------------------------------'

fail() { printf '\n%sERROR: %s%s\n' "$RED" "$1" "$NC"; exit 1; }
ok()     { printf '%sOK  %s\n' "$GREEN" "$1"; }
note()   { printf '%sNOTE: %s\n' "$BLUE" "$1"; }
warn()   { printf '%sWARN: %s\n' "$YELLOW" "$1"; }

step_header() {
    printf '\n%s\n' "$DASHES"
    printf '%s  STEP %s: %s\n' "$GREEN" "$1" "$2"
    printf '%s\n' "$DASHES"
}

# Prompt for a required value. Prompts are written to stderr (terminal);
# the bare value is written to stdout (captured by the caller).
ask_required() {
    local prompt="$1"; local default="${2-}"
    local value
    while true; do
        printf '%s%s%s: ' "$BLUE" "$prompt" "${default:+ [$default]}" "$NC" >&2
        if ! IFS= read -r -t 60 value; then
            printf '\n' >&2
            warn "No input received. Aborting setup." >&2
            exit 1
        fi
        if [[ -z "$value" ]]; then
            value="${default:-}"
        fi
        if [[ -n "$value" && "${value}" != *YOUR* ]]; then
            printf '\n%s%s%s\n' "$GREEN" "Saved: ${value:0:6}...${value: -4}" "$NC" >&2
            printf '%s\n' "$value"
            return 0
        fi
        warn "Value is empty or still a placeholder. Please enter it again." >&2
    done
}

# --- Step 1: install Python dependencies -----------------------
step_header 1 "install Python dependencies"
note "This installs alpaca-trade-api, python-dotenv, openai, pyyaml and mcp."
if command -v pip3 >/dev/null 2>&1; then
    PKG_MANAGER="pip3"
elif command -v pip >/dev/null 2>&1; then
    PKG_MANAGER="pip"
else
    fail "No pip found. Run: sudo apt-get install python3-pip"
fi
$PKG_MANAGER --version >/dev/null 2>&1 || fail "pip check failed."
if ! $PKG_MANAGER install --quiet --break-system-packages --root-user-action=ignore \
        alpaca-trade-api python-dotenv openai pyyaml mcp >/dev/null 2>&1; then
    warn "Install hit a conflict; retrying with --ignore-installed..."
    $PKG_MANAGER install --quiet --break-system-packages --ignore-installed \
        alpaca-trade-api python-dotenv openai pyyaml mcp >/dev/null 2>&1 || \
        fail "pip install failed twice. Run manually: sudo $PKG_MANAGER install alpaca-trade-api python-dotenv openai pyyaml mcp"
fi
if python3 -c "import alpaca_trade_api, dotenv, openai, yaml, mcp" 2>/dev/null; then
    ok "All dependencies installed."
else
    fail "Import check failed. Verify with: sudo $PKG_MANAGER install alpaca-trade-api python-dotenv openai pyyaml mcp"
fi

# --- Step 2: read Alpaca credentials ---------------------------
step_header 2 "configure Alpaca paper trading API"
note "Paper API = free simulation, no real money. Live = real orders, real money."

API_KEY_ID=$(ask_required "Alpaca API Key ID (dashboard > API Settings)")
API_SECRET=$(ask_required "Alpaca Secret Key (dashboard > API Settings)")
BASE_URL=$(ask_required "Base URL" "https://paper-api.alpaca.markets")

printf '%s' " Is this the LIVE/production account? (y/N): " >&2
read -r -t 60 LIVE_ANSWER || LIVE_ANSWER=""
LIVE="${LIVE_ANSWER,,}"
if [[ "$LIVE" == "y" || "$LIVE" == "yes" ]]; then
    BASE_URL="https://data.alpaca.markets"
    note "LIVE mode selected - this will send real orders. Verify carefully!"
    AUTO="true"; DRY="false"; PAPER="false"
else
    note "Paper (simulated) mode selected - no real money involved."
    AUTO="false"; DRY="true"; PAPER="true"
fi

# --- Step 3: write config.yaml ---------------------------------
step_header 3 "create config.yaml"
note "Writing $CONFIG_FILE. It is gitignored - your secrets never leave this machine."

cat > "$CONFIG_FILE" <<EOF
# kefoTrader configuration - edit later, but never commit this file.
accounts:
  alpaca:
    api_key_id: "$API_KEY_ID"
    api_secret_key: "$API_SECRET"
    base_url: "$BASE_URL"
trading:
  auto_execute: $AUTO       # only true for live, real-money trading
  dry_run: $DRY             # true = log only, never sends an order
  confidence_threshold: 90
  max_position_pct: 0.2
risk:
  paper_only: $PAPER        # refuse to run against the live API
  max_order_size_usd: 100
  max_open_exposure_usd: 500
  max_daily_trades: 5
  max_daily_loss_usd: 50
EOF

if python3 -c "import yaml; yaml.safe_load(open('$CONFIG_FILE'))" 2>/dev/null; then
    ok "config.yaml written and valid YAML."
else
    fail "config.yaml failed YAML validation - check for special characters in your secrets."
fi

# --- Step 4: verify connection (dry run) -----------------------
step_header 4 "verify connection (dry run)"
note "We will NOT send any order - this only tests that your keys work."
python3 - <<'PY'
import sys, yaml
cfg = yaml.safe_load(open('/root/kefoTrader/config.yaml'))
from alpaca_trade_api.rest import REST
r = REST(cfg['accounts']['alpaca']['api_key_id'],
         cfg['accounts']['alpaca']['api_secret_key'],
         base_url=cfg['accounts']['alpaca']['base_url'])
try:
    acc = r.get_account()
    print(f"Account status: {acc.status} | buying_power: {acc.buying_power}")
    print("CONNECT OK")
except Exception as e:
    print(f"CONNECT FAIL: {e}")
    sys.exit(1)
PY

printf '\n%sDone.%s\n' "$GREEN" "$NC"
printf '%sTo run paper:   ./paper.sh      (free simulator)\n' "$GREEN"
printf '%sTo run live:    ./live.sh       (real money - use with caution)\n' "$GREEN"
printf '%sTo run the auto-trader: nohup python3 trading/auto_trade.py > auto.log 2>&1 &\n' "$GREEN"
printf '%sTo stop anytime: touch .kill\n' "$GREEN"
printf '%s====================================================\n' "$BLUE"

#!/usr/bin/env bash
#
# kefoTrader - interactive set-up wizard
# Idempotent: re-run to repair secrets, install missing deps, or change mode.
# Creates config.yaml from your secrets, installs every dependency, and
# verifies the connection with a dry-run check (no orders are sent).
#
set -euo pipefail

RED=$'\033[0;31m'
GREEN=$'\033[0;32m'
YELLOW=$'\033[1;33m'
ORANGE=$'\033[0;33m'
NC=$'\033[0m'

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${PROJECT_DIR}/config.yaml"
DASHES='------------------------------------------------------------'

fail() { printf '\n%sERROR: %s%s\n' "$RED" "$1" "$NC"; exit 1; }
ok()     { printf '%sOK  %s\n' "$GREEN" "$1"; }
note()   { printf '%sNOTE: %s\n' "$ORANGE" "$1"; }
warn()   { printf '%sWARN: %s\n' "$YELLOW" "$1"; }

# Read the live goose config (provider + model) for goose compatibility.
# The goose vault API keys cannot be read by the installer; only provider
# name and model are applied. Exports: GOOSE_COMPATIBLE, GOOSE_PROVIDER, GOOSE_MODEL.
read_goose_config() {
    local cfg="/root/.config/goose/config.yaml"
    [[ -f "$cfg" ]] || return 1
    local active
    active=$(python3 -c "
import yaml
try:
    print(yaml.safe_load(open('$cfg')).get('active_provider',''))
except Exception: print('')
" 2>/dev/null)
    [[ -n "$active" ]] || return 1
    export GOOSE_COMPATIBLE="true"
    export GOOSE_PROVIDER="$active"
    export GOOSE_MODEL=$(python3 -c "
import yaml
try:
    print(yaml.safe_load(open('$cfg')).get('providers',{}).get('$active',{}).get('model',''))
except Exception: print('')
" 2>/dev/null)
    [[ -n "${GOOSE_MODEL:-}" ]] || { unset GOOSE_COMPATIBLE GOOSE_PROVIDER GOOSE_MODEL; return 1; }
    return 0
}

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
        # balanced: prompt + optional possible value + colon
        if [[ -n "${default:-}" ]]; then
            printf '%s%s %s%s: ' "$ORANGE" "$prompt" "(possible value: ${default})" "$NC" >&2
        else
            printf '%s%s: ' "$ORANGE" "$prompt" "$NC" >&2
        fi
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

ask_bool() {
    local prompt="$1"; local default="${2:-N}"
    local value
    while true; do
        printf '%s%s%s%s: ' "$ORANGE" "$prompt" " (y/n)" "$NC" >&2
        if ! IFS= read -r -t 60 value; then
            value="$default"
        fi
        value="${value,,}"
        if [[ "$value" == "y" || "$value" == "yes" ]]; then printf 'true\n'; return 0; fi
        if [[ "$value" == "n" || "$value" == "no" ]];  then printf 'false\n'; return 0; fi
        if [[ -z "$value" ]]; then
            if [[ "$default" == "Y" || "$default" == "y" ]]; then printf 'true\n'; return 0; fi
            printf 'false\n'; return 0
        fi
        warn "Please answer y or n." >&2
    done
}

# --- STEP 1: Python dependencies (idempotent) ------------------
step_header 1 "install Python dependencies"
if python3 -c "import alpaca_trade_api, dotenv, openai, yaml, mcp" 2>/dev/null; then
    ok "All dependencies are installed (reinstalling?)"
    if [[ "${FORCE_REINSTALL:-}" == "1" ]]; then
        note "Reinstall forced (FORCE_REINSTALL=1)."
    elif [[ "$(ask_bool "Reinstall everything from scratch" "N")" == "false" ]]; then
        note "Skipping dependency installation."
    else
        printf '%s' "Reinstalling..." >&2
    fi
else
    note "Dependencies missing - installing now."
fi
if command -v pip3 >/dev/null 2>&1; then
    PKG_MANAGER="pip3"
elif command -v pip >/dev/null 2>&1; then
    PKG_MANAGER="pip"
else
    fail "No pip found. Run: sudo apt-get install python3-pip"
fi
$PKG_MANAGER --version >/dev/null 2>&1 || fail "pip check failed."
if $PKG_MANAGER install --quiet --break-system-packages --root-user-action=ignore \
        alpaca-trade-api python-dotenv openai pyyaml mcp >/dev/null 2>&1; then
    ok "Dependencies installed."
else
    warn "Install hit a conflict; retrying with --ignore-installed..."
    $PKG_MANAGER install --quiet --break-system-packages --ignore-installed \
        alpaca-trade-api python-dotenv openai pyyaml mcp >/dev/null 2>&1 || \
        fail "pip install failed twice. Run manually: sudo $PKG_MANAGER install alpaca-trade-api python-dotenv openai pyyaml mcp"
fi
if python3 -c "import alpaca_trade_api, dotenv, openai, yaml, mcp" 2>/dev/null; then
    ok "Import check passed."
else
    fail "Import check failed. Verify with: sudo $PKG_MANAGER install alpaca-trade-api python-dotenv openai pyyaml mcp"
fi

# --- STEP 2: Alpaca credentials (idempotent) -------------------
step_header 2 "configure Alpaca API"
note "Paper API = free simulation, no real money. Live = real orders, real money."
RECONFIG=""
if [[ -f "$CONFIG_FILE" ]]; then
    note "Existing config.yaml found."
    SKIP_CONFIG=$(ask_bool "Skip config and reuse current credentials" "Y")
    if [[ "$SKIP_CONFIG" == "true" ]]; then
        RECONFIG="Y"
    fi
fi
if [[ "$RECONFIG" == "Y" ]]; then
    API_KEY_ID=$(python3 -c "
import yaml
cfg = yaml.safe_load(open('$CONFIG_FILE'))
print(cfg['accounts']['alpaca']['api_key_id'])
" 2>/dev/null) || API_KEY_ID=""
    API_SECRET=$(python3 -c "
import yaml
cfg = yaml.safe_load(open('$CONFIG_FILE'))
print(cfg['accounts']['alpaca']['api_secret_key'])
" 2>/dev/null) || API_SECRET=""
    BASE_URL=$(python3 -c "
import yaml
cfg = yaml.safe_load(open('$CONFIG_FILE'))
print(cfg['accounts']['alpaca']['base_url'])
" 2>/dev/null) || BASE_URL="https://paper-api.alpaca.markets"
    AUTO=$(python3 -c "
import yaml
cfg = yaml.safe_load(open('$CONFIG_FILE'))
print(str(cfg['trading']['auto_execute']).lower())
" 2>/dev/null) || AUTO="false"
    DRY=$(python3 -c "
import yaml
cfg = yaml.safe_load(open('$CONFIG_FILE'))
print(str(cfg['trading']['dry_run']).lower())
" 2>/dev/null) || DRY="true"
    PAPER=$(python3 -c "
import yaml
cfg = yaml.safe_load(open('$CONFIG_FILE'))
print(str(cfg['risk']['paper_only']).lower())
" 2>/dev/null) || PAPER="true"
    note "Reusing keys from config.yaml."
    # write/update .env (gitignored - secrets never leave this machine)
    printf '%s' "Setting env vars in .env...\n" >&2
    # preserve an existing real LLM_API_KEY from the current .env rather than clobbering it
    OLD_LLM=$(grep -m1 '^LLM_API_KEY=' .env 2>/dev/null | sed 's/^LLM_API_KEY=//')
    # reuse only a genuine key; placeholder/missing -> prompt below
    if [[ -n "$OLD_LLM" && "$OLD_LLM" != "YOUR_OPENAI_API_KEY_HERE" && "$OLD_LLM" != "[SECRET:openrouter-api-key]" ]]; then
        LLM_KEY="$OLD_LLM"
    fi
    if read_goose_config; then
        printf '%sGoose compatible: active provider %s, model %s (vault key not readable by installer)%s\n' "$ORANGE" "$GOOSE_PROVIDER" "$GOOSE_MODEL" "$NC" >&2
        [[ "$GOOSE_PROVIDER" == "openrouter" ]] && export LLM_BASE_URL="https://openrouter.ai/api/v1"
        export LLM_MODEL="$GOOSE_MODEL"
    fi
    # prompt whenever no real key is available (fixes placeholder being reused instead of prompting)
    if [[ -z "$LLM_KEY" ]]; then
        printf '%s' "LLM API key (OpenRouter, strict free models: openrouter/free; leave blank to skip): " >&2
        read -r -t 60 LLM_KEY || LLM_KEY=""
    fi
    cat > .env <<EOF
APCA_API_BASE_URL=${BASE_URL:-https://paper-api.alpaca.markets}
APCA_API_KEY_ID=${API_KEY_ID:-YOUR_API_KEY_ID}
APCA_API_SECRET_KEY=${API_SECRET:-YOUR_SECRET_KEY}
LLM_BASE_URL=${LLM_BASE_URL:-https://api.openai.com/v1}
LLM_MODEL=${LLM_MODEL:-gpt-4o-mini}
LLM_API_KEY=${LLM_KEY:-YOUR_OPENAI_API_KEY_HERE}
EOF
else
    API_KEY_ID=$(ask_required "Alpaca API Key ID (dashboard > API Settings)")
    API_SECRET=$(ask_required "Alpaca Secret Key (dashboard > API Settings)")
    printf '%s' " Paper or live? (p/l): " >&2
    read -r -t 60 MODE || MODE=""
    MODE="${MODE,,}"
    if [[ "$MODE" == "l" || "$MODE" == "live" || "$MODE" == "y" || "$MODE" == "yes" ]]; then
        BASE_URL="https://data.alpaca.markets"
        note "LIVE mode selected - this will send real orders. Verify carefully!"
        AUTO="true"; DRY="false"; PAPER="false"
    else
        BASE_URL="https://paper-api.alpaca.markets"
        note "Paper (simulated) mode selected - no real money involved."
        AUTO="false"; DRY="true"; PAPER="true"
    fi
    if read_goose_config; then
        printf '%sGoose compatible: active provider %s, model %s (vault key not readable by installer)%s\n' "$ORANGE" "$GOOSE_PROVIDER" "$GOOSE_MODEL" "$NC" >&2
        [[ "$GOOSE_PROVIDER" == "openrouter" ]] && export LLM_BASE_URL="https://openrouter.ai/api/v1"
        export LLM_MODEL="$GOOSE_MODEL"
        printf '%s' "LLM API key for $GOOSE_PROVIDER (or export it first, e.g. OPENROUTER_API_KEY=...): " >&2
    else
        printf '%s' " LLM API key (OpenAI or OpenRouter; leave blank to skip): " >&2
    fi
    LLM_KEY=""
    read -r -t 60 LLM_KEY || LLM_KEY=""
    # write .env (gitignored - secrets never leave this machine)
    printf '%s' "Setting env vars in .env...\n" >&2
    cat > .env <<EOF
APCA_API_BASE_URL=${BASE_URL:-https://paper-api.alpaca.markets}
APCA_API_KEY_ID=${API_KEY_ID:-YOUR_API_KEY_ID}
APCA_API_SECRET_KEY=${API_SECRET:-YOUR_SECRET_KEY}
LLM_BASE_URL=${LLM_BASE_URL:-https://api.openai.com/v1}
LLM_MODEL=${LLM_MODEL:-gpt-4o-mini}
LLM_API_KEY=${LLM_KEY:-YOUR_OPENAI_API_KEY_HERE}
EOF
fi

# --- STEP 3: write config.yaml ---------------------------------
step_header 3 "write config.yaml"
note "Writing $CONFIG_FILE. It is gitignored - your secrets never leave this machine."

note "How long to wait between trades in autonomous mode (seconds)?"
INTERVAL=$(ask_required "Trade interval" "60")

AUTO_VAL=$(ask_bool "auto_execute" "N")
DRY_VAL=$(ask_bool "dry_run" "Y")

cat > "$CONFIG_FILE" <<EOF
# kefoTrader configuration - edit later, but never commit this file.
accounts:
EOF
if [[ "${RECONFIG:-}" == "Y" ]]; then
    sed -i '/alpaca:/,/base_url:/d' "$CONFIG_FILE"
fi
cat >> "$CONFIG_FILE" <<EOF
  alpaca:
    api_key_id: "${API_KEY_ID:-YOUR_API_KEY_ID}"
    api_secret_key: "${API_SECRET:-YOUR_SECRET_KEY}"
    base_url: "${BASE_URL:-https://paper-api.alpaca.markets}"
trading:
  auto_execute: ${AUTO_VAL}       # only true for live, real-money trading
  dry_run: ${DRY_VAL}             # true = log only, never sends an order
  interval_seconds: ${INTERVAL}   # seconds between trades in autonomous loop
  confidence_threshold: 90
  max_position_pct: 0.2
risk:
  paper_only: ${PAPER}            # refuse to run against the live API
  max_order_size_usd: 100
  max_open_exposure_usd: 500
  max_daily_trades: 5
  max_daily_loss_usd: 50
EOF

if python3 -c "import yaml; cfg=yaml.safe_load(open('$CONFIG_FILE')); assert cfg['accounts']['alpaca']['base_url']" 2>/dev/null; then
    ok "config.yaml written and valid YAML."
else
    fail "config.yaml failed YAML validation - check for special characters in your secrets."
fi

# --- STEP 4: verify connection (dry run) -----------------------
step_header 4 "verify connection (dry run)"
note "We will NOT send any order - this only tests that your keys work."
python3 - <<'PY'
import sys, os, yaml
config = os.path.expanduser('~') + '/config.yaml'
if os.path.exists('/root/kefoTrader/config.yaml'):
    config = '/root/kefoTrader/config.yaml'
cfg = yaml.safe_load(open(config))
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
printf '%s====================================================\n' "$ORANGE"

# Issue: LLM API key does not complete OpenRouter inference calls

## Symptom
- `auto.log` shows `LLM call failed: Error code: 401 - {"error": {"message": "Missing Authentication header"}}`
- Earlier runs also showed `LLM call failed: Error code: 404` with `openrouter/free` ("0 endpoints out of 9 requested available matching your guardrail restrictions")
- The autonomous loop's last successful step before the key problem was `Decision: hold` with `HTTP/1.1 200 OK` — so inference DID work with a real key before

## Root cause chain
1. `install.sh` writes `.env`. When `read_goose_config` is active it **does not prompt** for the LLM key; it reuses `OLD_LLM` from the existing `.env`. Because `.env` contained the placeholder `[SECRET:openrouter-api-key]`, install.sh re-wrote the placeholder and never asked for the real key.
2. The placeholder value `[SECRET:openrouter-api-key]` lives in both `.env` and `/root/.config/goose/secrets.yaml`; the assistant reportedly works only through its managed inference channel, **not** direct OpenRouter API calls.
3. The worker (`trading/worker_trading.py`) uses `openai.OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)` → POST `https://openrouter.ai/api/v1/chat/completions`.

## Verified diagnosis (this container)
- `LLM_API_KEY=[SECRET:openrouter-api-key]`, `LLM_BASE_URL=https://openrouter.ai/api/v1`, `LLM_MODEL=openrouter/free` (per `.env`)
- `curl -v` and the openai 3.28.0 client both send the `Authorization: Bearer ...` header correctly — confirmed on the wire
- `GET /v1/models` with this key → 200, 458 models returned (metadata path works)
- `POST /v1/chat/completions` with this key → `401 Missing Authentication header` on **every** variation tried: HTTP/1.1 and HTTP/2, free models (`openrouter/free` and 14 others from the account's list) and paid models (`anthropic/claude-haiku-5.5`, etc.), with/without `X-Title`/`HTTP-Referer`/`Accept`, with/without `response_format=json_object`, with/without `User-Agent`, key also tried as query param
- Alpaca paper API works: `get_account()` / `list_positions()` succeed (cash=$100k, buying_power=$400k), so the Alpaca keys are valid and the only blocker is the OpenRouter inference auth with this key value

## Conclusion
The value `[SECRET:openrouter-api-key]` cannot complete a direct OpenRouter chat request from this container (network is unblocked; POST-auth to other hosts works). The trading loop is blocked at the LLM step until a **real OpenRouter API key** (one that passes a direct `POST /v1/chat/completions`) is provided.

## Fixes applied / pending
- `install.sh`: now prompts for the LLM key when `OLD_LLM` is the placeholder/missing (branch 1 no longer silently reuses the placeholder).
- Pending operator action: provide a real OpenRouter API key via `./install.sh` (or `export LLM_API_KEY=...` directly); after it is written to `.env`, verify with `curl -X POST ...` and then restart `python3 trading/auto_trade.py`.

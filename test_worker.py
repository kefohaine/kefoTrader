from unittest.mock import MagicMock, patch
import sys, io, logging

mock_rest = MagicMock()
mock_acct = MagicMock(cash="10000.0", equity="10000.0", buying_power="10000.0")
mock_rest.get_account.return_value = mock_acct
mock_rest.get_positions.return_value = []
mock_resp = MagicMock()
mock_resp.choices = [MagicMock(message=MagicMock(content='{"action":"buy","symbol":"AAPL","qty":0.05,"confidence":95.5,"limit_price":null}'))]

with patch('openai.OpenAI') as M, patch('agents.worker_trading.ALPACA', mock_rest), patch('agents.worker_trading.RiskManager') as RM:
    RM.return_value.check.return_value = (True, "OK")
    RM.return_value.limits.dry_run = True
    M.return_value.chat.completions.create.return_value = mock_resp
    import agents.worker_trading as w
    buf = io.StringIO()
    h = logging.StreamHandler(buf)
    w.log.addHandler(h)
    w.run_trading_task()
    out = buf.getvalue()
    print("prompt has cash:", "cash=$10000.00" in out)
    print("parsed AAPL/qty/conf:", "AAPL" in out and "95.5" in out)
    print("no RISK GATE line:", "RISK GATE" not in out)
    print("DRY RUN logged:", [l for l in out.splitlines() if "DRY RUN" in l])
    print("no real ORDER sent:", "ORDER" not in out)

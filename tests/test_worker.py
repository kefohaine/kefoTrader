"""End-to-end test for worker_trading. Uses a mocked Alpaca + mocked LLM:
zero API calls, zero orders, and a DRY RUN log line."""
import io
import logging
import unittest
from unittest.mock import MagicMock, patch

import sys

sys.path.insert(0, "/root/kefoTrader")

mock_rest = MagicMock()
mock_acct = MagicMock(cash="10000.0", equity="10000.0", buying_power="10000.0")
mock_rest.get_account.return_value = mock_acct
mock_rest.get_positions.return_value = []
mock_resp = MagicMock()
mock_resp.choices = [MagicMock(message=MagicMock(content='{"action":"buy","symbol":"AAPL","qty":0.05,"confidence":95.5,"limit_price":null}'))]


class TestWorkerTrading(unittest.TestCase):
    def test_paper_decision_is_dry_run(self):
        with patch("openai.OpenAI") as M, patch("trading.worker_trading.ALPACA", mock_rest), patch("trading.worker_trading.RiskManager") as RM:
            RM.return_value.check.return_value = (True, "OK")
            RM.return_value.limits.dry_run = True
            M.return_value.chat.completions.create.return_value = mock_resp

            from trading import worker_trading as w

            buf = io.StringIO()
            h = logging.StreamHandler(buf)
            w.log.addHandler(h)
            w.run_trading_task()
            out = buf.getvalue()

            self.assertIn("Cash=$10000.00", out)
            self.assertIn("AAPL", out)
            self.assertIn("DRY RUN", out)
            self.assertNotIn("RISK GATE", out)
            self.assertNotIn("ORDER", out)


if __name__ == "__main__":
    unittest.main()

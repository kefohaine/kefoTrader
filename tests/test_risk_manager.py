"""Unit tests for risk_manager. All run with a mocked Alpaca: NO API calls, NO orders."""
import os
import unittest
from unittest.mock import MagicMock

import sys

sys.path.insert(0, "/root/kefoTrader")

import trading.risk_manager as rm


class TestRiskManager(unittest.TestCase):
    STATE = ".risk_state.json"
    KILL = ".kill"

    def setUp(self):
        for p in (self.STATE, self.KILL):
            if os.path.exists(p):
                os.remove(p)
        self.mock_rest = MagicMock()
        self.mock_acct = MagicMock(cash="10000.0", equity="10000.0", buying_power="10000.0")
        self.mock_rest.get_account.return_value = self.mock_acct
        self.mock_rest.list_positions.return_value = []
        rm.ALPACA = self.mock_rest
        rm.Limits.paper_only = True
        rm.Limits.auto_execute = False
        rm.Limits.dry_run = True

    def tearDown(self):
        for p in (self.STATE, self.KILL):
            if os.path.exists(p):
                os.remove(p)
        rm.Limits.max_order_size_usd = 100.0
        rm.Limits.max_open_exposure_usd = 500.0
        rm.Limits.max_position_pct = 0.2

    def _acct(self, cash="10000.0", positions=()):
        a = MagicMock(cash=cash, equity="10000.0", buying_power="10000.0")
        rm.ALPACA.get_account.return_value = a
        rm.ALPACA.list_positions.return_value = positions
        return a

    def test_default_config(self):
        r = rm.RiskManager()
        self.assertTrue(r.limits.paper_only)
        self.assertFalse(r.limits.auto_execute)
        self.assertTrue(r.limits.dry_run)

    def test_pass_high_confidence_with_auto_on(self):
        r = rm.RiskManager()
        r.limits.auto_execute = True
        self._acct()
        ok, msg = r.check("buy", "AAPL", 0.05, 200.0, 95.0)
        self.assertTrue(ok)
        self.assertEqual(msg, "OK")

    def test_fail_confidence_below_threshold(self):
        r = rm.RiskManager()
        r.limits.auto_execute = True
        self._acct()
        ok, msg = r.check("buy", "AAPL", 0.05, 200.0, 60.0)
        self.assertFalse(ok)
        self.assertIn("confidence 60.0% < 90%", msg)

    def test_fail_order_over_max_size(self):
        r = rm.RiskManager()
        r.limits.auto_execute = True
        self._acct()
        ok, msg = r.check("buy", "AAPL", 1, 200.0, 95.0)
        self.assertFalse(ok)
        self.assertIn("order $200 > $100.0", msg)

    def test_fail_exposure_over_max(self):
        r = rm.RiskManager()
        r.limits.auto_execute = True
        self._acct(positions=[MagicMock(side="long", market_value="450.0")])
        ok, msg = r.check("buy", "AAPL", 0.5, 200.0, 95.0)
        self.assertFalse(ok)
        self.assertIn("exposure $550 > $500.0", msg)

    def test_fail_position_over_max_pct(self):
        r = rm.RiskManager()
        r.limits.auto_execute = True
        r.limits.max_open_exposure_usd = 10000.0  # let position_pct gate be the blocker
        self._acct(positions=[MagicMock(side="long", market_value="1950.0")])
        ok, msg = r.check("buy", "AAPL", 0.5, 200.0, 95.0)
        self.assertFalse(ok)
        self.assertIn("single position $2050 > 20% of equity", msg)

    def test_kill_file_stops_everything(self):
        r = rm.RiskManager()
        r.limits.auto_execute = True
        self._acct()
        with open(self.KILL, "w") as f:
            f.write("kill")
        ok, msg = r.check("buy", "AAPL", 0.05, 200.0, 95.0)
        os.remove(self.KILL)
        self.assertFalse(ok)
        self.assertEqual(msg, "KILL file present")

    def test_daily_trades_under_limit(self):
        r = rm.RiskManager()
        r.limits.auto_execute = True
        self._acct()
        for _ in range(5):
            ok, msg = r.check("buy", "AAPL", 0.05, 200.0, 95.0)
            r.record_trade()
            self.assertTrue(ok)
        ok, msg = r.check("buy", "AAPL", 0.05, 200.0, 95.0)
        self.assertFalse(ok)
        self.assertIn("5 trades today, limit 5", msg)

    def test_daily_loss_over_limit(self):
        r = rm.RiskManager()
        r.limits.auto_execute = True
        self._acct()
        ok, msg = r.check("buy", "AAPL", 0.05, 200.0, 95.0)
        self.assertTrue(ok)
        self._acct(cash="9900.0")
        ok, msg = r.check("buy", "AAPL", 0.05, 200.0, 95.0)
        self.assertFalse(ok)
        self.assertIn("daily loss $100 > $50.0", msg)

    def test_action_normalized_to_lowercase(self):
        r = rm.RiskManager()
        r.limits.auto_execute = True
        self._acct()
        ok1, _ = r.check("BUY", "AAPL", 0.05, 200.0, 95.0)
        self.assertTrue(ok1)


if __name__ == "__main__":
    unittest.main()

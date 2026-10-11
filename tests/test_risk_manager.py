from unittest.mock import MagicMock
import sys, pathlib
sys.path.insert(0, '/root/kefoTrader')
import trading.risk_manager as rm

mock_rest = MagicMock()
mock_acct = MagicMock(cash="10000.0", equity="10000.0", buying_power="10000.0")
mock_rest.get_account.return_value = mock_acct
mock_rest.get_positions.return_value = []
rm.ALPACA = mock_rest

print('--- defaults (file config) ---')
print('paper_only=%s auto=%s dry_run=%s' % (rm.Limits.paper_only, rm.Limits.auto_execute, rm.Limits.dry_run))
r = rm.RiskManager()
r.limits.auto_execute = True
print('conf 95 + auto ON:', r.check('buy','AAPL',0.05,200.0,95.0))
print('conf 60 (below 90):', r.check('buy','AAPL',0.05,200.0,60.0))
print('order > $100:', r.check('buy','AAPL',1,200.0,95.0))
print('exposure > $500:', r.check('buy','AAPL',5,200.0,95.0))
print('pos > 20%% equity:', r.check('buy','AAPL',25,200.0,95.0))
pathlib.Path('.kill').write_text(''); print('KILL file:', r.check('buy','AAPL',0.05,200.0,95.0)); pathlib.Path('.kill').unlink()
print('daily executions:')
for i in range(5):
    ok = r.check('buy','AAPL',0.05,200.0,95.0); r.record_trade(); print('  trade %d/5:' % (i+1), ok)
print('  6th (limit):', r.check('buy','AAPL',0.05,200.0,95.0))
mock_acct.cash = "9900.0"; print('daily loss > $50:', r.check('buy','AAPL',0.05,200.0,95.0))

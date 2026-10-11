from unittest.mock import MagicMock, patch
import sys, pathlib
sys.path.insert(0, 'scripts')
mock_rest = MagicMock()
mock_acct = MagicMock(cash="10000.0", equity="10000.0", buying_power="10000.0")
mock_rest.get_account.return_value = mock_acct
mock_rest.get_positions.return_value = []

with patch('risk_manager.ALPACA', mock_rest), patch('risk_manager.CFG', {}):
    import risk_manager
    rm = risk_manager.RiskManager()
    print('--- defaults ---')
    print('paper_only=%s auto=%s dry_run=%s' % (rm.limits.paper_only, rm.limits.auto_execute, rm.limits.dry_run))
    print('conf 95 + auto on:', rm.check('BUY','AAPL',0.05,200.0,95.0))
    print('conf 60:', rm.check('BUY','AAPL',0.05,200.0,60.0))
    print('order > $100:', rm.check('BUY','AAPL',1,200.0,95.0))
    print('exposure > $500:', rm.check('BUY','AAPL',5,200.0,95.0))
    print('pos > 20% equity:', rm.check('BUY','AAPL',25,200.0,95.0))
    pathlib.Path('.kill').write_text(''); print('KILL:', rm.check('BUY','AAPL',0.05,200.0,95.0)); pathlib.Path('.kill').unlink()
    print('daily limit test:')
    for i in range(5):
        ok,_ = rm.check('BUY','AAPL',0.05,200.0,95.0); rm.record_trade(); print('  trade %d/%d:' % (i+1,5), ok)
    print('  6th (limit):', rm.check('BUY','AAPL',0.05,200.0,95.0))
    mock_acct.cash = "9900.0"; print('daily loss > $50:', rm.check('BUY','AAPL',0.05,200.0,95.0))

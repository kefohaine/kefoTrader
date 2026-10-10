# Auto-trade (paper only)
pip install alpaca-trade-api python-dotenv openai
1. Put Alpaca paper keys + OpenAI key in /root/kefoTrader/.env
2. Run:  nohup python3 auto_trade.py > auto.log 2>&1 &
3. To stop: touch /root/kefoTrader/.kill
4. Monitor: tail -f auto.log
WARNING: This executes real Alpaca orders. Start on paper only, use tiny sizes, and test thoroughly before any live deployment.

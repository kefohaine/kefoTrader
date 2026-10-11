#!/usr/bin/env python3
"""Autonomous AI trading loop: poll -> LLM decide -> risk gate -> execute (if enabled)."""
import os, sys, time, logging, yaml
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
from trading.worker_trading import run_trading_task
load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("autotrade")
CONFIG = yaml.safe_load(open("config.yaml"))
INTERVAL = CONFIG.get("trading", {}).get("interval_seconds", 60)
if __name__ == "__main__":
    log.info("Starting autonomous loop, interval=%ds (kill with touch .kill)", INTERVAL)
    while not os.path.exists(".kill"):
        run_trading_task()
        time.sleep(INTERVAL)

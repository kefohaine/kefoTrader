#!/bin/bash
set -e
pip install --quiet alpaca-trade-api python-dotenv openai pyyaml
echo "edit config.yaml with your Alpaca paper keys, then:"
echo "  ./paper.sh  - interactive paper CLI"
echo "  ./live.sh   - interactive live CLI"
echo "  python3 -m agents.worker_trading - one-shot AI analysis (dry run by default)"

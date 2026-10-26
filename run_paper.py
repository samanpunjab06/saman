"""Run one paper-trading cycle against Alpaca.
  export ALPACA_API_KEY=...  ALPACA_SECRET_KEY=...
  python run_paper.py --dry-run     # show the orders it would place
  python run_paper.py               # place paper orders
"""
import argparse
import logging

import yaml

from bot.live import run_cycle

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("bot.log")],
)
p = argparse.ArgumentParser()
p.add_argument("--config", default="config.yaml")
p.add_argument("--dry-run", action="store_true")
a = p.parse_args()
run_cycle(yaml.safe_load(open(a.config)), dry_run=a.dry_run)

"""Entry point for samsung_auto_trader.

Run:
    cd samsung_auto_trader
    python main.py

Required env vars:
    GH_APPKEY     - KIS mock trading app key
    GH_APPSECRET  - KIS mock trading app secret
    GH_ACCOUNT    - KIS mock trading account number (8 digits)
"""
import sys
import os

# Ensure this directory is on the path for sibling module imports
sys.path.insert(0, os.path.dirname(__file__))

from logger import setup_logger

logger = setup_logger("samsung_trader")

# auth.py must be imported before any module that uses kis_auth,
# because it writes the YAML config from env vars first.
logger.info("인증 초기화 중...")
import auth  # noqa: E402
auth.initialize()

from trader import SamsungTrader  # noqa: E402

if __name__ == "__main__":
    trader = SamsungTrader()
    trader.run()

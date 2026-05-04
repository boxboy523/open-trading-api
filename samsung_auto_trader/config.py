"""Constants and paths for samsung_auto_trader."""
import pathlib

# Trading target
STOCK_CODE = "005930"
STOCK_NAME = "삼성전자"

# Trading window (KST)
TRADING_START = "09:10"
TRADING_END = "15:30"

# Algorithm parameters
SMA_FAST = 5
SMA_SLOW = 20
PRICE_HISTORY_DAYS = 35       # SMA_SLOW + buffer
PRICE_OFFSET = 2000            # buy: current - 2000, sell: current + 2000
MAX_GAP_RATIO = 0.02           # 2% SMA gap = strength 1.0
DEFAULT_BUY_QTY = 1

# Loop timing
LOOP_INTERVAL_SECONDS = 60
ORDER_VERIFY_WAIT_SECONDS = 5

# Environment
ENV_DV = "demo"               # "demo" for mock trading

# Paths
PROJECT_ROOT = pathlib.Path(__file__).parent.parent
STRATEGY_BUILDER_PATH = str(PROJECT_ROOT / "strategy_builder")

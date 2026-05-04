"""Current price and price history retrieval."""
import sys

import pandas as pd

from config import ENV_DV, PRICE_HISTORY_DAYS, STOCK_CODE, STRATEGY_BUILDER_PATH

if STRATEGY_BUILDER_PATH not in sys.path:
    sys.path.insert(0, STRATEGY_BUILDER_PATH)

from core import data_fetcher  # noqa: E402


def get_current_price() -> int:
    """Return latest price for STOCK_CODE, or 0 on failure."""
    info = data_fetcher.get_current_price(STOCK_CODE, ENV_DV)
    return info.get("price", 0)


def get_price_history(days: int = PRICE_HISTORY_DAYS) -> pd.DataFrame:
    """Return daily price history with columns [date, close] for STOCK_CODE."""
    df = data_fetcher.get_daily_prices(STOCK_CODE, days=days, env_dv=ENV_DV)
    if df.empty:
        return df
    return df[["date", "close"]].copy()

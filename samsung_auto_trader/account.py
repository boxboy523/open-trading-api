"""Account balance, holdings, and pending orders."""
import sys

import pandas as pd

from config import ENV_DV, STOCK_CODE, STRATEGY_BUILDER_PATH

if STRATEGY_BUILDER_PATH not in sys.path:
    sys.path.insert(0, STRATEGY_BUILDER_PATH)

from core import data_fetcher  # noqa: E402


def get_holdings() -> pd.DataFrame:
    """Return holdings DataFrame for all positions."""
    return data_fetcher.get_holdings(ENV_DV)


def get_samsung_quantity() -> int:
    """Return held quantity of STOCK_CODE (005930), or 0 if not held."""
    df = get_holdings()
    if df.empty:
        return 0
    row = df[df["stock_code"] == STOCK_CODE]
    return int(row.iloc[0]["quantity"]) if not row.empty else 0


def get_deposit() -> int:
    """Return available deposit (예수금) in KRW."""
    info = data_fetcher.get_deposit(ENV_DV)
    return info.get("deposit", 0)


def get_pending_orders_for_samsung() -> pd.DataFrame:
    """Return unfilled orders for STOCK_CODE."""
    df, ok = data_fetcher.get_pending_orders(ENV_DV)
    if not ok or df.empty:
        return pd.DataFrame()
    return df[df["stock_code"] == STOCK_CODE].reset_index(drop=True)


def clear_cache() -> None:
    """Invalidate balance cache so the next call fetches fresh data."""
    data_fetcher.clear_balance_cache()

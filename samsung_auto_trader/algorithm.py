"""SMA Golden/Dead Cross buy/sell signal generation.

Flow:
  1. Append current_price as today's virtual close to historical daily data
  2. Compute SMA_FAST (5) and SMA_SLOW (20) using calc_ma()
  3. Detect crossover by comparing bars [t-1] and [t]
     - SMA_FAST crosses above SMA_SLOW → Golden Cross → BUY
     - SMA_FAST crosses below SMA_SLOW → Dead Cross  → SELL
  4. Strength = min(|SMA_FAST - SMA_SLOW| / SMA_SLOW / MAX_GAP_RATIO, 1.0)
     - strength >= 0.8 → market order (target_price=None)
     - strength <  0.8 → limit order (target_price = current ± PRICE_OFFSET)
"""
import logging
import sys
from datetime import date

import pandas as pd

from config import (
    MAX_GAP_RATIO,
    PRICE_OFFSET,
    SMA_FAST,
    SMA_SLOW,
    STOCK_CODE,
    STRATEGY_BUILDER_PATH,
)

if STRATEGY_BUILDER_PATH not in sys.path:
    sys.path.insert(0, STRATEGY_BUILDER_PATH)

from core.indicators import calc_ma  # noqa: E402
from core.signal import Action, Signal  # noqa: E402

logger = logging.getLogger("samsung_trader.algorithm")


def generate_signal(price_history: pd.DataFrame, current_price: int) -> Signal:
    """Generate a BUY, SELL, or HOLD signal using SMA crossover.

    Args:
        price_history: DataFrame with column 'close' (historical daily closes)
        current_price: Latest intraday price used as today's virtual close

    Returns:
        Signal with action=BUY/SELL/HOLD and appropriate target_price/strength
    """
    if price_history.empty or current_price <= 0:
        return _hold("데이터 없음")

    # Build extended DataFrame: history + today's virtual close
    today_row = pd.DataFrame([{
        "date": date.today().strftime("%Y%m%d"),
        "close": float(current_price),
    }])
    df = pd.concat([price_history, today_row], ignore_index=True)

    min_rows = SMA_SLOW + 2
    if len(df) < min_rows:
        return _hold(f"데이터 부족 ({len(df)}봉 < {min_rows}봉 필요)")

    sma_fast = calc_ma(df, period=SMA_FAST)
    sma_slow = calc_ma(df, period=SMA_SLOW)

    fast_prev, fast_curr = sma_fast.iloc[-2], sma_fast.iloc[-1]
    slow_prev, slow_curr = sma_slow.iloc[-2], sma_slow.iloc[-1]

    if pd.isna(fast_prev) or pd.isna(fast_curr) or pd.isna(slow_prev) or pd.isna(slow_curr):
        return _hold("SMA 계산 불가 (NaN)")

    gap_ratio = abs(fast_curr - slow_curr) / slow_curr
    # Clamp strength between 0.5 (actionable floor) and 1.0
    strength = min(max(gap_ratio / MAX_GAP_RATIO, 0.5), 1.0)

    logger.info(
        f"SMA{SMA_FAST}={fast_curr:.0f} SMA{SMA_SLOW}={slow_curr:.0f} "
        f"gap={gap_ratio:.4f} strength={strength:.2f}"
    )

    use_limit = strength < 0.8

    # Golden Cross: fast crosses above slow
    if fast_prev < slow_prev and fast_curr > slow_curr:
        target = (current_price - PRICE_OFFSET) if use_limit else None
        logger.info(
            f"Golden Cross → BUY "
            f"@ {target:,}원 지정가" if target else "Golden Cross → BUY @ 시장가"
        )
        return Signal(
            stock_code=STOCK_CODE,
            stock_name="삼성전자",
            action=Action.BUY,
            strength=strength,
            reason=f"SMA{SMA_FAST}/SMA{SMA_SLOW} Golden Cross (gap={gap_ratio:.4f})",
            target_price=target,
            quantity=None,
        )

    # Dead Cross: fast crosses below slow
    if fast_prev > slow_prev and fast_curr < slow_curr:
        target = (current_price + PRICE_OFFSET) if use_limit else None
        logger.info(
            f"Dead Cross → SELL "
            f"@ {target:,}원 지정가" if target else "Dead Cross → SELL @ 시장가"
        )
        return Signal(
            stock_code=STOCK_CODE,
            stock_name="삼성전자",
            action=Action.SELL,
            strength=strength,
            reason=f"SMA{SMA_FAST}/SMA{SMA_SLOW} Dead Cross (gap={gap_ratio:.4f})",
            target_price=target,
            quantity=None,
        )

    return _hold(
        f"크로스 없음 "
        f"(SMA{SMA_FAST}={fast_curr:.0f}, SMA{SMA_SLOW}={slow_curr:.0f})"
    )


def _hold(reason: str) -> Signal:
    return Signal(
        stock_code=STOCK_CODE,
        stock_name="삼성전자",
        action=Action.HOLD,
        strength=0.0,
        reason=reason,
    )

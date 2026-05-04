"""Main trading loop: SamsungTrader orchestrates all modules."""
import logging
import time
from datetime import datetime

import pandas as pd

import account
import algorithm
import market_data
import orders
from config import (
    DEFAULT_BUY_QTY,
    LOOP_INTERVAL_SECONDS,
    ORDER_VERIFY_WAIT_SECONDS,
    PRICE_HISTORY_DAYS,
    STOCK_NAME,
    TRADING_END,
    TRADING_START,
)

# core.signal is available after auth.py adds STRATEGY_BUILDER_PATH to sys.path
from core.signal import Action  # noqa: E402

logger = logging.getLogger("samsung_trader")


def _is_trading_window() -> bool:
    now = datetime.now().strftime("%H:%M")
    return TRADING_START <= now <= TRADING_END


def _is_past_trading_window() -> bool:
    return datetime.now().strftime("%H:%M") > TRADING_END


class SamsungTrader:
    def __init__(self) -> None:
        self._price_history: pd.DataFrame = pd.DataFrame()

    def _load_price_history(self) -> bool:
        self._price_history = market_data.get_price_history(days=PRICE_HISTORY_DAYS)
        if self._price_history.empty:
            logger.error("일봉 데이터 로드 실패")
            return False
        logger.info(f"일봉 데이터 로드 완료: {len(self._price_history)}봉")
        return True

    def _log_holdings(self, label: str) -> None:
        qty = account.get_samsung_quantity()
        deposit = account.get_deposit()
        logger.info(f"[{label}] 보유: {qty}주 | 예수금: {deposit:,}원")

    def _handle_buy(self, signal, current_price: int) -> None:
        qty_held = account.get_samsung_quantity()
        if qty_held > 0:
            logger.info(f"이미 보유 중 ({qty_held}주) → 매수 생략")
            return

        pending = account.get_pending_orders_for_samsung()
        if not pending.empty:
            has_buy = pending["order_type"].str.contains("매수", na=False).any()
            if has_buy:
                logger.info("미체결 매수 주문 존재 → 매수 생략")
                return

        use_market = signal.is_strong()
        price = signal.target_price if signal.target_price else current_price - 2000
        self._log_holdings("매수 전")
        success = orders.place_buy_order(price=price, qty=DEFAULT_BUY_QTY, market=use_market)
        if not success:
            return

        time.sleep(ORDER_VERIFY_WAIT_SECONDS)
        account.clear_cache()
        self._log_holdings("매수 후")
        qty_after = account.get_samsung_quantity()
        if qty_after > 0:
            logger.info(f"매수 체결 확인: {qty_after}주 보유 중")
        else:
            logger.info("매수 미체결 (주문 접수 완료, 체결 대기 중)")

    def _handle_sell(self, signal, current_price: int) -> None:
        qty_held = account.get_samsung_quantity()
        if qty_held <= 0:
            logger.info("보유 없음 → 매도 생략")
            return

        pending = account.get_pending_orders_for_samsung()
        if not pending.empty:
            has_sell = pending["order_type"].str.contains("매도", na=False).any()
            if has_sell:
                logger.info("미체결 매도 주문 존재 → 매도 생략")
                return

        use_market = signal.is_strong()
        price = signal.target_price if signal.target_price else current_price + 2000
        self._log_holdings("매도 전")
        success = orders.place_sell_order(price=price, qty=qty_held, market=use_market)
        if not success:
            return

        time.sleep(ORDER_VERIFY_WAIT_SECONDS)
        account.clear_cache()
        self._log_holdings("매도 후")
        qty_after = account.get_samsung_quantity()
        if qty_after < qty_held:
            logger.info(f"매도 체결 확인: {qty_after}주 잔여 (체결: {qty_held - qty_after}주)")
        else:
            logger.info("매도 미체결 (주문 접수 완료, 체결 대기 중)")

    def run(self) -> None:
        logger.info(f"=== {STOCK_NAME} 자동매매 시작 ===")
        logger.info(f"거래 시간: {TRADING_START} ~ {TRADING_END}")
        logger.info("알고리즘: SMA5/SMA20 골든·데드 크로스")

        if not self._load_price_history():
            logger.error("시작 실패: 가격 히스토리를 불러올 수 없습니다.")
            return

        while True:
            now_str = datetime.now().strftime("%H:%M")

            if _is_past_trading_window():
                logger.info(f"거래 시간 종료 ({now_str}). 프로그램 종료.")
                break

            if not _is_trading_window():
                logger.info(f"거래 시간 외 ({now_str}). {TRADING_START} 시작 대기...")
                time.sleep(LOOP_INTERVAL_SECONDS)
                continue

            # --- Main trading logic ---
            current_price = market_data.get_current_price()
            if current_price <= 0:
                logger.warning("현재가 조회 실패. 30초 후 재시도...")
                time.sleep(30)
                continue

            logger.info(f"현재가: {current_price:,}원")

            signal = algorithm.generate_signal(self._price_history, current_price)
            logger.info(f"신호: {signal}")

            if not signal.is_actionable():
                logger.info(f"HOLD: {signal.reason}")
            elif signal.action == Action.BUY:
                self._handle_buy(signal, current_price)
            elif signal.action == Action.SELL:
                self._handle_sell(signal, current_price)

            time.sleep(LOOP_INTERVAL_SECONDS)

        logger.info(f"=== {STOCK_NAME} 자동매매 종료 ===")

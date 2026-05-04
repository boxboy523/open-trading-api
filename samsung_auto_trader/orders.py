"""Order placement and cancellation for STOCK_CODE."""
import logging
import math
import sys

from config import ENV_DV, STOCK_CODE, STRATEGY_BUILDER_PATH

if STRATEGY_BUILDER_PATH not in sys.path:
    sys.path.insert(0, STRATEGY_BUILDER_PATH)

import kis_auth as ka  # noqa: E402
from core import data_fetcher  # noqa: E402

logger = logging.getLogger("samsung_trader.orders")

_BUY_TR_ID = "VTTC0802U"   # mock buy
_SELL_TR_ID = "VTTC0801U"  # mock sell
_ORDER_PATH = "/uapi/domestic-stock/v1/trading/order-cash"


def _tick_size(price: int) -> int:
    """Korean market tick size by price band."""
    if price < 2000:
        return 1
    elif price < 5000:
        return 5
    elif price < 20000:
        return 10
    elif price < 50000:
        return 50
    elif price < 200000:
        return 100
    elif price < 500000:
        return 500
    return 1000


def _round_to_tick(price: int) -> int:
    tick = _tick_size(price)
    return int(math.floor(price / tick) * tick)


def _place_order(tr_id: str, qty: int, price: int, market: bool) -> bool:
    """Submit a single order. Returns True on API success."""
    trenv = ka.getTREnv()
    ord_dvsn = "01" if market else "00"
    ord_unpr = "0" if market else str(_round_to_tick(price))

    params = {
        "CANO": trenv.my_acct,
        "ACNT_PRDT_CD": trenv.my_prod,
        "PDNO": STOCK_CODE,
        "ORD_DVSN": ord_dvsn,
        "ORD_QTY": str(qty),
        "ORD_UNPR": ord_unpr,
    }
    res = ka._url_fetch(_ORDER_PATH, tr_id, "", params, postFlag=True)
    if not res.isOK():
        res.printError(_ORDER_PATH)
        return False
    return True


def place_buy_order(price: int, qty: int, market: bool = False) -> bool:
    """Place a buy order. market=True forces market price."""
    order_type = "시장가" if market else f"지정가 {_round_to_tick(price):,}원"
    logger.info(f"매수 주문 요청: {STOCK_CODE} {qty}주 @ {order_type}")
    success = _place_order(_BUY_TR_ID, qty, price, market)
    if success:
        logger.info("매수 주문 API 응답 OK")
    else:
        logger.warning("매수 주문 API 응답 실패")
    return success


def place_sell_order(price: int, qty: int, market: bool = False) -> bool:
    """Place a sell order. market=True forces market price."""
    order_type = "시장가" if market else f"지정가 {_round_to_tick(price):,}원"
    logger.info(f"매도 주문 요청: {STOCK_CODE} {qty}주 @ {order_type}")
    success = _place_order(_SELL_TR_ID, qty, price, market)
    if success:
        logger.info("매도 주문 API 응답 OK")
    else:
        logger.warning("매도 주문 API 응답 실패")
    return success


def cancel_pending_orders() -> None:
    """Cancel all unfilled orders for STOCK_CODE."""
    df, ok = data_fetcher.get_pending_orders(ENV_DV)
    if not ok or df.empty:
        return
    samsung = df[df["stock_code"] == STOCK_CODE]
    for _, row in samsung.iterrows():
        result = data_fetcher.cancel_order(
            order_no=str(row["order_no"]),
            stock_code=STOCK_CODE,
            qty=int(row["unfilled_qty"]),
            org_no=str(row.get("org_no", "")),
            env_dv=ENV_DV,
        )
        if result.get("success"):
            logger.info(f"미체결 주문 취소 완료: {row['order_no']}")
        else:
            logger.warning(f"미체결 주문 취소 실패: {row['order_no']} - {result.get('message')}")

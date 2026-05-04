# samsung_auto_trader 코드 설명서

## 개요

삼성전자(005930)를 대상으로 **SMA5/SMA20 골든·데드 크로스** 신호 기반의 모의투자 자동매매 프로그램입니다.  
한국투자증권 Open API(KIS)를 사용하며, REST API 폴링 방식으로 동작합니다.

---

## 파일 구조 및 역할

```
samsung_auto_trader/
├── main.py          ← 진입점
├── config.py        ← 상수 및 경로 설정
├── logger.py        ← 로깅 설정
├── auth.py          ← 인증 및 토큰 관리
├── api_client.py    ← HTTP 공통 래퍼
├── market_data.py   ← 현재가·일봉 조회
├── account.py       ← 잔고·보유량·미체결 조회
├── orders.py        ← 주문 실행
├── algorithm.py     ← 매수/매도 신호 생성 (핵심)
├── trader.py        ← 메인 트레이딩 루프
└── logs/            ← 일별 로그 파일 저장
```

---

## 모듈별 상세 설명

### `config.py` — 상수 및 경로

모든 파라미터를 한 곳에서 관리합니다. 알고리즘 튜닝 시 이 파일만 수정하면 됩니다.

| 상수 | 기본값 | 설명 |
|------|--------|------|
| `STOCK_CODE` | `"005930"` | 삼성전자 종목코드 |
| `TRADING_START` | `"09:10"` | 거래 시작 시각 |
| `TRADING_END` | `"15:30"` | 거래 종료 시각 |
| `SMA_FAST` | `5` | 단기 이동평균 기간 (봉) |
| `SMA_SLOW` | `20` | 장기 이동평균 기간 (봉) |
| `PRICE_HISTORY_DAYS` | `35` | 일봉 조회 기간 (SMA20 + 여유분) |
| `PRICE_OFFSET` | `2000` | 매수/매도 가격 오프셋 (KRW) |
| `MAX_GAP_RATIO` | `0.02` | strength=1.0 기준 SMA 이격률 (2%) |
| `DEFAULT_BUY_QTY` | `1` | 1회 매수 수량 |
| `LOOP_INTERVAL_SECONDS` | `60` | 루프 간격 (초) |
| `ORDER_VERIFY_WAIT_SECONDS` | `5` | 주문 후 체결 확인 대기 (초) |
| `ENV_DV` | `"demo"` | 환경 구분 (demo=모의, real=실전) |
| `STRATEGY_BUILDER_PATH` | 자동 계산 | 기존 strategy_builder 모듈 경로 |

---

### `logger.py` — 로깅 설정

파일(`logs/trader_YYYYMMDD.log`)과 콘솔에 동시 출력합니다.

```python
from logger import setup_logger
logger = setup_logger("samsung_trader")
logger.info("메시지")
```

로그 포맷:
```
[2026-04-29 09:15:00] INFO     samsung_trader: 현재가: 55,400원
```

---

### `auth.py` — 인증 및 토큰 관리

**동작 순서:**

1. 환경변수(`GH_APPKEY`, `GH_APPSECRET`, `GH_ACCOUNT`)를 읽어 `~/KIS/config/kis_devlp.yaml`에 씁니다.
2. `kis_auth` 모듈을 import합니다 (YAML이 있어야 import 가능하므로 순서 중요).
3. `initialize()` 호출 시 `ka.auth(svr="vps")`로 모의투자 토큰을 발급받습니다.
4. 토큰은 당일 재사용됩니다 (KIS 정책: 1일 유효, 6시간 내 재발급 시 기존 토큰 유지).

```python
import auth
auth.initialize()  # main.py에서 가장 먼저 호출
```

> **주의:** `auth.py`는 반드시 다른 모듈보다 먼저 import 해야 합니다.  
> (내부에서 `sys.path`에 `strategy_builder/` 경로를 추가하기 때문)

---

### `api_client.py` — HTTP 래퍼

`kis_auth._url_fetch()`를 얇게 감싼 공통 HTTP 함수입니다.  
실제 API 호출은 `market_data.py`, `account.py`, `orders.py`에서 `data_fetcher`나 `kis_auth`를 직접 사용하므로, 이 모듈은 확장용으로 준비된 레이어입니다.

```python
from api_client import fetch
res = fetch("/uapi/...", "TR_ID", params={"KEY": "value"}, post=False)
if res.isOK():
    data = res.getBody()
```

---

### `market_data.py` — 가격 데이터 조회

| 함수 | 반환 | 설명 |
|------|------|------|
| `get_current_price()` | `int` | 현재가 (실패 시 0) |
| `get_price_history(days)` | `DataFrame[date, close]` | 일봉 종가 데이터 |

- `get_current_price()`: TR ID `FHKST01010100` 사용. 루프마다 1회 호출.
- `get_price_history()`: TR ID `FHKST03010100` 사용. **시작 시 1회만 호출** (API 절약).

---

### `account.py` — 계좌 조회

| 함수 | 반환 | 설명 |
|------|------|------|
| `get_holdings()` | `DataFrame` | 전체 보유 종목 |
| `get_samsung_quantity()` | `int` | 삼성전자 보유 수량 |
| `get_deposit()` | `int` | 예수금 (KRW) |
| `get_pending_orders_for_samsung()` | `DataFrame` | 005930 미체결 주문 |
| `clear_cache()` | `None` | 잔고 캐시 강제 초기화 |

- 잔고 API는 10초 TTL 캐시 적용 (불필요한 중복 호출 방지).
- 주문 후 `clear_cache()` → `get_samsung_quantity()` 순으로 체결 여부를 확인합니다.

---

### `orders.py` — 주문 실행

| 함수 | 설명 |
|------|------|
| `place_buy_order(price, qty, market)` | 매수 주문 (지정가/시장가) |
| `place_sell_order(price, qty, market)` | 매도 주문 (지정가/시장가) |
| `cancel_pending_orders()` | 005930 미체결 주문 전체 취소 |

- 모의투자 TR ID: 매수 `VTTC0802U`, 매도 `VTTC0801U`
- 가격은 한국 주식 호가단위로 자동 조정됩니다 (`_round_to_tick`).

**호가단위표:**

| 가격대 | 호가단위 |
|--------|---------|
| ~2,000원 미만 | 1원 |
| 2,000~5,000원 | 5원 |
| 5,000~20,000원 | 10원 |
| 20,000~50,000원 | 50원 |
| 50,000~200,000원 | 100원 |
| 200,000~500,000원 | 500원 |
| 500,000원 이상 | 1,000원 |

---

### `algorithm.py` — 매수/매도 신호 생성 (핵심)

#### 입력
- `price_history`: 일봉 DataFrame (`date`, `close` 컬럼)
- `current_price`: 실시간 현재가 (오늘의 가상 종가로 활용)

#### 처리 흐름

```
price_history (과거 N봉)
        +
current_price → 오늘 가상 종가로 append
        ↓
SMA5  = calc_ma(df, period=5)
SMA20 = calc_ma(df, period=20)
        ↓
[t-1] vs [t] 비교:
  SMA5[t-1] < SMA20[t-1]
  SMA5[t]   > SMA20[t]   → Golden Cross → BUY

  SMA5[t-1] > SMA20[t-1]
  SMA5[t]   < SMA20[t]   → Dead Cross  → SELL

  그 외                  → HOLD
        ↓
신호 강도(strength) 계산:
  gap_ratio = |SMA5 - SMA20| / SMA20
  strength  = min(max(gap_ratio / 0.02, 0.5), 1.0)
        ↓
주문 방식 결정:
  strength >= 0.8 → 시장가 (target_price=None)
  strength <  0.8 → 지정가 (BUY: current-2000, SELL: current+2000)
```

#### Signal 객체 구조

```python
Signal(
    stock_code="005930",
    stock_name="삼성전자",
    action=Action.BUY | Action.SELL | Action.HOLD,
    strength=0.5 ~ 1.0,       # 신호 강도
    reason="설명 문자열",
    target_price=int | None,   # None이면 시장가
    quantity=None,             # trader.py에서 결정
)
```

#### strength 해석

| strength 범위 | 주문 방식 | 의미 |
|--------------|---------|------|
| 0.5 ~ 0.79 | 지정가 (±2,000원) | SMA 이격이 작음 → 보수적 |
| 0.8 ~ 1.0 | 시장가 | SMA 이격이 큼 → 적극적 |

---

### `trader.py` — 메인 트레이딩 루프

`SamsungTrader.run()`이 전체 루프를 제어합니다.

#### 루프 흐름

```
시작 시:
  price_history = get_price_history(days=35)  ← 딱 1회만 호출

while True:
  ┌ 거래 종료 시각 이후 → break
  ├ 거래 시간 외 → 60초 대기 후 continue
  └ 거래 시간 내:
      current_price = get_current_price()      ← 매 루프 1회
      signal = generate_signal(history, price)

      if HOLD → 로그 후 다음 루프

      if BUY:
        보유량 확인 → 이미 보유 시 스킵
        미체결 매수 확인 → 있으면 스킵
        place_buy_order()
        5초 대기 후 잔고 재확인 (체결 여부 로그)

      if SELL:
        보유량 확인 → 미보유 시 스킵
        미체결 매도 확인 → 있으면 스킵
        place_sell_order()
        5초 대기 후 잔고 재확인 (체결 여부 로그)

      sleep(60초)
```

#### 중복 주문 방지 로직

| 상황 | 동작 |
|------|------|
| 매수 신호 + 이미 보유 중 | 매수 스킵 |
| 매수 신호 + 미체결 매수 존재 | 매수 스킵 |
| 매도 신호 + 보유 없음 | 매도 스킵 |
| 매도 신호 + 미체결 매도 존재 | 매도 스킵 |

---

### `main.py` — 진입점

```python
# 실행 순서
setup_logger()     # 1. 로거 초기화
import auth        # 2. YAML 생성 + sys.path 설정
auth.initialize()  # 3. KIS 토큰 발급
SamsungTrader().run()  # 4. 루프 시작
```

`auth`는 반드시 다른 모듈보다 먼저 import해야 합니다.

---

## 기존 코드 재사용 현황

`strategy_builder/` 디렉토리의 기존 모듈을 `sys.path`를 통해 재사용합니다.

| 재사용 모듈 | 사용처 | 역할 |
|------------|--------|------|
| `strategy_builder/kis_auth.py` | `auth.py`, `orders.py` | 토큰 발급, HTTP 요청, smart_sleep |
| `strategy_builder/core/data_fetcher.py` | `market_data.py`, `account.py` | 가격·잔고·미체결 API 호출 |
| `strategy_builder/core/indicators.py` | `algorithm.py` | `calc_ma()` SMA 계산 |
| `strategy_builder/core/signal.py` | `algorithm.py`, `trader.py` | `Signal`, `Action` 데이터클래스 |

---

## API 호출 횟수 (루프당)

| 호출 | 시점 | 횟수 |
|------|------|------|
| `get_price_history()` | 시작 시 1회 | 1회/전체 |
| `get_current_price()` | 매 루프 | 1회/루프 |
| `get_samsung_quantity()` | 신호 발생 시만 | 0~2회/루프 |
| `place_buy/sell_order()` | 주문 조건 충족 시만 | 0~1회/루프 |

모의투자 API 호출 한도를 최소화하도록 설계되었습니다.

---

## 로그 예시

```
[2026-04-29 09:10:01] INFO     samsung_trader: === 삼성전자 자동매매 시작 ===
[2026-04-29 09:10:01] INFO     samsung_trader: 거래 시간: 09:10 ~ 15:30
[2026-04-29 09:10:02] INFO     samsung_trader: 일봉 데이터 로드 완료: 35봉
[2026-04-29 09:10:03] INFO     samsung_trader: 현재가: 55,400원
[2026-04-29 09:10:03] INFO     samsung_trader.algorithm: SMA5=55,100 SMA20=54,800 gap=0.0055 strength=0.50
[2026-04-29 09:10:03] INFO     samsung_trader: 신호: Signal(삼성전자[005930] HOLD ...)
[2026-04-29 09:10:03] INFO     samsung_trader: HOLD: 크로스 없음 (SMA5=55100, SMA20=54800)
...
[2026-04-29 10:23:05] INFO     samsung_trader.algorithm: Golden Cross → BUY @ 53,400원 지정가
[2026-04-29 10:23:05] INFO     samsung_trader: [매수 전] 보유: 0주 | 예수금: 1,000,000원
[2026-04-29 10:23:05] INFO     samsung_trader.orders: 매수 주문 요청: 005930 1주 @ 지정가 53,400원
[2026-04-29 10:23:06] INFO     samsung_trader.orders: 매수 주문 API 응답 OK
[2026-04-29 10:23:11] INFO     samsung_trader: [매수 후] 보유: 1주 | 예수금: 945,600원
[2026-04-29 10:23:11] INFO     samsung_trader: 매수 체결 확인: 1주 보유 중
```

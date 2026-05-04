# 삼성전자 자동매매 (SMA 골든/데드 크로스)

삼성전자(005930)를 대상으로 SMA5/SMA20 크로스 신호 기반으로 매수/매도를 자동 실행하는 모의투자 프로그램입니다.

## 매수/매도 판단 알고리즘

```
일봉 최근 35봉 데이터 + 현재가(오늘 가상 종가) 사용

SMA5 골든 크로스 → 매수 (현재가 - 2,000원 지정가)
SMA5 데드 크로스 → 매도 (현재가 + 2,000원 지정가)
신호 강도(strength) >= 0.8 → 시장가 주문으로 전환

거래 시간: 09:10 ~ 15:30 / 60초 폴링
```

## 사전 설정

### 환경변수 등록

```bash
export GH_APPKEY="모의투자 앱키"
export GH_APPSECRET="모의투자 앱시크릿"
export GH_ACCOUNT="모의투자 계좌번호 앞 8자리"
```

GitHub Codespaces 사용 시: https://github.com/settings/codespaces 에서 Secrets로 등록

### 의존성 설치

```bash
pip install -r requirements.txt
```

## 실행

```bash
cd samsung_auto_trader
python main.py
```

## 프로젝트 구조

```
samsung_auto_trader/
├── main.py          # 진입점
├── config.py        # 상수 (종목코드, SMA 기간, 오프셋 등)
├── logger.py        # 로깅 설정
├── auth.py          # 토큰 발급/재사용 (당일 캐시)
├── api_client.py    # HTTP 공통 래퍼
├── market_data.py   # 현재가·일봉 조회
├── account.py       # 잔고·보유량·미체결 조회
├── orders.py        # 매수/매도/취소 주문
├── algorithm.py     # SMA 크로스 신호 생성 (핵심 알고리즘)
├── trader.py        # 메인 트레이딩 루프
├── logs/            # 일별 로그 파일
└── requirements.txt
```

## 알고리즘 파라미터 변경

`config.py`에서 조정 가능:

| 상수 | 기본값 | 설명 |
|------|--------|------|
| `SMA_FAST` | 5 | 단기 이동평균 기간 |
| `SMA_SLOW` | 20 | 장기 이동평균 기간 |
| `PRICE_OFFSET` | 2000 | 매수/매도 가격 오프셋 (KRW) |
| `MAX_GAP_RATIO` | 0.02 | strength=1.0 기준 SMA 이격률 (2%) |
| `LOOP_INTERVAL_SECONDS` | 60 | 루프 간격 (초) |
| `DEFAULT_BUY_QTY` | 1 | 기본 매수 수량 |

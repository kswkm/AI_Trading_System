# 아키텍처 개요

## 전체 흐름

1. 후보 종목 수집
2. 시세/차트 수집
3. 예산 기반 필터링
4. 기술적 분석
5. AI 기반 종목 선정
6. 뉴스 요약
7. 최종 투자 판단
8. 승인/거절
9. Toss증권 주문 실행
10. 결과 저장 및 리포트 전송

## 디렉터리 역할

- `api/`: 증권사 API 어댑터
- `analysis/`: 퀀트 및 AI 분석 로직
- `communication/`: 이메일/리포트
- `data/`: 실시간 데이터 수집
- `database/`: SQLite 저장
- `trading/`: 주문/리스크 로직
- `docs/`: 문서
- `config/`: 환경변수 예제

## 핵심 파일

- `main.py`: 전체 워크플로 실행
- `config.py`: 설정 값 로딩
- `api/toss_api.py`: Toss증권 OAuth 및 주문 API
- `data/data_collector.py`: 시세, 차트, 뉴스 수집
- `analysis/quant_analyzer.py`: RSI, MACD, Bollinger Bands 계산
- `analysis/ai_analyzer.py`: AI 평가
- `trading/order_executor.py`: 주문 실행기

## 브로커 추상화

현재 구조는 증권사별 구현을 따로 두고, 상위 로직은 공통 인터페이스를 사용하도록 설계되어 있습니다.

이런 구조 덕분에 다음과 같은 전환이 가능합니다:
- Toss API 구현체 교체
- 다른 브로커 추가
- 주문 전용/조회 전용 분리

# 아키텍처 개요

## 전체 흐름

1. Toss 종목 마스터에서 국내·해외 후보 조회
2. Toss 현재가와 일봉 차트 수집
3. 예산 범위에 맞는 후보 구성
4. 기본 지표 계산
5. RSI, MACD, Bollinger Bands, 변동성, Sharpe Ratio 계산
6. 지표 점수로 추천 종목 선정
7. 사용자가 입력한 추가 종목을 합쳐 보고서 생성
8. Gmail로 HTML 분석 보고서 발송

## 디렉터리 역할

- `api/`: Toss증권 OAuth 및 시장 데이터 API 어댑터
- `analysis/`: 퀀트 지표와 신호 계산
- `communication/`: 이메일 발송과 HTML 보고서 생성
- `data/`: Toss 종목 목록·시세·차트 수집
- `docs/`: 설치·보안·구조 문서
- `docker/`: 컨테이너 실행 설정
- `scripts/`: Windows 로컬 실행 보조 스크립트

## 핵심 파일

- `main.py`: 실행 시 예산·추가 종목을 받고 전체 분석 흐름 실행
- `config.py`: 환경 변수와 분석 설정 로딩
- `api/toss_api.py`: Toss증권 인증, 종목 마스터, 현재가, 캔들 API
- `data/data_collector.py`: 국내·해외 후보와 시장 데이터 수집
- `analysis/quant_analyzer.py`: RSI, MACD, Bollinger Bands, 변동성, Sharpe Ratio
- `communication/report_generator.py`: HTML 분석 보고서 생성
- `communication/email_manager.py`: Gmail SMTP 보고서 발송

## 실행 범위

이 프로젝트는 투자 분석 보고서만 생성합니다. 주문, 결제, 승인 대기, 거래 실행 기능은 포함하지 않습니다.

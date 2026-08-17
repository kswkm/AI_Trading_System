# Toss AI Trading System

Toss증권 Open API를 활용하는 기본·퀀트 투자분석 보고서 프로젝트입니다.

## 주요 기능
- Toss증권 Open API 기반 실시간 시세/주문 연동
- 기술적 분석 (RSI, MACD, Bollinger Bands, 변동성, Sharpe Ratio)
- Toss 차트 기반 기본 지표 종목 선정
- 예산 기반 종목 선별
- 승인/거절 기반 주문 흐름
- SQLite 저장소를 통한 분석/거래 로그 보관
- 이메일 리포트 전송

## 프로젝트 구조
- `main.py`: 전체 워크플로 실행
- `config.py`: 환경변수와 투자 설정
- `api/toss_api.py`: Toss증권 API 어댑터
- `data/data_collector.py`: 데이터 수집기
- `analysis/quant_analyzer.py`: 퀀트 분석
- `analysis/ai_analyzer.py`: AI 종합 분석
- `trading/order_executor.py`: 매수/매도 실행
- `database/database.py`: SQLite 저장
- `communication/`: 이메일 및 리포트

## 준비 사항
1. Python 3.11 이상 권장
2. Toss증권 Open API Client ID / Client Secret 발급

## 환경 변수 예시
실제 키는 코드에 직접 넣지 말고 `.env` 파일에 넣으세요. 프로젝트 루트에 `.env`를 만들고 아래처럼 설정합니다.

```env
APP_ENV=production

TOSS_CLIENT_ID=your_toss_client_id_here
TOSS_CLIENT_SECRET=your_toss_client_secret_here
TOSS_ACCOUNT_NUMBER=1234567890
TOSS_ACCOUNT_SEQ=1234567890
TOSS_BASE_URL=https://api.tossinvest.com
TOSS_TOKEN_URL=https://api.tossinvest.com/oauth2/token
TOSS_REQUIRE_PHONE_APPROVAL=true
TOSS_APPROVAL_WAIT_SECONDS=60

GMAIL_ADDRESS=your@gmail.com
GMAIL_APP_PASSWORD=your_app_password
EMAIL_APPROVAL_MODE=gmail

TRADING_BUDGET=1000000
MAX_POSITION_RATIO=0.5
MAX_SELECTED_STOCKS=5
LOG_LEVEL=INFO
```

PowerShell에서 바로 만들려면:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\set_env_example.ps1
```

## 실행 방법

이 시스템은 실거래 모드로만 작동합니다. 모든 주문은 Toss증권 API를 통해 실제로 전송됩니다.

### 로컬 실행

```bash
pip install -r requirements.txt
python main.py
```

### Windows에서 바로 실행

```bat
scripts\setup_venv.bat
scripts\run_local.bat
```

### Docker 실행

먼저 루트에 `.env`를 준비하세요. 실제 보안값은 코드에 넣지 않고 `.env`에만 넣습니다.

```bash
copy .env.example .env
```

그 다음 Docker 컨테이너를 실행합니다.

```bash
cd docker
docker compose up --build
```

백그라운드로 실행하려면:

```bash
cd docker
docker compose up -d --build
```

실행 상태 확인:

```bash
cd docker
docker compose ps
```

로그 확인:

```bash
cd docker
docker compose logs -f
```

중지:

```bash
cd docker
docker compose down
```

재빌드:

```bash
docker compose build --no-cache
```

## 환경 검증

프로그램은 시작 시 필수 환경 변수를 확인합니다.
- `DRY_RUN=true`인 경우 실제 주문은 차단되고 경고만 기록됩니다.
- `DRY_RUN=false`인 경우 Toss API 인증 정보가 모두 있어야만 실행됩니다.

## 문서
- [docs/README.md](docs/README.md): 문서 인덱스
- [docs/setup.md](docs/setup.md): 설치 및 환경 변수 설정
- [docs/architecture.md](docs/architecture.md): 프로젝트 구조와 흐름
- [.env.example](.env.example): 환경 변수 예시

## 참고
- 이 프로젝트는 Toss증권 Open API 인증 방식에 맞춰 설계되었습니다.
- 실제 주문은 API 문서 기준의 엔드포인트와 응답 구조를 따라야 하며, 운영 전 문서와 함께 테스트가 필요합니다.
- 일부 도구는 실제 API가 없을 경우에도 로컬 테스트가 가능하도록 기본 폴백을 두고 있습니다.


Toss 차트
├─ 30일 수익률
├─ RSI
├─ MACD
├─ 볼린저 밴드
├─ 변동성
├─ Sharpe Ratio
├─ 거래량 비율
└─ 기술 신호 강도

추가 필터
├─ 예산 범위
├─ 종목당 투자 한도
└─ 기본 점수 기반 fallback 선정

외부 보조 데이터
└─ Toss 현재가·일봉 차트
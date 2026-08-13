"""
AI 트레이딩 시스템 설정
환경변수 또는 여기서 직접 설정
"""

import os
from typing import List

from dotenv import load_dotenv

load_dotenv()


def _as_bool(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _as_float(value, default):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_csv_list(value: str, default: List[str]):
    if value is None:
        return default
    values = [item.strip() for item in str(value).split(",")]
    return [item for item in values if item]


APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
DRY_RUN = _as_bool(os.getenv("DRY_RUN"), default=True)
TOSS_ENVIRONMENT = os.getenv("TOSS_ENVIRONMENT", "dry-run" if DRY_RUN else "live")
TOSS_USE_DEMO = _as_bool(os.getenv("TOSS_USE_DEMO"), default=DRY_RUN)

# =========================================================
# AI 트레이딩 예산 설정
# =========================================================

TRADING_BUDGET = _as_float(os.getenv("TRADING_BUDGET", "1000000"), 1_000_000)
MAX_POSITION_RATIO = _as_float(os.getenv("MAX_POSITION_RATIO", "0.50"), 0.50)
MIN_ORDER_AMOUNT = _as_float(os.getenv("MIN_ORDER_AMOUNT", "10000"), 10_000)
MAX_SELECTED_STOCKS = int(os.getenv("MAX_SELECTED_STOCKS", "5"))

# ============================================================================
# Gmail 설정
# ============================================================================
GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS", "your_email@gmail.com")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "xxxx xxxx xxxx xxxx")

# ============================================================================
# API 키
# ============================================================================
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "sk-ant-")
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY", "")

# Toss증권 Open API 설정
TOSS_CLIENT_ID = os.getenv("TOSS_CLIENT_ID", "")
TOSS_CLIENT_SECRET = os.getenv("TOSS_CLIENT_SECRET", "")
TOSS_ACCOUNT_NUMBER = os.getenv("TOSS_ACCOUNT_NUMBER", "")
TOSS_ACCOUNT_PASSWORD = os.getenv("TOSS_ACCOUNT_PASSWORD", "")
TOSS_ACCOUNT_SEQ = os.getenv("TOSS_ACCOUNT_SEQ", "")
TOSS_BASE_URL = os.getenv("TOSS_BASE_URL", "https://api.tossinvest.com")
TOSS_TOKEN_URL = os.getenv("TOSS_TOKEN_URL", "https://api.tossinvest.com/oauth2/token")
TOSS_REQUIRE_PHONE_APPROVAL = _as_bool(os.getenv("TOSS_REQUIRE_PHONE_APPROVAL"), default=True)
TOSS_APPROVAL_WAIT_SECONDS = int(os.getenv("TOSS_APPROVAL_WAIT_SECONDS", "60"))

# 브로커 선택 (기본값: Toss)
BROKER = os.getenv("BROKER", "TOSS").upper()

# ============================================================================
# Interactive Brokers 설정
# ============================================================================
IB_HOST = "localhost"
IB_PORT = 7497
IB_CLIENT_ID = 1

# ============================================================================
# 트레이딩 설정
# ============================================================================
STOCKS = _parse_csv_list(os.getenv("STOCKS", "AAPL,MSFT,GOOGL,TSLA,NVDA"), ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA"])
DEFAULT_QUANTITY = int(os.getenv("DEFAULT_QUANTITY", "100"))
MAX_POSITION_SIZE = int(os.getenv("MAX_POSITION_SIZE", "10000"))

# ============================================================================
# 스케줄 설정
# ============================================================================
DAILY_ANALYSIS_TIME = os.getenv("DAILY_ANALYSIS_TIME", "07:00")
APPROVAL_TIMEOUT_HOURS = int(os.getenv("APPROVAL_TIMEOUT_HOURS", "24"))

# ============================================================================
# 로깅 설정
# ============================================================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FILE = os.getenv("LOG_FILE", "trading_system.log")

# ============================================================================
# 데이터베이스 설정
# ============================================================================
DATABASE_PATH = os.getenv("DATABASE_PATH", "trading_history.db")

# ============================================================================
# 이메일 설정
# ============================================================================
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL", "your_email@gmail.com")
EMAIL_CHECK_INTERVAL = int(os.getenv("EMAIL_CHECK_INTERVAL", "30"))


def validate_runtime_config(require_live_trading: bool = False):
    """필수 환경 변수를 검증하고, dry-run 모드에서는 안전하게 경고만 남긴다.

    TOSS_ACCOUNT_PASSWORD는 실거래 시 사용자에게 직접 입력받는 방식으로 처리한다.
    따라서 파일/환경변수에 강제 저장하지 않고, 필요 시 런타임에서 프롬프트를 띄운다.
    """
    required_keys = []
    if require_live_trading or not DRY_RUN:
        required_keys.extend([
            "TOSS_CLIENT_ID",
            "TOSS_CLIENT_SECRET",
            "TOSS_ACCOUNT_NUMBER",
        ])

    if not required_keys:
        return {
            "dry_run": True,
            "app_env": APP_ENV,
            "mode": "dry-run",
            "warnings": [
                "DRY_RUN=true 이므로 실제 주문은 전송되지 않습니다."
            ],
        }

    missing = [key for key in required_keys if not globals().get(key, "")]
    if missing:
        raise ValueError(
            "Missing required environment values: " + ", ".join(missing)
            + ". Check your .env file or deployment settings."
        )

    return {
        "dry_run": False,
        "app_env": APP_ENV,
        "mode": "live",
        "warnings": [
            "TOSS_ACCOUNT_PASSWORD는 실거래 시 콘솔에서 직접 입력받습니다."
        ],
    }

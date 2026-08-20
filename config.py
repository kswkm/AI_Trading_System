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


APP_ENV = os.getenv("APP_ENV", "production").strip().lower()

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
GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS", "kswkmy7556@gmail.com")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")

# ============================================================================
# API 키
# ============================================================================
# Toss증권 Open API 설정
TOSS_CLIENT_ID = os.getenv("TOSS_CLIENT_ID", "")
TOSS_CLIENT_SECRET = os.getenv("TOSS_CLIENT_SECRET", "")
TOSS_BASE_URL = os.getenv("TOSS_BASE_URL", "https://api.tossinvest.com")
TOSS_TOKEN_URL = os.getenv("TOSS_TOKEN_URL", "https://api.tossinvest.com/oauth2/token")
TOSS_REQUIRE_PHONE_APPROVAL = _as_bool(os.getenv("TOSS_REQUIRE_PHONE_APPROVAL"), default=False)
TOSS_APPROVAL_WAIT_SECONDS = int(os.getenv("TOSS_APPROVAL_WAIT_SECONDS", "0"))

# 브로커 선택 (기본값: Toss)
BROKER = os.getenv("BROKER", "TOSS").upper()

# ============================================================================
# Interactive Brokers 설정
# ============================================================================
IB_HOST = "localhost"
IB_PORT = 7497
IB_CLIENT_ID = 1

# ============================================================================
# 분석 설정
# ============================================================================
SYMBOL_SCAN_LIMIT = int(os.getenv("SYMBOL_SCAN_LIMIT", "400"))
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
# 이메일 설정
# ============================================================================
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL", "kswkmy7556@gmail.com")
EMAIL_CHECK_INTERVAL = int(os.getenv("EMAIL_CHECK_INTERVAL", "30"))

# ============================================================================
# AI 신뢰도 분석 설정 (DART/SEC 공시 + 뉴스 + Ollama)
# ============================================================================
AI_RELIABILITY_ENABLED = _as_bool(os.getenv("AI_RELIABILITY_ENABLED"), default=True)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
DART_API_KEY = os.getenv("DART_API_KEY", "")
SEC_USER_AGENT = os.getenv("SEC_USER_AGENT", "AI_Trading_System kswkmy7556@gmail.com")
AI_NEWS_LIMIT = int(os.getenv("AI_NEWS_LIMIT", "5"))
AI_FILING_DAYS = int(os.getenv("AI_FILING_DAYS", "30"))
AI_CACHE_TTL_HOURS = int(os.getenv("AI_CACHE_TTL_HOURS", "12"))
AI_FILING_EXCERPT_COUNT = int(os.getenv("AI_FILING_EXCERPT_COUNT", "2"))
OLLAMA_TIMEOUT_SECONDS = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "300"))


def validate_runtime_config(require_live_trading: bool = True):
    """필수 환경 변수를 검증합니다."""
    required_keys = [
        "TOSS_CLIENT_ID",
        "TOSS_CLIENT_SECRET",
    ]

    missing = [key for key in required_keys if not globals().get(key, "")]
    if missing:
        raise ValueError(
            "Missing required environment values: " + ", ".join(missing)
            + ". Check your .env file or deployment settings."
        )

    warnings = []
    if AI_RELIABILITY_ENABLED:
        if not DART_API_KEY:
            warnings.append("⚠️ DART_API_KEY가 없어 국내 종목 AI 신뢰도 분석 근거가 제한됩니다.")
        if not SEC_USER_AGENT:
            warnings.append("⚠️ SEC_USER_AGENT가 없어 해외 종목 AI 신뢰도 분석 근거가 제한됩니다.")

    return {
        "app_env": APP_ENV,
        "mode": "live",
        "warnings": warnings,
    }

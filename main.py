"""
Toss증권 기반 AI 트레이딩 시스템

전체 workflow:

1. 후보 종목 데이터 수집
2. 예산 내 종목 필터링
3. AI StockSelector
4. Quant 분석
5. 뉴스 수집
6. Claude 종합 분석
7. 이메일 보고서
8. 종목별 승인/거절
9. 승인된 종목만 주문
10. 예산 기반 주문 수량 계산
"""

import getpass
import schedule
import time
import logging
import os

from datetime import datetime

from dotenv import load_dotenv

from config import (
    DAILY_ANALYSIS_TIME,
    GMAIL_ADDRESS,
    GMAIL_APP_PASSWORD,
    CLAUDE_API_KEY,
    FINNHUB_API_KEY,
    STOCKS,
    RECIPIENT_EMAIL,
    LOG_LEVEL,
    LOG_FILE,
    TRADING_BUDGET,
    MAX_POSITION_RATIO,
    MAX_SELECTED_STOCKS,
    TOSS_CLIENT_ID,
    TOSS_CLIENT_SECRET,
    TOSS_ACCOUNT_NUMBER,
    TOSS_ACCOUNT_PASSWORD,
    TOSS_ACCOUNT_SEQ,
    TOSS_BASE_URL,
    BROKER,
    DRY_RUN,
    validate_runtime_config,
)

from data.stock_selector import StockSelector

from data.data_collector import TossDataCollector

from analysis.quant_analyzer import QuantAnalyzer

from analysis.ai_analyzer import AIAnalyzer

from communication.report_generator import ReportGenerator

from communication.email_manager import EmailManager

from database.database import TradingDatabase

from trading.smart_timeout import SmartTimeoutSystem

from trading.order_executor import OrderExecutor


# =========================================================
# 환경변수
# =========================================================

load_dotenv()

# =========================================================
# 로깅
# =========================================================

logging.basicConfig(
    level=LOG_LEVEL,
    format=(
        "%(asctime)s - "
        "%(levelname)s - "
        "%(message)s"
    ),
    handlers=[
        logging.FileHandler(
            LOG_FILE,
            encoding="utf-8"
        ),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
validation = validate_runtime_config(require_live_trading=not DRY_RUN)
for warning in validation.get("warnings", []):
    logger.warning(warning)

if not DRY_RUN:
    logger.info("🚨 실전 거래 모드: 주문이 실제 Toss API로 전송됩니다.")
else:
    logger.info("🧪 DRY_RUN 모드 활성화: 실제 주문은 전송되지 않고 시뮬레이션만 수행됩니다.")


def prompt_for_toss_password() -> str:
    """실거래 시마다 사용자가 직접 Toss 비밀번호를 입력하도록 한다."""
    env_password = str(os.getenv("TOSS_ACCOUNT_PASSWORD", "")).strip()
    if env_password:
        return env_password

    if DRY_RUN:
        return ""

    print("\n=== Toss 비밀번호 입력 ===")
    print("실거래 전용입니다. 비밀번호는 화면에 보이지 않고, 메모리에서만 사용됩니다.")
    try:
        password = getpass.getpass("TOSS_ACCOUNT_PASSWORD를 직접 입력하세요: ")
    except (EOFError, KeyboardInterrupt):
        return ""

    password = str(password).strip()
    if password:
        os.environ["TOSS_ACCOUNT_PASSWORD"] = password
    return password


class AITradingSystemKI:
    """Toss증권 AI 트레이딩 시스템"""

    # =====================================================
    # 초기화
    # =====================================================

    def __init__(self):

        logger.info("=" * 70)

        logger.info(
            "🚀 Toss증권 "
            "AI 트레이딩 시스템 초기화"
        )

        logger.info("=" * 70)

        # -------------------------------------------------
        # Toss증권 설정
        # -------------------------------------------------

        toss_client_id = (
            os.getenv("TOSS_CLIENT_ID")
            or TOSS_CLIENT_ID
        )

        toss_client_secret = (
            os.getenv("TOSS_CLIENT_SECRET")
            or TOSS_CLIENT_SECRET
        )

        toss_account_number = (
            os.getenv("TOSS_ACCOUNT_NUMBER")
            or TOSS_ACCOUNT_NUMBER
        )

        toss_account_password = (
            os.getenv("TOSS_ACCOUNT_PASSWORD")
            or TOSS_ACCOUNT_PASSWORD
            or prompt_for_toss_password()
        )

        toss_account_seq = (
            os.getenv("TOSS_ACCOUNT_SEQ")
            or TOSS_ACCOUNT_SEQ
        )

        toss_base_url = (
            os.getenv("TOSS_BASE_URL")
            or TOSS_BASE_URL
        )

        if not toss_account_number and toss_account_seq:
            toss_account_number = toss_account_seq

        if not all([
            toss_client_id,
            toss_client_secret,
            toss_account_number,
        ]):
            raise ValueError(
                "❌ Toss증권 API 설정이 부족합니다. "
                "TOSS_CLIENT_ID / TOSS_CLIENT_SECRET / TOSS_ACCOUNT_NUMBER 를 확인하세요."
            )

        self.broker = BROKER
        self.dry_run = DRY_RUN

        if not self.dry_run and not toss_account_password:
            raise ValueError(
                "❌ 실거래 모드에서는 Toss 비밀번호를 직접 입력해야 합니다. "
                "콘솔에서 비밀번호를 입력하거나 TOSS_ACCOUNT_PASSWORD를 설정하세요."
            )

        # -------------------------------------------------
        # 데이터 수집기
        # -------------------------------------------------

        self.data_collector = (
            TossDataCollector(
                app_key=toss_client_id,
                app_secret=toss_client_secret,
                finnhub_key=FINNHUB_API_KEY,
                use_demo=self.dry_run
            )
        )

        # -------------------------------------------------
        # StockSelector
        # -------------------------------------------------

        self.stock_selector = StockSelector(
            api_key=CLAUDE_API_KEY,
            trading_budget=TRADING_BUDGET,
            max_position_ratio=MAX_POSITION_RATIO,
            max_selected_stocks=MAX_SELECTED_STOCKS
        )

        # -------------------------------------------------
        # Quant
        # -------------------------------------------------

        self.quant_analyzer = (
            QuantAnalyzer()
        )

        # -------------------------------------------------
        # AI Analyzer
        # -------------------------------------------------

        self.ai_analyzer = AIAnalyzer(
            api_key=CLAUDE_API_KEY
        )

        # -------------------------------------------------
        # Report
        # -------------------------------------------------

        self.report_gen = (
            ReportGenerator()
        )

        # -------------------------------------------------
        # Email
        # -------------------------------------------------

        self.email_manager = EmailManager(
            gmail_address=GMAIL_ADDRESS,
            gmail_app_password=GMAIL_APP_PASSWORD
        )

        # -------------------------------------------------
        # Database
        # -------------------------------------------------

        self.database = TradingDatabase()

        # -------------------------------------------------
        # Order Executor
        # -------------------------------------------------

        self.executor = OrderExecutor(
            app_key=toss_client_id,
            app_secret=toss_client_secret,
            account_number=toss_account_number,
            account_password=toss_account_password,
            use_demo=self.dry_run,
            trading_budget=TRADING_BUDGET,
            max_position_ratio=MAX_POSITION_RATIO,
            dry_run=self.dry_run,
        )

        # -------------------------------------------------
        # Timeout
        # -------------------------------------------------

        self.timeout_system = (
            SmartTimeoutSystem(
                email_manager=self.email_manager,
                executor=self.executor,
                database=self.database
            )
        )

        logger.info(
            "✅ 모든 모듈 초기화 완료"
        )

        logger.info(
            f"📋 후보 종목: {', '.join(STOCKS)}"
        )

        logger.info(
            f"💰 거래 예산: "
            f"{TRADING_BUDGET:,.0f}원"
        )

        logger.info(
            f"📊 종목당 최대: "
            f"{TRADING_BUDGET * MAX_POSITION_RATIO:,.0f}원"
        )

        logger.info("=" * 70)

    # =====================================================
    # 일일 workflow
    # =====================================================

    def daily_workflow(self):

        print("\n" + "=" * 70)

        print(
            f"📊 일일 분석 시작: "
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        print("=" * 70)

        try:

            # =================================================
            # STEP 1
            # 모든 후보 종목 데이터 수집
            # =================================================

            print(
                "\n1️⃣ 후보 종목 데이터 수집 중..."
            )

            raw_data = (
                self.data_collector.collect_all(
                    STOCKS
                )
            )

            available_symbols = [
                symbol
                for symbol in STOCKS
                if raw_data.get(symbol)
            ]

            print(
                f"   ✅ {len(available_symbols)}개 종목 수집"
            )

            if not available_symbols:

                raise RuntimeError(
                    "분석 가능한 종목이 없습니다."
                )

            # =================================================
            # STEP 2
            # 후보 데이터 생성
            # =================================================

            print(
                "\n2️⃣ 종목 후보 데이터 생성 중..."
            )

            candidates = []

            for symbol in available_symbols:

                stock_data = raw_data[symbol]

                historical = (
                    stock_data.get(
                        "historical_data",
                        []
                    )
                )

                current_price = float(
                    stock_data.get(
                        "current_price",
                        0
                    )
                )

                if current_price <= 0:
                    continue

                # 기본 후보 데이터
                candidate = {
                    "symbol": symbol,
                    "current_price":
                        current_price,
                    "return_30d": 0,
                    "volatility": 0,
                    "volume_ratio": 1,
                    "rsi": 50
                }

                # ---------------------------------------------
                # historical 데이터가 있으면 간단한 지표 계산
                # ---------------------------------------------

                if historical:

                    try:

                        closes = []

                        volumes = []

                        for row in historical:

                            close = (
                                row.get("close")
                                or row.get("stck_clpr")
                                or row.get("price")
                            )

                            volume = (
                                row.get("volume")
                                or row.get("acml_vol")
                            )

                            if close is not None:
                                closes.append(
                                    float(close)
                                )

                            if volume is not None:
                                volumes.append(
                                    float(volume)
                                )

                        # 30일 수익률
                        if len(closes) >= 2:

                            first_price = (
                                closes[0]
                            )

                            last_price = (
                                closes[-1]
                            )

                            if first_price > 0:

                                candidate[
                                    "return_30d"
                                ] = (
                                    last_price
                                    / first_price
                                    - 1
                                ) * 100

                        # 변동성
                        if len(closes) >= 2:

                            returns = []

                            for i in range(
                                1,
                                len(closes)
                            ):

                                if closes[i - 1] > 0:

                                    returns.append(
                                        (
                                            closes[i]
                                            / closes[i - 1]
                                            - 1
                                        )
                                    )

                            if returns:

                                import statistics

                                candidate[
                                    "volatility"
                                ] = (
                                    statistics.stdev(
                                        returns
                                    )
                                    * (
                                        252 ** 0.5
                                    )
                                    * 100
                                )

                        # 거래량 비율
                        if len(volumes) >= 5:

                            recent_volume = (
                                volumes[-1]
                            )

                            avg_volume = (
                                sum(
                                    volumes[-5:]
                                )
                                / len(
                                    volumes[-5:]
                                )
                            )

                            if avg_volume > 0:

                                candidate[
                                    "volume_ratio"
                                ] = (
                                    recent_volume
                                    / avg_volume
                                )

                    except Exception as e:

                        logger.warning(
                            f"⚠️ {symbol} "
                            f"후보 지표 계산 실패: {e}"
                        )

                candidates.append(
                    candidate
                )

            print(
                f"   ✅ 후보 {len(candidates)}개"
            )

            # =================================================
            # STEP 3
            # AI StockSelector
            # =================================================

            print(
                "\n3️⃣ AI 종목 선정 중..."
            )

            selected_symbols = (
                self.stock_selector.select_stocks(
                    candidates=candidates,
                    market_data=(
                        "한국 주식시장 후보 종목을 "
                        "기술적 지표와 위험을 고려하여 "
                        "분석합니다."
                    ),
                    top_n=MAX_SELECTED_STOCKS
                )
            )

            print(
                f"   🤖 AI 선정 종목: "
                f"{', '.join(selected_symbols)}"
            )

            if not selected_symbols:

                logger.warning(
                    "⚠️ 선정된 종목이 없습니다."
                )

                return

            # =================================================
            # STEP 4
            # Quant 분석
            # =================================================

            print(
                "\n4️⃣ 퀀트 분석 중..."
            )

            quant_results = {}

            for stock in selected_symbols:

                if not raw_data.get(stock):
                    continue

                quant_results[stock] = (
                    self.quant_analyzer.analyze_stock(
                        stock,
                        raw_data[stock].get(
                            "historical_data",
                            []
                        )
                    )
                )

            print("   ✅ 완료")

            # =================================================
            # STEP 5
            # 뉴스 수집
            # =================================================

            print(
                "\n5️⃣ 뉴스 수집 중..."
            )

            news_data = (
                self.data_collector.get_latest_news(
                    selected_symbols
                )
            )

            print("   ✅ 완료")

            # =================================================
            # STEP 6
            # AI 종합 분석
            # =================================================

            print(
                "\n6️⃣ AI 종합 분석 중..."
            )

            ai_results = {}

            for stock in selected_symbols:

                if not quant_results.get(stock):
                    continue

                ai_results[stock] = (
                    self.ai_analyzer.analyze(
                        stock,
                        quant_results[stock],
                        news_data.get(
                            stock,
                            "뉴스 없음"
                        )
                    )
                )

            print("   ✅ 완료")

            # =================================================
            # STEP 7
            # 보고서 생성
            # =================================================

            print(
                "\n7️⃣ 보고서 생성 중..."
            )

            analysis_data = []

            for stock in selected_symbols:

                if not ai_results.get(stock):
                    continue

                analysis_item = {

                    "symbol":
                        stock,

                    "current_price":
                        quant_results[stock][
                            "current_price"
                        ],

                    "recipient_email":
                        RECIPIENT_EMAIL,

                    **ai_results[stock]
                }

                analysis_data.append(
                    analysis_item
                )

                self.database.save_analysis(
                    symbol=stock,
                    analysis_data=analysis_item,
                    status="PENDING"
                )

            if not analysis_data:

                raise RuntimeError(
                    "최종 분석 결과가 없습니다."
                )

            html_report = (
                self.report_gen.generate_html_report(
                    analysis_data
                )
            )

            print("   ✅ 완료")

            # =================================================
            # STEP 8
            # 승인 요청 이메일
            # =================================================

            print(
                "\n8️⃣ 승인 요청 이메일 발송..."
            )

            self.email_manager.send_approval_request(
                recipient=RECIPIENT_EMAIL,
                analysis_data=analysis_data
            )

            print("   ✅ 완료")

            # =================================================
            # STEP 9
            # 사용자 승인 대기
            # =================================================

            print(
                "\n9️⃣ 사용자 종목별 "
                "승인/거절 대기..."
            )

            decision = (
                self.timeout_system
                .wait_for_user_decision(
                    analysis_data
                )
            )

            # =================================================
            # STEP 10
            # 결정 처리
            # =================================================

            print(
                "\n🔟 사용자 결정 처리 중..."
            )

            result = (
                self.timeout_system
                .process_decision(
                    decision,
                    analysis_data
                )
            )

            print(
                "\n" + "=" * 70
            )

            print(
                f"✅ 일일 workflow 완료"
            )

            print(
                f"결정: "
                f"{result.get('decision')}"
            )

            print(
                f"승인: "
                f"{result.get('approved', [])}"
            )

            print(
                f"거절: "
                f"{result.get('rejected', [])}"
            )

            print(
                "=" * 70
            )

        except Exception as e:

            logger.error(
                f"❌ workflow 오류: {e}",
                exc_info=True
            )

            self.email_manager.send_error_email(
                recipient=RECIPIENT_EMAIL,
                error_message=str(e)
            )

    # =====================================================
    # scheduler
    # =====================================================

    def start(self):

        schedule.every().day.at(
            DAILY_ANALYSIS_TIME
        ).do(
            self.daily_workflow
        )

        logger.info("=" * 70)

        logger.info(
            "🚀 AI 트레이딩 시스템 시작"
        )

        logger.info(
            f"📅 매일 "
            f"{DAILY_ANALYSIS_TIME} 실행"
        )

        logger.info(
            f"💰 거래 예산: "
            f"{TRADING_BUDGET:,.0f}원"
        )

        logger.info(
            "🤖 AI가 분석 대상 종목 선정"
        )

        logger.info(
            "👤 사용자 종목별 승인 대기"
        )

        logger.info(
            "⏰ 다음날 07:00 자동 거절"
        )

        logger.info("=" * 70)

        while True:

            try:

                schedule.run_pending()

                time.sleep(60)

            except KeyboardInterrupt:

                logger.info(
                    "⛔ 시스템 중지"
                )

                break

            except Exception as e:

                logger.error(
                    f"❌ 스케줄러 오류: {e}",
                    exc_info=True
                )

                time.sleep(60)


# =========================================================
# main
# =========================================================

def main():

    import sys

    test_mode = (
        "--test"
        in sys.argv
    )

    system = AITradingSystemKI()

    if test_mode:

        print(
            "\n🧪 테스트 모드 실행"
        )

        system.daily_workflow()

        print(
            "\n테스트 완료!"
        )

    else:

        system.start()


if __name__ == "__main__":
    main()
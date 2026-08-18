"""Toss 차트 기반 기본·퀀트 분석 보고서 시스템."""

import logging
import os
from pathlib import Path

from datetime import datetime

from dotenv import load_dotenv

from config import (
    GMAIL_ADDRESS,
    GMAIL_APP_PASSWORD,
    SYMBOL_SCAN_LIMIT,
    RECIPIENT_EMAIL,
    LOG_LEVEL,
    LOG_FILE,
    TRADING_BUDGET,
    MAX_POSITION_RATIO,
    MAX_SELECTED_STOCKS,
    TOSS_CLIENT_ID,
    TOSS_CLIENT_SECRET,
    validate_runtime_config,
)

from data.data_collector import TossDataCollector

from analysis.quant_analyzer import QuantAnalyzer

from communication.report_generator import ReportGenerator

from communication.email_manager import EmailManager

# =========================================================
# 환경변수
# =========================================================

load_dotenv()

# =========================================================
# 로깅
# =========================================================

Path(LOG_FILE).parent.mkdir(parents=True, exist_ok=True)

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
validation = validate_runtime_config()
for warning in validation.get("warnings", []):
    logger.warning(warning)

logger.info("📊 분석 보고서 전용 모드: 주문과 결제를 실행하지 않습니다.")


class AITradingSystemKI:
    """Toss증권 AI 트레이딩 시스템"""

    # =====================================================
    # 초기화
    # =====================================================

    def __init__(self, trading_budget=None, recipient_email=None, additional_symbols=None):

        self.trading_budget = float(trading_budget) if trading_budget is not None else float(TRADING_BUDGET)
        self.recipient_email = recipient_email or RECIPIENT_EMAIL or "kswkmy7556@gmail.com"
        self.additional_symbols = list(dict.fromkeys(additional_symbols or []))

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

        if not all([
            toss_client_id,
            toss_client_secret,
        ]):
            raise ValueError(
                "❌ Toss증권 API 설정이 부족합니다. "
                "TOSS_CLIENT_ID / TOSS_CLIENT_SECRET 를 확인하세요."
            )


        # -------------------------------------------------
        # 데이터 수집기
        # -------------------------------------------------

        self.data_collector = (
            TossDataCollector(
                app_key=toss_client_id,
                app_secret=toss_client_secret,
            )
        )

        # -------------------------------------------------
        # Quant
        # -------------------------------------------------

        self.quant_analyzer = (
            QuantAnalyzer()
        )

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

        logger.info(
            "✅ 모든 모듈 초기화 완료"
        )

        logger.info(
            f"📋 Toss 동적 후보 조회 상한: {SYMBOL_SCAN_LIMIT}개"
        )

        logger.info(
            f"💰 거래 예산: "
            f"{self.trading_budget:,.0f}원"
        )

        logger.info(
            f"📊 종목당 최대: "
            f"{self.trading_budget * MAX_POSITION_RATIO:,.0f}원"
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

            discovered_symbols = self.data_collector.discover_symbols(
                limit=SYMBOL_SCAN_LIMIT
            )
            requested_symbols = list(dict.fromkeys(
                discovered_symbols + self.additional_symbols
            ))
            if self.additional_symbols:
                print(
                    "   ➕ 추가 분석 요청 종목: "
                    f"{', '.join(self.additional_symbols)}"
                )
            raw_data = self.data_collector.collect_all(requested_symbols)

            available_symbols = [
                symbol
                for symbol in requested_symbols
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
                    "currency": stock_data.get("currency", "USD"),
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
            # 기본 지표 점수 기반 종목 선정
            # =================================================

            print("\n3️⃣ 기본·퀀트 지표 기반 종목 선정 중...")

            print("   📊 전체 후보 퀀트 지표 계산 중...")
            candidate_quant_results = {}
            for candidate in candidates:
                symbol = candidate["symbol"]
                result = self.quant_analyzer.analyze_stock(
                    symbol,
                    raw_data[symbol].get("historical_data", [])
                )
                if result:
                    candidate_quant_results[symbol] = result
            print("   ✅ 전체 후보 퀀트 지표 계산 완료")

            def basic_score(candidate):
                score = 0.0
                return_30d = candidate.get("return_30d", 0)
                volume_ratio = candidate.get("volume_ratio", 1)
                volatility = candidate.get("volatility", 100)
                quant_result = candidate_quant_results.get(candidate["symbol"], {})
                rsi = quant_result.get("rsi", 50)
                macd = quant_result.get("macd", 0)
                signal_line = quant_result.get("signal_line", 0)
                bb_position = quant_result.get("bb_position", 0.5)
                sharpe_ratio = quant_result.get("sharpe_ratio", 0)

                if return_30d > 0:
                    score += min(return_30d, 20)
                if volume_ratio > 1:
                    score += min(volume_ratio * 5, 15)
                if volatility < 30:
                    score += 10
                elif volatility > 50:
                    score -= 10

                if 45 <= rsi <= 65:
                    score += 8
                elif rsi < 30 or rsi > 70:
                    score -= 5

                score += 6 if macd > signal_line else -6

                if 0.2 <= bb_position <= 0.8:
                    score += 5
                elif bb_position < 0.1 or bb_position > 0.9:
                    score -= 3

                score += max(-5, min(5, sharpe_ratio * 2))
                return score

            candidates.sort(key=basic_score, reverse=True)
            ranked_symbols = [
                candidate["symbol"]
                for candidate in candidates[:MAX_SELECTED_STOCKS]
            ]
            selected_symbols = list(dict.fromkeys(
                ranked_symbols + [
                    symbol for symbol in self.additional_symbols
                    if symbol in available_symbols
                ]
            ))

            print(f"   📊 기본·퀀트 선정 종목: {', '.join(selected_symbols)}")

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

            quant_results = dict(candidate_quant_results)

            for stock in selected_symbols:

                if not raw_data.get(stock) or stock in quant_results:
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
            # 기본·퀀트 분석 보고서 생성
            # =================================================

            print(
                "\n7️⃣ 보고서 생성 중..."
            )

            analysis_data = []

            for stock in selected_symbols:
                quant_result = quant_results.get(stock)
                if not quant_result:
                    continue

                signal_strength = quant_result["signal_strength"]
                recommendation = (
                    "BUY" if signal_strength >= 60
                    else "SELL" if signal_strength <= 40
                    else "HOLD"
                )
                current_price = quant_result["current_price"]

                analysis_item = {
                    "symbol": stock,
                    "current_price": current_price,
                    "currency": raw_data[stock].get("currency", "USD"),
                    "recommendation": recommendation,
                    "confidence": signal_strength,
                    "price_target": current_price * (1.05 if recommendation == "BUY" else 0.95 if recommendation == "SELL" else 1.0),
                    "stop_loss": current_price * (0.97 if recommendation == "BUY" else 1.03 if recommendation == "SELL" else 0.95),
                    "time_horizon": "단기 (30거래일)",
                    "summary": "Toss 차트의 기술지표와 통계값만 사용한 정량 분석 결과입니다.",
                    "key_reasons": [
                        f"RSI: {quant_result['rsi']:.1f}",
                        f"MACD: {quant_result['macd']:.4f}",
                        f"30일 수익률: {quant_result['return_30d']:.2f}%",
                        f"연환산 변동성: {quant_result['volatility']:.2f}%",
                        f"Sharpe Ratio: {quant_result['sharpe_ratio']:.2f}",
                    ],
                    "risks": [
                        "과거 차트 기반 지표로 미래 수익을 보장하지 않습니다.",
                        "시장 변동성과 거래 가능 시간을 확인해야 합니다.",
                    ],
                    "catalyst": "기술적 신호 변화",
                }

                analysis_data.append(
                    analysis_item
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
            # STEP 6
            # 분석 보고서 이메일
            # =================================================

            print(
                "\n8️⃣ 투자 분석 보고서 이메일 발송..."
            )

            self.email_manager.send_report(
                recipient=self.recipient_email,
                subject="[Toss 정량 분석] 기본·퀀트 분석 보고서",
                html_report=html_report,
            )

            print("   ✅ 완료")

            print(
                "\n" + "=" * 70
            )

            print(
                f"✅ 투자 분석 보고서 생성 및 발송 완료"
            )

            print(
                "=" * 70
            )

        except Exception as e:

            logger.error(
                f"❌ workflow 오류: {e}",
                exc_info=True
            )

            logger.error("보고서 생성/발송 실패로 종료합니다.")

    # =====================================================
    # 실행
    # =====================================================

    def start(self):
        logger.info("=" * 70)

        logger.info(
            "🚀 AI 트레이딩 시스템 시작"
        )

        logger.info(
            f"💰 거래 예산: "
            f"{self.trading_budget:,.0f}원"
        )

        logger.info(
            "📌 실행 시점에 즉시 분석을 시작합니다"
        )

        logger.info(
            "📧 분석 보고서를 이메일로 발송합니다"
        )

        logger.info("=" * 70)

        self.daily_workflow()


# =========================================================
# main
# =========================================================

def prompt_for_budget():
    while True:
        raw = input("거래 예산을 원 단위로 입력하세요 (예: 1000000): ").strip()
        try:
            value = float(raw.replace(",", ""))
        except ValueError:
            print("숫자를 정확히 입력해주세요.")
            continue
        if value <= 0:
            print("예산은 0보다 커야 합니다.")
            continue
        return int(value)


def prompt_for_additional_symbols():
    raw = input(
        "추가로 분석할 종목을 입력하세요 "
        "(쉼표로 구분, 없으면 Enter): "
    ).strip()
    if not raw:
        return []

    symbols = []
    for value in raw.replace("\n", ",").split(","):
        symbol = value.strip().upper()
        if symbol and symbol not in symbols:
            symbols.append(symbol)
    return symbols


def main():

    import sys

    test_mode = (
        "--test"
        in sys.argv
    )

    budget = prompt_for_budget()
    additional_symbols = prompt_for_additional_symbols()
    system = AITradingSystemKI(
        trading_budget=budget,
        recipient_email="kswkmy7556@gmail.com",
        additional_symbols=additional_symbols,
    )

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
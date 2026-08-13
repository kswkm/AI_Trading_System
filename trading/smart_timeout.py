"""
스마트 타임아웃 시스템

- 사용자 승인/거절 대기
- 종목별 부분 승인/거절
- 다음날 7시까지 대기
- 타임아웃 시 자동 거절
"""

import time
import logging

from datetime import datetime, timedelta

from config import (
    EMAIL_CHECK_INTERVAL
)


logger = logging.getLogger(__name__)


class SmartTimeoutSystem:

    def __init__(
        self,
        email_manager,
        executor,
        database
    ):

        self.email_manager = email_manager
        self.executor = executor
        self.database = database

        self.current_analysis = None

    # =========================================================
    # 타임아웃 계산
    # =========================================================

    def calculate_timeout(self):

        now = datetime.now()

        tomorrow_7am = (
            now.replace(
                hour=7,
                minute=0,
                second=0,
                microsecond=0
            )
            + timedelta(days=1)
        )

        timeout = (
            tomorrow_7am - now
        )

        return int(
            timeout.total_seconds()
        )

    # =========================================================
    # 사용자 응답 대기
    # =========================================================

    def wait_for_user_decision(
        self,
        analysis_data
    ):

        self.current_analysis = (
            analysis_data
        )

        timeout_seconds = (
            self.calculate_timeout()
        )

        start_time = time.time()

        last_log_time = start_time

        print("\n" + "=" * 60)

        print(
            "📧 사용자 승인/거절 대기 중..."
        )

        print(
            "종목별 승인/거절이 가능합니다."
        )

        print(
            "다음날 07:00까지 응답이 없으면 "
            "전체 자동 거절됩니다."
        )

        print("=" * 60)

        while True:

            elapsed = (
                time.time() - start_time
            )

            remaining = (
                timeout_seconds - elapsed
            )

            # -------------------------------------------------
            # 사용자 응답 확인
            # -------------------------------------------------

            decision = (
                self.email_manager.check_approval(
                    analysis_data
                )
            )

            if decision is not None:

                logger.info(
                    f"📧 사용자 결정 감지: "
                    f"{decision}"
                )

                return decision

            # -------------------------------------------------
            # 타임아웃
            # -------------------------------------------------

            if remaining <= 0:

                logger.warning(
                    "⏰ 타임아웃"
                )

                symbols = [
                    a["symbol"]
                    for a in analysis_data
                ]

                return {
                    "decision":
                        "AUTO_REJECTED",
                    "approved": [],
                    "rejected": symbols
                }

            # -------------------------------------------------
            # 1시간마다 로그
            # -------------------------------------------------

            current_time = time.time()

            if (
                current_time - last_log_time
                >= 3600
            ):

                hours = int(
                    remaining / 3600
                )

                minutes = int(
                    (remaining % 3600) / 60
                )

                logger.info(
                    f"⏳ 응답 대기 중 "
                    f"{hours}시간 {minutes}분 남음"
                )

                last_log_time = current_time

            time.sleep(
                EMAIL_CHECK_INTERVAL
            )

    # =========================================================
    # 결정 처리
    # =========================================================

    def process_decision(
        self,
        decision,
        analysis_data
    ):

        if not decision:

            return {
                "status": "NO_DECISION"
            }

        approved_symbols = set(
            decision.get(
                "approved",
                []
            )
        )

        rejected_symbols = set(
            decision.get(
                "rejected",
                []
            )
        )

        approved_analysis = [
            analysis
            for analysis in analysis_data
            if analysis["symbol"]
            in approved_symbols
        ]

        rejected_analysis = [
            analysis
            for analysis in analysis_data
            if analysis["symbol"]
            in rejected_symbols
        ]

        # =====================================================
        # 승인된 종목만 주문
        # =====================================================

        execution_results = []

        for analysis in approved_analysis:

            try:

                symbol = analysis["symbol"]

                logger.info(
                    f"🟢 승인 종목 주문: {symbol}"
                )

                result = (
                    self.executor.execute_order(
                        analysis
                    )
                )

                execution_results.append(
                    result
                )

                status = (
                    "EXECUTED"
                    if result.get("status")
                    == "SUCCESS"
                    else "NOT_EXECUTED"
                )

                self.database.save_analysis(
                    symbol=symbol,
                    analysis_data=analysis,
                    status=status
                )

                self.email_manager.send_execution_email(
                    recipient=analysis.get(
                        "recipient_email",
                        "your_email@gmail.com"
                    ),
                    analysis=analysis,
                    order_result=result
                )

            except Exception as e:

                logger.error(
                    f"❌ {analysis['symbol']} "
                    f"주문 처리 실패: {e}"
                )

        # =====================================================
        # 거절된 종목 DB 저장
        # =====================================================

        for analysis in rejected_analysis:

            self.database.save_analysis(
                symbol=analysis["symbol"],
                analysis_data=analysis,
                status="REJECTED"
            )

        # =====================================================
        # 결정 유형
        # =====================================================

        if approved_analysis and rejected_analysis:

            final_decision = "PARTIAL"

        elif approved_analysis:

            final_decision = "APPROVED"

        elif rejected_analysis:

            final_decision = "REJECTED"

        else:

            final_decision = "NO_DECISION"

        # =====================================================
        # DB 결정 저장
        # =====================================================

        self.database.save_decision(
            decision=final_decision,
            analysis_count=len(
                analysis_data
            ),
            details=(
                f"Approved: "
                f"{list(approved_symbols)} | "
                f"Rejected: "
                f"{list(rejected_symbols)}"
            )
        )

        # =====================================================
        # 거절 이메일
        # =====================================================

        if rejected_analysis:

            recipient = rejected_analysis[0].get(
                "recipient_email",
                "your_email@gmail.com"
            )

            self.email_manager.send_rejection_email(
                recipient=recipient,
                rejection_type=(
                    f"{len(rejected_analysis)}개 "
                    f"종목 거절"
                )
            )

        return {
            "status": "COMPLETED",
            "decision": final_decision,
            "approved": list(
                approved_symbols
            ),
            "rejected": list(
                rejected_symbols
            ),
            "execution_results":
                execution_results,
            "timestamp": datetime.now()
        }
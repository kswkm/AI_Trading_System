"""
이메일 관리 모듈

- 이메일 발송
- 사용자 종목별 승인/거절
- 전체 승인/거절
"""

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import policy
from email.parser import BytesParser

import imaplib
import smtplib
import logging
import os

from datetime import datetime


logger = logging.getLogger(__name__)


class EmailManager:

    def __init__(
        self,
        gmail_address,
        gmail_app_password
    ):

        self.gmail = gmail_address
        self.password = gmail_app_password
        self.approval_mode = os.getenv(
            "EMAIL_APPROVAL_MODE",
            "gmail" if self.gmail and self.password and not self._is_dry_run() else "local"
        ).lower()

    @staticmethod
    def _is_dry_run():
        return str(os.getenv("DRY_RUN", "false")).strip().lower() in {
            "1", "true", "yes", "y", "on"
        }

    def _extract_message_text(self, msg):
        if msg.is_multipart():
            chunks = []
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        try:
                            chunks.append(payload.decode("utf-8"))
                        except UnicodeDecodeError:
                            chunks.append(payload.decode("utf-8", errors="replace"))
            return "\n".join(chunks)

        payload = msg.get_payload(decode=True)
        if not payload:
            return ""
        try:
            return payload.decode("utf-8")
        except UnicodeDecodeError:
            return payload.decode("utf-8", errors="replace")

    def _parse_approval_response(self, response, symbols):
        if not response:
            return None

        if response.upper() == "APPROVED":
            return {
                "decision": "APPROVED",
                "approved": symbols,
                "rejected": []
            }

        if response.upper() == "REJECTED":
            return {
                "decision": "REJECTED",
                "approved": [],
                "rejected": symbols
            }

        approved = []
        rejected = []
        for line in response.splitlines():
            line = line.strip()
            if not line:
                continue
            upper_line = line.upper()
            if upper_line.startswith("APPROVED:"):
                values = line.split(":", 1)[1]
                for symbol in values.split(","):
                    symbol = symbol.strip()
                    if symbol in symbols:
                        approved.append(symbol)
            elif upper_line.startswith("REJECTED:"):
                values = line.split(":", 1)[1]
                for symbol in values.split(","):
                    symbol = symbol.strip()
                    if symbol in symbols:
                        rejected.append(symbol)

        approved = list(dict.fromkeys(approved))
        rejected = list(dict.fromkeys(rejected))
        if not approved and not rejected:
            return None
        return {
            "decision": "PARTIAL",
            "approved": approved,
            "rejected": rejected,
        }

    def check_gmail_response(self, analysis_data=None):
        if not self.gmail or not self.password:
            logger.warning("⚠️ Gmail IMAP 검증을 위해 계정 정보가 없습니다.")
            return None

        try:
            with imaplib.IMAP4_SSL("imap.gmail.com") as mail:
                mail.login(self.gmail, self.password)
                mail.select("INBOX")
                status, message_ids = mail.search(None, "(UNSEEN)")
                if status != "OK":
                    return None

                ids = [item for item in message_ids[0].split() if item]
                symbols = [analysis["symbol"] for analysis in (analysis_data or [])]
                for message_id in reversed(ids):
                    status, msg_data = mail.fetch(message_id, "(RFC822)")
                    if status != "OK" or not msg_data or not msg_data[0]:
                        continue

                    for _, raw_email in msg_data:
                        if not raw_email:
                            continue
                        msg = BytesParser(policy=policy.default).parsebytes(raw_email)
                        response = self._extract_message_text(msg)
                        decision = self._parse_approval_response(response, symbols)
                        if decision:
                            mail.store(message_id, "+FLAGS", "\\Seen")
                            return decision
                return None
        except Exception as exc:
            logger.warning("⚠️ Gmail 승인 응답 확인 실패: %s", exc)
            return None

    # =========================================================
    # 이메일 발송
    # =========================================================

    def send_report(
        self,
        recipient,
        subject,
        html_report
    ):

        try:

            msg = MIMEMultipart(
                "alternative"
            )

            msg["Subject"] = subject
            msg["From"] = self.gmail
            msg["To"] = recipient

            msg.attach(
                MIMEText(
                    html_report,
                    "html",
                    "utf-8"
                )
            )

            with smtplib.SMTP_SSL(
                "smtp.gmail.com",
                465
            ) as server:

                server.login(
                    self.gmail,
                    self.password
                )

                server.send_message(msg)

            logger.info(
                f"✅ 이메일 발송 성공: "
                f"{recipient}"
            )

            return True

        except Exception as e:

            logger.error(
                f"❌ 이메일 발송 실패: {e}"
            )

            return False

    # =========================================================
    # 승인 요청 이메일
    # =========================================================

    def send_approval_request(
        self,
        recipient,
        analysis_data
    ):

        rows = ""

        for analysis in analysis_data:

            rows += f"""
            <tr>
                <td>{analysis['symbol']}</td>
                <td>{analysis['recommendation']}</td>
                <td>{analysis['confidence']}</td>
                <td>{analysis['current_price']}</td>
                <td>{analysis['price_target']}</td>
                <td>{analysis['stop_loss']}</td>
            </tr>
            """

        html = f"""
<!DOCTYPE html>

<html>

<head>

<meta charset="UTF-8">

<style>

body {{
    font-family: Arial;
    background: #f3f4f6;
}}

.container {{
    max-width: 900px;
    margin: 20px auto;
}}

.header {{
    background: #2563eb;
    color: white;
    padding: 20px;
}}

.content {{
    background: white;
    padding: 20px;
}}

table {{
    width: 100%;
    border-collapse: collapse;
}}

th, td {{
    border: 1px solid #ddd;
    padding: 8px;
    text-align: center;
}}

th {{
    background: #f3f4f6;
}}

.command {{
    margin-top: 20px;
    background: #fef3c7;
    padding: 20px;
}}

code {{
    background: #e5e7eb;
    padding: 5px;
}}

</style>

</head>

<body>

<div class="container">

<div class="header">

<h2>🤖 AI 트레이딩 승인 요청</h2>

<p>
분석 결과를 확인하고 종목별로 승인/거절해주세요.
</p>

</div>

<div class="content">

<table>

<tr>
<th>종목</th>
<th>추천</th>
<th>신뢰도</th>
<th>현재가</th>
<th>목표가</th>
<th>손절가</th>
</tr>

{rows}

</table>

<div class="command">

<h3>📌 응답 방법</h3>

<p>
종목별 승인:
</p>

<code>
APPROVED:005930
</code>

<p>
종목별 거절:
</p>

<code>
REJECTED:005380
</code>

<p>
여러 종목 승인:
</p>

<code>
APPROVED:005930,000660
</code>

<p>
여러 종목을 각각 처리:
</p>

<code>
APPROVED:005930
<br>
REJECTED:000660
<br>
APPROVED:005380
</code>

<p>
전체 승인:
<code>APPROVED</code>
</p>

<p>
전체 거절:
<code>REJECTED</code>
</p>

</div>

</div>

</div>

</body>

</html>
"""

        return self.send_report(
            recipient,
            "[AI 트레이딩] 종목별 승인 요청",
            html
        )

    # =========================================================
    # 승인 응답 확인
    # =========================================================

    def check_approval(
        self,
        analysis_data=None
    ):

        try:
            if self.approval_mode == "gmail" and self.gmail and self.password:
                decision = self.check_gmail_response(analysis_data)
                if decision is not None:
                    return decision

            return self.check_local_response(
                analysis_data
            )

        except Exception as e:

            logger.warning(
                f"⚠️ 승인 확인 오류: {e}"
            )

            return None

    # =========================================================
    # 로컬 응답
    # =========================================================

    def check_local_response(
        self,
        analysis_data=None
    ):

        try:

            with open(
                "approval_response.txt",
                "r",
                encoding="utf-8"
            ) as f:

                response = f.read().strip()

        except FileNotFoundError:

            return None
        if not response:
            return None

        symbols = [
            analysis["symbol"]
            for analysis in (
                analysis_data or []
            )
        ]

        decision = self._parse_approval_response(response, symbols)
        if decision is None:
            return None

        self._delete_response_file()
        return decision
    # =========================================================
    # 파일 삭제
    # =========================================================

    def _delete_response_file(self):

        try:

            os.remove(
                "approval_response.txt"
            )

        except FileNotFoundError:

            pass

    # =========================================================
    # 거래 결과 이메일
    # =========================================================

    def send_execution_email(
        self,
        recipient,
        analysis,
        order_result=None
    ):

        order_result = (
            order_result or {}
        )

        html = f"""
<html>

<body>

<h2>✅ 거래 실행 결과</h2>

<hr>

<p>
<strong>종목:</strong>
{analysis['symbol']}
</p>

<p>
<strong>추천:</strong>
{analysis['recommendation']}
</p>

<p>
<strong>신뢰도:</strong>
{analysis['confidence']}/100
</p>

<p>
<strong>주문 상태:</strong>
{order_result.get('status', 'N/A')}
</p>

<p>
<strong>주문 수량:</strong>
{order_result.get('quantity', 0)}
</p>

<p>
<strong>주문 금액:</strong>
{order_result.get('order_amount', 0):,.0f}원
</p>

<p>
<strong>실행 시간:</strong>
{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
</p>

</body>

</html>
"""

        return self.send_report(
            recipient,
            f"[거래 실행] {analysis['symbol']}",
            html
        )

    # =========================================================
    # 거절 이메일
    # =========================================================

    def send_rejection_email(
        self,
        recipient,
        rejection_type
    ):

        html = f"""
<html>

<body>

<h2>❌ 분석 거절</h2>

<p>
{rejection_type}
</p>

<p>
시간:
{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
</p>

</body>

</html>
"""

        return self.send_report(
            recipient,
            f"[거절됨] {rejection_type}",
            html
        )

    # =========================================================
    # 에러 이메일
    # =========================================================

    def send_error_email(
        self,
        recipient,
        error_message
    ):

        html = f"""
<html>

<body>

<h2>⚠️ AI 트레이딩 시스템 오류</h2>

<p>
{error_message}
</p>

<p>
시간:
{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
</p>

</body>

</html>
"""

        return self.send_report(
            recipient,
            "[에러] AI 트레이딩 시스템",
            html
        )
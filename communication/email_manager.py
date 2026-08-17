"""분석 보고서 이메일 발송 모듈."""

from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
import smtplib


logger = logging.getLogger(__name__)


class EmailManager:
    """Gmail SMTP를 통해 분석 보고서만 발송합니다."""

    def __init__(self, gmail_address, gmail_app_password):
        self.gmail = gmail_address
        self.password = gmail_app_password

    def send_report(self, recipient, subject, html_report):
        if not self.gmail or not self.password:
            logger.error("Gmail 주소 또는 앱 비밀번호가 설정되지 않았습니다.")
            return False

        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = self.gmail
        message["To"] = recipient
        message.attach(MIMEText(html_report, "html", "utf-8"))

        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(self.gmail, self.password)
                server.send_message(message)
            logger.info("분석 보고서 이메일 발송 성공: %s", recipient)
            return True
        except Exception as exc:
            logger.error("분석 보고서 이메일 발송 실패: %s", exc)
            return False

    def send_error_email(self, recipient, error_message):
        html_report = f"""
        <html><body>
        <h2>Toss 분석 시스템 오류</h2>
        <p>{error_message}</p>
        <p>시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </body></html>
        """
        return self.send_report(recipient, "[Toss 분석] 시스템 오류", html_report)

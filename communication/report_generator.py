"""분석 전용 HTML 보고서 생성 모듈."""

from datetime import datetime
from html import escape
import logging


logger = logging.getLogger(__name__)


class ReportGenerator:
    """주문이나 승인 흐름 없이 투자 분석 보고서를 생성합니다."""

    def generate_html_report(self, analysis_data):
        logger.info("보고서 생성 중... (%d개 종목)", len(analysis_data))

        buy_count = sum(
            1 for result in analysis_data
            if "BUY" in result.get("recommendation", "")
        )
        sell_count = sum(
            1 for result in analysis_data
            if "SELL" in result.get("recommendation", "")
        )
        hold_count = len(analysis_data) - buy_count - sell_count
        sections = []

        for result in analysis_data:
            recommendation = result.get("recommendation", "HOLD")
            currency = result.get("currency", "USD")
            currency_mark = "₩" if currency == "KRW" else "$"
            signal_class = (
                "buy" if "BUY" in recommendation
                else "sell" if "SELL" in recommendation
                else "hold"
            )
            reasons = "".join(
                f"<li>{escape(str(reason))}</li>"
                for reason in result.get("key_reasons", [])
            )
            risks = "".join(
                f"<li>{escape(str(risk))}</li>"
                for risk in result.get("risks", [])
            )
            sections.append(f"""
            <section class="stock {signal_class}">
                <header>
                    <div>
                        <h2>{escape(str(result.get('symbol', '')))}</h2>
                        <p>현재가: {currency_mark}{float(result.get('current_price', 0)):,.2f} {currency}</p>
                    </div>
                    <strong class="signal">{escape(recommendation.replace('_', ' '))}</strong>
                </header>
                <div class="metrics">
                    <div><span>목표가</span><b>{currency_mark}{float(result.get('price_target', 0)):,.2f}</b></div>
                    <div><span>손절 기준</span><b>{currency_mark}{float(result.get('stop_loss', 0)):,.2f}</b></div>
                    <div><span>신뢰도</span><b>{result.get('confidence', 0)}/100</b></div>
                    <div><span>투자 기간</span><b>{escape(str(result.get('time_horizon', 'N/A')))}</b></div>
                </div>
                <h3>분석 요약</h3>
                <p>{escape(str(result.get('summary', '')))}</p>
                <h3>긍정 요인</h3><ul>{reasons}</ul>
                <h3>위험 요소</h3><ul>{risks}</ul>
                <p class="catalyst">촉매: {escape(str(result.get('catalyst', 'N/A')))}</p>
            </section>
            """)

        generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Toss 기본·퀀트 분석 보고서</title>
    <style>
        body {{ margin: 0; padding: 24px; background: #f4f6f8; color: #17202a; font-family: Arial, sans-serif; line-height: 1.6; }}
        .container {{ max-width: 900px; margin: 0 auto; }}
        .header, .notice, .stock, .stats {{ background: #fff; border-radius: 8px; padding: 24px; margin-bottom: 16px; box-shadow: 0 2px 8px #00000012; }}
        .header {{ background: #17324d; color: #fff; }}
        .header h1 {{ margin: 0 0 6px; }}
        .notice {{ border-left: 4px solid #2b7a78; }}
        .stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; text-align: center; }}
        .stats b {{ display: block; font-size: 22px; color: #17324d; }}
        .stock {{ border-left: 5px solid #d99a2b; }}
        .stock.buy {{ border-left-color: #238b68; }}
        .stock.sell {{ border-left-color: #c94c4c; }}
        .stock header {{ display: flex; justify-content: space-between; align-items: center; gap: 16px; }}
        .stock h2 {{ margin: 0; }}
        .stock header p {{ margin: 2px 0 0; color: #637381; }}
        .signal {{ padding: 6px 10px; border-radius: 4px; background: #e9eef2; white-space: nowrap; }}
        .metrics {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 18px 0; }}
        .metrics div {{ background: #f4f6f8; padding: 10px; }}
        .metrics span, .metrics b {{ display: block; }}
        .metrics span {{ color: #637381; font-size: 12px; }}
        .stock h3 {{ font-size: 14px; margin-bottom: 4px; }}
        .stock ul {{ margin-top: 4px; }}
        .catalyst {{ color: #637381; }}
        footer {{ color: #637381; font-size: 12px; text-align: center; padding: 12px; }}
        @media (max-width: 640px) {{ .stats, .metrics {{ grid-template-columns: repeat(2, 1fr); }} .stock header {{ align-items: flex-start; flex-direction: column; }} }}
    </style>
</head>
<body>
    <main class="container">
        <section class="header">
            <h1>Toss 기본·퀀트 분석 보고서</h1>
            <p>{generated_at} 생성</p>
        </section>
        <section class="notice">
            Toss 현재가·차트와 기본·퀀트 지표만 사용한 참고용 분석입니다. 주문, 결제, 승인 및 거절 처리는 수행하지 않습니다.
        </section>
        <section class="stats">
            <div><b>{len(analysis_data)}</b>분석 종목</div>
            <div><b>{buy_count}</b>매수 신호</div>
            <div><b>{sell_count}</b>매도 신호</div>
            <div><b>{hold_count}</b>보유 신호</div>
        </section>
        {''.join(sections)}
        <footer>최종 투자 판단과 위험 관리는 사용자 책임입니다.</footer>
    </main>
</body>
</html>
"""

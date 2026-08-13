"""
보고서 생성 모듈
- HTML 형식의 아름다운 보고서 생성
"""

from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class ReportGenerator:
    """보고서 생성 클래스"""
    
    def generate_html_report(self, analysis_data):
        """HTML 보고서 생성"""
        
        logger.info(f"📄 보고서 생성 중... ({len(analysis_data)}개 종목)")
        
        # 타임아웃 계산
        now = datetime.now()
        tomorrow_7am = now.replace(hour=7, minute=0, second=0) + timedelta(days=1)
        timeout_str = tomorrow_7am.strftime('%Y년 %m월 %d일 %H:%M')
        
        # 통계
        buy_count = sum(1 for r in analysis_data if 'BUY' in r['recommendation'])
        sell_count = sum(1 for r in analysis_data if 'SELL' in r['recommendation'])
        hold_count = len(analysis_data) - buy_count - sell_count
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI 트레이딩 분석 리포트</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f3f4f6;
            padding: 20px;
            line-height: 1.6;
        }}
        .container {{ max-width: 900px; margin: 0 auto; }}
        .header {{ 
            background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
            color: white; 
            padding: 30px; 
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .header h1 {{ font-size: 28px; margin-bottom: 5px; }}
        .header p {{ opacity: 0.9; }}
        
        .alert-box {{
            background: #fef3c7;
            border-left: 4px solid #f59e0b;
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 4px;
        }}
        
        .stats {{
            background: #f0f9ff;
            padding: 15px;
            border-radius: 6px;
            margin-bottom: 20px;
            font-size: 13px;
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
        }}
        .stat-item {{ text-align: center; }}
        .stat-number {{ font-size: 18px; font-weight: bold; color: #1e3a8a; }}
        .stat-label {{ color: #6b7280; margin-top: 5px; }}
        
        .stock {{ 
            background: white;
            margin-bottom: 15px; 
            padding: 20px; 
            border-left: 4px solid #3b82f6; 
            border-radius: 6px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .stock.buy {{ border-left-color: #10b981; }}
        .stock.sell {{ border-left-color: #ef4444; }}
        .stock.hold {{ border-left-color: #f59e0b; }}
        
        .stock-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }}
        .stock-symbol {{ font-size: 22px; font-weight: bold; }}
        .stock-price {{ font-size: 12px; color: #6b7280; }}
        .signal {{ 
            padding: 6px 12px; 
            border-radius: 20px; 
            font-size: 12px; 
            font-weight: bold;
        }}
        .signal.buy {{ background: #d1fae5; color: #065f46; }}
        .signal.sell {{ background: #fee2e2; color: #7f1d1d; }}
        .signal.hold {{ background: #fef3c7; color: #92400e; }}
        
        .metrics {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 10px;
            margin-bottom: 15px;
        }}
        .metric {{
            padding: 10px;
            background: #f9fafb;
            border-radius: 4px;
        }}
        .metric-label {{ font-size: 12px; color: #6b7280; margin-bottom: 3px; }}
        .metric-value {{ font-size: 16px; font-weight: bold; }}
        
        .reasoning {{
            margin-top: 15px;
            padding: 15px;
            background: #f9fafb;
            border-radius: 4px;
        }}
        .reasoning h4 {{ font-size: 13px; color: #374151; margin-bottom: 8px; margin-top: 0; }}
        .reasoning h4:first-child {{ margin-top: 0; }}
        .reasoning ul {{ margin-left: 20px; font-size: 13px; }}
        .reasoning li {{ margin-bottom: 5px; }}
        
        .action-section {{
            background: white;
            padding: 30px;
            border-radius: 8px;
            text-align: center;
            margin-top: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .action-section h2 {{
            margin-bottom: 20px;
            font-size: 18px;
            color: #1f2937;
        }}
        
        .button-group {{ display: flex; gap: 15px; justify-content: center; }}
        .button {{ 
            padding: 14px 40px; 
            border: none; 
            border-radius: 6px; 
            cursor: pointer; 
            font-size: 16px;
            font-weight: 600;
            text-decoration: none;
            display: inline-block;
            transition: all 0.3s ease;
        }}
        .btn-approve {{ 
            background: #10b981; 
            color: white;
        }}
        .btn-approve:hover {{ background: #059669; }}
        
        .btn-reject {{ 
            background: #ef4444; 
            color: white;
        }}
        .btn-reject:hover {{ background: #dc2626; }}
        
        .timeout-info {{
            margin-top: 20px;
            padding: 15px;
            background: #eff6ff;
            border-left: 4px solid #3b82f6;
            border-radius: 4px;
            font-size: 13px;
            color: #1e40af;
        }}
        
        footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #e5e7eb;
            color: #6b7280;
            font-size: 12px;
            text-align: center;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 AI 투자 분석 리포트</h1>
            <p>{datetime.now().strftime('%Y년 %m월 %d일 %A')} | 자동 생성됨</p>
        </div>
        
        <div class="alert-box">
            <p>⏳ <strong>중요:</strong> 이 보고서는 내일 아침 7시까지만 유효합니다.<br>
            그 이후에는 자동으로 거절 처리되며 새로운 분석을 시작합니다.</p>
        </div>
        
        <div class="stats">
            <div class="stat-item">
                <div class="stat-number">{len(analysis_data)}</div>
                <div class="stat-label">분석 종목</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">{buy_count}</div>
                <div class="stat-label">매수 신호</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">{sell_count}</div>
                <div class="stat-label">매도 신호</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">{hold_count}</div>
                <div class="stat-label">보유 신호</div>
            </div>
        </div>
"""
        
        # 종목별 분석
        for result in analysis_data:
            if 'BUY' in result.get('recommendation', 'HOLD'):
                signal_class = 'buy'
            elif 'SELL' in result.get('recommendation', 'HOLD'):
                signal_class = 'sell'
            else:
                signal_class = 'hold'
            
            recommendation_text = result.get('recommendation', 'HOLD').replace('_', ' ')
            
            html += f"""
        <div class="stock {signal_class}">
            <div class="stock-header">
                <div>
                    <div class="stock-symbol">{result['symbol']}</div>
                    <div class="stock-price">현재가: ${result['current_price']:.2f}</div>
                </div>
                <span class="signal {signal_class}">{recommendation_text}</span>
            </div>
            
            <div class="metrics">
                <div class="metric">
                    <div class="metric-label">목표가</div>
                    <div class="metric-value">${result['price_target']:.2f}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">손절가</div>
                    <div class="metric-value">${result['stop_loss']:.2f}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">신뢰도</div>
                    <div class="metric-value">{result['confidence']}/100</div>
                </div>
                <div class="metric">
                    <div class="metric-label">투자기간</div>
                    <div class="metric-value">{result['time_horizon']}</div>
                </div>
            </div>
            
            <div class="reasoning">
                <h4>📝 분석 요약</h4>
                <p>{result['summary']}</p>
                
                <h4>✅ 긍정 요인</h4>
                <ul>
"""
            for reason in result.get('key_reasons', []):
                html += f"                    <li>{reason}</li>\n"
            
            html += """
                </ul>
                
                <h4>⚠️ 위험 요소</h4>
                <ul>
"""
            for risk in result.get('risks', []):
                html += f"                    <li>{risk}</li>\n"
            
            html += """
                </ul>
            </div>
        </div>
"""
        
        html += f"""
        <div class="action-section">
            <h2>👇 이제 결정해주세요</h2>
            
            <p style="margin-bottom: 25px; color: #6b7280; font-size: 14px;">
                아래 버튼을 클릭하여 이 분석을 승인하거나 거절하세요.
            </p>
            
            <div class="button-group">
                <a href="mailto:your_email@gmail.com?subject=APPROVE_TRADING" class="button btn-approve">
                    ✅ 승인 - 거래 진행
                </a>
                
                <a href="mailto:your_email@gmail.com?subject=REJECT_ANALYSIS" class="button btn-reject">
                    ❌ 거절 - 다시 분석
                </a>
            </div>
            
            <div class="timeout-info">
                <strong>⏰ 타임아웃 안내</strong><br>
                응답이 없으면 <strong>{timeout_str}</strong>에 자동으로 <strong>거절 처리</strong>되고<br>
                새로운 분석을 시작합니다.
            </div>
        </div>
        
        <footer>
            <p>이 보고서는 AI 자동분석 결과입니다. 최종 투자결정은 전적으로 사용자의 판단입니다.</p>
            <p>생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </footer>
    </div>
</body>
</html>
"""
        
        logger.info("✅ 보고서 생성 완료")
        return html
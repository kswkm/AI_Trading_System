"""
AI 분석 모듈
- Claude API를 사용한 종합 분석
- 뉴스 감정분석
- 투자 추천
"""

import anthropic
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class AIAnalyzer:
    """AI 분석 클래스"""
    
    def __init__(self, api_key):
        self.client = anthropic.Anthropic(api_key=api_key)
     
    def analyze(self, symbol, quant_result, news_data):
        """Claude를 이용한 종합 분석"""
        
        try:
            logger.info(f"🤖 {symbol} AI 분석 중...")
            
            # 프롬프트 생성
            prompt = self.create_analysis_prompt(symbol, quant_result, news_data)
            
            # Claude API 호출
            message = self.client.messages.create(
                model="claude-opus-4-1",
                max_tokens=1000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # 응답 파싱
            response_text = message.content[0].text
            
            try:
                # JSON 추출 시도
                if "```json" in response_text:
                    json_str = response_text.split("```json")[1].split("```")[0].strip()
                    analysis = json.loads(json_str)
                else:
                    analysis = json.loads(response_text)
                
                logger.info(f"✅ {symbol} AI 분석 완료 ({analysis.get('recommendation', 'N/A')})")
                return analysis
            
            except json.JSONDecodeError:
                logger.error(f"❌ JSON 파싱 실패: {response_text[:200]}")
                return self.create_default_analysis(symbol, quant_result)
        
        except Exception as e:
            logger.error(f"❌ {symbol} AI 분석 오류: {e}")
            return self.create_default_analysis(symbol, quant_result)
    
    def create_analysis_prompt(self, symbol, quant_result, news_data):
        """분석 프롬프트 생성"""
        
        prompt = f"""당신은 전문 투자 분석가입니다. 다음 데이터를 분석하고 투자 결정을 내려주세요.

【 종목: {symbol} 】

【 정량적 분석 결과 】
- 현재가: ${quant_result['current_price']:.2f}
- RSI: {quant_result['rsi']:.1f}
- MACD: {quant_result['macd']:.4f}
- Signal Line: {quant_result['signal_line']:.4f}
- Bollinger Bands 위치: {quant_result['bb_position']:.2f} (0=하한, 1=상한)
- 30일 수익률: {quant_result['return_30d']:.2f}%
- 연간 변동성: {quant_result['volatility']:.2f}%
- Sharpe Ratio: {quant_result['sharpe_ratio']:.2f}
- 신호 강도: {quant_result['signal_strength']}/100

기술 신호:
"""
        
        for signal in quant_result.get('signals', []):
            prompt += f"- {signal['type']}: {signal['signal']} (강도: {signal['strength']:.1f})\n"
        
        prompt += f"""
【 최근 뉴스 】
{news_data}

【 분석 요청 】
다음을 JSON 형식으로만 분석해주세요. 다른 텍스트는 없어야 합니다:

{{
    "recommendation": "STRONG_BUY / BUY / HOLD / SELL / STRONG_SELL",
    "confidence": 0-100,
    "price_target": X.XX,
    "stop_loss": X.XX,
    "time_horizon": "단기 (1주) / 중기 (1개월) / 장기 (3개월)",
    "key_reasons": ["이유1", "이유2", "이유3"],
    "risks": ["위험1", "위험2"],
    "catalyst": "긍정적 / 부정적 / 중립적 이벤트",
    "summary": "한 문단 요약 (50자 이상 200자 이하)"
}}

JSON만 출력하고, 마크다운이나 다른 텍스트는 없어야 합니다."""
        
        return prompt
    
    def create_default_analysis(self, symbol, quant_result):
        """기본 분석 결과 생성 (API 실패 시)"""
        
        logger.warning(f"⚠️ {symbol} 기본 분석 생성 중...")
        
        current_price = quant_result['current_price']
        signal_strength = quant_result['signal_strength']
        
        # 신호 강도에 따른 추천
        if signal_strength > 70:
            recommendation = "STRONG_BUY"
            confidence = 75
            target = current_price * 1.10
            stop_loss = current_price * 0.95
        elif signal_strength > 55:
            recommendation = "BUY"
            confidence = 65
            target = current_price * 1.05
            stop_loss = current_price * 0.97
        elif signal_strength < 30:
            recommendation = "STRONG_SELL"
            confidence = 75
            target = current_price * 0.90
            stop_loss = current_price * 1.05
        elif signal_strength < 45:
            recommendation = "SELL"
            confidence = 65
            target = current_price * 0.95
            stop_loss = current_price * 1.03
        else:
            recommendation = "HOLD"
            confidence = 50
            target = current_price
            stop_loss = current_price * 0.95
        
        return {
            "recommendation": recommendation,
            "confidence": confidence,
            "price_target": round(target, 2),
            "stop_loss": round(stop_loss, 2),
            "time_horizon": "중기 (1개월)",
            "key_reasons": [
                f"기술적 신호: {quant_result['signal_strength']}/100",
                f"RSI: {quant_result['rsi']:.1f}",
                f"변동성: {quant_result['volatility']:.2f}%"
            ],
            "risks": [
                "시장 변동성",
                "거시경제 불확실성"
            ],
            "catalyst": "중립적 이벤트",
            "summary": f"{symbol}는 기술적 분석 신호를 바탕으로 {recommendation} 추천합니다."
        }


class SentimentAnalyzer:
    """감정 분석 클래스 (선택사항)"""
    
    def __init__(self):
        pass
    
    def analyze_sentiment(self, text):
        """텍스트 감정 분석"""
        
        try:
            from transformers import pipeline
            
            classifier = pipeline('sentiment-analysis', model='FinBERT')
            result = classifier(text[:512])  # 텍스트 길이 제한
            
            return result[0]
        
        except:
            # FinBERT 없을 시 간단한 키워드 분석
            positive_words = ['positive', 'bullish', 'strong', 'growth', 'excellent', 'surge', 'rally']
            negative_words = ['negative', 'bearish', 'weak', 'decline', 'poor', 'crash', 'drop']
            
            text_lower = text.lower()
            
            positive_count = sum(1 for word in positive_words if word in text_lower)
            negative_count = sum(1 for word in negative_words if word in text_lower)
            
            if positive_count > negative_count:
                return {'label': 'POSITIVE', 'score': 0.7}
            elif negative_count > positive_count:
                return {'label': 'NEGATIVE', 'score': 0.7}
            else:
                return {'label': 'NEUTRAL', 'score': 0.5}

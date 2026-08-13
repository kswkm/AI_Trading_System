"""
퀀트 분석 모듈
- RSI, MACD, Bollinger Bands 등 기술지표
- 통계 분석 (변동성, Sharpe Ratio)
- 신호 생성
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class QuantAnalyzer:
    """퀀트 분석 클래스"""
    
    def __init__(self):
        pass
    
    def analyze_stock(self, symbol, historical_data):
        """종목별 퀀트 분석"""
        
        try:
            logger.info(f"📊 {symbol} 퀀트 분석 중...")
            
            # DataFrame으로 변환
            if isinstance(historical_data, list):
                df = pd.DataFrame(historical_data)
            else:
                df = historical_data.copy()
            
            # 기술지표 계산
            df['RSI'] = self.calculate_rsi(df['close'], period=14)
            df['MACD'], df['Signal'] = self.calculate_macd(df['close'])
            df['BB_Upper'], df['BB_Middle'], df['BB_Lower'] = self.calculate_bollinger(df['close'])
            
            # 통계 분석
            returns = df['close'].pct_change()
            volatility = returns.std() * np.sqrt(252)  # 연간 변동성
            sharpe_ratio = (returns.mean() / returns.std() * np.sqrt(252)) if returns.std() > 0 else 0
            
            # 최근 30일 수익률
            recent_return = ((df['close'].iloc[-1] / df['close'].iloc[0]) - 1) * 100
            
            # 최신 데이터
            latest = df.iloc[-1]
            
            # 신호 생성
            signals = self.generate_signals(latest)
            signal_strength = self.calculate_signal_strength(signals)
            
            result = {
                'symbol': symbol,
                'current_price': float(latest['close']),
                'rsi': float(latest['RSI']) if not pd.isna(latest['RSI']) else 50,
                'macd': float(latest['MACD']) if not pd.isna(latest['MACD']) else 0,
                'signal_line': float(latest['Signal']) if not pd.isna(latest['Signal']) else 0,
                'bb_upper': float(latest['BB_Upper']) if not pd.isna(latest['BB_Upper']) else latest['close'],
                'bb_middle': float(latest['BB_Middle']) if not pd.isna(latest['BB_Middle']) else latest['close'],
                'bb_lower': float(latest['BB_Lower']) if not pd.isna(latest['BB_Lower']) else latest['close'],
                'bb_position': self.calculate_bb_position(
                    latest['close'],
                    latest['BB_Upper'],
                    latest['BB_Lower']
                ),
                'volatility': float(volatility),
                'sharpe_ratio': float(sharpe_ratio),
                'return_30d': float(recent_return),
                'signals': signals,
                'signal_strength': signal_strength
            }
            
            logger.info(f"✅ {symbol} 분석 완료 (신호강도: {signal_strength}/100)")
            return result
        
        except Exception as e:
            logger.error(f"❌ {symbol} 분석 실패: {e}")
            return None
    
    def calculate_rsi(self, prices, period=14):
        """RSI (Relative Strength Index) 계산"""
        
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def calculate_macd(self, prices, fast=12, slow=26, signal=9):
        """MACD (Moving Average Convergence Divergence) 계산"""
        
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        
        macd = ema_fast - ema_slow
        macd_signal = macd.ewm(span=signal).mean()
        
        return macd, macd_signal
    
    def calculate_bollinger(self, prices, period=20, num_std=2):
        """Bollinger Bands 계산"""
        
        sma = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        
        upper = sma + (std * num_std)
        lower = sma - (std * num_std)
        
        return upper, sma, lower
    
    def calculate_bb_position(self, price, upper, lower):
        """Bollinger Bands 내 가격 위치 (0-1)"""
        
        if pd.isna(upper) or pd.isna(lower):
            return 0.5
        
        if upper - lower == 0:
            return 0.5
        
        position = (price - lower) / (upper - lower)
        return max(0, min(1, position))  # 0-1 범위로 클리핑
    
    def generate_signals(self, latest_data):
        """기술지표 기반 신호 생성"""
        
        signals = []
        
        # RSI 신호
        rsi = latest_data.get('RSI', 50)
        if pd.notna(rsi):
            if rsi < 30:
                signals.append({
                    'type': 'RSI',
                    'signal': 'BUY',
                    'value': rsi,
                    'strength': 0.8
                })
            elif rsi > 70:
                signals.append({
                    'type': 'RSI',
                    'signal': 'SELL',
                    'value': rsi,
                    'strength': 0.8
                })
        
        # MACD 신호
        macd = latest_data.get('MACD', 0)
        signal_line = latest_data.get('Signal', 0)
        if pd.notna(macd) and pd.notna(signal_line):
            if macd > signal_line:
                signals.append({
                    'type': 'MACD',
                    'signal': 'BUY',
                    'value': macd - signal_line,
                    'strength': 0.7
                })
            else:
                signals.append({
                    'type': 'MACD',
                    'signal': 'SELL',
                    'value': signal_line - macd,
                    'strength': 0.7
                })
        
        # Bollinger Bands 신호
        bb_pos = latest_data.get('bb_position', 0.5)
        if pd.notna(bb_pos):
            if bb_pos < 0.2:
                signals.append({
                    'type': 'BB',
                    'signal': 'BUY',
                    'value': bb_pos,
                    'strength': 0.6
                })
            elif bb_pos > 0.8:
                signals.append({
                    'type': 'BB',
                    'signal': 'SELL',
                    'value': bb_pos,
                    'strength': 0.6
                })
        
        return signals
    
    def calculate_signal_strength(self, signals):
        """신호 강도 계산 (0-100)"""
        
        if not signals:
            return 50
        
        buy_count = sum(s['strength'] for s in signals if s['signal'] == 'BUY')
        sell_count = sum(s['strength'] for s in signals if s['signal'] == 'SELL')
        
        total_strength = buy_count + sell_count
        
        if total_strength == 0:
            return 50
        
        buy_ratio = buy_count / total_strength
        signal_strength = int(50 + (buy_ratio - 0.5) * 100)
        
        return max(0, min(100, signal_strength))
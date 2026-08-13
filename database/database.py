"""
데이터베이스 모듈
- SQLite를 사용한 분석 결과 저장
- 히스토리 추적
"""

import sqlite3
import logging
from datetime import datetime
from config import DATABASE_PATH

logger = logging.getLogger(__name__)


class TradingDatabase:
    """트레이딩 데이터베이스 클래스"""
    
    def __init__(self, db_path=DATABASE_PATH):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """데이터베이스 테이블 초기화"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 분석 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    symbol TEXT,
                    recommendation TEXT,
                    confidence INTEGER,
                    current_price REAL,
                    target_price REAL,
                    stop_loss REAL,
                    status TEXT,
                    execution_time TEXT
                )
            ''')
            
            # 거래 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    symbol TEXT,
                    action TEXT,
                    quantity INTEGER,
                    price REAL,
                    status TEXT
                )
            ''')
            
            # 결정 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    decision TEXT,
                    analysis_count INTEGER,
                    details TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
            
            logger.info("✅ 데이터베이스 초기화 완료")
        
        except Exception as e:
            logger.error(f"❌ 데이터베이스 초기화 실패: {e}")
    
    def save_analysis(self, symbol, analysis_data, status='PENDING'):
        """분석 결과 저장"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO analyses 
                (timestamp, symbol, recommendation, confidence, current_price, target_price, stop_loss, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                symbol,
                analysis_data.get('recommendation', 'N/A'),
                analysis_data.get('confidence', 0),
                analysis_data.get('current_price', 0),
                analysis_data.get('price_target', 0),
                analysis_data.get('stop_loss', 0),
                status
            ))
            
            conn.commit()
            conn.close()
            
            logger.debug(f"✅ {symbol} 분석 저장 완료 ({status})")
        
        except Exception as e:
            logger.error(f"❌ 분석 저장 실패: {e}")
    
    def save_trade(self, symbol, action, quantity, price, status='PENDING'):
        """거래 저장"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO trades 
                (timestamp, symbol, action, quantity, price, status)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                symbol,
                action,
                quantity,
                price,
                status
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ {symbol} {action} {quantity}주 거래 저장")
        
        except Exception as e:
            logger.error(f"❌ 거래 저장 실패: {e}")
    
    def save_decision(self, decision, analysis_count, details):
        """결정 저장"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO decisions 
                (timestamp, decision, analysis_count, details)
                VALUES (?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                decision,
                analysis_count,
                details
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ 결정 저장 완료: {decision}")
        
        except Exception as e:
            logger.error(f"❌ 결정 저장 실패: {e}")
    
    def get_performance(self):
        """성능 분석"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    symbol,
                    COUNT(*) as total_analyses,
                    SUM(CASE WHEN status='APPROVED' THEN 1 ELSE 0 END) as approved_count
                FROM analyses
                GROUP BY symbol
                ORDER BY total_analyses DESC
            ''')
            
            results = cursor.fetchall()
            conn.close()
            
            return results
        
        except Exception as e:
            logger.error(f"❌ 성능 분석 실패: {e}")
            return []
    
    def get_recent_decisions(self, limit=10):
        """최근 결정 조회"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT timestamp, decision, analysis_count
                FROM decisions
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,))
            
            results = cursor.fetchall()
            conn.close()
            
            return results
        
        except Exception as e:
            logger.error(f"❌ 최근 결정 조회 실패: {e}")
            return []
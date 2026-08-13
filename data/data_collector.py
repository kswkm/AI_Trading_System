""" 
Toss증권 Open API를 사용한 데이터 수집 모듈
"""

import logging
import os
from datetime import datetime, timedelta

import requests

from api.toss_api import TossAPI
from data.mock_market_data import build_mock_market_snapshot, build_mock_news

logger = logging.getLogger(__name__)


class TossDataCollector:
    """Toss증권 데이터 수집 클래스"""

    def __init__(self, app_key, app_secret, finnhub_key='', use_demo=True):
        self.dry_run = bool(use_demo) or str(os.getenv('DRY_RUN', 'false')).strip().lower() in {'1', 'true', 'yes', 'y', 'on'}
        self.api = TossAPI(
            client_id=app_key,
            client_secret=app_secret,
            use_demo=use_demo,
        )
        self.finnhub_key = finnhub_key

    def collect_all(self, symbols):
        logger.info(f"📊 {len(symbols)}개 종목 데이터 수집 시작")
        if self.dry_run:
            logger.warning("🧪 DRY_RUN: Toss 실시간 데이터를 조회하지 않고 모의 시장 데이터를 사용합니다.")
            return build_mock_market_snapshot(list(symbols))

        data = {}
        for symbol in symbols:
            try:
                data[symbol] = self.get_stock_data(symbol)
            except Exception as exc:
                logger.error(f"❌ {symbol} 데이터 수집 실패: {exc}")
                data[symbol] = None
        return data

    def get_stock_data(self, symbol):
        if self.dry_run:
            logger.info("🧪 DRY_RUN: %s의 모의 종목 데이터를 반환합니다.", symbol)
            return build_mock_market_snapshot([symbol]).get(symbol)

        current_price_data = self.api.get_current_price(symbol)
        if not current_price_data:
            logger.warning(f"⚠️ {symbol} 현재가 조회 실패")
            return None

        historical = self.api.get_daily_chart(symbol, period=30)
        if not historical:
            logger.warning(f"⚠️ {symbol} 차트 데이터 조회 실패")
            historical = []

        return {
            'symbol': symbol,
            'current_price': current_price_data['current_price'],
            'open_price': current_price_data['open_price'],
            'high_price': current_price_data['high_price'],
            'low_price': current_price_data['low_price'],
            'volume': current_price_data['volume'],
            'historical_data': historical,
        }

    def get_latest_news(self, symbols):
        news_data = {}
        if self.dry_run:
            logger.warning("🧪 DRY_RUN: 모의 뉴스 피드를 사용합니다.")
            return build_mock_news(list(symbols))

        if not self.finnhub_key:
            logger.warning("⚠️ Finnhub API 키가 없습니다. 뉴스 수집을 건너뜁니다.")
            for symbol in symbols:
                news_data[symbol] = "뉴스 데이터 없음"
            return news_data

        for symbol in symbols:
            try:
                ticker = self.get_us_ticker(symbol)
                if not ticker:
                    news_data[symbol] = "뉴스 없음"
                    continue

                url = "https://finnhub.io/api/v1/company-news"
                params = {
                    'symbol': ticker,
                    'from': (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
                    'to': datetime.now().strftime('%Y-%m-%d'),
                    'token': self.finnhub_key,
                }

                response = requests.get(url, params=params, timeout=10)
                news = response.json()
                if isinstance(news, list) and len(news) > 0:
                    top_news = news[:3]
                    news_text = '\n'.join([
                        f"- {article['headline']} ({article['source']})"
                        for article in top_news
                    ])
                else:
                    news_text = "최근 뉴스 없음"

                news_data[symbol] = news_text
                logger.info(f"✅ {symbol} 뉴스 수집 완료")
            except Exception as exc:
                logger.warning(f"⚠️ {symbol} 뉴스 수집 실패: {exc}")
                news_data[symbol] = "뉴스 조회 불가"

        return news_data

    def get_us_ticker(self, korean_code):
        ticker_map = {
            '005930': 'SSNLF',
            '000660': 'LGPYY',
            '051910': 'LGGGY',
            '000270': 'KIACPY',
            '005380': 'HHDCY',
            '207940': 'SMDNF',
            '068270': 'CELLTRIP',
            '012330': 'DXCOF',
        }
        return ticker_map.get(korean_code)

    def get_account_balance(self, account_number):
        return self.api.get_account_balance(account_number)

    def get_holdings(self, account_number):
        return self.api.get_holdings(account_number)

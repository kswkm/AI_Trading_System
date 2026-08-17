""" 
Toss증권 Open API를 사용한 데이터 수집 모듈
"""

import logging
import re
import time

import requests

from api.toss_api import TossAPI

logger = logging.getLogger(__name__)


class TossDataCollector:
    """Toss증권 데이터 수집 클래스"""

    def __init__(self, app_key, app_secret):
        self.api = TossAPI(
            client_id=app_key,
            client_secret=app_secret,
        )

    def collect_all(self, symbols):
        logger.info(f"📊 {len(symbols)}개 종목 데이터 수집 시작")
        data = {}
        for symbol in symbols:
            try:
                data[symbol] = self.get_stock_data(symbol)
            except Exception as exc:
                logger.error(f"❌ {symbol} 데이터 수집 실패: {exc}")
                data[symbol] = None
        return data

    def discover_symbols(self, limit=100):
        """Toss 종목 마스터에서 차트 조회가 가능한 국내·해외 종목을 찾습니다."""
        symbols = []
        markets = ["KOSPI", "KOSDAQ", "NYSE", "NASDAQ"]
        per_market_limit = max(1, limit // len(markets))

        for market_index, market in enumerate(markets):
            if market_index:
                time.sleep(1.1)
            stock_items = self.api.list_stocks(market) or []
            market_count = 0

            for item in stock_items:
                symbol = str(item.get("symbol", "")).upper().strip()
                if not symbol or symbol in symbols:
                    continue

                symbols.append(symbol)
                market_count += 1
                if market_count >= per_market_limit or len(symbols) >= limit:
                    break

            if len(symbols) >= limit:
                break

        if not symbols:
            raise RuntimeError(
                "Toss에서 분석 가능한 종목을 찾지 못했습니다. "
                "Toss 종목 마스터 API와 TOSS_CLIENT_ID/SECRET을 확인하세요."
            )

        logger.info("✅ Toss 동적 종목 목록 조회 완료: %d개", len(symbols))
        return symbols

    def get_stock_data(self, symbol):
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
            'currency': 'KRW' if re.fullmatch(r'\d{6}', symbol) else 'USD',
        }

    def get_account_balance(self, account_number):
        return self.api.get_account_balance(account_number)

    def get_holdings(self, account_number):
        return self.api.get_holdings(account_number)

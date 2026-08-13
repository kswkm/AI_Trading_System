"""Sample market data used for dry-run validation without live broker calls."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List


def _sample_close_prices(base: float, drift: float = 0.0):
    return [
        round(base * (1 + drift + i * 0.004), 2)
        for i in range(30)
    ]


def build_mock_stock_data(symbol: str) -> Dict[str, object]:
    symbol_map = {
        "005930": {"base": 72000, "name": "삼성전자"},
        "000660": {"base": 87000, "name": "SK하이닉스"},
        "AAPL": {"base": 214.5, "name": "Apple"},
        "MSFT": {"base": 430.0, "name": "Microsoft"},
        "GOOGL": {"base": 178.0, "name": "Alphabet"},
        "TSLA": {"base": 221.5, "name": "Tesla"},
        "NVDA": {"base": 124.8, "name": "NVIDIA"},
    }
    info = symbol_map.get(symbol, {"base": 100.0, "name": symbol})
    base_price = float(info["base"])
    closes = _sample_close_prices(base_price)
    current_price = closes[-1]
    historical = []
    anchor = datetime.now() - timedelta(days=29)
    for i, close in enumerate(closes):
        point = anchor + timedelta(days=i)
        historical.append(
            {
                "date": point.strftime("%Y-%m-%d"),
                "close": close,
                "open": round(close * 0.995, 2),
                "high": round(close * 1.01, 2),
                "low": round(close * 0.99, 2),
                "volume": 1000000 + i * 35000,
            }
        )

    return {
        "symbol": symbol,
        "name": info["name"],
        "current_price": current_price,
        "open_price": round(current_price * 0.995, 2),
        "high_price": round(current_price * 1.01, 2),
        "low_price": round(current_price * 0.99, 2),
        "volume": 1500000,
        "historical_data": historical,
    }


def build_mock_market_snapshot(symbols: List[str]) -> Dict[str, dict]:
    return {symbol: build_mock_stock_data(symbol) for symbol in symbols}


def build_mock_news(symbols: List[str]) -> Dict[str, str]:
    news_map = {
        "005930": "[시뮬레이션] 삼성전자 반도체 수요 회복 기대. 모의 분석 기준으로 매수 관점 유지.",
        "000660": "[시뮬레이션] SK하이닉스 메모리 가격 안정화. 단기 반등 가능성 확인.",
        "AAPL": "[시뮬레이션] Apple AI 관련 수요 가속화. 반도체/소프트웨어 동반 개선.",
        "MSFT": "[시뮬레이션] Microsoft 클라우드 성장 둔화 완화. 기술주 반등 시나리오.",
        "GOOGL": "[시뮬레이션] Alphabet AI 투자 심리 안정. 웹검색 광고 매출 회복 기대.",
        "TSLA": "[시뮬레이션] Tesla 생산량 변동성 유지. 중단기 변동성 확대 전망.",
        "NVDA": "[시뮬레이션] NVIDIA AI 칩 공급 확대. 시황 우위 유지.",
    }
    return {symbol: news_map.get(symbol, "[시뮬레이션] 최근 시장 뉴스 없음") for symbol in symbols}

"""
QuantAnalyzer 테스트

실제 API를 호출하지 않고
샘플 과거 데이터로 퀀트 분석 로직을 테스트합니다.
"""

import unittest
from analysis.quant_analyzer import QuantAnalyzer


class TestQuantAnalyzer(unittest.TestCase):

    def setUp(self):
        """각 테스트 전에 실행"""
        self.analyzer = QuantAnalyzer()

        # 테스트용 과거 주가 데이터
        self.historical_data = [
            {
                "date": "2026-07-01",
                "close": 70000,
                "volume": 1000000
            },
            {
                "date": "2026-07-02",
                "close": 70500,
                "volume": 1100000
            },
            {
                "date": "2026-07-03",
                "close": 71000,
                "volume": 1200000
            },
            {
                "date": "2026-07-04",
                "close": 72000,
                "volume": 1300000
            },
            {
                "date": "2026-07-05",
                "close": 73000,
                "volume": 1500000
            },
            {
                "date": "2026-07-06",
                "close": 74000,
                "volume": 1600000
            },
            {
                "date": "2026-07-07",
                "close": 75000,
                "volume": 1700000
            },
            {
                "date": "2026-07-08",
                "close": 76000,
                "volume": 1800000
            },
            {
                "date": "2026-07-09",
                "close": 77000,
                "volume": 1900000
            },
            {
                "date": "2026-07-10",
                "close": 78000,
                "volume": 2000000
            },
        ]

    def test_analyzer_creation(self):
        """QuantAnalyzer 객체 생성 테스트"""

        self.assertIsNotNone(self.analyzer)

    def test_analyze_stock_returns_result(self):
        """analyze_stock()이 결과를 반환하는지 테스트"""

        result = self.analyzer.analyze_stock(
            "005930",
            self.historical_data
        )

        self.assertIsNotNone(result)
        self.assertIsInstance(result, dict)

    def test_result_contains_required_fields(self):
        """분석 결과에 필요한 필드가 있는지 테스트"""

        result = self.analyzer.analyze_stock(
            "005930",
            self.historical_data
        )

        required_fields = [
            "current_price",
            "rsi",
            "macd",
            "signal_line",
            "bb_position",
            "return_30d",
            "volatility",
            "sharpe_ratio",
            "signal_strength"
        ]

        for field in required_fields:
            with self.subTest(field=field):
                self.assertIn(field, result)

    def test_signal_strength_range(self):
        """신호 강도가 0~100 범위인지 테스트"""

        result = self.analyzer.analyze_stock(
            "005930",
            self.historical_data
        )

        signal_strength = result["signal_strength"]

        self.assertGreaterEqual(signal_strength, 0)
        self.assertLessEqual(signal_strength, 100)

    def test_current_price_is_numeric(self):
        """현재가가 숫자인지 테스트"""

        result = self.analyzer.analyze_stock(
            "005930",
            self.historical_data
        )

        self.assertIsInstance(
            result["current_price"],
            (int, float)
        )


if __name__ == "__main__":
    unittest.main()
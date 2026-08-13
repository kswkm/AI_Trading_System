"""
OrderExecutor 테스트

실제 Toss증권 주문을 실행하지 않습니다.
TossAPI를 Mock으로 대체합니다.
"""

import os
import unittest
from unittest.mock import patch

from trading.order_executor import OrderExecutor


class TestOrderExecutor(unittest.TestCase):

    def setUp(self):
        os.environ["TOSS_REQUIRE_PHONE_APPROVAL"] = "false"
        os.environ["TOSS_APPROVAL_WAIT_SECONDS"] = "1"
        self.api_patcher = patch("trading.order_executor.TossAPI")
        self.mock_api_class = self.api_patcher.start()
        self.mock_api = self.mock_api_class.return_value
        self.mock_api.get_holdings.return_value = [{"symbol": "005930", "quantity": 100}]
        self.executor = OrderExecutor(
            app_key="TEST_APP_KEY",
            app_secret="TEST_APP_SECRET",
            account_number="1234567890",
            account_password="0000",
            use_demo=True,
        )

    def tearDown(self):
        self.api_patcher.stop()

    def test_executor_creation(self):
        self.assertIsNotNone(self.executor)

    def test_hold_order_is_skipped(self):
        analysis = {
            "symbol": "005930",
            "recommendation": "HOLD",
            "current_price": 70000,
            "stop_loss": 66500,
        }
        result = self.executor.execute_order(analysis)
        self.assertEqual(result["status"], "SKIPPED")
        self.assertEqual(result["reason"], "HOLD")
        self.mock_api.place_order.assert_not_called()

    def test_buy_order(self):
        self.mock_api.place_order.return_value = {"order_number": "TEST12345"}
        analysis = {
            "symbol": "005930",
            "recommendation": "BUY",
            "current_price": 70000,
            "stop_loss": 66500,
        }
        result = self.executor.execute_order(analysis)
        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(result["symbol"], "005930")
        self.assertEqual(result["action"], "매수")
        self.assertEqual(result["quantity"], 7)
        self.mock_api.place_order.assert_called_once()

    def test_strong_buy_order(self):
        self.mock_api.place_order.return_value = {"order_number": "TEST12345"}
        analysis = {
            "symbol": "005930",
            "recommendation": "STRONG_BUY",
            "current_price": 70000,
            "stop_loss": 66500,
        }
        result = self.executor.execute_order(analysis)
        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(result["action"], "매수")
        self.assertEqual(result["quantity"], 7)

    def test_sell_order(self):
        self.mock_api.place_order.return_value = {"order_number": "TEST12345"}
        analysis = {
            "symbol": "005930",
            "recommendation": "SELL",
            "current_price": 70000,
            "stop_loss": 73500,
        }
        result = self.executor.execute_order(analysis)
        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(result["action"], "매도")
        self.assertEqual(result["quantity"], 50)

    def test_strong_sell_order(self):
        self.mock_api.place_order.return_value = {"order_number": "TEST12345"}
        analysis = {
            "symbol": "005930",
            "recommendation": "STRONG_SELL",
            "current_price": 70000,
            "stop_loss": 73500,
        }
        result = self.executor.execute_order(analysis)
        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(result["action"], "매도")
        self.assertEqual(result["quantity"], 50)

    def test_order_failure(self):
        self.mock_api.place_order.return_value = None
        analysis = {
            "symbol": "005930",
            "recommendation": "BUY",
            "current_price": 70000,
            "stop_loss": 66500,
        }
        result = self.executor.execute_order(analysis)
        self.assertEqual(result["status"], "FAILED")

def test_dry_run_mode_skips_real_api_call(self):
    dry_run_executor = OrderExecutor(
        app_key="TEST_APP_KEY",
        app_secret="TEST_APP_SECRET",
        account_number="1234567890",
        account_password="0000",
        use_demo=True,
        dry_run=True,
    )
    analysis = {
        "symbol": "005930",
        "recommendation": "BUY",
        "current_price": 70000,
        "stop_loss": 66500,
    }
    result = dry_run_executor.execute_order(analysis)
    self.assertEqual(result["status"], "SUCCESS")
    self.assertTrue(result.get("dry_run"))
    self.mock_api.place_order.assert_not_called()


if __name__ == "__main__":
    unittest.main()

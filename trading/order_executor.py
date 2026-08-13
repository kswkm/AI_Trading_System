"""Order execution module used to send orders through the Toss API."""

import logging
import os
import time
from datetime import datetime, timezone

from api.toss_api import TossAPI

logger = logging.getLogger(__name__)


class OrderExecutor:
    """Handles buy and sell decisions for the trading workflow."""

    _DRY_RUN_REFERENCE_PRICES = {
        "005930": 70000,
        "000660": 87000,
        "AAPL": 214.50,
        "MSFT": 430.00,
        "GOOGL": 178.00,
        "TSLA": 221.50,
        "NVDA": 124.80,
    }

    def __init__(
        self,
        app_key,
        app_secret,
        account_number,
        account_password,
        use_demo=True,
        trading_budget=1_000_000,
        max_position_ratio=0.5,
        dry_run=False,
    ):
        self.ki_api = TossAPI(
            client_id=app_key,
            client_secret=app_secret,
            account_seq=account_number,
            use_demo=use_demo,
        )

        self.account_number = account_number
        self.account_password = account_password
        self.use_demo = use_demo
        self.dry_run = bool(dry_run)
        self.trading_budget = trading_budget
        self.max_position_ratio = max_position_ratio
        self.max_per_stock = trading_budget * max_position_ratio
        self.require_phone_approval = bool(
            str(os.getenv("TOSS_REQUIRE_PHONE_APPROVAL", "true")).strip().lower() in {"1", "true", "yes", "y", "on"}
        )
        self.approval_wait_seconds = int(os.getenv("TOSS_APPROVAL_WAIT_SECONDS", "60"))
        self._dry_run_balance = float(trading_budget)
        self._dry_run_holdings = {}
        self._dry_run_orders = []

        mode_label = "DRY_RUN" if self.dry_run else ("demo" if use_demo else "live")
        logger.info("Trading executor initialized in %s mode", mode_label)
        logger.info("Daily trading budget: %,.0f KRW", trading_budget)

    def _dry_run_order_number(self, prefix="DRYRUN"):
        return f"{prefix}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"

    def _dry_run_reference_price(self, symbol):
        return float(self._DRY_RUN_REFERENCE_PRICES.get(str(symbol), 10000.0))

    def wait_for_phone_approval(self, symbol, quantity, is_buy):
        if self.dry_run:
            logger.info("🧪 DRY_RUN: phone approval is skipped because no real order is transmitted.")
            return True

        if not self.require_phone_approval:
            logger.info("📱 phone approval check disabled by config; proceeding without Toss app approval.")
            return True

        approval_flag = str(os.getenv("TOSS_PHONE_APPROVED", "")).strip().lower()
        if approval_flag in {"1", "true", "yes", "y", "approved"}:
            logger.info("📱 Toss app approval already marked by environment; proceeding.")
            return True

        approval_file = "toss_phone_approval.txt"
        if os.path.exists(approval_file):
            try:
                with open(approval_file, "r", encoding="utf-8") as handle:
                    content = handle.read().strip().lower()
                if content in {"1", "true", "yes", "y", "approved"}:
                    os.remove(approval_file)
                    logger.info("📱 Toss app approval detected from %s; proceeding.", approval_file)
                    return True
            except OSError:
                pass

        action = "매수" if is_buy else "매도"
        logger.warning(
            "📱 Toss 앱에서 %s 주문 승인(알림/모바일 인증)을 기다리는 중: symbol=%s quantity=%s",
            action,
            symbol,
            quantity,
        )
        print("\n=== Toss 인증 대기 ===")
        print(f"주문: {action} {symbol} {quantity}주")
        print("휴대폰 Toss 앱의 인증 알림을 승인한 뒤 Enter 키를 눌러주세요.")
        print("승인 후에는 이 프로세스가 계속 진행됩니다.")
        print("실거래 전용: 승인하지 않으면 주문이 전송되지 않습니다.")

        start = time.time()
        while True:
            approval_flag = str(os.getenv("TOSS_PHONE_APPROVED", "")).strip().lower()
            if approval_flag in {"1", "true", "yes", "y", "approved"}:
                logger.info("📱 Toss app approval confirmed via environment variable.")
                return True

            if os.path.exists(approval_file):
                try:
                    with open(approval_file, "r", encoding="utf-8") as handle:
                        content = handle.read().strip().lower()
                    if content in {"1", "true", "yes", "y", "approved"}:
                        os.remove(approval_file)
                        logger.info("📱 Toss app approval confirmed via file marker.")
                        return True
                except OSError:
                    pass

            if time.time() - start > self.approval_wait_seconds:
                logger.warning("⏰ Toss phone approval timed out after %s seconds.", self.approval_wait_seconds)
                return False

            try:
                input()
                return True
            except EOFError:
                time.sleep(1)

    def _simulate_dry_run_order(self, symbol, quantity, is_buy, order_type="MARKET"):
        quantity = int(quantity)
        reference_price = self._dry_run_reference_price(symbol)
        notional = reference_price * quantity
        fee = round(notional * 0.00015, 2)
        action = "BUY" if is_buy else "SELL"

        if is_buy:
            if self._dry_run_balance < notional + fee:
                return {
                    "status": "REJECTED",
                    "symbol": symbol,
                    "action": action,
                    "quantity": quantity,
                    "reason": "INSUFFICIENT_AVAILABLE_CASH",
                    "estimated_price": reference_price,
                    "notional": notional,
                    "fee": fee,
                    "dry_run": True,
                    "message": "dry-run account does not have enough cash for this order.",
                }
            self._dry_run_balance -= notional + fee
            current_qty = int(self._dry_run_holdings.get(symbol, 0))
            self._dry_run_holdings[symbol] = current_qty + quantity
        else:
            current_qty = int(self._dry_run_holdings.get(symbol, 0))
            if quantity > current_qty:
                return {
                    "status": "REJECTED",
                    "symbol": symbol,
                    "action": action,
                    "quantity": quantity,
                    "reason": "INSUFFICIENT_HOLDINGS",
                    "estimated_price": reference_price,
                    "notional": notional,
                    "fee": fee,
                    "dry_run": True,
                    "message": "dry-run account does not hold enough shares to sell.",
                }
            self._dry_run_balance += notional - fee
            self._dry_run_holdings[symbol] = current_qty - quantity
            if self._dry_run_holdings[symbol] <= 0:
                self._dry_run_holdings.pop(symbol, None)

        order_record = {
            "order_number": self._dry_run_order_number(),
            "symbol": symbol,
            "quantity": quantity,
            "action": action,
            "order_type": order_type,
            "status": "ACCEPTED",
            "estimated_price": reference_price,
            "notional": notional,
            "fee": fee,
            "dry_run": True,
            "simulated": True,
            "transmission": "SIMULATED",
            "message": "dry-run order accepted and queued for simulated execution; no funds moved.",
            "processed_at": datetime.now(timezone.utc).isoformat(),
        }
        self._dry_run_orders.append(order_record)
        return order_record

    def execute_order(self, analysis):
        try:
            symbol = analysis["symbol"]
            recommendation = analysis.get("recommendation", "HOLD")

            if recommendation == "HOLD":
                logger.info("%s: HOLD - skipping order", symbol)
                return {"status": "SKIPPED", "symbol": symbol, "reason": "HOLD"}

            if recommendation in ["SELL", "STRONG_SELL"]:
                logger.info("%s: sell signal detected", symbol)
                return self.execute_sell(analysis)

            if recommendation in ["BUY", "STRONG_BUY"]:
                return self.execute_buy(analysis)

            return {
                "status": "SKIPPED",
                "symbol": symbol,
                "reason": "UNKNOWN_RECOMMENDATION",
            }

        except Exception as exc:
            logger.error("Order execution error for %s: %s", analysis.get("symbol"), exc, exc_info=True)
            return {
                "status": "ERROR",
                "symbol": analysis.get("symbol"),
                "error": str(exc),
            }

    def execute_buy(self, analysis):
        symbol = analysis["symbol"]
        current_price = float(analysis.get("current_price", 0))

        max_amount = min(self.trading_budget, self.max_per_stock)
        quantity = int(max_amount // current_price) if current_price > 0 else 0

        if quantity <= 0:
            logger.warning("%s: insufficient budget to buy even one share.", symbol)
            return {"status": "SKIPPED", "symbol": symbol, "reason": "INSUFFICIENT_BUDGET"}

        order_amount = current_price * quantity
        logger.info("Preparing buy order: %s", symbol)
        logger.info("Current price: %,.0f KRW", current_price)
        logger.info("Quantity: %s shares", quantity)
        logger.info("Expected order value: %,.0f KRW", order_amount)

        order_result = self.place_market_order(
            symbol=symbol,
            quantity=quantity,
            is_buy=True,
        )

        if order_result:
            logger.info("Buy order succeeded for %s %s shares", symbol, quantity)
            self.set_stop_loss(
                symbol=symbol,
                current_price=current_price,
                stop_loss_price=analysis.get("stop_loss", current_price * 0.95),
            )
            self.set_take_profit(
                symbol=symbol,
                current_price=current_price,
                target_price=analysis.get("price_target", current_price * 1.05),
            )
            return {
                "status": "SUCCESS",
                "symbol": symbol,
                "action": "매수",
                "quantity": quantity,
                "order_amount": order_amount,
                "order_number": order_result.get("order_number"),
                "dry_run": bool(order_result.get("dry_run", False)),
            }

        logger.error("Buy order failed for %s", symbol)
        return {"status": "FAILED", "symbol": symbol}

    def execute_sell(self, analysis):
        symbol = analysis["symbol"]
        holdings = self.ki_api.get_holdings(self.account_number)

        holding_quantity = 0
        if holdings:
            for holding in holdings:
                if str(holding.get("symbol")) == str(symbol):
                    holding_quantity = int(
                        holding.get("quantity", holding.get("qty", 0))
                    )
                    break

        if holding_quantity <= 0:
            logger.info("%s: no available position to sell", symbol)
            return {"status": "SKIPPED", "symbol": symbol, "reason": "NO_HOLDING"}

        quantity = max(1, holding_quantity // 2)
        order_result = self.place_market_order(
            symbol=symbol,
            quantity=quantity,
            is_buy=False,
        )

        if order_result:
            return {
                "status": "SUCCESS",
                "symbol": symbol,
                "action": "매도",
                "quantity": quantity,
                "order_number": order_result.get("order_number"),
                "dry_run": bool(order_result.get("dry_run", False)),
            }

        return {"status": "FAILED", "symbol": symbol}

    def place_market_order(self, symbol, quantity, is_buy):
        if self.dry_run:
            action = "매수" if is_buy else "매도"
            simulated = self._simulate_dry_run_order(symbol, quantity, is_buy, order_type="MARKET")
            logger.warning(
                "DRY_RUN: simulated %s order for %s %s shares; no real transmission happened.",
                action,
                symbol,
                quantity,
            )
            return simulated

        if not self.wait_for_phone_approval(symbol, quantity, is_buy):
            logger.warning("📱 Toss phone approval was not received; live order was blocked.")
            return {
                "order_number": None,
                "symbol": symbol,
                "quantity": int(quantity),
                "status": "PENDING_APPROVAL",
                "dry_run": False,
                "message": "Toss app approval is required before sending the order.",
            }

        try:
            return self.ki_api.place_order(
                account_number=self.account_number,
                password=self.account_password,
                symbol=symbol,
                quantity=quantity,
                price=0,
                order_type="00",
                is_buy=is_buy,
            )
        except Exception as exc:
            logger.error("Market order failed: %s", exc)
            return None

    def place_limit_order(self, symbol, quantity, limit_price, is_buy):
        if self.dry_run:
            action = "매수" if is_buy else "매도"
            simulated = self._simulate_dry_run_order(symbol, quantity, is_buy, order_type="LIMIT")
            simulated["limit_price"] = int(limit_price)
            logger.warning(
                "DRY_RUN: simulated %s limit order for %s %s shares; no real transmission happened.",
                action,
                symbol,
                quantity,
            )
            return simulated

        if not self.wait_for_phone_approval(symbol, quantity, is_buy):
            logger.warning("📱 Toss phone approval was not received; limit order was blocked.")
            return {
                "order_number": None,
                "symbol": symbol,
                "quantity": int(quantity),
                "status": "PENDING_APPROVAL",
                "dry_run": False,
                "message": "Toss app approval is required before sending the order.",
            }

        try:
            return self.ki_api.place_order(
                account_number=self.account_number,
                password=self.account_password,
                symbol=symbol,
                quantity=quantity,
                price=int(limit_price),
                order_type="01",
                is_buy=is_buy,
            )
        except Exception as exc:
            logger.error("Limit order failed: %s", exc)
            return None


    def set_stop_loss(self, symbol, current_price, stop_loss_price):
        logger.info("Stop-loss for %s is %s, current price %s", symbol, stop_loss_price, current_price)
        return True

    def set_take_profit(self, symbol, current_price, target_price):
        logger.info("Take-profit for %s is %s, current price %s", symbol, target_price, current_price)
        return True

    def get_account_status(self):
        if self.dry_run:
            cash_after_orders = self._dry_run_balance
            status = {
                "dry_run": True,
                "balance": {
                    "available_cash": cash_after_orders,
                    "total_budget": self.trading_budget,
                    "cash_used": self.trading_budget - cash_after_orders,
                },
                "holdings": [
                    {
                        "symbol": symbol,
                        "quantity": quantity,
                        "average_price": self._dry_run_reference_price(symbol),
                    }
                    for symbol, quantity in self._dry_run_holdings.items()
                ],
                "message": "dry-run account status is simulated and does not represent real funds.",
            }
            logger.info(
                "[DRY_RUN_ACCOUNT] available_cash=%.2f total_budget=%.2f cash_used=%.2f holdings=%s",
                status["balance"]["available_cash"],
                status["balance"]["total_budget"],
                status["balance"]["cash_used"],
                status["holdings"],
            )
            return status

        try:
            balance = self.ki_api.get_account_balance(self.account_number)
            holdings = self.ki_api.get_holdings(self.account_number)
            return {"balance": balance, "holdings": holdings}
        except Exception as exc:
            logger.error("Account status query failed: %s", exc)
            return None

    def cancel_order(self, order_number, symbol):
        if self.dry_run:
            for order in self._dry_run_orders:
                if order.get("order_number") == order_number:
                    order["status"] = "CANCELLED"
                    order["message"] = "dry-run order cancelled without any real transmission."
                    logger.info("Dry-run order cancellation succeeded: %s", order_number)
                    return order
            logger.warning("Dry-run order not found for cancellation: %s", order_number)
            return {"order_number": order_number, "status": "NOT_FOUND", "dry_run": True}

        try:
            result = self.ki_api.cancel_order(
                account_number=self.account_number,
                order_number=order_number,
                symbol=symbol,
            )
            if result:
                logger.info("Order cancellation succeeded: %s", order_number)
            else:
                logger.error("Order cancellation failed: %s", order_number)
            return result
        except Exception as exc:
            logger.error("Order cancellation error: %s", exc)
            return None

"""Dry-run smoke test for the Toss-based AI trading workflow."""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("DRY_RUN", "true")

from data.data_collector import TossDataCollector
from trading.order_executor import OrderExecutor


def main() -> None:
    symbols = ["005930", "000660", "AAPL", "NVDA"]
    collector = TossDataCollector(app_key="demo", app_secret="demo", finnhub_key="", use_demo=True)
    snapshot = collector.collect_all(symbols)
    print("[market_snapshot]", json.dumps({k: {"symbol": v["symbol"], "current_price": v["current_price"]} for k, v in snapshot.items()}, ensure_ascii=False, indent=2))

    executor = OrderExecutor(
        app_key="demo",
        app_secret="demo",
        account_number="1234567890",
        account_password="0000",
        use_demo=True,
        dry_run=True,
    )
    result = executor.execute_order({
        "symbol": "005930",
        "recommendation": "BUY",
        "current_price": 72000,
        "stop_loss": 68400,
    })
    print("[order_result]", json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

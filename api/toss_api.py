"""
Toss증권 Open API 어댑터

Toss의 OAuth 2.0 기반 인증과 주문/조회 API와 연결한다.
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


class TossAPI:
    """Toss증권 Open API용 브로커 구현체"""

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        base_url: Optional[str] = None,
        account_seq: Optional[str] = None,
    ):
        self.client_id = client_id or os.getenv("TOSS_CLIENT_ID", "")
        self.client_secret = client_secret or os.getenv("TOSS_CLIENT_SECRET", "")
        self.base_url = (base_url or os.getenv("TOSS_BASE_URL") or "https://api.tossinvest.com").rstrip("/")
        self.token_url = os.getenv("TOSS_TOKEN_URL") or f"{self.base_url}/oauth2/token"
        self.account_seq = account_seq or os.getenv("TOSS_ACCOUNT_SEQ") or os.getenv("TOSS_ACCOUNT_NUMBER")
        self.access_token = None
        self.token_type = "Bearer"

        logger.info("🔗 Toss증권 API 초기화")
        self.get_access_token()

    @staticmethod
    def _find_payload(data: Any, keys: List[str]) -> Any:
        if not isinstance(data, dict):
            return data
        for key in keys:
            if key in data:
                return data[key]
        return data

    def _request(self, method, path, params=None, json_data=None, headers=None, timeout=20, retry_auth=True):
        if not self.access_token:
            self.get_access_token()

        req_headers = {
            "Content-Type": "application/json",
            "Authorization": f"{self.token_type} {self.access_token}",
        }
        if headers:
            req_headers.update(headers)

        url = path if path.startswith("http") else f"{self.base_url}{path}"

        try:
            response = requests.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                headers=req_headers,
                timeout=timeout,
            )
            try:
                payload = response.json()
            except ValueError:
                payload = {"raw": response.text}

            if response.status_code == 401 and self.access_token and retry_auth:
                logger.warning("⚠️ Toss access token이 만료되었거나 유효하지 않아 재발급합니다.")
                self.access_token = None
                if self.get_access_token():
                    return self._request(
                        method,
                        path,
                        params=params,
                        json_data=json_data,
                        headers=headers,
                        timeout=timeout,
                        retry_auth=False,
                    )

            if response.status_code >= 400:
                logger.error("❌ Toss API 오류: status=%s path=%s payload=%s", response.status_code, path, payload)
                return None
            return payload
        except Exception as exc:
            logger.error("❌ Toss API 호출 실패: %s", exc)
            return None

    def get_access_token(self) -> bool:
        if not self.client_id or not self.client_secret:
            logger.warning("⚠️ Toss API 인증 정보가 없습니다. 토큰 발급을 건너뜁니다.")
            return False

        try:
            response = requests.post(
                self.token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                timeout=20,
            )
            response.raise_for_status()
            payload = response.json()
            self.access_token = payload.get("access_token")
            self.token_type = payload.get("token_type", "Bearer")

            if self.access_token:
                logger.info("✅ Toss access token 발급 완료")
                return True

            logger.warning("⚠️ Toss access token이 비어 있습니다: %s", payload)
            return False
        except Exception as exc:
            logger.error("❌ Toss access token 발급 실패: %s", exc)
            return False

    def get_headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"{self.token_type} {self.access_token}",
        }

    def get_current_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        payload = self._request("GET", "/api/v1/prices", params={"symbols": symbol})
        if not payload:
            return None

        data = self._find_payload(payload, ["data", "result", "output", "body"])
        if isinstance(data, list):
            data = data[0] if data else {}
        if not isinstance(data, dict):
            return None

        return {
            "symbol": symbol,
            "current_price": float(data.get("currentPrice") or data.get("price") or data.get("lastPrice") or 0),
            "open_price": 0,
            "high_price": 0,
            "low_price": 0,
            "volume": 0,
            "timestamp": datetime.now().isoformat(),
            "currency": data.get("currency"),
        }

    def get_daily_chart(self, symbol: str, period: int = 30) -> Optional[List[Dict[str, Any]]]:
        payload = self._request("GET", "/api/v1/candles", params={"symbol": symbol, "interval": "1d", "count": period})
        if not payload:
            return None

        data = self._find_payload(payload, ["data", "result", "candles", "chart", "body"])
        if isinstance(data, dict):
            data = data.get("candles") or data.get("items") or data.get("series") or []
        if not isinstance(data, list):
            return None

        chart_data = []
        for item in data[:period]:
            if isinstance(item, dict):
                chart_data.append({
                    "date": item.get("date") or item.get("time") or item.get("candleDate"),
                    "open": float(item.get("open") or item.get("openPrice") or 0),
                    "high": float(item.get("high") or item.get("highPrice") or 0),
                    "low": float(item.get("low") or item.get("lowPrice") or 0),
                    "close": float(item.get("close") or item.get("closePrice") or 0),
                    "volume": int(item.get("volume") or item.get("tradingVolume") or 0),
                })
        return chart_data

    def list_stocks(self, market: str) -> Optional[List[Dict[str, Any]]]:
        payload = self._request(
            "GET",
            "/api/v1/stocks/all",
            params={
                "market": market,
                "status": "ACTIVE",
                "securityType": "STOCK",
                "commonShare": "true",
            },
        )
        if not payload:
            return None

        data = self._find_payload(payload, ["data", "result", "output", "body"])
        return data if isinstance(data, list) else []

    def get_account_balance(self, account_number: str) -> Optional[Dict[str, Any]]:
        account_key = account_number or self.account_seq
        if not account_key:
            return None
        payload = self._request("GET", f"/api/v1/accounts/{account_key}", headers={"X-Tossinvest-Account": account_key})
        if not payload:
            return None
        data = self._find_payload(payload, ["data", "result", "body"])
        return data if isinstance(data, dict) else payload

    def get_holdings(self, account_number: str) -> Optional[List[Dict[str, Any]]]:
        account_key = account_number or self.account_seq
        if not account_key:
            return []

        payload = self._request("GET", f"/api/v1/accounts/{account_key}/holdings", headers={"X-Tossinvest-Account": account_key})
        if not payload:
            return []

        data = self._find_payload(payload, ["data", "result", "body"])
        if isinstance(data, dict):
            data = data.get("items") or data.get("holdings") or data.get("positions") or []
        if not isinstance(data, list):
            return []

        holdings = []
        for item in data:
            if isinstance(item, dict):
                holdings.append({
                    "symbol": item.get("symbol") or item.get("ticker") or item.get("code"),
                    "quantity": int(item.get("quantity") or item.get("qty") or 0),
                    "price": float(item.get("price") or item.get("avgPrice") or 0),
                    "current_price": float(item.get("currentPrice") or item.get("price") or 0),
                })
        return holdings


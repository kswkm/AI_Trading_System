import io
import json
import os
import re
import time
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv


load_dotenv()


class DARTClient:
    """Open DART API 클라이언트"""

    BASE_URL = "https://opendart.fss.or.kr/api"
    CORP_CODE_CACHE_TTL_SECONDS = 7 * 24 * 3600

    def __init__(self, api_key: Optional[str] = None):
        """
        DART API 클라이언트 초기화

        Args:
            api_key:
                Open DART 인증키
                지정하지 않으면 .env의 DART_API_KEY 사용
        """

        self.api_key = (
            api_key
            or os.getenv("DART_API_KEY")
        )

        if not self.api_key:
            raise ValueError(
                "DART_API_KEY가 설정되지 않았습니다."
            )

        self._corp_code_map = None

    # ---------------------------------------------------------
    # 기업 코드 목록
    # ---------------------------------------------------------

    def get_corp_code_list(self):
        """
        DART 기업코드 전체 목록을 가져온다.

        반환:
            기업명 / 종목코드 / 고유번호(corp_code)
        """

        url = f"{self.BASE_URL}/corpCode.xml"

        params = {
            "crtfc_key": self.api_key
        }

        response = requests.get(
            url,
            params=params,
            timeout=20
        )

        response.raise_for_status()

        return response.content

    # ---------------------------------------------------------
    # 종목코드 → corp_code 매핑
    # ---------------------------------------------------------

    def _corp_code_cache_path(self) -> Path:
        return Path(__file__).resolve().parent / ".cache" / "dart_corp_codes.json"

    def _load_corp_code_map(self, force_refresh: bool = False):
        """corpCode.xml.zip을 내려받아 stock_code → corp_code 매핑을 만든다."""

        cache_path = self._corp_code_cache_path()

        if not force_refresh and cache_path.exists():
            age = time.time() - cache_path.stat().st_mtime
            if age < self.CORP_CODE_CACHE_TTL_SECONDS:
                with open(cache_path, "r", encoding="utf-8") as f:
                    return json.load(f)

        raw = self.get_corp_code_list()

        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            xml_bytes = zf.read(zf.namelist()[0])

        root = ET.fromstring(xml_bytes)

        mapping = {}
        for item in root.iter("list"):
            stock_code = (item.findtext("stock_code") or "").strip()
            corp_code = (item.findtext("corp_code") or "").strip()
            if stock_code:
                mapping[stock_code] = corp_code

        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(mapping, f)

        return mapping

    def get_corp_code_by_stock_code(self, stock_code: str) -> Optional[str]:
        """6자리 종목코드로 DART corp_code를 조회한다."""

        if self._corp_code_map is None:
            self._corp_code_map = self._load_corp_code_map()

        return self._corp_code_map.get(stock_code)

    # ---------------------------------------------------------
    # 기업 기본정보
    # ---------------------------------------------------------

    def get_company_info(
        self,
        corp_code: str
    ):
        """
        특정 기업의 기본정보를 조회한다.

        Args:
            corp_code:
                DART 고유번호
        """

        url = f"{self.BASE_URL}/company.json"

        params = {
            "crtfc_key": self.api_key,
            "corp_code": corp_code
        }

        response = requests.get(
            url,
            params=params,
            timeout=10
        )

        response.raise_for_status()

        data = response.json()

        if data.get("status") != "000":
            raise RuntimeError(
                f"DART API 오류: {data.get('message')}"
            )

        return data

    # ---------------------------------------------------------
    # 공시 검색
    # ---------------------------------------------------------

    def search_filings(
        self,
        corp_code: str,
        days: int = 30,
        page_no: int = 1,
        page_count: int = 20
    ):
        """
        특정 기업의 최근 공시를 검색한다.

        Args:
            corp_code:
                DART 기업 고유번호

            days:
                최근 며칠 동안의 공시를 검색할지

            page_no:
                페이지 번호

            page_count:
                페이지당 결과 수
        """

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        url = f"{self.BASE_URL}/list.json"

        params = {
            "crtfc_key": self.api_key,
            "corp_code": corp_code,
            "bgn_de": start_date.strftime("%Y%m%d"),
            "end_de": end_date.strftime("%Y%m%d"),
            "page_no": page_no,
            "page_count": page_count,
            "sort": "date",
            "sort_mth": "desc"
        }

        response = requests.get(
            url,
            params=params,
            timeout=10
        )

        response.raise_for_status()

        data = response.json()

        if data.get("status") != "000":
            raise RuntimeError(
                f"DART API 오류: {data.get('message')}"
            )

        return data

    # ---------------------------------------------------------
    # 재무정보
    # ---------------------------------------------------------

    def get_financials(
        self,
        corp_code: str,
        bsns_year: str,
        reprt_code: str = "11011"
    ):
        """
        기업 재무정보를 가져온다.

        Args:
            corp_code:
                DART 기업 고유번호

            bsns_year:
                사업연도
                예: "2025"

            reprt_code:
                11011 = 사업보고서
                11012 = 반기보고서
                11013 = 1분기보고서
                11014 = 3분기보고서
        """

        url = f"{self.BASE_URL}/fnlttSinglAcnt.json"

        params = {
            "crtfc_key": self.api_key,
            "corp_code": corp_code,
            "bsns_year": bsns_year,
            "reprt_code": reprt_code
        }

        response = requests.get(
            url,
            params=params,
            timeout=20
        )

        response.raise_for_status()

        data = response.json()

        if data.get("status") != "000":
            raise RuntimeError(
                f"DART API 오류: {data.get('message')}"
            )

        return data

    # ---------------------------------------------------------
    # 주요 재무계정 요약
    # ---------------------------------------------------------

    def get_key_financials(self, corp_code: str, years_to_try=None):
        """최근 사업보고서에서 매출액/영업이익/당기순이익 등 주요 계정을 조회한다.

        여러 사업연도를 순서대로 시도하며, 첫 성공 결과를 반환한다.
        """

        if years_to_try is None:
            current_year = datetime.now().year
            years_to_try = [str(current_year - 1), str(current_year - 2)]

        target_accounts = ["매출액", "영업이익", "당기순이익", "자산총계", "부채총계", "자본총계"]

        for year in years_to_try:
            try:
                data = self.get_financials(corp_code, bsns_year=year, reprt_code="11011")
            except Exception:
                continue

            rows = data.get("list", [])
            if not rows:
                continue

            summary = {}
            for row in rows:
                account_nm = (row.get("account_nm") or "").strip()
                if account_nm not in target_accounts:
                    continue

                # 연결재무제표(CFS)를 개별재무제표(OFS)보다 우선한다
                if account_nm in summary and summary[account_nm].get("fs_div") == "CFS":
                    continue

                summary[account_nm] = {
                    "thstrm_amount": row.get("thstrm_amount"),
                    "frmtrm_amount": row.get("frmtrm_amount"),
                    "fs_div": row.get("fs_div"),
                }

            if summary:
                summary["_bsns_year"] = year
                return summary

        return {}

    # ---------------------------------------------------------
    # 공시 원문 발췌
    # ---------------------------------------------------------

    def get_filing_document_excerpt(self, rcept_no: str, max_chars: int = 800) -> str:
        """공시 원문(zip)을 내려받아 태그를 제거한 텍스트 일부를 반환한다."""

        url = f"{self.BASE_URL}/document.xml"

        params = {
            "crtfc_key": self.api_key,
            "rcept_no": rcept_no,
        }

        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()

        content = response.content

        # 정상 응답이 아니면(오류 메시지 XML 등) zip 시그니처가 없다
        if content[:2] != b"PK":
            return ""

        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            names = zf.namelist()
            if not names:
                return ""
            raw = zf.read(names[0])

        text = None
        for encoding in ("utf-8", "euc-kr", "cp949"):
            try:
                text = raw.decode(encoding)
                break
            except UnicodeDecodeError:
                continue

        if text is None:
            return ""

        plain = re.sub(r"<[^>]+>", " ", text)
        plain = re.sub(r"\s+", " ", plain).strip()

        return plain[:max_chars]
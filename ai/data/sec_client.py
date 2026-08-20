import re
import requests
from typing import Optional


class SECClient:
    """SEC EDGAR API 클라이언트"""

    TICKER_URL = "https://www.sec.gov/files/company_tickers.json"
    SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{}.json"
    COMPANY_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{}.json"

    def __init__(self, user_agent: str):
        """
        SEC API 클라이언트 초기화

        Args:
            user_agent:
                SEC에서 요구하는 User-Agent.
                예:
                "AI_Trading_System kswkmy7556@gmail.com"
        """

        self.headers = {
            "User-Agent": user_agent,
            "Accept-Encoding": "gzip, deflate",
        }

        self.ticker_map = None

    # ---------------------------------------------------------
    # Ticker → CIK 매핑
    # ---------------------------------------------------------

    def _load_ticker_map(self):
        """SEC에서 미국 주식 Ticker → CIK 정보를 가져온다."""

        # www.sec.gov 호스트로 요청 (Host 헤더를 강제하지 않는다)
        response = requests.get(
            self.TICKER_URL,
            headers={k: v for k, v in self.headers.items() if k != "Host"},
            timeout=10
        )

        response.raise_for_status()

        data = response.json()

        ticker_map = {}

        for company in data.values():

            ticker = company.get("ticker")

            cik = company.get("cik_str")

            if ticker and cik:

                ticker_map[ticker.upper()] = str(
                    cik
                ).zfill(10)

        self.ticker_map = ticker_map

    def get_cik(self, ticker: str) -> Optional[str]:
        """
        Ticker를 이용해서 SEC CIK를 찾는다.

        예:
            AAPL → 0000320193
        """

        if self.ticker_map is None:
            self._load_ticker_map()

        return self.ticker_map.get(ticker.upper())

    # ---------------------------------------------------------
    # 기업 공시
    # ---------------------------------------------------------

    def get_company_filings(self, ticker: str):
        """
        특정 기업의 SEC 공시 제출 정보를 가져온다.

        예:
            AAPL → 최근 10-K, 10-Q, 8-K 등의 제출 정보
        """

        cik = self.get_cik(ticker)

        if not cik:
            raise ValueError(
                f"SEC에서 {ticker}의 CIK를 찾을 수 없습니다."
            )

        url = self.SUBMISSIONS_URL.format(cik)

        response = requests.get(
            url,
            headers=self.headers,
            timeout=10
        )

        response.raise_for_status()

        return response.json()

    # ---------------------------------------------------------
    # 최근 공시
    # ---------------------------------------------------------

    def get_recent_filings(
        self,
        ticker: str,
        limit: int = 10
    ):
        """
        최근 공시 목록을 가져온다.

        Args:
            ticker: 미국 주식 티커
            limit: 가져올 공시 개수
        """

        data = self.get_company_filings(ticker)

        recent = data.get("filings", {}).get("recent", {})

        forms = recent.get("form", [])
        dates = recent.get("filingDate", [])
        accession_numbers = recent.get(
            "accessionNumber",
            []
        )
        primary_documents = recent.get(
            "primaryDocument",
            []
        )

        filings = []

        for i in range(
            min(
                limit,
                len(forms)
            )
        ):

            filings.append({
                "form": forms[i],
                "filing_date": dates[i],
                "accession_number": accession_numbers[i],
                "primary_document": primary_documents[i]
                if i < len(primary_documents)
                else None
            })

        return filings

    # ---------------------------------------------------------
    # XBRL 재무정보
    # ---------------------------------------------------------

    def get_company_facts(self, ticker: str):
        """
        SEC XBRL Company Facts 데이터를 가져온다.

        예:
            매출
            순이익
            자산
            부채
            현금
            EPS
            등
        """

        cik = self.get_cik(ticker)

        if not cik:
            raise ValueError(
                f"SEC에서 {ticker}의 CIK를 찾을 수 없습니다."
            )

        url = self.COMPANY_FACTS_URL.format(cik)

        response = requests.get(
            url,
            headers=self.headers,
            timeout=10
        )

        response.raise_for_status()

        return response.json()

    # ---------------------------------------------------------
    # 주요 재무수치 요약
    # ---------------------------------------------------------

    def get_key_financials(self, ticker: str):
        """XBRL Company Facts에서 최근 연간(10-K) 매출/순이익/자산/부채를 추출한다."""

        facts = self.get_company_facts(ticker)

        us_gaap = facts.get("facts", {}).get("us-gaap", {})

        concepts = {
            "Revenues": "매출",
            "NetIncomeLoss": "순이익",
            "Assets": "자산총계",
            "Liabilities": "부채총계",
        }

        summary = {}

        for concept, label in concepts.items():
            node = us_gaap.get(concept)
            if not node:
                continue

            entries = node.get("units", {}).get("USD", [])
            annual_entries = [
                entry for entry in entries
                if entry.get("form") == "10-K" and entry.get("val") is not None
            ]

            if not annual_entries:
                continue

            latest = max(annual_entries, key=lambda entry: entry.get("end", ""))

            summary[label] = {
                "value": latest.get("val"),
                "end": latest.get("end"),
                "form": latest.get("form"),
            }

        return summary

    # ---------------------------------------------------------
    # 공시 원문 발췌
    # ---------------------------------------------------------

    def get_filing_excerpt(self, ticker: str, filing: dict, max_chars: int = 800) -> str:
        """공시 원문 문서의 앞부분만 내려받아 태그를 제거한 텍스트로 반환한다."""

        accession_number = filing.get("accession_number")
        primary_document = filing.get("primary_document")

        if not accession_number or not primary_document:
            return ""

        cik = self.get_cik(ticker)
        if not cik:
            return ""

        accession_no_nodash = accession_number.replace("-", "")
        cik_no_padding = str(int(cik))

        url = (
            f"https://www.sec.gov/Archives/edgar/data/"
            f"{cik_no_padding}/{accession_no_nodash}/{primary_document}"
        )

        headers = dict(self.headers)
        headers["Host"] = "www.sec.gov"

        response = requests.get(url, headers=headers, timeout=20, stream=True)
        response.raise_for_status()

        # 대용량 문서 전체를 받지 않고 앞부분만 읽어 발췌한다
        raw = b""
        for chunk in response.iter_content(chunk_size=4096):
            raw += chunk
            if len(raw) >= 50_000:
                break
        response.close()

        text = raw.decode("utf-8", errors="ignore")
        plain = re.sub(r"<[^>]+>", " ", text)
        plain = re.sub(r"\s+", " ", plain).strip()

        return plain[:max_chars]
"""국내(DART)·해외(SEC) 공시와 뉴스를 근거로, 퀀트 분석에서 선정된
종목의 신뢰도를 로컬 Ollama LLM으로 평가하는 모듈."""

import json
import logging
import re
import time
from pathlib import Path

from ai.data.dart_client import DARTClient
from ai.data.sec_client import SECClient
from ai.data.news_client import NewsClient
from ai.data.data_normalizer import DataNormalizer
from ai.ollama_client import OllamaClient


logger = logging.getLogger(__name__)

# 국내 종목은 6자리 숫자 코드를 사용한다 (data/data_collector.py 와 동일한 규칙)
KR_SYMBOL_PATTERN = re.compile(r"\d{6}")

# 미국 상장 티커는 영문자(+ ./- 구분자)로만 구성된다 (예: AAPL, BRK-A, BF.B)
US_SYMBOL_PATTERN = re.compile(r"^[A-Z]{1,6}([.-][A-Z]{1,3})?$")

CACHE_DIR = Path(__file__).resolve().parent / "data" / ".cache" / "ai_analysis"


class AIReliabilityAnalyzer:
    """DART/SEC 공시 + 뉴스 + 퀀트 지표를 근거로 종목 신뢰도를 평가한다."""

    def __init__(
        self,
        ollama_base_url,
        ollama_model,
        dart_api_key=None,
        sec_user_agent=None,
        news_limit=5,
        filing_days=30,
        enabled=True,
        cache_ttl_hours=12,
        filing_excerpt_count=2,
        ollama_timeout_seconds=300,
    ):
        self.enabled = enabled
        self.news_limit = news_limit
        self.filing_days = filing_days
        self.cache_ttl_seconds = cache_ttl_hours * 3600
        self.filing_excerpt_count = filing_excerpt_count
        self.ollama = OllamaClient(
            base_url=ollama_base_url,
            model=ollama_model,
            timeout=ollama_timeout_seconds,
        )

        self.dart_client = None
        if dart_api_key:
            try:
                self.dart_client = DARTClient(api_key=dart_api_key)
            except Exception as exc:
                logger.warning("⚠️ DART 클라이언트 초기화 실패: %s", exc)

        self.sec_client = None
        if sec_user_agent:
            try:
                self.sec_client = SECClient(user_agent=sec_user_agent)
            except Exception as exc:
                logger.warning("⚠️ SEC 클라이언트 초기화 실패: %s", exc)

        try:
            self.news_client = NewsClient()
        except Exception as exc:
            logger.warning("⚠️ 뉴스 클라이언트 초기화 실패: %s", exc)
            self.news_client = None

    @staticmethod
    def is_korean_symbol(symbol: str) -> bool:
        return bool(KR_SYMBOL_PATTERN.fullmatch(symbol))

    @staticmethod
    def is_us_symbol(symbol: str) -> bool:
        return bool(US_SYMBOL_PATTERN.fullmatch(symbol.upper()))

    def is_supported_symbol(self, symbol: str) -> bool:
        """DART(6자리 숫자) 또는 SEC(영문 티커) 형식을 따르는 종목인지 확인한다."""
        return self.is_korean_symbol(symbol) or self.is_us_symbol(symbol)

    # ---------------------------------------------------------
    # 근거 데이터 수집
    # ---------------------------------------------------------

    def _collect_filings(self, symbol):
        """국내 종목은 DART, 해외 종목은 SEC 공시를 조회하고, 최근 공시 일부는 본문을 발췌한다."""

        if self.is_korean_symbol(symbol):
            if not self.dart_client:
                return []
            try:
                corp_code = self.dart_client.get_corp_code_by_stock_code(symbol)
                if not corp_code:
                    return []
                filings = self.dart_client.search_filings(
                    corp_code, days=self.filing_days
                ).get("list", [])
                documents = [DataNormalizer.normalize_dart(symbol, filing) for filing in filings]

                for doc, filing in zip(documents[: self.filing_excerpt_count], filings):
                    rcept_no = filing.get("rcept_no")
                    if not rcept_no:
                        continue
                    try:
                        excerpt = self.dart_client.get_filing_document_excerpt(rcept_no)
                        if excerpt:
                            doc["content"] = excerpt
                    except Exception as exc:
                        logger.warning("⚠️ %s DART 공시 본문 조회 실패: %s", symbol, exc)

                return documents
            except Exception as exc:
                logger.warning("⚠️ %s DART 공시 조회 실패: %s", symbol, exc)
                return []

        if not self.sec_client:
            return []
        try:
            filings = self.sec_client.get_recent_filings(symbol, limit=10)
            documents = [DataNormalizer.normalize_sec(symbol, filing) for filing in filings]

            for doc, filing in zip(documents[: self.filing_excerpt_count], filings):
                try:
                    excerpt = self.sec_client.get_filing_excerpt(symbol, filing)
                    if excerpt:
                        doc["content"] = excerpt
                except Exception as exc:
                    logger.warning("⚠️ %s SEC 공시 본문 조회 실패: %s", symbol, exc)

            return documents
        except Exception as exc:
            logger.warning("⚠️ %s SEC 공시 조회 실패: %s", symbol, exc)
            return []

    def _collect_news(self, symbol):
        if not self.news_client:
            return []
        try:
            news = self.news_client.search_news(symbol, limit=self.news_limit)
            return [DataNormalizer.normalize_news(symbol, item) for item in news]
        except Exception as exc:
            logger.warning("⚠️ %s 뉴스 조회 실패: %s", symbol, exc)
            return []

    @staticmethod
    def _format_dart_financials(summary):
        if not summary:
            return ""

        year = summary.get("_bsns_year")
        lines = [f"({year}년 사업보고서 기준)"] if year else []

        for account in ["매출액", "영업이익", "당기순이익", "자산총계", "부채총계", "자본총계"]:
            row = summary.get(account)
            if not row:
                continue

            try:
                current_text = f"{int(row['thstrm_amount']):,}원"
            except (TypeError, ValueError):
                current_text = str(row.get("thstrm_amount"))

            try:
                prior_text = f"{int(row['frmtrm_amount']):,}원"
            except (TypeError, ValueError):
                prior_text = None

            line = f"- {account}: {current_text}"
            if prior_text:
                line += f" (전기 {prior_text})"
            lines.append(line)

        return "\n".join(lines)

    @staticmethod
    def _format_sec_financials(summary):
        if not summary:
            return ""

        lines = []
        for label, row in summary.items():
            try:
                value_text = f"${int(row.get('value')):,}"
            except (TypeError, ValueError):
                value_text = str(row.get("value"))
            lines.append(f"- {label}: {value_text} (기준일 {row.get('end', 'N/A')})")

        return "\n".join(lines)

    def _collect_financial_summary(self, symbol):
        """DART/SEC 재무 API에서 매출·이익·자산 등 핵심 계정을 조회해 텍스트로 요약한다."""

        if self.is_korean_symbol(symbol):
            if not self.dart_client:
                return ""
            try:
                corp_code = self.dart_client.get_corp_code_by_stock_code(symbol)
                if not corp_code:
                    return ""
                summary = self.dart_client.get_key_financials(corp_code)
                return self._format_dart_financials(summary)
            except Exception as exc:
                logger.warning("⚠️ %s DART 재무정보 조회 실패: %s", symbol, exc)
                return ""

        if not self.sec_client:
            return ""
        try:
            summary = self.sec_client.get_key_financials(symbol)
            return self._format_sec_financials(summary)
        except Exception as exc:
            logger.warning("⚠️ %s SEC 재무정보 조회 실패: %s", symbol, exc)
            return ""

    @staticmethod
    def _fallback_result(reason):
        return {
            "available": False,
            "reliability_score": None,
            "verdict": "분석 불가",
            "reasoning": reason,
            "key_risks": [],
            "financial_summary": "",
            "sources": [],
        }

    # ---------------------------------------------------------
    # 결과 캐시 (동일 종목 반복 분석 시 Ollama/외부 API 호출 절감)
    # ---------------------------------------------------------

    @staticmethod
    def _cache_path(symbol):
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        safe_symbol = re.sub(r"[^A-Za-z0-9]", "_", symbol)
        return CACHE_DIR / f"{safe_symbol}.json"

    def _read_cache(self, symbol):
        path = self._cache_path(symbol)
        if not path.exists():
            return None
        try:
            if time.time() - path.stat().st_mtime > self.cache_ttl_seconds:
                return None
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            logger.warning("⚠️ %s AI 분석 캐시 로드 실패: %s", symbol, exc)
            return None

    def _write_cache(self, symbol, result):
        try:
            with open(self._cache_path(symbol), "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False)
        except Exception as exc:
            logger.warning("⚠️ %s AI 분석 캐시 저장 실패: %s", symbol, exc)

    # ---------------------------------------------------------
    # 신뢰도 분석
    # ---------------------------------------------------------

    def analyze(self, symbol, quant_result):
        """공시/뉴스 근거와 퀀트 지표를 Ollama에 전달해 신뢰도를 평가한다."""

        if not self.enabled:
            return self._fallback_result("AI 신뢰도 분석이 비활성화되어 있습니다.")

        if not self.is_supported_symbol(symbol):
            logger.info(
                "ℹ️ %s 는 DART/SEC 조회 대상 형식이 아니라 근거 조회를 건너뜁니다.", symbol
            )
            return self._fallback_result(
                "종목코드 형식이 DART(국내 6자리)/SEC(해외 티커) 어디에도 해당하지 않아 "
                "공시 조회를 건너뛰었습니다."
            )

        cached = self._read_cache(symbol)
        if cached is not None:
            logger.info("♻️ %s AI 신뢰도 분석 캐시 사용", symbol)
            return cached

        sources = self._collect_filings(symbol) + self._collect_news(symbol)

        if not sources:
            logger.info("ℹ️ %s 공시/뉴스 근거를 찾지 못해 퀀트 지표만으로 평가합니다.", symbol)

        financial_summary = self._collect_financial_summary(symbol)

        evidence_lines = []
        for doc in sources[:15]:
            line = f"- [{doc['source']}/{doc['source_type']}] {doc['date']} {doc['title']}"
            content = (doc.get("content") or "").strip()
            if content and content != doc["title"]:
                line += f"\n  본문 발췌: {content[:300]}"
            evidence_lines.append(line)

        evidence_text = "\n".join(evidence_lines) or "관련 공시/뉴스 없음"

        prompt = f"""다음은 퀀트 분석으로 선정된 종목 {symbol}에 대한 정보입니다.

[퀀트 지표]
- RSI: {quant_result.get('rsi')}
- MACD: {quant_result.get('macd')} / Signal: {quant_result.get('signal_line')}
- 30일 수익률: {quant_result.get('return_30d')}%
- 연환산 변동성: {quant_result.get('volatility')}%
- Sharpe Ratio: {quant_result.get('sharpe_ratio')}
- 신호강도: {quant_result.get('signal_strength')}/100

[재무 요약]
{financial_summary or "재무 데이터 없음"}

[최근 공시/뉴스 근거]
{evidence_text}

위 퀀트 신호와 재무 요약, 공시/뉴스 내용을 근거로 이 종목 선정의 신뢰도를 평가해줘.
매출/이익이 감소하거나 적자전환, 부채비율 급증 등 재무 악화 신호가 있으면 신뢰도를 낮게 평가해야 한다.
공시나 뉴스에서 리스크(적자전환, 소송, 횡령, 상장폐지, 회계 이슈 등)가 발견되면 신뢰도를 낮게 평가해야 한다.
근거가 부족하면 신뢰도를 중립 이하로 평가해라.
반드시 아래 JSON 형식으로만 응답해:
{{
  "reliability_score": 0부터 100 사이의 정수,
  "verdict": "신뢰" 또는 "주의" 또는 "위험" 중 하나,
  "reasoning": "판단 근거를 2~3문장 한국어로 설명",
  "key_risks": ["발견된 리스크 요인들"]
}}
"""

        try:
            result = self.ollama.generate_json(
                prompt,
                system=(
                    "당신은 신중한 금융 리스크 분석가입니다. "
                    "제공된 공시/뉴스 근거에 기반해서만 판단하고, "
                    "추측이나 과장 없이 사실에 근거해 답하세요."
                ),
            )
        except Exception as exc:
            logger.warning("⚠️ %s AI 신뢰도 분석 실패(Ollama 호출 오류): %s", symbol, exc)
            return self._fallback_result(f"Ollama 호출 실패: {exc}")

        analysis_result = {
            "available": True,
            "reliability_score": result.get("reliability_score"),
            "verdict": result.get("verdict", "N/A"),
            "reasoning": result.get("reasoning", ""),
            "key_risks": result.get("key_risks", []),
            "financial_summary": financial_summary,
            "sources": sources[:10],
        }

        self._write_cache(symbol, analysis_result)

        return analysis_result

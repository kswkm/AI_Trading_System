from typing import Optional, Dict, Any


class DataNormalizer:
    """
    DART / SEC / News 데이터를
    AI가 공통적으로 처리할 수 있는 형태로 변환하는 클래스
    """

    # ---------------------------------------------------------
    # 공통 문서 형태
    # ---------------------------------------------------------

    @staticmethod
    def create_document(
        source: str,
        source_type: str,
        ticker: str,
        title: str,
        date: Optional[str] = None,
        content: Optional[str] = None,
        url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        AI/RAG에서 사용할 공통 데이터 구조를 생성한다.
        """

        return {
            "source": source,
            "source_type": source_type,
            "ticker": ticker,
            "title": title,
            "date": date,
            "content": content or "",
            "url": url,
            "metadata": metadata or {}
        }

    # ---------------------------------------------------------
    # DART
    # ---------------------------------------------------------

    @staticmethod
    def normalize_dart(
        ticker: str,
        filing: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        DART 공시 데이터를 공통 형태로 변환
        """

        return DataNormalizer.create_document(

            source="DART",

            source_type="official_filing",

            ticker=ticker,

            title=filing.get(
                "report_nm",
                "DART 공시"
            ),

            date=filing.get(
                "rcept_dt"
            ),

            content=filing.get(
                "report_nm",
                ""
            ),

            url=filing.get(
                "report_url"
            ),

            metadata={
                "corp_code": filing.get(
                    "corp_code"
                ),

                "corp_name": filing.get(
                    "corp_name"
                ),

                "report_type": filing.get(
                    "pblntf_ty"
                ),

                "receipt_number": filing.get(
                    "rcept_no"
                )
            }
        )

    # ---------------------------------------------------------
    # SEC
    # ---------------------------------------------------------

    @staticmethod
    def normalize_sec(
        ticker: str,
        filing: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        SEC 공시 데이터를 공통 형태로 변환
        """

        form = filing.get(
            "form",
            ""
        )

        return DataNormalizer.create_document(

            source="SEC",

            source_type="official_filing",

            ticker=ticker,

            title=f"SEC {form} Filing",

            date=filing.get(
                "filing_date"
            ),

            content="",

            url=filing.get(
                "url"
            ),

            metadata={
                "form": form,

                "accession_number": filing.get(
                    "accession_number"
                ),

                "primary_document": filing.get(
                    "primary_document"
                )
            }
        )

    # ---------------------------------------------------------
    # News
    # ---------------------------------------------------------

    @staticmethod
    def normalize_news(
        ticker: str,
        news: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        뉴스 데이터를 공통 형태로 변환
        """

        return DataNormalizer.create_document(

            source=news.get(
                "source",
                "News"
            ),

            source_type="news",

            ticker=ticker,

            title=news.get(
                "title",
                ""
            ),

            date=news.get(
                "published"
            ),

            content=news.get(
                "summary",
                ""
            ),

            url=news.get(
                "url"
            ),

            metadata={
                "original_source": news.get(
                    "source"
                )
            }
        )
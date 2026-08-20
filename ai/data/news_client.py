import feedparser
from urllib.parse import quote
from typing import Optional


class NewsClient:
    """Google News RSS 기반 뉴스 수집기"""

    BASE_URL = "https://news.google.com/rss/search"

    def __init__(
        self,
        language: str = "ko",
        country: str = "KR"
    ):
        """
        Args:
            language:
                뉴스 언어

            country:
                국가
        """

        self.language = language
        self.country = country

    # ---------------------------------------------------------
    # 뉴스 검색
    # ---------------------------------------------------------

    def search_news(
        self,
        keyword: str,
        limit: int = 10
    ):
        """
        특정 키워드의 뉴스 검색

        Args:
            keyword:
                종목명 또는 티커

            limit:
                가져올 뉴스 개수
        """

        query = quote(keyword)

        url = (
            f"{self.BASE_URL}"
            f"?q={query}"
            f"&hl={self.language}"
            f"&gl={self.country}"
            f"&ceid={self.country}:{self.language}"
        )

        feed = feedparser.parse(url)

        news = []

        for entry in feed.entries[:limit]:

            source = None

            if hasattr(entry, "source"):
                source = entry.source.get(
                    "title"
                )

            news.append({
                "title": entry.get(
                    "title"
                ),

                "url": entry.get(
                    "link"
                ),

                "published": entry.get(
                    "published"
                ),

                "source": source,

                "summary": entry.get(
                    "summary"
                )
            })

        return news
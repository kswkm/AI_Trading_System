"""
AI 종목 선정 모듈

역할:
1. 후보 종목 중 예산으로 매수 가능한 종목 필터링
2. 기본적인 시장 지표 계산
3. Claude AI를 이용하여 분석 우선 종목 선정
4. 선정된 종목 리스트 반환
"""

import json
import logging

import anthropic


logger = logging.getLogger(__name__)


class StockSelector:
    """AI 기반 종목 선정 클래스"""

    def __init__(
        self,
        api_key,
        trading_budget,
        max_position_ratio=0.5,
        max_selected_stocks=5
    ):
        self.client = anthropic.Anthropic(
            api_key=api_key
        )

        self.trading_budget = trading_budget
        self.max_position_ratio = max_position_ratio
        self.max_selected_stocks = max_selected_stocks

        self.max_per_stock = (
            trading_budget * max_position_ratio
        )

    # =========================================================
    # 종목 선정
    # =========================================================

    def select_stocks(
        self,
        candidates,
        market_data="",
        top_n=None
    ):
        """
        후보 종목에서 AI가 분석 대상 종목 선정

        Args:
            candidates:
                [
                    {
                        "symbol": "005930",
                        "current_price": 70000,
                        "return_30d": 8.5,
                        "volatility": 25.3,
                        "volume_ratio": 1.8,
                        "rsi": 58.2
                    }
                ]

            market_data:
                시장 상황 설명

            top_n:
                최대 선정 종목 수

        Returns:
            선정된 종목 코드 리스트
        """

        if top_n is None:
            top_n = self.max_selected_stocks

        # -----------------------------------------------------
        # 1. 예산으로 1주도 살 수 없는 종목 제거
        # -----------------------------------------------------

        affordable_candidates = []

        for candidate in candidates:

            price = float(
                candidate.get(
                    "current_price",
                    0
                )
            )

            if price <= 0:
                continue

            if price > self.max_per_stock:
                logger.info(
                    f"⏭️ {candidate['symbol']} 제외 "
                    f"(종목당 최대 예산 초과)"
                )
                continue

            affordable_candidates.append(
                candidate
            )

        if not affordable_candidates:

            logger.warning(
                "⚠️ 예산 내 분석 가능한 종목이 없습니다."
            )

            return []

        # -----------------------------------------------------
        # 2. Claude 프롬프트
        # -----------------------------------------------------

        candidate_text = ""

        for candidate in affordable_candidates:

            candidate_text += f"""
종목코드: {candidate['symbol']}
현재가: {candidate.get('current_price', 0)}
30일 수익률: {candidate.get('return_30d', 0):.2f}%
변동성: {candidate.get('volatility', 0):.2f}%
거래량 비율: {candidate.get('volume_ratio', 1):.2f}
RSI: {candidate.get('rsi', 50):.2f}
"""

        prompt = f"""
당신은 주식 포트폴리오의 분석 대상 종목을 선정하는 AI입니다.

총 신규 투자 예산:
{self.trading_budget:,.0f}원

종목당 최대 투자 금액:
{self.max_per_stock:,.0f}원

최대 선정 종목 수:
{top_n}

시장 상황:
{market_data}

후보 종목:
{candidate_text}

위 후보 중에서 기술적 지표와 위험을 고려하여
추가 분석 가치가 높은 종목을 최대 {top_n}개 선정하세요.

중요:
- 현재가가 종목당 최대 예산보다 높은 종목은 선정하지 마세요.
- 단순히 수익률이 높은 종목만 선택하지 마세요.
- 과도하게 높은 RSI는 위험 요소로 고려하세요.
- 변동성이 지나치게 높은 종목은 신중하게 평가하세요.
- 분산을 고려하세요.

반드시 다음 JSON 형식만 반환하세요.

{{
    "selected_stocks": [
        {{
            "symbol": "005930",
            "reason": "선정 이유"
        }}
    ]
}}

다른 설명은 출력하지 마세요.
"""

        # -----------------------------------------------------
        # 3. Claude 호출
        # -----------------------------------------------------

        try:

            message = self.client.messages.create(
                model="claude-opus-4-1",
                max_tokens=1000,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            response_text = (
                message.content[0].text
            )

            # -------------------------------------------------
            # JSON 추출
            # -------------------------------------------------

            if "```json" in response_text:

                response_text = (
                    response_text
                    .split("```json", 1)[1]
                    .split("```", 1)[0]
                    .strip()
                )

            result = json.loads(
                response_text
            )

            selected = result.get(
                "selected_stocks",
                []
            )

            # -------------------------------------------------
            # 실제 후보에 존재하는 종목만 허용
            # -------------------------------------------------

            candidate_symbols = {
                c["symbol"]
                for c in affordable_candidates
            }

            selected_symbols = []

            for item in selected:

                symbol = item.get("symbol")

                if symbol in candidate_symbols:

                    if symbol not in selected_symbols:

                        selected_symbols.append(
                            symbol
                        )

            selected_symbols = (
                selected_symbols[:top_n]
            )

            logger.info(
                f"🤖 AI 종목 선정 완료: "
                f"{selected_symbols}"
            )

            return selected_symbols

        except Exception as e:

            logger.error(
                f"❌ AI 종목 선정 실패: {e}"
            )

            # -------------------------------------------------
            # AI 실패 시 기본 점수 기반 fallback
            # -------------------------------------------------

            return self.fallback_selection(
                affordable_candidates,
                top_n
            )

    # =========================================================
    # AI 실패 시 기본 선정
    # =========================================================

    def fallback_selection(
        self,
        candidates,
        top_n
    ):
        """
        AI 호출 실패 시 기본 점수로 선정
        """

        scored = []

        for candidate in candidates:

            return_30d = float(
                candidate.get(
                    "return_30d",
                    0
                )
            )

            volume_ratio = float(
                candidate.get(
                    "volume_ratio",
                    1
                )
            )

            rsi = float(
                candidate.get(
                    "rsi",
                    50
                )
            )

            volatility = float(
                candidate.get(
                    "volatility",
                    100
                )
            )

            score = 0

            # 상승 모멘텀
            if return_30d > 0:
                score += min(
                    return_30d,
                    20
                )

            # 거래량 증가
            if volume_ratio > 1:
                score += min(
                    volume_ratio * 5,
                    15
                )

            # RSI
            if 45 <= rsi <= 65:
                score += 10

            elif 65 < rsi <= 70:
                score += 5

            elif rsi > 75:
                score -= 10

            # 변동성
            if volatility < 30:
                score += 10

            elif volatility > 50:
                score -= 10

            scored.append(
                (
                    candidate["symbol"],
                    score
                )
            )

        scored.sort(
            key=lambda x: x[1],
            reverse=True
        )

        selected = [
            symbol
            for symbol, score in scored[:top_n]
        ]

        logger.info(
            f"📊 Fallback 종목 선정: {selected}"
        )

        return selected
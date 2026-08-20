"""로컬/원격 Ollama 서버를 통해 LLM 추론을 수행하는 클라이언트."""

import json
import logging
import time

import requests


logger = logging.getLogger(__name__)


class OllamaClient:
    """Ollama의 /api/generate 엔드포인트로 JSON 응답을 요청하는 클라이언트."""

    def __init__(
        self,
        base_url="http://localhost:11434",
        model="llama3",
        timeout=120,
        max_retries=2,
        retry_backoff_seconds=2,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff_seconds = retry_backoff_seconds

    def generate_json(self, prompt: str, system: str = None) -> dict:
        """프롬프트를 전달하고 JSON으로 파싱된 응답을 반환한다.

        일시적인 네트워크 오류나 JSON 파싱 실패는 지수 백오프로 재시도한다.
        """

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        }

        if system:
            payload["system"] = system

        last_exc = None

        for attempt in range(self.max_retries + 1):
            try:
                response = requests.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    timeout=self.timeout,
                )
                response.raise_for_status()

                raw_text = response.json().get("response", "")

                try:
                    return json.loads(raw_text)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"Ollama 응답을 JSON으로 해석할 수 없습니다: {raw_text[:200]}"
                    ) from exc

            except (requests.RequestException, ValueError) as exc:
                last_exc = exc
                if attempt < self.max_retries:
                    wait_seconds = self.retry_backoff_seconds * (attempt + 1)
                    logger.warning(
                        "⚠️ Ollama 호출 실패 (재시도 %d/%d, %.0f초 후): %s",
                        attempt + 1, self.max_retries, wait_seconds, exc,
                    )
                    time.sleep(wait_seconds)

        raise last_exc


"""LLM client abstraction.

Production note: agents should depend on this interface instead of importing an SDK directly.
"""

import json
import threading
import time
from dataclasses import dataclass
from urllib import request
from urllib.error import HTTPError, URLError

from multi_agent_research_lab.core.config import Settings, get_settings
from multi_agent_research_lab.core.errors import AgentExecutionError


@dataclass(frozen=True)
class LLMResponse:
    content: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None


class LLMClient:
    """Small OpenAI-compatible client with a deterministic mock fallback."""

    _rate_lock = threading.Lock()
    _request_times: list[float] = []

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """Return a model completion.

        Uses NVIDIA/OpenAI-compatible chat completions when a key exists.
        """

        api_key = self.settings.nvidia_api_key or self.settings.openai_api_key
        if self.settings.use_mock_llm or not api_key:
            return self._mock_complete(system_prompt, user_prompt)

        self._wait_for_rate_limit()
        payload = {
            "model": self.settings.openai_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 600,
        }
        data = json.dumps(payload).encode("utf-8")
        req = request.Request(
            f"{self.settings.openai_base_url.rstrip('/')}/chat/completions",
            data=data,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        last_error: Exception | None = None
        for _ in range(2):
            try:
                with request.urlopen(req, timeout=self.settings.timeout_seconds) as response:
                    raw = json.loads(response.read().decode("utf-8"))
                break
            except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
                last_error = exc
        else:
            raise AgentExecutionError(f"LLM call failed: {last_error}") from last_error

        content = raw["choices"][0]["message"]["content"]
        usage = raw.get("usage", {})
        input_tokens = usage.get("prompt_tokens") or 0
        output_tokens = usage.get("completion_tokens") or 0
        return LLMResponse(
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=self._estimate_cost(input_tokens, output_tokens),
        )

    def _estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        return (
            input_tokens * self.settings.llm_input_cost_per_1m_tokens
            + output_tokens * self.settings.llm_output_cost_per_1m_tokens
        ) / 1_000_000

    def _wait_for_rate_limit(self) -> None:
        # ponytail: process-local limit; use Redis/db locks only for multi-process runners.
        limit = self.settings.llm_requests_per_minute
        while True:
            with self._rate_lock:
                now = time.monotonic()
                self._request_times = [item for item in self._request_times if now - item < 60]
                if len(self._request_times) < limit:
                    self._request_times.append(now)
                    return
                sleep_for = 60 - (now - self._request_times[0])
            time.sleep(max(0.1, sleep_for))

    def _mock_complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        # ponytail: deterministic mock is enough for flow tests; swap to real key for quality.
        text = f"{system_prompt}\n{user_prompt}".lower()
        if "search-error" in text:
            raise AgentExecutionError("Mock LLM failure requested by prompt")
        if "writer" in text or "final" in text:
            content = "Final answer: multi-agent workflows help when tasks need research, analysis, and synthesis."
        elif "analyst" in text or "analysis" in text:
            content = "Analysis: use multi-agent flow for complex research; use single-agent for simple prompts."
        else:
            content = "Baseline answer: compare single-agent speed with multi-agent traceability and coverage."
        return LLMResponse(
            content=content,
            input_tokens=len(user_prompt.split()),
            output_tokens=len(content.split()),
            cost_usd=0.0,
        )

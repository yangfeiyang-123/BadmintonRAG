from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from typing import Mapping, Protocol


class JsonTransport(Protocol):
    def post_json(
        self, url: str, headers: dict[str, str], payload: dict[str, object], timeout: float
    ) -> dict[str, object]:
        ...


class HttpJsonTransport:
    def post_json(
        self, url: str, headers: dict[str, str], payload: dict[str, object], timeout: float
    ) -> dict[str, object]:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))


@dataclass(frozen=True)
class LLMConfig:
    base_url: str
    api_key: str
    model: str
    temperature: float = 0.2
    timeout: float = 60.0

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "LLMConfig":
        source = env if env is not None else os.environ
        return cls(
            base_url=source.get("BADMINTON_LLM_BASE_URL", "").rstrip("/"),
            api_key=source.get("BADMINTON_LLM_API_KEY", ""),
            model=source.get("BADMINTON_LLM_MODEL", ""),
            temperature=float(source.get("BADMINTON_LLM_TEMPERATURE", "0.2")),
            timeout=float(source.get("BADMINTON_LLM_TIMEOUT", "60")),
        )


class OpenAICompatibleClient:
    def __init__(self, config: LLMConfig, transport: JsonTransport | None = None):
        self.config = config
        self.transport = transport or HttpJsonTransport()

    def complete(self, messages: list[dict[str, str]]) -> str:
        if not self.config.base_url:
            raise ValueError("BADMINTON_LLM_BASE_URL is required")
        if not self.config.model:
            raise ValueError("BADMINTON_LLM_MODEL is required")

        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"

        payload: dict[str, object] = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
        }
        response = self.transport.post_json(
            f"{self.config.base_url}/chat/completions",
            headers=headers,
            payload=payload,
            timeout=self.config.timeout,
        )
        try:
            choices = response["choices"]
            first = choices[0]  # type: ignore[index]
            message = first["message"]  # type: ignore[index]
            return str(message["content"])  # type: ignore[index]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError("LLM response does not contain choices[0].message.content") from exc

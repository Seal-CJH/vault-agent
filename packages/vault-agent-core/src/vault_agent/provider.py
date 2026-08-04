from __future__ import annotations

import json
from typing import Callable, Iterable
from urllib.request import Request, urlopen

from .settings import ProviderSettings


class ProviderError(RuntimeError):
    """Raised when a model provider cannot be called safely."""


RequestFunction = Callable[[str, dict[str, str], str], str]
StreamRequestFunction = Callable[[str, dict[str, str], str], Iterable[str]]


def _post_json(url: str, headers: dict[str, str], body: str) -> str:
    request = Request(url, data=body.encode("utf-8"), headers=headers, method="POST")
    with urlopen(request, timeout=60) as response:  # nosec: URL is provider constant
        return response.read().decode("utf-8")


def _post_json_stream(url: str, headers: dict[str, str], body: str) -> Iterable[str]:
    request = Request(url, data=body.encode("utf-8"), headers=headers, method="POST")
    with urlopen(request, timeout=60) as response:  # nosec: URL is provider constant
        for raw_line in response:
            yield raw_line.decode("utf-8").strip()


class DeepSeekProvider:
    """A minimal OpenAI-compatible DeepSeek adapter with an explicit send gate."""

    endpoint = "https://api.deepseek.com/chat/completions"

    def __init__(
        self,
        api_key: str,
        model: str = "deepseek-v4-flash",
        thinking: bool = False,
        reasoning_effort: str = "medium",
        request: RequestFunction = _post_json,
        stream_request: StreamRequestFunction = _post_json_stream,
    ):
        if not api_key:
            raise ProviderError("DeepSeek API key is required")
        self.api_key = api_key
        self.model = model
        self.thinking = thinking
        self.reasoning_effort = reasoning_effort
        self._request = request
        self._stream_request = stream_request

    def complete(self, messages: list[dict[str, str]], confirmed: bool) -> str:
        if not confirmed:
            raise ProviderError("remote provider use requires explicit confirmation")
        payload = {"model": self.model, "messages": messages, "stream": False}
        if self.thinking:
            payload["thinking"] = {"type": "enabled"}
            payload["reasoning_effort"] = self.reasoning_effort
        body = json.dumps(payload)
        raw = self._request(
            self.endpoint,
            {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            body,
        )
        try:
            content = json.loads(raw)["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as error:
            raise ProviderError("provider returned an invalid response") from error
        if not isinstance(content, str) or not content.strip():
            raise ProviderError("provider returned an empty response")
        return content

    def stream(self, messages: list[dict[str, str]], confirmed: bool) -> Iterable[str]:
        if not confirmed:
            raise ProviderError("remote provider use requires explicit confirmation")
        payload = {"model": self.model, "messages": messages, "stream": True}
        if self.thinking:
            payload["thinking"] = {"type": "enabled"}
            payload["reasoning_effort"] = self.reasoning_effort
        for line in self._stream_request(
            self.endpoint,
            {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json.dumps(payload),
        ):
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                return
            try:
                delta = json.loads(data)["choices"][0]["delta"].get("content", "")
            except (KeyError, IndexError, TypeError, json.JSONDecodeError) as error:
                raise ProviderError("provider returned an invalid stream") from error
            if delta:
                yield delta


def provider_from_settings(api_key: str, settings: ProviderSettings) -> DeepSeekProvider:
    return DeepSeekProvider(
        api_key=api_key,
        model=settings.model,
        thinking=settings.thinking,
        reasoning_effort=settings.reasoning_effort,
    )

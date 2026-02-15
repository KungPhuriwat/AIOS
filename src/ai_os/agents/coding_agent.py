from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Protocol
from urllib import request

from ..core.models import TaskResult
from ..core.retry import retry_call


SUPPORTED_LANGUAGES = {
    "python",
    "javascript",
    "typescript",
    "java",
    "c",
    "cpp",
    "csharp",
    "go",
    "rust",
    "kotlin",
    "swift",
    "php",
    "ruby",
}


class LLMProvider(Protocol):
    provider_name: str

    def generate(self, prompt: str, language: str) -> TaskResult: ...


@dataclass
class OpenAIProvider:
    api_key: str
    model: str = "gpt-4.1-mini"
    base_url: str = "https://api.openai.com/v1/responses"
    attempts: int = 3

    provider_name: str = "openai"

    def generate(self, prompt: str, language: str) -> TaskResult:
        instruction = (
            "You are an elite coding assistant. "
            "Return concise implementation guidance in Thai, with test strategy and edge cases."
        )
        payload = {
            "model": self.model,
            "input": [
                {"role": "system", "content": instruction},
                {
                    "role": "user",
                    "content": f"Language: {language}\nTask: {prompt}",
                },
            ],
        }
        req = request.Request(
            self.base_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            raw = retry_call(
                lambda: _post_json(req, timeout=45),
                attempts=self.attempts,
                base_delay=0.7,
            )
        except Exception as exc:  # noqa: BLE001
            return TaskResult(
                ok=False,
                output=f"OpenAI request failed: {exc}",
                confidence=0.2,
                evidence=["openai-error"],
                inferred=True,
            )

        text = _extract_openai_text(raw)
        if not text:
            return TaskResult(
                ok=False,
                output="OpenAI response has no text output",
                confidence=0.2,
                evidence=["openai-empty-output"],
                inferred=True,
            )

        return TaskResult(
            ok=True,
            output=text,
            confidence=0.86,
            evidence=["openai", self.model],
            inferred=False,
        )


@dataclass
class OpencodeProvider:
    api_key: str
    model: str = "opencode/coder"
    endpoint: str = "https://api.opencode.ai/v1/chat/completions"
    attempts: int = 3

    provider_name: str = "opencode"

    def generate(self, prompt: str, language: str) -> TaskResult:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an elite coding assistant. "
                    "Answer in Thai with practical implementation steps, tests, and risk checks."
                ),
            },
            {
                "role": "user",
                "content": f"Language: {language}\nTask: {prompt}",
            },
        ]
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
        }
        req = request.Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            raw = retry_call(
                lambda: _post_json(req, timeout=45),
                attempts=self.attempts,
                base_delay=0.7,
            )
        except Exception as exc:  # noqa: BLE001
            return TaskResult(
                ok=False,
                output=f"Opencode request failed: {exc}",
                confidence=0.2,
                evidence=["opencode-error"],
                inferred=True,
            )

        text = _extract_chat_text(raw)
        if not text:
            return TaskResult(
                ok=False,
                output="Opencode response has no text output",
                confidence=0.2,
                evidence=["opencode-empty-output"],
                inferred=True,
            )

        return TaskResult(
            ok=True,
            output=text,
            confidence=0.84,
            evidence=["opencode", self.model],
            inferred=False,
        )


@dataclass
class OllamaProvider:
    model: str = "qwen2.5-coder:7b"
    endpoint: str = "http://127.0.0.1:11434/api/generate"
    attempts: int = 3

    provider_name: str = "ollama"

    def generate(self, prompt: str, language: str) -> TaskResult:
        full_prompt = (
            "You are an elite coding assistant. "
            "Answer in Thai with practical implementation steps, test plan, and pitfalls.\n"
            f"Language: {language}\nTask: {prompt}"
        )
        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": False,
        }
        req = request.Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            raw = retry_call(
                lambda: _post_json(req, timeout=60),
                attempts=self.attempts,
                base_delay=0.7,
            )
        except Exception as exc:  # noqa: BLE001
            return TaskResult(
                ok=False,
                output=f"Ollama request failed: {exc}",
                confidence=0.2,
                evidence=["ollama-error"],
                inferred=True,
            )

        text = str(raw.get("response", "")).strip()
        if not text:
            return TaskResult(
                ok=False,
                output="Ollama response has no text output",
                confidence=0.2,
                evidence=["ollama-empty-output"],
                inferred=True,
            )

        return TaskResult(
            ok=True,
            output=text,
            confidence=0.8,
            evidence=["ollama", self.model],
            inferred=False,
        )


@dataclass
class RuleBasedFallbackProvider:
    provider_name: str = "fallback"

    def generate(self, prompt: str, language: str) -> TaskResult:
        lang = language.lower()
        inferred = lang not in SUPPORTED_LANGUAGES
        if inferred:
            output = (
                f"ยังไม่มีโปรไฟล์เฉพาะของภาษา '{lang}' จึงใช้แนวทางทั่วไป: "
                "แตกโจทย์เป็นฟังก์ชันเล็ก, เขียนเทสต์ก่อน, รัน lint/test ทุกครั้ง"
            )
            confidence = 0.62
        else:
            output = (
                f"[{lang}] แผนสร้างโค้ดระดับ production: "
                "กำหนดสัญญาอินพุต/เอาต์พุต, เขียน unit tests, พัฒนาแบบ incremental, "
                "และทำ static analysis ก่อนส่งมอบ"
            )
            confidence = 0.82

        return TaskResult(
            ok=True,
            output=output,
            confidence=confidence,
            evidence=["fallback-policy", "testing-policy", "static-analysis-policy"],
            inferred=inferred,
        )


@dataclass
class CodingAgent:
    name: str = "coder-v3"

    def __post_init__(self) -> None:
        self.provider = self._build_provider()

    def _build_provider(self) -> LLMProvider:
        provider = os.getenv("AIOS_LLM_PROVIDER", "fallback").strip().lower()
        retry_attempts = int(os.getenv("AIOS_RETRY_ATTEMPTS", "3"))

        if provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY", "").strip()
            if api_key:
                model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
                base_url = os.getenv(
                    "OPENAI_BASE_URL", "https://api.openai.com/v1/responses"
                )
                return OpenAIProvider(
                    api_key=api_key,
                    model=model,
                    base_url=base_url,
                    attempts=retry_attempts,
                )

        if provider == "opencode":
            api_key = os.getenv("OPENCODE_API_KEY", "").strip()
            if api_key:
                model = os.getenv("OPENCODE_MODEL", "opencode/coder")
                endpoint = os.getenv(
                    "OPENCODE_ENDPOINT", "https://api.opencode.ai/v1/chat/completions"
                )
                return OpencodeProvider(
                    api_key=api_key,
                    model=model,
                    endpoint=endpoint,
                    attempts=retry_attempts,
                )

        if provider in {"ollama", "local"}:
            model = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")
            endpoint = os.getenv(
                "OLLAMA_ENDPOINT", "http://127.0.0.1:11434/api/generate"
            )
            return OllamaProvider(
                model=model, endpoint=endpoint, attempts=retry_attempts
            )

        return RuleBasedFallbackProvider()

    def run(self, prompt: str, language: str | None = None) -> TaskResult:
        lang = (language or "python").lower()
        return self.provider.generate(prompt=prompt, language=lang)

    def provider_status(self) -> dict[str, str]:
        return {
            "provider": getattr(self.provider, "provider_name", "unknown"),
            "model": getattr(self.provider, "model", "n/a"),
            "endpoint": getattr(
                self.provider, "base_url", getattr(self.provider, "endpoint", "n/a")
            ),
        }


def _post_json(req: request.Request, timeout: int) -> dict:
    with request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _extract_openai_text(raw: dict) -> str:
    output = raw.get("output", [])
    chunks: list[str] = []
    for item in output:
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"} and content.get("text"):
                chunks.append(str(content["text"]))
    if chunks:
        return "\n".join(chunks).strip()

    if isinstance(raw.get("output_text"), str):
        return raw["output_text"].strip()

    return ""


def _extract_chat_text(raw: dict) -> str:
    choices = raw.get("choices", [])
    if choices:
        msg = choices[0].get("message", {})
        content = msg.get("content")
        if isinstance(content, str):
            return content.strip()
    return _extract_openai_text(raw)

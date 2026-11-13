"""One interface for every LLM provider.

The rest of the code calls get_llm().complete(system, user) and never knows
which provider or model is behind it. Backends are defined in configs/llm.yaml;
LLM_BACKEND (env) or the `backend` argument picks one.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]


@dataclass
class LLMResponse:
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_s: float
    finish_reason: str = "stop"


class OpenAICompatibleLLM:
    """Any provider with an OpenAI-style /chat/completions endpoint (Groq, Gemini, OpenAI...)."""

    def __init__(self, name: str, base_url: str, api_key_env: str, model: str,
                 extra_body: dict | None = None, max_retries: int = 4, timeout: float = 60.0):
        from openai import OpenAI
        key = os.getenv(api_key_env)
        if not key:
            raise RuntimeError(f"{api_key_env} is not set (add it to .env)")
        self.name, self.model, self.extra_body = name, model, extra_body or {}
        # The SDK retries 429 (rate limit) and 5xx errors itself, with exponential backoff.
        self.client = OpenAI(api_key=key, base_url=base_url, max_retries=max_retries, timeout=timeout)

    def complete(self, system: str, user: str, temperature: float = 0.0, max_tokens: int = 800) -> LLMResponse:
        t0 = time.monotonic()
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=temperature,
            max_tokens=max_tokens,
            **({"extra_body": self.extra_body} if self.extra_body else {}),
        )
        usage = resp.usage
        return LLMResponse(
            text=(resp.choices[0].message.content or "").strip(),
            model=resp.model or self.model,
            input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            output_tokens=getattr(usage, "completion_tokens", 0) or 0,
            latency_s=time.monotonic() - t0,
            finish_reason=resp.choices[0].finish_reason or "stop",
        )

    def list_models(self) -> list[str]:
        return sorted(m.id for m in self.client.models.list())


def load_config() -> dict:
    return yaml.safe_load(open(ROOT / "configs" / "llm.yaml"))


def resolve_backend(backend: str | None = None) -> tuple[str, str]:
    """-> (backend name, where the choice came from). Precedence: flag > env var > config."""
    if backend:
        return backend, "--backend flag"
    if os.getenv("LLM_BACKEND"):
        return os.environ["LLM_BACKEND"].strip(), "LLM_BACKEND env var"
    return load_config()["default_backend"], "configs/llm.yaml"


def get_llm(backend: str | None = None) -> OpenAICompatibleLLM:
    cfg = load_config()
    name, source = resolve_backend(backend)
    if name not in cfg["backends"]:
        raise ValueError(f"Unknown LLM backend {name!r} (from {source}); choose from {list(cfg['backends'])}")
    b = cfg["backends"][name]
    llm = OpenAICompatibleLLM(name, b["base_url"], b["api_key_env"], b["model"], b.get("extra_body"))
    llm.source = source
    return llm


if __name__ == "__main__":   # python -m sectra.llm.base groq  -> lists that provider's models
    import sys

    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    llm = get_llm(sys.argv[1] if len(sys.argv) > 1 else None)
    print(f"{llm.name}: configured model = {llm.model}")
    print("\n".join(f"  {m}" for m in llm.list_models()))
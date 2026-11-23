"""Provider-agnostic LLM shim.

The agents used to call ``ChatOllama`` directly, which meant the app could only
run next to a local Ollama server. ``get_llm()`` returns an object with the same
surface the agents already use (``.invoke(...)`` / ``.stream(...)`` returning
objects with ``.content``) but can talk to:

* Google Gemini   (GEMINI_API_KEY)   - free tier, good default for deployment
* Groq            (GROQ_API_KEY)     - free tier, very fast
* OpenAI-compat.  (OPENAI_API_KEY, optional OPENAI_BASE_URL)
* Ollama          (local, default when no key is configured)

Settings are read from environment variables, ``.env`` or ``st.secrets``.
Force a provider with LLM_PROVIDER=gemini|groq|openai|ollama.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover
    pass


def setting(name: str, default: str | None = None) -> str | None:
    # 1) keys typed into the sidebar are per-browser-session (never shared between visitors)
    try:
        import streamlit as st

        v = st.session_state.get("cfg_" + name)
        if v and v != "auto":
            return str(v)
    except Exception:
        pass
    # 2) environment / .env  3) Streamlit secrets
    v = os.getenv(name)
    if v:
        return v
    try:
        import streamlit as st

        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:
        pass
    return default


@dataclass
class Msg:
    content: str


def _normalize(x) -> list[dict]:
    if isinstance(x, str):
        return [{"role": "user", "content": x}]
    out = []
    for m in x:
        if isinstance(m, dict):
            out.append({"role": m.get("role", "user"), "content": m.get("content", "")})
        else:  # langchain message objects
            role = {"human": "user", "ai": "assistant"}.get(getattr(m, "type", "user"), getattr(m, "type", "user"))
            out.append({"role": role, "content": m.content})
    return out


def provider_name() -> str:
    forced = (setting("LLM_PROVIDER") or "").lower().strip()
    if forced:
        return forced
    if setting("GEMINI_API_KEY") or setting("GOOGLE_API_KEY"):
        return "gemini"
    if setting("GROQ_API_KEY"):
        return "groq"
    if setting("OPENAI_API_KEY"):
        return "openai"
    return "ollama"


def model_name(provider: str | None = None) -> str:
    p = provider or provider_name()
    return {
        "gemini": setting("GEMINI_MODEL", "gemini-2.5-flash"),
        "groq": setting("GROQ_MODEL", "llama-3.3-70b-versatile"),
        "openai": setting("OPENAI_MODEL", "gpt-4o-mini"),
        "ollama": setting("OLLAMA_MODEL", "mistral"),
    }.get(p, "unknown")


class LLM:
    def __init__(self, temperature: float = 0.2):
        self.temperature = temperature
        self.provider = provider_name()
        self.model = model_name(self.provider)

    # ------------------------------------------------------------------ public
    def invoke(self, x) -> Msg:
        return Msg("".join(c.content for c in self.stream(x)))

    def stream(self, x):
        messages = _normalize(x)
        fn = {
            "gemini": self._gemini,
            "groq": self._openai_like,
            "openai": self._openai_like,
            "ollama": self._ollama,
        }.get(self.provider)
        if fn is None:
            raise RuntimeError(f"Unknown LLM_PROVIDER '{self.provider}'")
        for piece in fn(messages):
            if piece:
                yield Msg(piece)

    # --------------------------------------------------------------- providers
    def _gemini(self, messages):
        from google import genai
        from google.genai import types

        key = setting("GEMINI_API_KEY") or setting("GOOGLE_API_KEY")
        if not key:
            raise RuntimeError("GEMINI_API_KEY is not set")
        client = genai.Client(api_key=key)
        system = "\n\n".join(m["content"] for m in messages if m["role"] == "system") or None
        contents = [
            types.Content(
                role="model" if m["role"] == "assistant" else "user",
                parts=[types.Part(text=m["content"])],
            )
            for m in messages
            if m["role"] != "system"
        ]
        cfg = types.GenerateContentConfig(system_instruction=system, temperature=self.temperature)
        for chunk in client.models.generate_content_stream(model=self.model, contents=contents, config=cfg):
            yield chunk.text or ""

    def _openai_like(self, messages):
        from openai import OpenAI

        if self.provider == "groq":
            client = OpenAI(api_key=setting("GROQ_API_KEY"), base_url="https://api.groq.com/openai/v1")
        else:
            client = OpenAI(api_key=setting("OPENAI_API_KEY"), base_url=setting("OPENAI_BASE_URL") or None)
        stream = client.chat.completions.create(
            model=self.model, messages=messages, temperature=self.temperature, stream=True
        )
        for ev in stream:
            if ev.choices and ev.choices[0].delta.content:
                yield ev.choices[0].delta.content

    def _ollama(self, messages):
        import requests

        url = (setting("OLLAMA_URL", "http://localhost:11434") or "").rstrip("/")
        try:
            r = requests.post(
                f"{url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": True,
                    "options": {"temperature": self.temperature},
                },
                stream=True,
                timeout=600,
            )
            r.raise_for_status()
        except requests.ConnectionError as e:
            raise RuntimeError(
                "No LLM available. Set GEMINI_API_KEY or GROQ_API_KEY (Settings / secrets), "
                "or start Ollama locally."
            ) from e
        for line in r.iter_lines():
            if not line:
                continue
            data = json.loads(line)
            yield (data.get("message") or {}).get("content", "")


def get_llm(temperature: float = 0.2) -> LLM:
    return LLM(temperature)


def status() -> str:
    p = provider_name()
    return f"{p} · {model_name(p)}"

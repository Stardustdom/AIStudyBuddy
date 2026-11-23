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
        "gemini": setting("GEMINI_MODEL", "gemini-3.8-flash"),
        "groq": setting("GROQ_MODEL", "llama-3.3-70b-versatile"),
        "openai": setting("OPENAI_MODEL", "gpt-4o-mini"),
        "ollama": setting("OLLAMA_MODEL", "mistral"),
    }.get(p, "unknown")


_DISCOVERED: dict[str, str] = {}
_SKIP = ("whisper", "guard", "tts", "embed", "vision-preview", "image", "audio", "orpheus", "safeguard", "imagen", "veo", "live")
_PREFER = {
    "groq": ("llama-3.3", "llama-3.1-70b", "gpt-oss-120b", "llama-4", "qwen", "gpt-oss", "llama"),
    "gemini": ("flash", "pro"),
}


def discover_model(provider: str) -> str | None:
    """Ask the provider which chat models this key can use and pick the best current one."""
    if provider in _DISCOVERED:
        return _DISCOVERED[provider]
    import requests

    names: list[str] = []
    try:
        if provider == "groq":
            r = requests.get("https://api.groq.com/openai/v1/models",
                             headers={"Authorization": f"Bearer {setting('GROQ_API_KEY')}"}, timeout=15)
            r.raise_for_status()
            names = [m["id"] for m in r.json().get("data", []) if m.get("active", True)]
        elif provider == "gemini":
            key = setting("GEMINI_API_KEY") or setting("GOOGLE_API_KEY")
            r = requests.get("https://generativelanguage.googleapis.com/v1beta/models",
                             params={"key": key, "pageSize": 200}, timeout=15)
            r.raise_for_status()
            names = [m["name"].split("/", 1)[1] for m in r.json().get("models", [])
                     if "generateContent" in m.get("supportedGenerationMethods", [])]
    except Exception:
        return None
    names = [n for n in names if not any(b in n.lower() for b in _SKIP)]
    for pref in _PREFER.get(provider, ()):
        cands = sorted([n for n in names if pref in n.lower() and "preview" not in n.lower() and "exp" not in n.lower()],
                       reverse=True)
        if cands:
            _DISCOVERED[provider] = cands[0]
            return cands[0]
    if names:
        _DISCOVERED[provider] = names[0]
        return names[0]
    return None


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
        import time

        chain = [self.provider]
        if self.provider != "groq" and setting("GROQ_API_KEY"):
            chain.append("groq")  # automatic fallback when the main provider is overloaded
        last = None
        for prov in chain:
            self._use(prov)
            for attempt in range(4 if prov == chain[0] else 2):
                started = False
                try:
                    for piece in self._dispatch(prov)(messages):
                        if piece:
                            started = True
                            yield Msg(piece)
                    return
                except Exception as e:
                    last = e
                    if not started and not setting(prov.upper() + "_MODEL") and (
                        "404" in str(e) or "NOT_FOUND" in str(e) or "does not exist" in str(e)
                    ):
                        found = discover_model(prov)
                        if found and found != self.model:
                            self.model = found
                            continue
                    transient = any(t in str(e) for t in ("503", "429", "UNAVAILABLE", "overloaded", "RESOURCE_EXHAUSTED"))
                    if started or not transient:
                        raise
                    time.sleep(min(2 ** attempt * 1.5, 8))
        raise RuntimeError(f"The model is busy right now - please try again in a minute. ({last})")

    def _use(self, prov):
        self.active = prov
        self.model = _DISCOVERED.get(prov) if (prov in _DISCOVERED and not setting(prov.upper() + "_MODEL")) else model_name(prov)

    def _dispatch(self, prov):
        self.provider_in_use = prov
        fn = {
            "gemini": self._gemini,
            "groq": self._openai_like,
            "openai": self._openai_like,
            "ollama": self._ollama,
        }.get(prov)
        if fn is None:
            raise RuntimeError(f"Unknown LLM_PROVIDER '{prov}'")
        return fn

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

        if self.provider_in_use == "groq":
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

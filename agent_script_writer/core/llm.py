"""Hệ thống gọi LLM tự động thích ứng & chống nghẽn (Resilient Multi-Provider LLM).
Hỗ trợ: OpenAI, OpenRouter, Google Gemini, và Groq Cloud (auto-cascade & circuit breaker).
"""
import json
import re
import time
from typing import List, Optional, Type, TypeVar

import httpx
from pydantic import BaseModel

from core.config import LLM_PROVIDER, MODELS, OPENAI_MODEL, OPENROUTER_MODEL, get_key
from core.config import LLM_PROVIDER, MODELS, OPENAI_BASE_URL, OPENAI_MODEL, OPENROUTER_MODEL, get_key

T = TypeVar("T", bound=BaseModel)

_gemini_client = None
_groq_client = None
_gemini_cooling_until = 0.0
_openrouter_cooling_until = 0.0

_OVERLOAD_KEYS = ("503", "504", "deadline", "unavailable", "demand", "resource_exhausted", "429", "rate limit")


def _get_gemini():
    global _gemini_client
    if _gemini_client is None:
        from google import genai
        from google.genai import types
        key = get_key("GEMINI_API_KEY", required=False)
        if key:
            _gemini_client = genai.Client(
                api_key=key,
                http_options=types.HttpOptions(timeout=20000),
            )
    return _gemini_client


def _get_groq():
    global _groq_client
    if _groq_client is None:
        from groq import Groq
        key = get_key("GROQ_API_KEY", required=False)
        if key:
            _groq_client = Groq(api_key=key, timeout=30.0)
    return _groq_client


def _extract_json_block(text: str) -> str:
    """Trích xuất & làm sạch khối JSON từ markdown hoặc text thô."""
    t = text.strip()
    if "```json" in t:
        t = t.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in t:
        t = t.split("```", 1)[1].split("```", 1)[0].strip()

    match = re.search(r"(\{.*\})", t, re.DOTALL)
    if match:
        t = match.group(1).strip()

    # Sửa lỗi JSON phổ biến của các model free: dấu + trước số (: +3.5 -> : 3.5) và dấu phẩy thừa cuối object/array
    t = re.sub(r":\s*\+(\d)", r": \1", t)
    t = re.sub(r",\s*([}\]])", r"\1", t)
    return t


def _schema_system_prompt(schema: Type[BaseModel]) -> str:
    schema_json_desc = json.dumps(schema.model_json_schema(), ensure_ascii=False)
    return (
        "You are an expert structured data generator. "
        "You MUST output ONLY a valid JSON object matching this JSON Schema:\n"
        f"{schema_json_desc}\n"
        "Do NOT write any explanation or markdown prose. Output ONLY the raw JSON object starting with '{' and ending with '}'."
    )


def _call_openai_compat(
    base_url: str,
    api_key: str,
    model: str,
    messages: List[dict],
    temperature: float,
    max_tokens: int = 16384,
    json_mode: bool = False,
    extra_headers: Optional[dict] = None,
) -> str:
    """Gọi chung chuẩn OpenAI Chat Completions cho cả OpenAI và OpenRouter."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if extra_headers:
        headers.update(extra_headers)

    payload: dict = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    with httpx.Client(timeout=30.0) as client:
        resp = client.post(f"{base_url.rstrip('/')}/chat/completions", headers=headers, json=payload)
        if resp.status_code >= 400:
            raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")
        data = resp.json()
    return (data["choices"][0]["message"]["content"] or "").strip()


def _call_openai_structured(prompt: str, schema: Type[T], temperature: float) -> T:
    key = get_key("OPENAI_API_KEY", required=False)
    if not key:
        raise RuntimeError("No OPENAI_API_KEY")
    raw = _call_openai_compat(
        base_url=OPENAI_BASE_URL,
        api_key=key,
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": _schema_system_prompt(schema)},
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
        json_mode=("api.openai.com" in OPENAI_BASE_URL),
    )
    return schema.model_validate_json(_extract_json_block(raw))


def _call_openrouter_structured(role: str, prompt: str, schema: Type[T], temperature: float) -> T:
    key = get_key("OPENROUTER_API_KEY", required=False)
    if not key:
        raise RuntimeError("No OPENROUTER_API_KEY")
    models = [m.strip() for m in OPENROUTER_MODEL.split(",") if m.strip()] or ["openrouter/free"]
    if models == ["openrouter/free"]:
        if role == "writer_hook":
            models = ["anthropic/claude-3.7-sonnet", "openai/gpt-4o", "google/gemini-2.5-pro", "google/gemini-2.5-flash"]
        elif role == "writer":
            models = ["google/gemini-2.5-flash", "openai/gpt-4o-mini", "openrouter/free"]
        else:
            models = ["openrouter/free", "google/gemini-2.5-flash", "openai/gpt-4o-mini"]
    last_err: Optional[Exception] = None
    for m in models:
        try:
            raw = _call_openai_compat(
                base_url="https://openrouter.ai/api/v1",
                api_key=key,
                model=m,
                messages=[
                    {"role": "system", "content": _schema_system_prompt(schema)},
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
                max_tokens=12000,
                json_mode=(m != "openrouter/free"),
                extra_headers={"HTTP-Referer": "https://faceless-studio.local", "X-Title": "Faceless Studio v3"},
            )
            return schema.model_validate_json(_extract_json_block(raw))
        except Exception as e:
            last_err = e
            if "free-models-per-day" in str(e).lower():
                break
            time.sleep(0.3)
    raise last_err or RuntimeError("OpenRouter structured output failed")


def _call_gemini_structured(role: str, prompt: str, schema: Type[T], temperature: float) -> T:
    from google.genai import types
    client = _get_gemini()
    if not client:
        raise RuntimeError("No Gemini Client")
    model = MODELS.get(role, "gemini-3.5-flash")
    resp = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=temperature,
            response_mime_type="application/json",
            response_schema=schema,
        ),
    )
    return schema.model_validate_json(resp.text)


GROQ_MODELS = [
    "openai/gpt-oss-120b",
    "llama-3.3-70b-versatile",
    "openai/gpt-oss-20b",
    "llama-3.1-8b-instant",
]


def _call_groq_structured(prompt: str, schema: Type[T], temperature: float) -> T:
    client = _get_groq()
    if not client:
        raise RuntimeError("No Groq Client")

    system_instruction = _schema_system_prompt(schema)
    last_err = None

    for m in GROQ_MODELS:
        try:
            resp = client.chat.completions.create(
                model=m,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
                max_tokens=16384 if "120b" in m else 8192,
            )
            raw = resp.choices[0].message.content or ""
            return schema.model_validate_json(_extract_json_block(raw))
        except Exception as e:
            last_err = e
            time.sleep(0.5)

    raise last_err or RuntimeError("Groq structured output failed")


def _provider_order() -> List[str]:
    """Xác định thứ tự ưu tiên provider dựa trên LLM_PROVIDER và các key đang có."""
    now = time.time()
    available: List[str] = []
    if get_key("OPENAI_API_KEY", required=False):
        available.append("openai")
    if get_key("OPENROUTER_API_KEY", required=False) and now >= _openrouter_cooling_until:
        available.append("openrouter")
    if get_key("GEMINI_API_KEY", required=False) and now >= _gemini_cooling_until:
        available.append("gemini")
    if get_key("GROQ_API_KEY", required=False):
        available.append("groq")

    if LLM_PROVIDER != "auto" and LLM_PROVIDER in available:
        available.remove(LLM_PROVIDER)
        available.insert(0, LLM_PROVIDER)
    return available


def structured(role: str, prompt: str, schema: Type[T], temperature: float = 0.2, retries: int = 2) -> T:
    """Gọi LLM ra schema Pydantic theo chuỗi ưu tiên: OpenAI -> OpenRouter -> Gemini -> Groq."""
    global _gemini_cooling_until, _openrouter_cooling_until
    providers = _provider_order()
    if not providers:
        raise RuntimeError("Chưa cấu hình API key LLM nào (OPENAI / OPENROUTER / GEMINI / GROQ) trong .env!")

    last_err: Optional[Exception] = None
    for idx, prov in enumerate(providers):
        for attempt in range(retries):
            try:
                if prov == "openai":
                    return _call_openai_structured(prompt, schema, temperature)
                if prov == "openrouter":
                    return _call_openrouter_structured(role, prompt, schema, temperature)
                if prov == "gemini":
                    return _call_gemini_structured(role, prompt, schema, temperature)
                if prov == "groq":
                    return _call_groq_structured(prompt, schema, temperature)
            except Exception as e:
                last_err = e
                err_str = str(e).lower()
                if prov == "openrouter" and any(k in err_str for k in ("429", "free-models-per-day", "rate limit")):
                    _openrouter_cooling_until = time.time() + 900  # Nghỉ 15 phút khi chạm trần OpenRouter
                    print(f"[Auto-Fallback] OpenRouter chạm giới hạn ({str(e)[:70]}). Tạm ngưng OpenRouter 15p...")
                    break
                if prov == "gemini" and any(k in err_str for k in _OVERLOAD_KEYS):
                    _gemini_cooling_until = time.time() + 300
                    print(f"[Auto-Fallback] Gemini quá tải ({str(e)[:60]}). Chuyển sang provider tiếp theo...")
                    break
                print(f"[{prov.upper()}] Thử lần {attempt + 1}/{retries} lỗi: {str(e)[:90]}")
                time.sleep(0.8 * (attempt + 1))

        if idx < len(providers) - 1:
            print(f"[Auto-Fallback] {prov.upper()} không khả dụng, chuyển sang {providers[idx + 1].upper()}...")

    raise RuntimeError(f"Tất cả các mô hình LLM ({role}) đều thất bại: {last_err}")


def text(role: str, prompt: str, temperature: float = 0.2) -> str:
    """Gọi LLM sinh text thông thường với chuỗi fallback đa provider."""
    global _gemini_cooling_until, _openrouter_cooling_until
    providers = _provider_order()
    last_err: Optional[Exception] = None

    for prov in providers:
        try:
            if prov == "openai":
                return _call_openai_compat(
                    OPENAI_BASE_URL,
                    get_key("OPENAI_API_KEY"),
                    OPENAI_MODEL,
                    [{"role": "user", "content": prompt}],
                    temperature,
                    max_tokens=4096,
                )
            if prov == "openrouter":
                first_or_model = [m.strip() for m in OPENROUTER_MODEL.split(",") if m.strip()][0]
                return _call_openai_compat(
                    "https://openrouter.ai/api/v1",
                    get_key("OPENROUTER_API_KEY"),
                    first_or_model,
                    [{"role": "user", "content": prompt}],
                    temperature,
                    max_tokens=4096,
                    extra_headers={"HTTP-Referer": "https://faceless-studio.local", "X-Title": "Faceless Studio v3"},
                )
            if prov == "gemini":
                client = _get_gemini()
                if client:
                    from google.genai import types
                    resp = client.models.generate_content(
                        model=MODELS.get(role, "gemini-3.5-flash"),
                        contents=prompt,
                        config=types.GenerateContentConfig(temperature=temperature),
                    )
                    return resp.text
            if prov == "groq":
                client_groq = _get_groq()
                if client_groq:
                    for gm in GROQ_MODELS:
                        try:
                            resp = client_groq.chat.completions.create(
                                model=gm,
                                messages=[{"role": "user", "content": prompt}],
                                temperature=temperature,
                                max_tokens=4096,
                            )
                            return resp.choices[0].message.content or ""
                        except Exception:
                            continue
        except Exception as e:
            last_err = e
            if prov == "openrouter" and "429" in str(e).lower():
                _openrouter_cooling_until = time.time() + 900
            if prov == "gemini" and any(k in str(e).lower() for k in _OVERLOAD_KEYS):
                _gemini_cooling_until = time.time() + 300

    raise RuntimeError(f"Không có LLM nào khả dụng! Lỗi cuối: {last_err}")

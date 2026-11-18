"""Kiểm tra key hoạt động (mỗi dịch vụ 1 lệnh gọi nhỏ):  python scripts/smoke_test.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.config import get_key  # noqa: E402


def check(name, fn):
    try:
        print(f"[OK ] {name}: {fn()}")
    except Exception as e:
        print(f"[ERR] {name}: {type(e).__name__}: {str(e)[:200]}")


def gemini():
    from core.llm import text
    return text("autopsy", "Reply with the single word: pong").strip()


def groq():
    from groq import Groq
    r = Groq(api_key=get_key("GROQ_API_KEY")).chat.completions.create(
        model="openai/gpt-oss-20b", messages=[{"role": "user", "content": "Reply: pong"}], max_tokens=5)
    return r.choices[0].message.content.strip()


def exa():
    from exa_py import Exa
    r = Exa(get_key("EXA_API_KEY")).search("Apollo 13 post-mortem report", num_results=1)
    return r.results[0].url


check("Gemini", gemini)
check("Groq", groq)
check("Exa", exa)

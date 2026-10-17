"""Shared model router: Groq first, Gemini second, never a fabricated answer."""
import json, os, re, urllib.error, urllib.request

def _offline_extract(prompt: str):
    """Small local fallback so backend workflows remain demonstrable without API keys.

    It is deliberately extractive: it never claims to be an LLM and only returns
    sentences found in the supplied prompt/context.
    """
    question = prompt.split("QUESTION:", 1)[-1].strip().lower()
    source_block = prompt.split("SOURCES:", 1)[-1] if "SOURCES:" in prompt else prompt
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", source_block) if len(s.strip()) > 20]
    question_words = set(re.findall(r"[a-z]{4,}", question))
    ranked = sorted(sentences, key=lambda s: len(question_words & set(re.findall(r"[a-z]{4,}", s.lower()))), reverse=True)
    selected = ranked[:3]
    if not selected:
        return "I do not know from the supplied sources."
    return "Based only on the supplied sources:\n- " + "\n- ".join(selected)

def hermes_base_url():
    return os.getenv("HERMES_BASE_URL", "").rstrip("/")

def hermes_configured():
    return bool(hermes_base_url())

def hermes_is_private_safe(private_mode: bool):
    """Private mode may only use a local Hermes endpoint."""
    if not private_mode:
        return True
    base = hermes_base_url().lower()
    return os.getenv("HERMES_PRIVATE_MODE", "false").lower() in {"1", "true", "yes", "on"} and any(host in base for host in ("localhost", "127.0.0.1", "::1"))

def generate_hermes(prompt: str, private_mode: bool = False):
    base = hermes_base_url()
    if not base:
        return None, None
    if not hermes_is_private_safe(private_mode):
        return None, "hermes-private-blocked"
    payload = {"model": os.getenv("HERMES_MODEL", "hermes"), "messages": [{"role": "user", "content": prompt}], "temperature": 0.1, "stream": False}
    headers = {"Content-Type": "application/json"}
    if os.getenv("HERMES_API_KEY"):
        headers["Authorization"] = f"Bearer {os.environ['HERMES_API_KEY']}"
    try:
        request = urllib.request.Request(base + os.getenv("HERMES_CHAT_PATH", "/v1/chat/completions"), data=json.dumps(payload).encode(), headers=headers, method="POST")
        with urllib.request.urlopen(request, timeout=float(os.getenv("HERMES_TIMEOUT_SECONDS", "60"))) as response:
            body = json.loads(response.read().decode())
        choices = body.get("choices") or []
        message = choices[0].get("message", {}) if choices else {}
        text = message.get("content") or body.get("response") or body.get("text")
        return text, "hermes" if text else None
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError, IndexError):
        return None, "hermes-unavailable"

def hermes_status(probe: bool = False):
    base = hermes_base_url()
    result = {"configured": bool(base), "base_url": base or None, "model": os.getenv("HERMES_MODEL", "hermes"), "reachable": False}
    if not base or not probe:
        return result
    try:
        request = urllib.request.Request(base + os.getenv("HERMES_HEALTH_PATH", "/health"), method="GET")
        with urllib.request.urlopen(request, timeout=5) as response:
            result["reachable"] = 200 <= response.status < 300
    except (urllib.error.URLError, TimeoutError, OSError):
        result["reachable"] = False
    return result

def generate(prompt: str, private_mode: bool = False, hermes_mode: bool = False):
    if hermes_mode:
        return generate_hermes(prompt, private_mode)
    if private_mode:
        base=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
        try:
            request=urllib.request.Request(base+"/api/generate",data=json.dumps({"model":os.getenv("OLLAMA_MODEL","qwen3:8b"),"prompt":prompt,"stream":False}).encode(),headers={"Content-Type":"application/json"})
            with urllib.request.urlopen(request,timeout=120) as response:
                body=json.loads(response.read().decode())
            return body.get("response"), "ollama-private"
        except Exception:
            return None, None
    if os.getenv("GROQ_API_KEY"):
        try:
            from groq import Groq
            result=Groq(api_key=os.environ["GROQ_API_KEY"]).chat.completions.create(model=os.getenv("GROQ_MODEL","openai/gpt-oss-20b"),messages=[{"role":"user","content":prompt}],temperature=0.1)
            return result.choices[0].message.content, "groq"
        except Exception:
            pass
    if os.getenv("GEMINI_API_KEY"):
        try:
            from google import genai
            result=genai.Client(api_key=os.environ["GEMINI_API_KEY"]).models.generate_content(model=os.getenv("GEMINI_MODEL","gemini-2.5-flash"),contents=prompt)
            return result.text, "gemini"
        except Exception:
            pass
    if os.getenv("LOCAL_FALLBACK", "true").lower() in {"1", "true", "yes", "on"}:
        return _offline_extract(prompt), "offline-extractive"
    return None, None

def configured_models():
    return {"groq": bool(os.getenv("GROQ_API_KEY")), "gemini": bool(os.getenv("GEMINI_API_KEY")), "ollama": bool(os.getenv("OLLAMA_BASE_URL")), "hermes": hermes_configured()}

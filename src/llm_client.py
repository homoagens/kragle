# llm_client.py — calls the LLM backend and returns text.
# Supports three providers: backend (custom proxy), openai (compatible), anthropic.

import json
import time
import requests

import config


def _resolved_endpoint(provider, base_url, api_key):
    p = provider or config.LLM_PROVIDER or "openai"
    if p == "anthropic":
        url = (base_url or config.LLM_BASE_URL or "https://api.anthropic.com").rstrip("/")
        key = api_key or config.LLM_API_KEY
    elif p == "backend":
        url = (base_url or config.LLM_BASE_URL or config.BACKEND_URL).rstrip("/")
        key = api_key or config.LLM_API_KEY or config.BACKEND_KEY
    else:  # openai-compatible (Ollama, OpenAI, Groq, etc.)
        url = (base_url or config.LLM_BASE_URL or "http://localhost:11434/v1").rstrip("/")
        key = api_key or config.LLM_API_KEY
    return p, url, key


def _post_with_retry(url, headers, payload, timeout, label):
    last = None
    for attempt in range(5):
        print(f"[llm_client] {label} is thinking...")
        last = requests.post(url, headers=headers, json=payload, timeout=timeout)
        if last.status_code != 502:
            break
        wait = 30 * (attempt + 1)
        print(f"[llm_client] 502 — waiting {wait}s, retrying ({attempt + 1}/5)...")
        time.sleep(wait)
    last.raise_for_status()
    return last


def _call_backend(messages, model, temperature, max_tokens, timeout, base_url, api_key):
    payload = {"messages": messages, "model": model,
               "temperature": temperature, "max_tokens": max_tokens}
    headers = {"Content-Type": "application/json",
               "Authorization": f"Bearer {api_key}"}
    resp   = _post_with_retry(f"{base_url}/llm", headers, payload, timeout, model)
    data   = resp.json()
    msg    = data["raw"]["choices"][0]["message"]
    finish = data["raw"]["choices"][0].get("finish_reason", "")
    text   = (msg.get("content") or msg.get("reasoning_content") or "").strip()
    return text, finish


def _call_openai_compatible(messages, model, temperature, max_tokens, timeout, base_url, api_key):
    payload = {"model": model, "messages": messages,
               "temperature": temperature, "max_tokens": max_tokens}
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    resp   = _post_with_retry(f"{base_url}/chat/completions", headers, payload, timeout, model)
    data   = resp.json()
    choice = data["choices"][0]
    msg    = choice.get("message", {})
    finish = choice.get("finish_reason", "")
    text   = (msg.get("content") or msg.get("reasoning_content") or "").strip()
    return text, finish


def _call_anthropic(messages, model, temperature, max_tokens, timeout, base_url, api_key):
    ANTHROPIC_VERSION = "2023-06-01"
    system_content = ""
    user_messages  = []
    for m in messages:
        if m.get("role") == "system" and not user_messages:
            system_content = m.get("content", "")
        else:
            role = m.get("role", "user")
            if role not in ("user", "assistant"):
                role = "user"
            user_messages.append({"role": role, "content": m.get("content", "")})
    if not user_messages:
        user_messages = [{"role": "user", "content": ""}]
    payload: dict = {"model": model, "messages": user_messages,
                     "max_tokens": max_tokens, "temperature": temperature}
    if system_content:
        payload["system"] = system_content
    headers = {"Content-Type": "application/json",
               "x-api-key": api_key,
               "anthropic-version": ANTHROPIC_VERSION}
    resp = _post_with_retry(f"{base_url}/v1/messages", headers, payload, timeout, model)
    data = resp.json()
    content_blocks = data.get("content", [])
    text = "".join(b.get("text", "") for b in content_blocks if b.get("type") == "text").strip()
    finish = data.get("stop_reason", "")
    if finish == "max_tokens":
        finish = "length"
    return text, finish


# ── Streaming variants ─────────────────────────────────────────────────
# Used when an `on_token` callback is supplied: tokens are forwarded as they
# arrive so the UI can render the model's output live. The full text and
# finish_reason are still returned, identical in shape to the blocking calls.

def _stream_openai_compatible(messages, model, temperature, max_tokens, timeout,
                              base_url, api_key, on_token):
    payload = {"model": model, "messages": messages, "temperature": temperature,
               "max_tokens": max_tokens, "stream": True}
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    print(f"[llm_client] {model} is streaming...")
    parts, finish = [], ""
    with requests.post(f"{base_url}/chat/completions", headers=headers, json=payload,
                       timeout=timeout, stream=True) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            try:
                obj = json.loads(data)
            except ValueError:
                continue
            choice = (obj.get("choices") or [{}])[0]
            delta  = choice.get("delta", {}) or {}
            piece  = delta.get("content") or delta.get("reasoning_content") or ""
            if piece:
                parts.append(piece)
                on_token(piece)
            if choice.get("finish_reason"):
                finish = choice["finish_reason"]
    return "".join(parts).strip(), finish


def _stream_anthropic(messages, model, temperature, max_tokens, timeout,
                      base_url, api_key, on_token):
    ANTHROPIC_VERSION = "2023-06-01"
    system_content = ""
    user_messages  = []
    for m in messages:
        if m.get("role") == "system" and not user_messages:
            system_content = m.get("content", "")
        else:
            role = m.get("role", "user")
            if role not in ("user", "assistant"):
                role = "user"
            user_messages.append({"role": role, "content": m.get("content", "")})
    if not user_messages:
        user_messages = [{"role": "user", "content": ""}]
    payload: dict = {"model": model, "messages": user_messages,
                     "max_tokens": max_tokens, "temperature": temperature, "stream": True}
    if system_content:
        payload["system"] = system_content
    headers = {"Content-Type": "application/json",
               "x-api-key": api_key,
               "anthropic-version": ANTHROPIC_VERSION}
    print(f"[llm_client] {model} is streaming...")
    parts, finish = [], ""
    with requests.post(f"{base_url}/v1/messages", headers=headers, json=payload,
                       timeout=timeout, stream=True) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data:"):
                continue
            try:
                obj = json.loads(line[5:].strip())
            except ValueError:
                continue
            t = obj.get("type")
            if t == "content_block_delta":
                d     = obj.get("delta", {}) or {}
                piece = d.get("text") or d.get("thinking") or ""
                if piece:
                    parts.append(piece)
                    on_token(piece)
            elif t == "message_delta":
                sr = obj.get("delta", {}).get("stop_reason")
                if sr:
                    finish = sr
    if finish == "max_tokens":
        finish = "length"
    return "".join(parts).strip(), finish


def call_llm(messages, model=None, temperature=None, max_tokens=None, timeout=None,
             provider=None, base_url=None, api_key=None, on_token=None):
    if model       is None: model       = config.DEFAULT_MODEL
    if temperature is None: temperature = config.DEFAULT_TEMPERATURE
    if max_tokens  is None: max_tokens  = config.MAX_TOKENS
    if timeout     is None: timeout     = config.TIMEOUT

    prov, url, key = _resolved_endpoint(provider, base_url, api_key)

    # Streaming path — only for providers that support it natively. The custom
    # backend proxy has no streaming endpoint, so it falls through to blocking
    # below and replays the full text through on_token once it arrives.
    if on_token is not None and prov == "openai":
        text, finish = _stream_openai_compatible(messages, model, temperature, max_tokens, timeout, url, key, on_token)
    elif on_token is not None and prov == "anthropic":
        text, finish = _stream_anthropic(messages, model, temperature, max_tokens, timeout, url, key, on_token)
    elif prov == "backend":
        text, finish = _call_backend(messages, model, temperature, max_tokens, timeout, url, key)
        if on_token is not None and text:
            on_token(text)
    elif prov == "openai":
        text, finish = _call_openai_compatible(messages, model, temperature, max_tokens, timeout, url, key)
    elif prov == "anthropic":
        text, finish = _call_anthropic(messages, model, temperature, max_tokens, timeout, url, key)
    else:
        raise ValueError(f"Unknown provider: {prov!r}. Use 'backend', 'openai' or 'anthropic'.")

    if finish == "length":
        raise RuntimeError(f"Response truncated (finish_reason=length). Increase MAX_TOKENS. Text: {text[:100]!r}")
    if not text:
        raise RuntimeError("The model returned an empty response.")
    return text


if __name__ == "__main__":
    try:
        r = call_llm([{"role": "user", "content": "Reply only: OK"}], temperature=0.0, max_tokens=64)
        print(f"PASS — {r}")
    except Exception as e:
        print(f"FAIL — {e}")

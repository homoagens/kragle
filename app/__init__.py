import os
import re
import sys
import json
import importlib
import subprocess
from pathlib import Path

from flask import Flask, Response, jsonify, request, send_from_directory
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(ENV_PATH)

sys.path.insert(0, str(BASE_DIR))
import config

WEB_DIR    = BASE_DIR / "web"
OUTPUT_DIR = config.OUTPUT_DIR

app = Flask(__name__, static_folder=str(WEB_DIR), static_url_path="/web")

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[mKGHFJABCDnsuhl]")

def strip_ansi(text):
    return ANSI_RE.sub("", text)

def sse_subprocess(cmd, cwd):
    env = {
        **os.environ,
        "PYTHONUNBUFFERED": "1",
        "NO_COLOR":         "1",
        "FORCE_COLOR":      "0",
        "COLUMNS":          "120",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUTF8":       "1",
        "TERM":             "dumb",
    }
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", cwd=str(cwd), env=env,
    )
    for raw in proc.stdout:
        line = strip_ansi(raw.rstrip())
        if line:
            yield f"data: {json.dumps({'type': 'log', 'text': line})}\n\n"
    proc.wait()
    yield f"data: {json.dumps({'type': 'done', 'code': proc.returncode})}\n\n"

SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


# ── Routes ────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(str(WEB_DIR), "index.html")


@app.route("/api/config")
def get_config():
    return jsonify({
        "provider": config.LLM_PROVIDER,
        "model":    config.DEFAULT_MODEL,
    })


# ── Settings — manage .env from the UI ────────────────────────────────

def _upsert_env(env_path, updates):
    """Update or insert env vars in .env, preserving comments and order."""
    lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    seen  = set()
    out   = []
    pat   = re.compile(r"^([A-Z_][A-Z0-9_]*)=(.*)$")
    for line in lines:
        m = pat.match(line.lstrip())
        if m and m.group(1) in updates:
            key = m.group(1)
            seen.add(key)
            out.append(f"{key}={updates[key]}")
        else:
            out.append(line)
    for key, val in updates.items():
        if key in seen:
            continue
        out.append(f"{key}={val}")
    env_path.write_text("\n".join(out) + "\n", encoding="utf-8")


def _reload_config():
    load_dotenv(ENV_PATH, override=True)
    importlib.reload(config)


def _mask(value):
    if not value:
        return ""
    if len(value) <= 4:
        return "•" * len(value)
    return "•" * (len(value) - 4) + value[-4:]


@app.route("/api/settings", methods=["GET"])
def get_settings():
    return jsonify({
        "provider":            config.LLM_PROVIDER,
        "base_url":            config.LLM_BASE_URL,
        "api_key_set":         bool(config.LLM_API_KEY),
        "api_key_preview":     _mask(config.LLM_API_KEY),
        "default_model":       config.DEFAULT_MODEL,
        "backend_url":         config.BACKEND_URL,
        "backend_key_set":     bool(config.BACKEND_KEY),
        "backend_key_preview": _mask(config.BACKEND_KEY),
        "env_path":            str(ENV_PATH),
        "env_exists":          ENV_PATH.exists(),
    })


@app.route("/api/settings", methods=["POST"])
def save_settings():
    body = request.get_json(silent=True) or {}
    mapping = {
        "provider":      "LLM_PROVIDER",
        "base_url":      "LLM_BASE_URL",
        "api_key":       "LLM_API_KEY",
        "default_model": "DEFAULT_MODEL",
        "backend_url":   "BACKEND_URL",
        "backend_key":   "BACKEND_KEY",
    }
    updates = {env_key: body[k] for k, env_key in mapping.items() if k in body and body[k] is not None}
    _upsert_env(ENV_PATH, updates)
    _reload_config()
    return jsonify({"ok": True})


@app.route("/api/generate", methods=["POST"])
def generate():
    brief     = request.get_json(silent=True) or {}
    brief_arg = json.dumps(brief)

    def gen():
        yield from sse_subprocess(
            [sys.executable, "main.py",
             "--brief", brief_arg,
             "--out",   str(OUTPUT_DIR)],
            BASE_DIR,
        )
        # After completion, find the most recently created file
        files = sorted(OUTPUT_DIR.glob("prompt_*.md"), key=lambda p: p.stat().st_mtime)
        if files:
            latest  = files[-1]
            content = latest.read_text(encoding="utf-8")
            yield f"data: {json.dumps({'type': 'result', 'filename': latest.name, 'content': content})}\n\n"

    return Response(gen(), mimetype="text/event-stream", headers=SSE_HEADERS)


@app.route("/api/prompts")
def list_prompts():
    prompts = []
    for f in sorted(OUTPUT_DIR.glob("prompt_*.md"), key=lambda p: -p.stat().st_mtime):
        prompts.append({
            "name":  f.name,
            "size":  f.stat().st_size,
            "mtime": f.stat().st_mtime,
        })
    return jsonify(prompts)


@app.route("/api/prompts/<path:filename>")
def get_prompt(filename):
    return send_from_directory(str(OUTPUT_DIR), filename)


@app.route("/api/quit", methods=["POST"])
def quit_app():
    import threading
    threading.Timer(0.3, lambda: os._exit(0)).start()
    return jsonify({"ok": True})


@app.route("/api/prompts/<path:filename>", methods=["DELETE"])
def delete_prompt(filename):
    f = OUTPUT_DIR / filename
    if not f.exists():
        return jsonify({"error": "not found"}), 404
    f.unlink()
    return jsonify({"ok": True})

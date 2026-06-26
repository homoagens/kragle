# config.py — KRAGLE global parameters

from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv(Path(__file__).parent / ".env")

DEBUG = os.getenv("KRAGLE_DEBUG", "").lower() in ("1", "true", "yes")

# ── LLM Provider ───────────────────────────────────────────────────────
# "backend"   — local custom proxy (uses BACKEND_URL / BACKEND_KEY below)
# "openai"    — OpenAI, Groq, Ollama /v1, vLLM, LM Studio, OpenRouter...
# "anthropic" — native Anthropic API
#
# Leave LLM_BASE_URL empty unless you want to override the provider default.
# When provider="openai" and LLM_BASE_URL is empty, the client falls back
# to a local Ollama (http://localhost:11434/v1).

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "")
LLM_API_KEY  = os.getenv("LLM_API_KEY",  "")

# ── Backend (custom proxy) credentials ─────────────────────────────────
# Only used when LLM_PROVIDER="backend".
BACKEND_URL = os.getenv("BACKEND_URL", "")
BACKEND_KEY = os.getenv("BACKEND_KEY", "")

# ── Default model ──────────────────────────────────────────────────────
DEFAULT_MODEL       = os.getenv("DEFAULT_MODEL", "llama3.2")
DEFAULT_TEMPERATURE = float(os.getenv("DEFAULT_TEMPERATURE", "0.2"))

# ── General parameters ─────────────────────────────────────────────────
# MAX_TOKENS / MAX_STEPS are env-driven so they can be tuned live from the UI
# (the right value depends on the model under the hood — thinking models need
# a larger output budget or the answer gets truncated).
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "4096"))
TIMEOUT    = int(os.getenv("TIMEOUT", "300"))

MAX_STEPS       = int(os.getenv("MAX_STEPS", "15"))
MAX_MESSAGES    = 30
MAX_CHARS       = 150000
MESSAGES_RECENT = 6

# ── Output directory (generated prompt_*.md files) ─────────────────────
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# ── Web server ─────────────────────────────────────────────────────────
WEB_HOST = os.getenv("WEB_HOST", "0.0.0.0")
WEB_PORT = int(os.getenv("WEB_PORT", "7861"))

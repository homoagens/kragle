# Kragle

A prompt generator for AI coding agents.

You describe what you want to build. Kragle assembles a panel of three AI agents — a pragmatist, a critic, and an architect — each of whom reads the brief and writes an independent prompt draft from their own angle. A fourth agent acts as jury, merges the drafts into a single coherent prompt, and saves it as a ready-to-use `prompt_<project>.md` file.

The result is a structured, opinionated prompt that covers the task, context, implementation steps, constraints, expected output, and verification — exactly what a coding agent needs to work autonomously.

---

## Why

Writing a good prompt for Claude Code or Codex is harder than it looks. A single perspective misses edge cases (the critic's job), skips architectural reasoning (the architect's job), or stays too abstract to be actionable (the pragmatist's job). Three agents with conflicting biases produce a more complete brief than any one of them would alone.

---

## Pipeline

```
INTAKE  →  ENSEMBLE (pragmatist + critic + architect)  →  AGGREGATE  →  prompt_<project>.md
```

1. **Intake** — collects context from the user (via form in web mode, via interactive Q&A in CLI mode)
2. **Ensemble** — three independent agents, each with a different reasoning bias and temperature, write a full prompt draft
3. **Aggregate** — a jury agent fuses the three drafts into one final prompt, resolving conflicts and keeping the best of each
4. **Output** — the prompt is saved to `output/prompt_<project>.md`, displayed in the UI, and ready to paste

Each ensemble agent runs a full ReAct loop (take notes, reason, refine) before producing its draft. They share the same brief but start with an empty notepad — no cross-contamination between perspectives.

---

## Setup

One-shot install (creates a `venv/` and installs dependencies):

```bat
install.bat       :: Windows
```
```bash
chmod +x install.sh start.sh && ./install.sh    # Linux / macOS
```

Then launch the web UI (also opens your browser at `http://localhost:7861`):

```bat
start.bat         :: Windows
./start.sh        # Linux / macOS
```

If you prefer the manual setup:

```
cd kragle
pip install -r requirements.txt
cp .env.example .env       # then edit .env with your LLM credentials
python -m app.run          # → http://0.0.0.0:7861
```

Or use the CLI (interactive intake with Q&A):

```
python main.py
python main.py --out ~/prompts/      # custom output directory
python main.py --target codex        # target agent (default: claude-code)
python main.py --steps 10            # ReAct steps per ensemble agent (default: 6)
```

---

## Web UI

Fill in the form:

- **Project name** — used as the filename (`prompt_<name>.md`)
- **Task description** — the core of the brief; be specific about files, behaviour, and expected outcome
- **Additional context** — stack, conventions, patterns to follow, things to avoid
- **Target** — `claude-code` or `codex`
- **Steps per agent** — higher means more detailed drafts, longer generation time

Click **Genera prompt**. The agent log streams in real time. When done, the result panel appears with the final prompt. Copy it to clipboard or download the `.md` file.

Previously generated prompts are listed in the sidebar. Click any entry to view it again; the delete button removes it permanently.

---

## Provider configuration

Edit `.env` to choose your LLM provider.

**Local backend (default)**
```env
LLM_PROVIDER=backend
BACKEND_URL=http://127.0.0.1:19000
BACKEND_KEY=your-key
DEFAULT_MODEL=gemma4-e4b
```

**Ollama (local, free)**
```env
LLM_PROVIDER=openai
LLM_BASE_URL=http://localhost:11434/v1
DEFAULT_MODEL=llama3.2
```

**OpenAI**
```env
LLM_PROVIDER=openai
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-...
DEFAULT_MODEL=gpt-4o-mini
```

**Anthropic**
```env
LLM_PROVIDER=anthropic
LLM_API_KEY=sk-ant-...
DEFAULT_MODEL=claude-haiku-4-5
```

**Groq, OpenRouter, DeepSeek, Mistral, vLLM...**
```env
LLM_PROVIDER=openai
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_API_KEY=gsk_...
DEFAULT_MODEL=llama-3.3-70b-versatile
```

All three agents (pragmatist, critic, architect) use the same `DEFAULT_MODEL`. The temperature varies per agent (0.15 / 0.40 / 0.65) to enforce different reasoning styles — no configuration needed.

### Settings from the UI

The gear icon in the top-right header opens an in-app settings panel. From there you can switch provider, change model and base URL, paste an API key, and save — Kragle writes the changes to `.env` and reloads the config in place. No need to edit files by hand.

---

## Agent biases

| Agent | Temperature | Bias |
|---|---|---|
| Pragmatist | 0.15 | Concrete steps. Every file that must be created or modified. Exact function names. Precise order of operations. |
| Critic | 0.40 | Failure modes. Wrong assumptions. Edge cases. The hardest verification scenario, not the happy path. |
| Architect | 0.65 | Component structure. Data flow. Existing patterns the new code must respect. Architectural justification for every step. |

---

## Output format

The final prompt follows a consistent structure regardless of the task:

```markdown
## Task
## Context
## Steps
## Constraints
## Expected output
## Verification
```

The aggregator agent is instructed to keep all three perspectives present in the final output — the pragmatist's file list, the critic's edge cases, the architect's design rationale — merged into a single coherent document.

---

## Architecture

```
main.py          entry point: intake → ensemble loop → aggregate → save
agent.py         generic ReAct loop (THOUGHT → ACTION → OBSERVATION → FINAL)
orchestrator.py  Profile dataclass, run_ensemble helper
aggregator.py    single LLM call that merges N result dicts into one
skills.py        take_note, read_notes, ask_user (CLI only)
prompts.py       INTAKE_PROMPT, ENSEMBLE_PROMPT, AGGREGATOR_PROMPT
llm_client.py    multi-provider HTTP client (backend / openai / anthropic)
config.py        settings loaded from .env
app/__init__.py  Flask: POST /api/generate (SSE), GET/DELETE /api/prompts
output/          generated prompt_*.md files
```

---

## Web UI port

Default: `7861`. Override with `WEB_PORT=8080` in `.env` or `--port 8080` on the command line.

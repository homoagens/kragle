<h2 align="center">⚙️ Kragle</h2>

<p align="center">
  <em>Don't write the prompt. Convene a panel that writes it for you.</em>
</p>

<p align="center">
  Three biased agents  ·  One merged brief  ·  Built for Claude Code &amp; Codex  ·  Runs on your own LLM
</p>

<p align="center">
  <a href="./LICENSE"><img src="https://img.shields.io/badge/license-MIT-7b68ee?style=flat-square" alt="License"></a>
  <img src="https://img.shields.io/badge/python-3.10%2B-3776ab?style=flat-square" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/frontend-vanilla%20JS%2C%20no%20build-43a047?style=flat-square" alt="No build step">
  <img src="https://img.shields.io/badge/provider-any%20OpenAI--compatible-f97316?style=flat-square" alt="Any provider">
</p>

---

You describe what you want to build. Kragle convenes a panel of three AI agents — a **pragmatist**, a **critic**, and an **architect** — each of whom reads your brief and writes an independent prompt draft from their own angle. A fourth agent acts as **jury**, merges the drafts into one coherent prompt, and saves it as a ready-to-use `prompt_<project>.md`.

The result is a structured, opinionated prompt covering task, context, steps, constraints, expected output, and verification — exactly what a coding agent needs to work autonomously.

---

## ✦ Why three agents?

Writing a good prompt for Claude Code or Codex is harder than it looks. A single perspective misses edge cases (the critic's job), skips architectural reasoning (the architect's job), or stays too abstract to be actionable (the pragmatist's job).

**Three agents with conflicting biases produce a more complete brief than any one of them would alone.** Kragle makes that disagreement productive, then resolves it.

---

## 🔁 Pipeline

```
INTAKE  →  ENSEMBLE (pragmatist + critic + architect)  →  AGGREGATE  →  prompt_<project>.md
```

1. **Intake** — collects context (via form in web mode, interactive Q&A in CLI mode)
2. **Ensemble** — three independent agents, each with a different reasoning bias and temperature, write a full prompt draft
3. **Aggregate** — a jury agent fuses the three drafts into one final prompt, resolving conflicts and keeping the best of each
4. **Output** — saved to `output/prompt_<project>.md`, displayed in the UI, ready to paste

Each ensemble agent runs a full ReAct loop (take notes, reason, refine) before producing its draft. They share the same brief but start with an empty notepad — no cross-contamination between perspectives.

---

## ⚡ Quickstart

One-shot install (creates a `venv/` and installs dependencies):

```bat
install.bat       :: Windows
```
```bash
chmod +x install.sh start.sh && ./install.sh    # Linux / macOS
```

Point it at your LLM (interactive — writes `.env` for you):

```bat
configure.bat     :: Windows
./configure.sh    # Linux / macOS
```

Launch the web UI (opens your browser at `http://localhost:7861`):

```bat
start.bat         :: Windows
./start.sh        # Linux / macOS
```

<details>
<summary>Manual setup / CLI mode</summary>

```bash
cd kragle
pip install -r requirements.txt
cp .env.example .env       # then edit .env with your LLM credentials
python -m app.run          # → http://0.0.0.0:7861
```

CLI mode (interactive intake with Q&A):

```bash
python main.py
python main.py --out ~/prompts/      # custom output directory
python main.py --target codex        # target agent (default: claude-code)
python main.py --steps 10            # ReAct steps per ensemble agent (default: 6)
```

</details>

---

## 🖥 Web UI

Fill in the form:

- **Project name** — used as the filename (`prompt_<name>.md`)
- **Task description** — the core of the brief; be specific about files, behaviour, and expected outcome
- **Additional context** — stack, conventions, patterns to follow, things to avoid
- **Target** — `claude-code` or `codex`
- **Steps per agent** — higher means more detailed drafts, longer generation time

Click **Generate**. The agent log streams in real time. When done, the result panel appears with the final prompt — copy it to clipboard or download the `.md`. Previously generated prompts live in the sidebar; click to view, or delete permanently.

The **gear icon** in the header opens an in-app settings panel: switch provider, change model and base URL, paste an API key, and save — Kragle writes `.env` and reloads config in place. No file editing required.

---

## 🔌 Provider configuration

Kragle speaks any **OpenAI-compatible** endpoint, plus native Anthropic. Edit `.env` or use the settings panel.

**Ollama (local, free — default)**
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

**Groq, OpenRouter, DeepSeek, Mistral, vLLM, LM Studio…**
```env
LLM_PROVIDER=openai
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_API_KEY=gsk_...
DEFAULT_MODEL=llama-3.3-70b-versatile
```

All three agents share the same `DEFAULT_MODEL`. The temperature varies per agent (0.15 / 0.40 / 0.65) to enforce different reasoning styles — no extra configuration needed.

---

## 🎭 Agent biases

| Agent | Temp | Bias |
|---|---|---|
| **Pragmatist** | 0.15 | Concrete steps. Every file to create or modify. Exact function names. Precise order of operations. |
| **Critic** | 0.40 | Failure modes. Wrong assumptions. Edge cases. The hardest verification scenario, not the happy path. |
| **Architect** | 0.65 | Component structure. Data flow. Existing patterns the new code must respect. Architectural justification for every step. |

---

## 📄 Output format

Every generated prompt follows the same structure, whatever the task:

```markdown
## Task
## Context
## Steps
## Constraints
## Expected output
## Verification
```

The aggregator keeps all three perspectives present in the final output — the pragmatist's file list, the critic's edge cases, the architect's design rationale — merged into one coherent document.

---

## 🗂 Architecture

```
main.py          entry point: intake → ensemble loop → aggregate → save
agent.py         generic ReAct loop (THOUGHT → ACTION → OBSERVATION → FINAL)
orchestrator.py  Profile dataclass, run_ensemble helper
aggregator.py    single LLM call that merges N result dicts into one
skills.py        take_note, read_notes, ask_user (CLI only)
prompts.py       INTAKE_PROMPT, ENSEMBLE_PROMPT, AGGREGATOR_PROMPT
llm_client.py    multi-provider HTTP client (openai / anthropic / backend)
config.py        settings loaded from .env
app/__init__.py  Flask: POST /api/generate (SSE), GET/DELETE /api/prompts
output/          generated prompt_*.md files
```

Web UI port defaults to `7861` — override with `WEB_PORT=8080` in `.env` or `--port 8080`.

---

## 🌱 Part of Homo Agens

Kragle is part of **[Homo Agens](https://github.com/homoagens)** — an open-source effort exploring autonomous agents, local inference, and a simple thesis:

> The model matters less than the architecture around it.
> Memory, tools, transparency, and execution control are what turn an LLM into something that actually gets things done.

---

## 📬 Contact

If you work on agents, local AI, open-source tooling, or developer experience — let's talk.

[Email](mailto:homoagens1@gmail.com) &nbsp;·&nbsp; [X / Twitter](https://x.com/homoagens1)

---

## License

[MIT](./LICENSE)

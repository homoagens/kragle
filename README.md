<h2 align="center">⚙️ Kragle</h2>

<p align="center">
  <em>Don't write the prompt. Convene a panel that writes it for you.</em>
</p>

<p align="center">
  <a href="./LICENSE"><img src="https://img.shields.io/badge/license-MIT-7b68ee?style=flat-square" alt="License"></a>
  <img src="https://img.shields.io/badge/python-3.10%2B-3776ab?style=flat-square" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/provider-any%20OpenAI--compatible-f97316?style=flat-square" alt="Any provider">
</p>

---

You describe what you want to build. Kragle runs your brief through three biased **LLM passes** — a **pragmatist**, a **critic**, and an **architect** — each writing an independent prompt draft from its own angle. A fourth pass acts as **jury**, merging them into one coherent prompt and saving it as a ready-to-use `prompt_<project>.md`.

The result is structured and opinionated — task, context, steps, constraints, expected output, verification — exactly what a coding agent needs to work autonomously.

> Under the hood these are plain LLM calls with different system prompts and temperatures, not autonomous agents. The orchestration is the point: bias them, run them, merge them.

---

## 🔁 Pipeline

```
INTAKE  →  ENSEMBLE (pragmatist + critic + architect)  →  AGGREGATE  →  prompt_<project>.md
```

1. **Intake** — collects context (form in web mode, interactive Q&A in CLI mode)
2. **Ensemble** — three independent passes, each with a different bias and temperature, write a full draft
3. **Aggregate** — a jury pass fuses the drafts into one, resolving conflicts and keeping the best of each
4. **Output** — saved to `output/prompt_<project>.md`, shown in the UI, ready to paste

Three conflicting biases produce a more complete brief than any single perspective would. Kragle makes that disagreement productive, then resolves it.

---

## ⚡ Quickstart

Three scripts, run in order — same flow on every platform.

| Step | Windows | Linux / macOS | What it does |
|---|---|---|---|
| **1. Install** | `install.bat` | `./install.sh` | Creates `venv/` and installs dependencies |
| **2. Configure** | `configure.bat` | `./configure.sh` | Points Kragle at your LLM and writes `.env` |
| **3. Start** | `start.bat` | `./start.sh` | Launches the web UI at `http://localhost:7861` |

```bat
:: Windows
install.bat
configure.bat
start.bat
```

```bash
# Linux / macOS
chmod +x install.sh configure.sh start.sh
./install.sh
./configure.sh
./start.sh
```

Step 1 is one-time; step 2 only when you change LLM; step 3 every time you use Kragle.

<details>
<summary>Manual setup / CLI mode</summary>

All source lives under `src/`; run it from the repo root.

```bash
pip install -r requirements.txt
cp .env.example .env                  # then edit .env with your LLM credentials
PYTHONPATH=src python -m app.run      # web UI → http://0.0.0.0:7861
```

CLI mode (interactive intake with Q&A):

```bash
python src/main.py
python src/main.py --out ~/prompts/   # custom output directory
python src/main.py --target codex     # target agent (default: claude-code)
python src/main.py --steps 10         # steps per ensemble pass (default: 6)
```

</details>

---

## 🖥 Web UI

Fill in the form — project name, task description, additional context, target (`claude-code` / `codex`), steps per pass — and click **Generate**. The run log streams in real time. When done, the result panel shows the final prompt to copy or download. Previous prompts live in the sidebar.

The **gear icon** opens an in-app settings panel: switch model, base URL, and API key, then save — Kragle writes `.env` and reloads in place.

---

## 🔌 Provider configuration

Kragle speaks any **OpenAI-compatible** endpoint. Set it via `configure` or edit `.env` directly.

```env
LLM_PROVIDER=openai
LLM_BASE_URL=http://localhost:11434/v1   # Ollama (local, default)
LLM_API_KEY=                             # empty for local; key for hosted
DEFAULT_MODEL=llama3.2
```

Swap `LLM_BASE_URL` / `DEFAULT_MODEL` for any other provider — OpenAI (`https://api.openai.com/v1`), Groq, OpenRouter, DeepSeek, Mistral, vLLM, LM Studio, llama.cpp…

All three passes share the same `DEFAULT_MODEL`. Only the temperature varies per role (0.15 / 0.40 / 0.65) — no extra configuration.

---

## 🎭 The three biases

| Role | Temp | Bias |
|---|---|---|
| **Pragmatist** | 0.15 | Concrete steps. Every file to create or modify. Exact function names. Precise order of operations. |
| **Critic** | 0.40 | Failure modes. Wrong assumptions. Edge cases. The hardest verification scenario, not the happy path. |
| **Architect** | 0.65 | Component structure. Data flow. Existing patterns the new code must respect. |

Every generated prompt follows the same structure: `## Task` · `## Context` · `## Steps` · `## Constraints` · `## Expected output` · `## Verification`.

---

## 🌱 Part of Homo Agens

Kragle is part of **[Homo Agens](https://github.com/homoagens)** — an open-source effort exploring autonomous agents and local inference, on a simple thesis:

> The model matters less than the architecture around it.

[Email](mailto:homoagens1@gmail.com) &nbsp;·&nbsp; [X / Twitter](https://x.com/homoagens1) &nbsp;·&nbsp; [MIT License](./LICENSE)

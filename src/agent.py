# agent.py — generic ReAct loop (Reasoning + Acting).
#
# An Agent is configured with:
#   - system_prompt : base instructions + description of JSON response formats
#   - skills        : dict {name: callable} — the agent's toolkit
#   - final_keys    : set of JSON keys that, if present in the response,
#                     terminate the loop (e.g. {"conclusion"} or {"final_answer"})
#
# The cycle:
#   1. the LLM responds with JSON containing "thought" + ("action"+"args" or a final_key)
#   2. if a final_key is present → loop ends, return the dict
#   3. otherwise execute skills[action](**args), append the OBSERVATION, repeat
#   4. if steps are exhausted → forced verdict
#
# Completely domain-agnostic. What the agent does is decided by
# system_prompt + skills. See README.md for an example.

import sys
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from rich.console import Console
from rich.panel import Panel

import config
import llm_client
import memory
from json_parser import extract_json

console = Console()


@dataclass
class AgentConfig:
    """Configuration for a single ReAct agent."""
    name:         str
    system_prompt: str
    skills:       dict                    # {skill_name: callable}
    final_keys:   tuple = ("conclusion",)  # keys that terminate the loop
    model:        Optional[str] = None
    temperature:  Optional[float] = None
    max_steps:    Optional[int] = None
    style:        str = ""                # operating style description, appended to system_prompt
    # Optional context passed as first argument to every skill
    # (e.g. case_dir, log_dir, session_id). None = not passed.
    skill_context: object = None
    skill_context_kwarg: str = "context"  # kwarg name used to inject it


def _token_emitter():
    """Returns a callback that streams model tokens, or None if disabled.

    In a real terminal (TTY) tokens are written raw so you see live typing.
    As a subprocess (the web server) each token is wrapped in STREAM_MARKER so
    the SSE layer can forward it as a 'stream' event. stdout is flushed per
    token so the UI updates immediately rather than waiting on buffering.
    """
    if not getattr(config, "STREAM_TOKENS", True):
        return None
    if sys.stdout.isatty():
        def emit(chunk):
            sys.stdout.write(chunk)
            sys.stdout.flush()
    else:
        marker = config.STREAM_MARKER
        def emit(chunk):
            sys.stdout.write(marker + json.dumps(chunk, ensure_ascii=False) + "\n")
            sys.stdout.flush()
    return emit


def _log_step(log_path: Path, entry: dict):
    """Incrementally writes each step to a JSON log file (list of dicts)."""
    if log_path.exists():
        log = json.loads(log_path.read_text(encoding="utf-8"))
    else:
        log = []
    log.append(entry)
    log_path.write_text(json.dumps(log, indent=2, ensure_ascii=False), encoding="utf-8")


def _call_skill(cfg: AgentConfig, action: str, args: dict) -> str:
    """Executes a skill with error handling. Always returns a string."""
    if action not in cfg.skills:
        return f"ERROR: skill '{action}' does not exist. Available: {list(cfg.skills)}"
    try:
        fn = cfg.skills[action]
        kwargs = dict(args)
        if cfg.skill_context is not None:
            kwargs.setdefault(cfg.skill_context_kwarg, cfg.skill_context)
        return str(fn(**kwargs))
    except Exception as e:
        return f"ERROR executing {action}: {e}"


def run_agent(cfg: AgentConfig, user_task: str, log_path: Optional[Path] = None) -> Optional[dict]:
    """
    Starts the ReAct loop.
    cfg       : AgentConfig
    user_task : initial user message (what the agent must do)
    log_path  : optional path to write the narrative step log

    Returns the final dict (containing one of the final_keys), or None.
    The dict is enriched with: name, forced (bool).
    """
    model       = cfg.model       or config.DEFAULT_MODEL
    temperature = cfg.temperature if cfg.temperature is not None else config.DEFAULT_TEMPERATURE
    max_steps   = cfg.max_steps   or config.MAX_STEPS

    on_token = _token_emitter()

    system_prompt = cfg.system_prompt
    if cfg.style:
        system_prompt += f"\n\nYour operating style: {cfg.style}"

    if log_path is not None:
        log_path = Path(log_path)
        log_path.write_text("[]", encoding="utf-8")

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_task},
    ]

    console.print(Panel(
        f"Agent started: [bold]{cfg.name.upper()}[/bold]",
        style="bold red"
    ))

    for step in range(1, max_steps + 1):
        console.print(f"\n[dim]━━━ Step {step}/{max_steps} ━━━[/dim]")

        # ── Memory compression ──────────────────────────────────────
        messages = memory.compress(messages, config.MAX_MESSAGES,
                                   f"loop {cfg.name}", model=model)
        total_chars = sum(len(m.get("content", "")) for m in messages)
        if total_chars > config.MAX_CHARS:
            console.print(
                f"[yellow]Payload {total_chars} chars — compressing...[/yellow]"
            )
            messages = memory.compress(messages, 0, f"loop {cfg.name}", model=model)

        # ── LLM call ─────────────────────────────────────────────────
        try:
            text = llm_client.call_llm(
                messages=messages, model=model,
                temperature=temperature, max_tokens=config.MAX_TOKENS,
                on_token=on_token,
            )
        except Exception as e:
            console.print(f"[red]LLM error at step {step}: {e}[/red]")
            continue

        # ── JSON parsing ─────────────────────────────────────────────
        try:
            response = extract_json(text)
        except RuntimeError as e:
            console.print(f"[red]{e}[/red]")
            continue

        thought = response.get("thought", "")
        console.print(Panel(thought, title="THOUGHT", style="bold yellow"))

        # ── FINAL — one of the final_keys is present ─────────────────
        final_key = next((k for k in cfg.final_keys if k in response), None)
        if final_key:
            console.print(Panel(
                json.dumps(
                    {k: response[k] for k in response if k != "thought"},
                    indent=2, ensure_ascii=False,
                ),
                title="FINAL", style="bold yellow"
            ))
            if log_path is not None:
                _log_step(log_path, {"step": step, **response})
            response["name"]   = cfg.name
            response["forced"] = False
            return response

        # ── ACTION ───────────────────────────────────────────────────
        if "action" not in response:
            console.print("[red]Response has no action or final key — skipping.[/red]")
            continue

        action = response["action"]
        args   = response.get("args", {}) or {}
        console.print(f"[cyan]ACTION:[/cyan] {action}({args})")

        observation = _call_skill(cfg, action, args)
        console.print(Panel(observation, title="OBSERVATION", style="cyan"))

        if log_path is not None:
            _log_step(log_path, {
                "step": step, "thought": thought,
                "action": action, "args": args, "observation": observation,
            })

        messages.append({"role": "assistant", "content": text})
        messages.append({"role": "user",      "content": f"[OBSERVATION]: {observation}"})

    # ── Steps exhausted — forced verdict ─────────────────────────────
    console.print(f"[yellow]Steps exhausted — requesting forced verdict...[/yellow]")
    final_list = " or ".join(f'"{k}"' for k in cfg.final_keys)
    messages.append({
        "role": "user",
        "content": (
            f"You have exhausted the available steps. "
            f"Using the information collected so far, produce NOW a final response "
            f"in JSON format with one of these keys: {final_list}. "
            f"You must conclude — no more actions allowed."
        )
    })
    messages = memory.compress(messages, config.MAX_MESSAGES,
                               f"forced {cfg.name}", model=model)

    try:
        text     = llm_client.call_llm(
            messages=messages, model=model,
            temperature=temperature, max_tokens=config.MAX_TOKENS,
            on_token=on_token,
        )
        response = extract_json(text)
    except Exception as e:
        console.print(f"[red]Forced verdict failed: {e}[/red]")
        return None

    thought = response.get("thought", "")
    console.print(Panel(thought, title="THOUGHT (forced)", style="bold yellow"))
    console.print(Panel(
        json.dumps(
            {k: response[k] for k in response if k != "thought"},
            indent=2, ensure_ascii=False,
        ),
        title="FINAL (forced)", style="bold yellow"
    ))
    if log_path is not None:
        _log_step(log_path, {"step": max_steps + 1, **response, "forced": True})
    response["name"]   = cfg.name
    response["forced"] = True
    return response

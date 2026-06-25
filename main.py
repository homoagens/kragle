# main.py — KRAGLE entry point
#
# Pipeline:
#   1. INTAKE   — an agent collects context via ask_user
#   2. ENSEMBLE — three agents (pragmatic / critical / architect) independently
#                 write draft prompts in English
#   3. AGGREGATE — an aggregator merges the drafts into the final prompt
#   4. OUTPUT   — prints to screen + saves to prompt_<project>.md
#
# Usage:
#   python main.py              → runs the full pipeline
#   python main.py --out dir/   → destination folder for the .md file
#   python main.py --target codex
#   python main.py --steps 12   → ReAct steps per agent (default 10)

import sys
import json
import argparse
import re
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

import config
from agent import AgentConfig, run_agent
from orchestrator import Profile
from aggregator import aggregate
from skills import take_note, read_notes, ask_user
from prompts import INTAKE_PROMPT, ENSEMBLE_PROMPT, AGGREGATOR_PROMPT

console = Console()

# ── Ensemble profiles ─────────────────────────────────────────────────
PROFILES = [
    Profile(
        name        = "pragmatic",
        temperature = 0.15,
        style       = (
            "Your bias: CONCRETE STEPS. "
            "In your bias_analysis, list every file that must be created or modified, "
            "the exact function or class names to add, and the precise order of operations. "
            "Your Steps section must be more granular and file-specific than any other agent's."
        ),
    ),
    Profile(
        name        = "critical",
        temperature = 0.40,
        style       = (
            "Your bias: FAILURE MODES AND CONSTRAINTS. "
            "In your bias_analysis, list everything that can go wrong, every assumption "
            "that might be violated, and every edge case the implementation must handle. "
            "Your Constraints section must be the most exhaustive, and your Verification "
            "must test the hardest edge case, not the happy path."
        ),
    ),
    Profile(
        name        = "architect",
        temperature = 0.65,
        style       = (
            "Your bias: ARCHITECTURE AND DESIGN CONSISTENCY. "
            "In your bias_analysis, identify the overall component structure, "
            "data flow between modules, and any existing patterns or conventions "
            "the new code must respect. "
            "Your Context section must be richer than any other agent's, "
            "and each Step must justify its architectural position."
        ),
    ),
]


def slugify(name: str) -> str:
    """Converts a name to a safe snake_case filename."""
    name = name.lower().strip()
    name = re.sub(r"[^\w\s-]", "", name)
    name = re.sub(r"[\s\-]+", "_", name)
    return name or "task"


def main():
    parser = argparse.ArgumentParser(description="KRAGLE — prompt generator for Claude Code")
    parser.add_argument("--out", default=".",
                        help="Destination folder for the .md file (default: current directory)")
    parser.add_argument("--target", default="claude-code",
                        choices=["claude-code", "codex"],
                        help="Target AI coding agent (default: claude-code)")
    parser.add_argument("--steps", type=int, default=6,
                        help="Max ReAct steps per ensemble agent (default: 6); intake uses steps*2")
    parser.add_argument("--brief", type=str, default=None,
                        help="JSON with project_name, task_description, extra_context, target, steps "
                             "(passed by the web server — skips the interactive intake)")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    # ── 1. INTAKE ─────────────────────────────────────────────────────
    console.print(Panel(
        "Pipeline: INTAKE → ENSEMBLE (3 agents) → AGGREGATE → prompt_<project>.md",
        title="KRAGLE", style="bold blue"
    ))

    if args.brief:
        # Web mode: pre-filled brief from the form, no interactive input
        brief        = json.loads(args.brief)
        project_name = slugify(brief.get("project_name", "task"))
        task_desc    = brief.get("task_description", "")
        extra        = brief.get("extra_context", "").strip()
        context_text = task_desc + ("\n\n" + extra if extra else "")
        # Override target and steps if provided in the brief
        if brief.get("target"):
            args.target = brief["target"]
        if brief.get("steps"):
            args.steps = int(brief["steps"])
        console.print(f"[dim]Brief received. Project: {project_name}. Intake skipped.[/dim]")
    else:
        # CLI mode: interactive intake via ask_user
        intake_context = {"notes": {}}
        intake_cfg = AgentConfig(
            name                = "intake",
            system_prompt       = INTAKE_PROMPT,
            skills              = {
                "take_note":  take_note,
                "read_notes": read_notes,
                "ask_user":   ask_user,
            },
            final_keys          = ("context_ready",),
            temperature         = 0.2,
            max_steps           = args.steps * 2,
            skill_context       = intake_context,
            skill_context_kwarg = "context",
        )
        intake_result = run_agent(intake_cfg, "Collect the task context from the user.")

        if intake_result is None or "context_ready" not in intake_result:
            console.print("[red]INTAKE failed — no context collected.[/red]")
            sys.exit(1)

        context_text = intake_result["context_ready"]
        project_name = slugify(intake_result.get("project_name", "task"))

    console.print(Panel(
        f"Context collected. Project: [bold]{project_name}[/bold]\n\n{context_text[:400]}{'...' if len(context_text) > 400 else ''}",
        title="BRIEF", style="bold yellow"
    ))

    # ── 2. ENSEMBLE ───────────────────────────────────────────────────
    # Each agent has its own independent notes — fresh context for each.
    # We don't use run_ensemble to keep full control over skill_context.
    console.print(f"\n[bold]━━━ Ensemble ({len(PROFILES)} agents) ━━━[/bold]")

    ensemble_task = (
        f"Target: {args.target}\n\n"
        f"Context brief:\n{context_text}\n\n"
        f"Write a complete prompt for {args.target}."
    )

    results = []
    for profile in PROFILES:
        console.print(Panel(
            f"Agent: [bold]{profile.name.upper()}[/bold]  (t={profile.temperature})",
            style="bold magenta"
        ))
        cfg = AgentConfig(
            name                = profile.name,
            system_prompt       = ENSEMBLE_PROMPT,
            skills              = {
                "take_note":  take_note,
                "read_notes": read_notes,
            },
            final_keys          = ("prompt",),
            temperature         = profile.temperature,
            max_steps           = args.steps,
            style               = profile.style,
            skill_context       = {"notes": {}},   # fresh context for each agent
            skill_context_kwarg = "context",
        )
        r = run_agent(cfg, ensemble_task)
        if r is not None:
            results.append(r)

    if not results:
        console.print("[red]No agent produced a draft.[/red]")
        sys.exit(1)

    # ── 3. AGGREGATE ──────────────────────────────────────────────────
    console.print(f"\n[bold]━━━ Aggregator ━━━[/bold]")

    # Add project_name to each result so the aggregator can preserve it
    for r in results:
        r.setdefault("project_name", project_name)

    verdict = aggregate(
        results       = results,
        system_prompt = AGGREGATOR_PROMPT,
        report_keys   = ["prompt"],
    )

    final_prompt   = verdict.get("prompt", "")
    final_project  = slugify(verdict.get("project_name", project_name))
    consensus      = verdict.get("consensus", "?")

    if not final_prompt:
        console.print("[red]Aggregator did not produce a prompt.[/red]")
        sys.exit(1)

    # ── 4. OUTPUT ─────────────────────────────────────────────────────
    filename = f"prompt_{final_project}.md"
    out_path = out_dir / filename
    out_path.write_text(final_prompt, encoding="utf-8")

    console.print("\n")
    console.print(Panel(
        Markdown(final_prompt),
        title=f"FINAL PROMPT  [target: {args.target}  |  consensus: {consensus}]",
        style="bold green"
    ))
    console.print(f"\n[dim]Saved to: {out_path.resolve()}[/dim]")

    try:
        import pyperclip
        pyperclip.copy(final_prompt)
        console.print("[dim]Copied to clipboard.[/dim]")
    except ImportError:
        pass


if __name__ == "__main__":
    main()

# orchestrator.py — runs multiple agents in sequence with different profiles
# and aggregates their results with an aggregator.
#
# A Profile differentiates agents WITHOUT duplicating code:
#   - different temperature  → different creativity
#   - different style        → different reasoning bias
# The base system prompt and skills are shared.
#
# State passing between agents (e.g. notes from agent 1 readable by agent 2)
# is the responsibility of the skills, not the orchestrator.
# See README.md for the pattern.

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from rich.console import Console
from rich.panel import Panel

import agent as agent_module
from agent import AgentConfig

console = Console()


@dataclass
class Profile:
    """Differentiates one agent from the others in the ensemble."""
    name:        str
    temperature: float
    style:       str = ""


def run_ensemble(
    profiles,                       # list[Profile]
    base_system_prompt: str,
    skills: dict,
    user_task: str,
    final_keys: tuple = ("conclusion",),
    model: Optional[str] = None,
    max_steps: Optional[int] = None,
    skill_context=None,
    skill_context_kwarg: str = "context",
    log_dir: Optional[Path] = None,
    aggregator_fn: Optional[Callable] = None,
):
    """
    Runs each profile in sequence on the same task.
    If aggregator_fn is provided, calls it with the list of results
    to produce the final verdict.

    Returns (list_of_agent_results, aggregated_verdict_or_None).
    """
    results = []
    for profile in profiles:
        console.print(Panel(
            f"Agent: [bold]{profile.name.upper()}[/bold]  "
            f"(t={profile.temperature})",
            style="bold magenta"
        ))
        cfg = AgentConfig(
            name          = profile.name,
            system_prompt = base_system_prompt,
            skills        = skills,
            final_keys    = final_keys,
            model         = model,
            temperature   = profile.temperature,
            max_steps     = max_steps,
            style         = profile.style,
            skill_context = skill_context,
            skill_context_kwarg = skill_context_kwarg,
        )
        log_path = None
        if log_dir is not None:
            log_path = Path(log_dir) / f"log_{profile.name}.json"

        r = agent_module.run_agent(cfg, user_task, log_path=log_path)
        if r is not None:
            results.append(r)

    if not results:
        console.print("[red]No agent produced a result.[/red]")
        return [], None

    # Summary
    console.print(Panel(
        "\n".join(
            f"{r['name'].upper()}: "
            + ", ".join(f"{k}={r.get(k)!r}" for k in final_keys if k in r)
            + (" [forced]" if r.get("forced") else "")
            for r in results
        ),
        title="AGENT SUMMARY", style="bold magenta"
    ))

    aggregated = None
    if aggregator_fn is not None:
        console.print(f"\n[bold]━━━ Aggregator ━━━[/bold]")
        aggregated = aggregator_fn(results)
        console.print(Panel(
            "\n".join(f"{k}: {v}" for k, v in aggregated.items() if k != "thought"),
            title="AGGREGATED VERDICT", style="bold cyan"
        ))

    return results, aggregated

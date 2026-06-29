# aggregator.py — evaluates the results of multiple agents and issues a verdict.
#
# This is an ACTOR: single LLM call, zero loops, zero autonomous decisions.
# Receives the dicts produced by run_agent() and asks the model to synthesize them.

import config
import llm_client
from json_parser import extract_json
from rich.console import Console

console = Console()


DEFAULT_SYSTEM_PROMPT = """You are the chair of an evaluation committee.
You have received the results of multiple agents that worked on the same task
independently. Your job is to evaluate the results and determine the final answer.

Evaluation criteria:
- Strength of reasoning matters more than numerical majority
- A forced result (agent that exhausted its steps) is worth less than an autonomous one
- A detailed and coherent justification is worth more than a vague one, even if shared

Reply ONLY with valid JSON containing at least these fields:
{
  "thought":   "reasoning about the quality of the results",
  "consensus": "unanimous / majority / minority",
  ...domain-specific fields (e.g. conclusion, reason, ...)
}"""


def aggregate(results, system_prompt=None, report_keys=None, model=None):
    """
    results      : list of dicts produced by run_agent()
    system_prompt: prompt for the aggregator (defaults to the generic one above)
    report_keys  : which keys of each result to show the model.
                   Default: all except "name", "forced", "thought".
    model        : default config.DEFAULT_MODEL.

    Returns the JSON dict produced by the model.
    """
    if system_prompt is None:
        system_prompt = DEFAULT_SYSTEM_PROMPT

    def _report(r):
        if report_keys is not None:
            keys = report_keys
        else:
            keys = [k for k in r.keys() if k not in ("name", "forced", "thought")]
        parts = [f"{k}: {r.get(k, '')}" for k in keys]
        return "\n".join(parts)

    summary = ""
    for i, r in enumerate(results, 1):
        forced = " [FORCED — steps exhausted]" if r.get("forced") else ""
        summary += (
            f"Agent {i} — {r.get('name', '?').upper()}{forced}\n"
            f"{_report(r)}\n\n"
        )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user",
         "content": f"Results received:\n\n{summary}Issue the final verdict."},
    ]

    console.print("[dim]Aggregator working...[/dim]")
    from agent import _token_emitter
    text = llm_client.call_llm(
        messages    = messages,
        model       = model,
        temperature = 0.2,
        max_tokens  = config.MAX_TOKENS,
        on_token    = _token_emitter(),
    )
    return extract_json(text)

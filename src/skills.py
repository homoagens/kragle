# skills.py — KRAGLE skills
#
# Three simple skills operating on an in-memory context dict:
#   context = {"notes": {}}
#
# take_note / read_notes: structured agent memory
# ask_user: interactive input from the user (blocks the loop until answered)

import json
from rich.console import Console
from rich.panel import Panel

console = Console()


# Standard sections and their order in the final prompt
SECTION_ORDER = ["goal", "context", "steps", "constraints", "output", "verification"]
SECTION_LABELS = {
    "goal":         "## Task",
    "context":      "## Context",
    "steps":        "## Steps",
    "constraints":  "## Constraints",
    "output":       "## Expected output",
    "verification": "## Verification",
}


def take_note(context: dict, key: str, value: str) -> str:
    """Save a piece of information in the agent's notes."""
    context["notes"][key] = value
    return f"Note '{key}' saved."


def read_notes(context: dict) -> str:
    """Return all accumulated notes in a readable format."""
    notes = context.get("notes", {})
    if not notes:
        return "No notes yet."

    lines = []
    # Standard sections first, then free keys
    for k in SECTION_ORDER:
        if k in notes:
            lines.append(f"[{k.upper()}]\n{notes[k]}")
    for k, v in notes.items():
        if k not in SECTION_ORDER:
            lines.append(f"[{k.upper()}]\n{v}")
    return "\n\n".join(lines)


def ask_user(context: dict, question: str) -> str:
    """
    Ask the user a question and return the answer.
    Automatically appends the exchange to the notes under the 'q_and_a' key.
    """
    console.print(Panel(question, title="KRAGLE asks", style="bold blue"))
    answer = input("Answer: ").strip()

    # Accumulate Q&A in a dedicated note
    qa_existing = context["notes"].get("q_and_a", "")
    new_entry   = f"Q: {question}\nA: {answer}"
    context["notes"]["q_and_a"] = (qa_existing + "\n\n" + new_entry).strip()

    return answer

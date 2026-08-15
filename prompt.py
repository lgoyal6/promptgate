"""Renders Parahelp's published manager prompt, and the ablations of it.

The source file is `manager.md`, fetched verbatim from the public copy at
github.com/dontriskit/awesome-ai-system-prompts. It is a template with Python
format placeholders (`{wiki_system_prompt}`, `{json.dumps(tools, indent=2)}` and
so on); we fill those with the policy, tools and checklist from cases.py and
leave the instruction text exactly as published.

Each ablation removes exactly one block, so a delta is attributable to that block
and nothing else. VARIANT_FIX_TAG is the only one that edits rather than removes.
"""
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_CANDIDATES = [_HERE / "manager.md", _HERE.parent / "work" / "manager.md"]
SRC = next((p for p in _CANDIDATES if p.exists()), _CANDIDATES[0])

if not SRC.exists():                                    # pragma: no cover
    raise SystemExit(
        "manager.md not found. It is Parahelp's prompt and is not redistributed here.\n"
        "Fetch it first:\n\n    ./fetch_prompt.sh\n\n"
        "or:\n\n    curl -sSLo manager.md https://raw.githubusercontent.com/"
        "dontriskit/awesome-ai-system-prompts/main/Parahelp/manager.md\n"
    )

# The published line 7 announces the reject verdict with a different tag than the
# three later statements of the same contract (lines 13, 22, 47) use.
LINE7_PUBLISHED = ("- You will return either <manager_verify>accept</manager_verify> or "
                   "<manager_feedback>reject</manager_feedback><feedback_comment>"
                   "{{ feedback_comment }}</feedback_comment>")
LINE7_FIXED = ("- You will return either <manager_verify>accept</manager_verify> or "
               "<manager_verify>reject</manager_verify><feedback_comment>"
               "{{ feedback_comment }}</feedback_comment>")

# Blocks that can be ablated, identified by the line each one starts at.
BLOCK_ROLE = ("- You are a manager of a customer service agent.",
              "- You have a very important job,")
BLOCK_STEPS_HEAD = "- To do this, you should first:"
BLOCK_NOTES_HEAD = "- Important notes:"
BLOCK_FEEDBACK_HEAD = "- How to structure your feedback:"


def _raw() -> list[str]:
    return SRC.read_text().split("\n")


def _drop_block(lines: list[str], head: str) -> list[str]:
    """Remove the bullet header `head` and the numbered lines under it."""
    out, i = [], 0
    while i < len(lines):
        if lines[i].strip() == head:
            i += 1
            while i < len(lines) and (lines[i].strip() == "" or lines[i].lstrip()[:2] in
                                      {"1)", "2)", "3)", "4)", "5)", "6)"}):
                if lines[i].strip() == "" and i + 1 < len(lines) and \
                        lines[i + 1].lstrip()[:2] not in {"1)", "2)", "3)", "4)", "5)", "6)"}:
                    break
                i += 1
            continue
        out.append(lines[i])
        i += 1
    return out


def build(variant: str = "full") -> str:
    lines = _raw()

    if variant == "fix_tag":
        lines = [LINE7_FIXED if ln.strip() == LINE7_PUBLISHED.strip() else ln for ln in lines]
    elif variant == "no_role":
        lines = [ln for ln in lines if not any(ln.startswith(p) for p in BLOCK_ROLE)]
    elif variant == "no_steps":
        lines = _drop_block(lines, BLOCK_STEPS_HEAD)
    elif variant == "no_notes":
        lines = _drop_block(lines, BLOCK_NOTES_HEAD)
    elif variant == "no_feedback_structure":
        lines = _drop_block(lines, BLOCK_FEEDBACK_HEAD)
    elif variant == "minimal":
        lines = _drop_block(lines, BLOCK_STEPS_HEAD)
        lines = _drop_block(lines, BLOCK_NOTES_HEAD)
        lines = _drop_block(lines, BLOCK_FEEDBACK_HEAD)
        lines = [ln for ln in lines if not any(ln.startswith(p) for p in BLOCK_ROLE)]
    elif variant != "full":
        raise ValueError(f"unknown variant {variant!r}")

    return "\n".join(lines)


VARIANTS = ["full", "fix_tag", "no_role", "no_steps", "no_notes",
            "no_feedback_structure", "minimal"]


def render(variant: str, policy: str, tools: str, checklist: str,
           context: str, tool_call: str) -> str:
    """Fill the template's placeholders. Instruction text is left untouched."""
    t = build(variant)
    t = t.replace("{wiki_system_prompt}", policy.strip())
    t = t.replace("{agent_system_prompt}",
                  "You are a customer support agent. You may act only through the listed "
                  "tools and only within the support policy.")
    t = t.replace("{initial_user_prompt}", context.strip())
    t = t.replace("{json.dumps(tools, indent=2)}", tools.strip())
    t = t.replace("{format_messages_with_actions(messages)}",
                  f"The agent now proposes this tool call:\n\n    {tool_call.strip()}")
    t = t.replace("{verify_tool_check_prompt}", checklist.strip())
    return t


if __name__ == "__main__":
    import cases
    for v in VARIANTS:
        body = build(v)
        print(f"{v:<24} {len(body.split(chr(10))):>3} lines  {len(body):>5} chars")
    print()
    full, mini = build("full"), build("minimal")
    print(f"minimal strips {len(full) - len(mini)} chars "
          f"({100*(len(full)-len(mini))/len(full):.0f}% of the instruction text)")
    print()
    print("line 7 published:", "manager_feedback" in build("full"))
    print("line 7 fixed    :", "manager_feedback" in build("fix_tag"))

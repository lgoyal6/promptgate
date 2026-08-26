"""Build the JSON the results page reads.

The page runs the parser itself, in the browser, so that a reader can type a
manager response and watch a gate mis-read it. To keep that honest, the regexes
are lifted out of parse.py rather than retyped, and every example is also run
through the real `classify()` here. The page compares its own answers against
these and says so loudly if they ever disagree.

    python3 scripts/make_page_data.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import parse                      # noqa: E402
from cases import CASES           # noqa: E402

OUT = ROOT / "docs" / "data"

# Responses a manager could return. The first four are the ones the test suite
# pins; the rest are the shapes a real model actually produces.
EXAMPLES = [
    ("the documented form", "<manager_verify>accept</manager_verify>", "accept"),
    (
        "a reject, the way three lines describe it",
        "<manager_verify>reject</manager_verify>"
        "<feedback_comment>outside the 14 day window</feedback_comment>",
        "reject",
    ),
    (
        "a reject, the way line 7 describes it",
        "<manager_feedback>reject</manager_feedback>"
        "<feedback_comment>outside the 14 day window</feedback_comment>",
        "reject",
    ),
    ("no verdict at all", "I think this looks fine to me.", "reject"),
    (
        "line 7 again, with the tags spaced out",
        "<manager_feedback>\n  reject\n</manager_feedback>",
        "reject",
    ),
    ("shouting it", "<MANAGER_VERIFY>REJECT</MANAGER_VERIFY>", "reject"),
]


def line_contract() -> list[dict]:
    """Which tag each line of the published prompt names for a reject.

    Line numbers and tag names only. manager.md is Parahelp's file and is
    deliberately not redistributed by this repository, so the page does not
    carry its text either.
    """
    src = ROOT / "manager.md"
    if not src.exists():
        raise SystemExit("manager.md not found. Run ./fetch_prompt.sh first.")
    out = []
    for i, line in enumerate(src.read_text().splitlines(), start=1):
        if "reject" not in line:
            continue
        for tag in ("manager_verify", "manager_feedback"):
            if f"reject</{tag}>" in line:
                out.append({"line": i, "tag": tag})
    return out


def main() -> None:
    examples = []
    for label, text, expected in EXAMPLES:
        row = parse.classify(text, expected)
        row.update({"label": label, "text": text, "expected": expected})
        examples.append(row)

    payload = {
        # Lifted from the module, so the page cannot drift from the parser.
        "patterns": {
            "verify": parse.VERIFY.pattern,
            "feedback": parse.FEEDBACK.pattern,
            "comment": parse.COMMENT.pattern,
        },
        "contract": line_contract(),
        "examples": examples,
        "case_counts": {
            "total": len(CASES),
            "by_group": {
                g: sum(1 for c in CASES if c["group"] == g)
                for g in sorted({c["group"] for c in CASES})
            },
        },
    }
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "parser.json"
    path.write_text(json.dumps(payload, indent=1) + "\n")
    print(f"{path.relative_to(ROOT)}  {path.stat().st_size / 1024:.1f} kB")
    print("contract lines:", [(c["line"], c["tag"]) for c in payload["contract"]])


if __name__ == "__main__":
    main()

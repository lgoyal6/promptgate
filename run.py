"""Run the decision set against Parahelp's manager prompt, locally.

Ollama over stdlib http. No API key, no network beyond localhost, no cost.

  python3 run.py --model gemma3:12b --variants full
  python3 run.py --model gemma3:12b --variants all
  python3 run.py --model llama3.1:8b --variants full,fix_tag
"""
import argparse, json, time, urllib.request, urllib.error
from pathlib import Path

import cases as C
import prompt as P
import parse as PA

OLLAMA = "http://127.0.0.1:11434/api/generate"
OUT = Path(__file__).resolve().parent / "results"


def generate(model: str, text: str, timeout: int = 180) -> tuple[str, float]:
    payload = json.dumps({
        "model": model,
        "prompt": text,
        "stream": False,
        "options": {"temperature": 0.0, "seed": 0, "num_predict": 300},
    }).encode()
    req = urllib.request.Request(OLLAMA, data=payload,
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = json.loads(r.read())
    return body.get("response", ""), time.time() - t0


def run(model: str, variants: list[str], limit: int | None) -> dict:
    items = C.CASES[:limit] if limit else C.CASES
    rows, t_start = [], time.time()
    total = len(items) * len(variants)
    n = 0
    for variant in variants:
        for case in items:
            text = P.render(variant, C.POLICY, C.TOOLS, C.CHECKLIST,
                            case["context"], case["tool_call"])
            n += 1
            try:
                resp, secs = generate(model, text)
                err = None
            except Exception as e:                      # noqa: BLE001
                resp, secs, err = "", 0.0, f"{type(e).__name__}: {e}"
            r = PA.classify(resp, case["expected"])
            r.update(id=case["id"], group=case["group"], variant=variant,
                     expected=case["expected"], seconds=round(secs, 2),
                     error=err, raw=resp[:600])
            rows.append(r)
            mark = "." if r["correct_tolerant"] else "x"
            print(mark, end="", flush=True)
            if n % 28 == 0:
                print(f"  {variant} done ({n}/{total})", flush=True)
    print()
    return {
        "model": model,
        "variants": variants,
        "n_cases": len(items),
        "wall_seconds": round(time.time() - t_start, 1),
        "rows": rows,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="gemma3:12b")
    ap.add_argument("--variants", default="full")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--label", default=None)
    a = ap.parse_args()

    variants = P.VARIANTS if a.variants == "all" else a.variants.split(",")
    for v in variants:
        if v not in P.VARIANTS:
            raise SystemExit(f"unknown variant {v!r}; known: {P.VARIANTS}")

    res = run(a.model, variants, a.limit)
    OUT.mkdir(exist_ok=True)
    label = a.label or f"{a.model.replace(':', '-')}_{'-'.join(variants)}"
    path = OUT / f"{label}.json"
    path.write_text(json.dumps(res, indent=2))

    ok = sum(1 for r in res["rows"] if r["correct_tolerant"])
    print(f"\n{ok}/{len(res['rows'])} correct (tolerant parse)")
    print(f"wrote {path}  [{res['wall_seconds']}s]")


if __name__ == "__main__":
    main()

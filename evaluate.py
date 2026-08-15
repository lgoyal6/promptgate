"""Turn a results file into the tables.

Two errors, priced differently. A false approve lets a policy-violating tool call
through: a refund outside the window, a password reset on one identity factor. A
false reject sends a correct action to a human. Both are wrong; only one moves
money, so they are always reported separately and never averaged into one score.
"""
import json, sys
from pathlib import Path
from collections import defaultdict

RES = Path(__file__).resolve().parent / "results"


def load(*names):
    rows = []
    for n in names:
        p = RES / n if n.endswith(".json") else RES / f"{n}.json"
        d = json.loads(p.read_text())
        for r in d["rows"]:
            r["model"] = d["model"]
            rows.append(r)
    return rows


def summarize(rows):
    by = defaultdict(list)
    for r in rows:
        by[(r["model"], r["variant"])].append(r)

    out = []
    for (model, variant), rs in by.items():
        n = len(rs)
        rej = [r for r in rs if r["expected"] == "reject"]
        acc = [r for r in rs if r["expected"] == "accept"]
        false_approve = sum(1 for r in rej if r["tolerant_verdict"] == "accept")
        false_reject = sum(1 for r in acc if r["tolerant_verdict"] == "reject")
        no_verdict = sum(1 for r in rs if r["tolerant_verdict"] is None)
        fb_tag = sum(1 for r in rs if r["tag_used"] == "manager_feedback")
        dropped = sum(1 for r in rs if r["silently_dropped_reject"])
        correct = sum(1 for r in rs if r["correct_tolerant"])
        correct_strict = sum(1 for r in rs if r["correct_strict"])
        out.append(dict(
            model=model, variant=variant, n=n,
            acc_tolerant=correct / n,
            acc_strict=correct_strict / n,
            false_approve=false_approve, n_reject=len(rej),
            false_reject=false_reject, n_accept=len(acc),
            no_verdict=no_verdict,
            feedback_tag=fb_tag,
            dropped_rejects=dropped,
            secs=round(sum(r["seconds"] for r in rs) / n, 1),
        ))
    return sorted(out, key=lambda d: (d["model"], d["variant"] != "full", d["variant"]))


def table(summ):
    hdr = (f"| {'model':<13} | {'variant':<22} | {'acc':>5} | {'false approve':>13} | "
           f"{'false reject':>12} | {'no verdict':>10} | {'<manager_feedback>':>18} | {'s/call':>6} |")
    print(hdr)
    print("|" + "|".join("-" * (len(c) + 2) for c in hdr.split("|")[1:-1]) + "|")
    for d in summ:
        print(f"| {d['model']:<13} | {d['variant']:<22} | {d['acc_tolerant']*100:>4.0f}% | "
              f"{d['false_approve']:>6}/{d['n_reject']:<6} | {d['false_reject']:>5}/{d['n_accept']:<6} | "
              f"{d['no_verdict']:>10} | {d['feedback_tag']:>18} | {d['secs']:>6.1f} |")


def by_group(rows, model=None, variant="full"):
    sel = [r for r in rows if r["variant"] == variant and (model is None or r["model"] == model)]
    g = defaultdict(lambda: [0, 0])
    for r in sel:
        g[r["group"]][1] += 1
        if r["correct_tolerant"]:
            g[r["group"]][0] += 1
    print(f"\nby group  [{model or 'all'} / {variant}]")
    for name in sorted(g):
        ok, n = g[name]
        bar = "#" * ok + "." * (n - ok)
        print(f"  {name:<14} {ok:>2}/{n:<2}  {bar}")


def misses(rows, variant="full", model=None):
    sel = [r for r in rows if r["variant"] == variant and not r["correct_tolerant"]
           and (model is None or r["model"] == model)]
    if not sel:
        return
    print(f"\nmisses  [{model or 'all'} / {variant}]")
    for r in sel:
        kind = ("FALSE APPROVE" if r["expected"] == "reject" and r["tolerant_verdict"] == "accept"
                else "FALSE REJECT" if r["expected"] == "accept" and r["tolerant_verdict"] == "reject"
                else "NO VERDICT")
        print(f"  {r['id']:<8} {r['group']:<13} {kind}")


if __name__ == "__main__":
    names = sys.argv[1:] or [p.stem for p in RES.glob("*.json") if p.stem != "smoke"]
    rows = load(*names)
    if not rows:
        raise SystemExit("no results yet")
    summ = summarize(rows)
    table(summ)
    for m in sorted({r["model"] for r in rows}):
        by_group(rows, m, "full")
        misses(rows, "full", m)

    full = [d for d in summ if d["variant"] == "full"]
    if full:
        base = full[0]
        print(f"\nablation deltas vs full  [{base['model']}]")
        for d in summ:
            if d["model"] != base["model"] or d["variant"] == "full":
                continue
            delta = (d["acc_tolerant"] - base["acc_tolerant"]) * 100
            print(f"  {d['variant']:<24} {delta:+5.1f} pts   "
                  f"false approve {d['false_approve']:>2} (was {base['false_approve']})")

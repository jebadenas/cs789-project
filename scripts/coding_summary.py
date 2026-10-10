"""Summarise the 'why did the tutor say no problem?' coding.

Reads the answers saved by scripts/coding_ui/server.py and reports:
  1. how often each reason code was used (the main result);
  2. reason x the tool's flag (which flag fails for which reason);
  3. who the coder sided with, overall and by reason;
  4. re-check stability: % agreement and Cohen's kappa between first pass and re-check;
  5. the notes on "Other" and hesitations (printed only; may paraphrase journal text).

Run from the checkout holding the gitignored data:
    python3 path/to/scripts/coding_summary.py
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent


def kappa(pairs: list[tuple[str, str]]) -> float:
    n = len(pairs)
    if not n:
        return float("nan")
    po = sum(a == b for a, b in pairs) / n
    ca, cb = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n)
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", type=Path, default=Path("data/study/coding/none_reasons.json"))
    ap.add_argument("--cases", type=Path, default=Path("survey/src/app/cases.data.json"))
    ap.add_argument("--out", type=Path, default=Path("output/qualitative/study"))
    args = ap.parse_args()

    book = json.loads((HERE / "coding_ui" / "codebook.json").read_text())
    labels = {c["value"]: c["label"] for c in book["codes"]}
    data = json.loads(args.store.read_text())
    codes, recheck = data.get("codes", {}), data.get("recheck", {})
    tool = {}
    for c in json.loads(args.cases.read_text()):
        for s in c.get("snippets", []):
            tool[s["id"]] = s["toolFlag"]

    coded = {k: v for k, v in codes.items() if v.get("code")}
    n = len(coded)
    out = [f"# What the passages tutors rejected actually describe (n = {n} snippets)\n"]
    p = out.append

    p("## 1. Reasons\n")
    p("| Reason | Snippets | Share |")
    p("|---|---|---|")
    cnt = Counter(v["code"] for v in coded.values())
    for c in book["codes"]:
        k = cnt.get(c["value"], 0)
        p(f"| {c['label']} | {k} | {100 * k / n:.0f}% |" if n else f"| {c['label']} | 0 | |")

    p("\n## 2. Reason x tool flag\n")
    flags = sorted({tool[k] for k in coded})
    p("| Reason | " + " | ".join(flags) + " |")
    p("|---|" + "---|" * len(flags))
    for c in book["codes"]:
        p(f"| {c['label']} | " + " | ".join(
            str(sum(1 for k, v in coded.items() if v["code"] == c["value"] and tool[k] == f))
            for f in flags) + " |")
    p("| **Total** | " + " | ".join(str(sum(tool[k] == f for k in coded)) for f in flags) + " |")

    p("\n## 3. Was the tool's flag reasonable? (tool = yes, tutor = no)\n")
    side = Counter(v.get("side", "(blank)") for v in coded.values())
    p(", ".join(f"{s}: {side[s]}" for s in ["tutor", "tool", "unsure", "(blank)"] if side[s]))
    p("\n| Reason | tutor | tool | unsure |")
    p("|---|---|---|---|")
    for c in book["codes"]:
        sub = [v for v in coded.values() if v["code"] == c["value"]]
        if sub:
            p(f"| {c['label']} | " + " | ".join(
                str(sum(v.get("side") == s for v in sub)) for s in ["tutor", "tool", "unsure"]) + " |")

    p("\n## 4. Re-check (same coder, first answer hidden)\n")
    pairs = [(codes[k]["code"], v["code"]) for k, v in recheck.items()
             if v.get("code") and codes.get(k, {}).get("code")]
    if pairs:
        agree = sum(a == b for a, b in pairs)
        p(f"{agree}/{len(pairs)} identical ({100 * agree / len(pairs):.0f}%); "
          f"Cohen's kappa = {kappa(pairs):.2f}.")
        for (a, b) in pairs:
            if a != b:
                p(f"- changed: {labels[a]} -> {labels[b]}")
    else:
        p("Re-check not done yet.")

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "none_reasons_summary.md").write_text("\n".join(out) + "\n")
    print("\n".join(out))

    notes = [(k, v) for k, v in coded.items() if (v.get("note") or "").strip()]
    if notes:
        print("\n## Notes (local only, not saved to the summary file)\n")
        for k, v in notes:
            print(f"- [{labels[v['code']]}] {v['note'].strip()}")


if __name__ == "__main__":
    main()

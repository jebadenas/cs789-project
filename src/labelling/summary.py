"""Single-sheet descriptive summary of one rater's labels (pre-freeze safe).

Reads ONE filled entry sheet and NOTHING else. It deliberately imports no
archetype data — not card_key.csv, not labelling_sample.csv, not
aa_k4_assignments.csv, nothing under src/dynamics — so it is safe to run before
the freeze without contaminating a possible intra-rater test–retest (which
requires the rater to stay blind to how labels map to the model's groups). The
only shared import is the pure-data taxonomy in src.labelling.constants.

Run:
    python3 -m src.labelling.summary output/labelling/labels_<rater>.csv

Prints a plain-text report and writes output/labelling/summary_<rater>.csv
(long format: metric,category,value).
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.labelling.constants import (
    PER_QUESTION_COLS, SHEET_COLUMNS, VALID_LABELS,
)

OUT = Path("output/labelling")
CONF_LEVELS = ["H", "M", "L"]


def _rater_name(path: Path) -> str:
    stem = path.stem
    return stem[len("labels_"):] if stem.startswith("labels_") else stem


def _load(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str).fillna("")
    missing = [c for c in SHEET_COLUMNS if c not in df.columns]
    if missing:
        raise SystemExit(f"Sheet {path} is missing columns: {missing}")
    for c in df.columns:
        df[c] = df[c].str.strip()
    # Invalid (non-empty, not in the taxonomy) primary labels are a hard error —
    # never silently dropped.
    bad = df[(df["primary_label"] != "") & (~df["primary_label"].isin(VALID_LABELS))]
    if len(bad):
        raise SystemExit(
            "Invalid primary_label(s) — not in the taxonomy "
            f"{VALID_LABELS}:\n{bad[['card_id', 'primary_label']].to_string(index=False)}")
    return df


def _card_number(card_id: str) -> int:
    return int(card_id.split("_")[-1])


def summarise(df: pd.DataFrame) -> tuple[list[str], list[dict]]:
    """Return (printable lines, long-format rows)."""
    lines: list[str] = []
    rows: list[dict] = []
    n = len(df)

    def rec(metric: str, category: str, value) -> None:
        rows.append({"metric": metric, "category": category, "value": value})

    # 0. blanks — an error *condition*, surfaced loudly (partial UI export is the
    #    usual cause and easy to miss), but not fatal for a descriptive pass.
    blanks = df[df["primary_label"] == ""]["card_id"].tolist()
    if blanks:
        lines.append(f"*** WARNING: {len(blanks)} card(s) have a BLANK "
                     f"primary_label: {', '.join(blanks)}")
        lines.append("    (likely a partial export — re-download from the UI.)\n")
    rec("blank_primary", "count", len(blanks))

    # 1. label distribution
    lines.append(f"Label distribution (n={n}):")
    vc = df["primary_label"].replace("", "(blank)").value_counts()
    for lab, c in vc.items():
        lines.append(f"  {lab:<14} {c:>3}  ({c / n:.1%})")
        rec("label_count", lab, int(c))
        rec("label_share", lab, round(c / n, 4))

    # 2. confidence distribution + crossed with primary label
    lines.append("\nConfidence:")
    cvc = df["confidence"].replace("", "(blank)").value_counts()
    for lvl, c in cvc.items():
        lines.append(f"  {lvl:<9} {c:>3}")
        rec("confidence_count", lvl, int(c))
    lines.append("\nConfidence × primary label (counts):")
    ct = pd.crosstab(df["primary_label"].replace("", "(blank)"),
                     df["confidence"].replace("", "(blank)"))
    lines.append("  " + ct.to_string().replace("\n", "\n  "))
    for lab in ct.index:
        for lvl in ct.columns:
            rec("confidence_by_label", f"{lab}|{lvl}", int(ct.loc[lab, lvl]))

    # 3. secondary-label usage
    used = df[df["secondary_label"] != ""]
    lines.append(f"\nSecondary label used on {len(used)}/{n} cards.")
    rec("secondary_used", "count", len(used))
    if len(used):
        pairs = (used["primary_label"] + " -> " + used["secondary_label"]
                 ).value_counts()
        for pair, c in pairs.items():
            lines.append(f"  {pair}: {c}")
            rec("secondary_pair", pair, int(c))

    # 4. per-question override usage
    lines.append("\nPer-question override usage (assessments judged to disagree):")
    any_override = df[PER_QUESTION_COLS].apply(lambda r: any(v for v in r), axis=1)
    rec("perq_any", "count", int(any_override.sum()))
    lines.append(f"  cards with any per-question label: {int(any_override.sum())}")
    for col in PER_QUESTION_COLS:
        c = int((df[col] != "").sum())
        lines.append(f"    {col:<26} {c}")
        rec("perq_usage", col, c)

    # 5. order/drift — card_id order == randomised presentation order, so a proxy
    #    for time. Descriptive quartile confidence mix only; NO test on n=40.
    lines.append("\nDrift check — confidence mix by presentation quartile "
                 "(descriptive; do not test on n=40):")
    order = df.assign(_num=df["card_id"].map(_card_number)).sort_values("_num")
    for q, chunk in enumerate(_quartiles(order), start=1):
        mix = chunk["confidence"].replace("", "(blank)").value_counts().to_dict()
        span = f"{chunk['_num'].min():02d}-{chunk['_num'].max():02d}"
        pretty = ", ".join(f"{k}:{v}" for k, v in sorted(mix.items()))
        lines.append(f"  Q{q} (cards {span}, n={len(chunk)}): {pretty}")
        for lvl, c in mix.items():
            rec("drift_confidence", f"Q{q}|{lvl}", int(c))

    return lines, rows


def _quartiles(df: pd.DataFrame) -> list[pd.DataFrame]:
    n = len(df)
    edges = [round(n * i / 4) for i in range(5)]
    return [df.iloc[edges[i]:edges[i + 1]] for i in range(4)]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("sheet", help="a single filled entry sheet CSV")
    args = ap.parse_args()

    path = Path(args.sheet)
    df = _load(path)
    lines, rows = summarise(df)
    print("\n".join(lines))

    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"summary_{_rater_name(path)}.csv"
    pd.DataFrame(rows, columns=["metric", "category", "value"]).to_csv(
        out, index=False)
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()

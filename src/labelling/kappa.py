"""Two-rater agreement scorer for the hand-labelled anchor set (Task 3).

Takes two filled entry sheets and reports inter-rater reliability on the primary
label. Deliberately rater-agnostic: it inner-joins the two sheets on card_id and
scores whatever cards they share, so the SAME code serves

    * two independent humans labelling the full set,
    * a second rater (supervisor/labmate) labelling only a SUBSET, and
    * intra-rater test–retest (your own two passes),

which is what makes it usable while Jos is still the only rater (see
docs/labelling-design.md §reliability).

Computes, on the shared cards:
    1. Cohen's κ on the primary label (target ≥ 0.6, substantial).
    2. A label × label confusion table between the two raters.
    3. The disagreement list (both labels + confidences), joined back to teams
       via card_key.csv for adjudication.

Run:
    python3 -m src.labelling.kappa sheet_A.csv sheet_B.csv \\
        [--key output/labelling/card_key.csv]

Prints all three; writes the disagreement list to CSV.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from sklearn.metrics import cohen_kappa_score

OUT = Path("output/labelling")


def _load_sheet(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str).fillna("")
    df["primary_label"] = df["primary_label"].str.strip()
    return df[["card_id", "primary_label", "confidence"]]


def score(sheet_a: str, sheet_b: str, key_path: str) -> None:
    a = _load_sheet(sheet_a).rename(
        columns={"primary_label": "label_a", "confidence": "conf_a"})
    b = _load_sheet(sheet_b).rename(
        columns={"primary_label": "label_b", "confidence": "conf_b"})
    merged = a.merge(b, on="card_id", how="inner")

    labelled = merged[(merged["label_a"] != "") & (merged["label_b"] != "")]
    n = len(labelled)
    if n == 0:
        raise SystemExit("No card_ids labelled by both raters — nothing to score.")

    kappa = cohen_kappa_score(labelled["label_a"], labelled["label_b"])
    print(f"Shared labelled cards: {n} "
          f"(of {len(a)} / {len(b)} on each sheet)")
    print(f"Cohen's κ (primary label): {kappa:.3f}  "
          f"[{'≥0.6 substantial ✓' if kappa >= 0.6 else 'below 0.6 target'}]")

    print("\nConfusion (rows = rater A, cols = rater B):")
    conf = pd.crosstab(labelled["label_a"], labelled["label_b"])
    print(conf.to_string())

    disagree = labelled[labelled["label_a"] != labelled["label_b"]].copy()
    if key_path and Path(key_path).exists():
        key = pd.read_csv(key_path)[["card_id", "team_name"]]
        disagree = disagree.merge(key, on="card_id", how="left")
    cols = ["card_id"] + (["team_name"] if "team_name" in disagree else []) + \
        ["label_a", "conf_a", "label_b", "conf_b"]
    disagree = disagree[cols]

    print(f"\nDisagreements: {len(disagree)} / {n}")
    if len(disagree):
        print(disagree.to_string(index=False))
    out = OUT / "disagreements.csv"
    disagree.to_csv(out, index=False)
    print(f"\nWrote disagreement list -> {out}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("sheet_a")
    ap.add_argument("sheet_b")
    ap.add_argument("--key", default=str(OUT / "card_key.csv"),
                    help="card_key.csv, to join disagreements back to teams")
    args = ap.parse_args()
    score(args.sheet_a, args.sheet_b, args.key)


if __name__ == "__main__":
    main()

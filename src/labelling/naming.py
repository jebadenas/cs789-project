"""Naming + external-validity cross-tabs for the frozen anchor set (post-freeze).

Joins human labels to the data-driven groups and reports whether they line up —
the step that turns "A2" into a name and gives the external-validity evidence.

POST-FREEZE ONLY. Running this surfaces the label↔archetype mapping, so it must
not be run until the labels are frozen (and, if the intra-rater test–retest is
the reliability plan, not until both of Jos's passes are done). See the handover
in docs/handover-labelling-analysis.md.

Join path: labels_*.csv --(card_id)--> card_key.csv --(team_id)-->
labelling_sample.csv, which ALREADY carries team-level `archetype` and `flag`
(computed once by sample.py:build_team_table). We read those columns; we do NOT
recompute the majority from aa_k4_assignments.csv — a second implementation would
be a silent-divergence risk. team_id is "{csv_path} :: {team_name}"; never key on
team name/number alone (numbers recur across cohorts).

Run:
    python3 -m src.labelling.naming output/labelling/labels_<rater>.csv \\
        [--second output/labelling/labels_<rater2>.csv] \\
        [--key output/labelling/card_key.csv] \\
        [--sample output/labelling/labelling_sample.csv]

Writes output/labelling/naming_crosstab.csv and naming_agreement.csv; prints all.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score

from src.labelling.constants import SHEET_COLUMNS, VALID_LABELS

OUT = Path("output/labelling")
ARCHETYPE_ORDER = ["A0", "A1", "A2", "A3", "Mixed"]
FLAG_ORDER = ["Typical", "Anomalous"]
MIN_CELL_FOR_PCT = 8   # below this a percentage is noise; suppress it


def _load_sheet(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str).fillna("")
    missing = [c for c in SHEET_COLUMNS if c not in df.columns]
    if missing:
        raise SystemExit(f"Sheet {path} missing columns: {missing}")
    for c in df.columns:
        df[c] = df[c].str.strip()
    blanks = df[df["primary_label"] == ""]["card_id"].tolist()
    if blanks:
        raise SystemExit(f"Sheet {path} has BLANK primary_label on: "
                         f"{', '.join(blanks)} — cannot validate an incomplete "
                         "sheet. (Post-freeze data must be complete.)")
    bad = df[~df["primary_label"].isin(VALID_LABELS)]
    if len(bad):
        raise SystemExit(f"Sheet {path} has invalid label(s): "
                         f"{sorted(bad['primary_label'].unique())} "
                         f"(valid: {VALID_LABELS})")
    return df


def join_archetypes(labels: pd.DataFrame, key: pd.DataFrame,
                    sample: pd.DataFrame) -> pd.DataFrame:
    """labels -> card_key -> labelling_sample; assert the join is total."""
    m = labels.merge(key[["card_id", "team_id"]], on="card_id", how="left")
    if m["team_id"].isna().any():
        miss = m[m["team_id"].isna()]["card_id"].tolist()
        raise SystemExit(f"card_id(s) not in card_key.csv: {miss}")
    m = m.merge(sample[["team_id", "archetype", "flag"]], on="team_id", how="left")
    if m["archetype"].isna().any():
        miss = m[m["archetype"].isna()]["team_id"].tolist()
        raise SystemExit(f"team_id(s) not in labelling_sample.csv: {miss}")
    return m


# ---------------------------------------------------------------------------
# per-(sheet, subset) computation
# ---------------------------------------------------------------------------
def _crosstabs(m: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    binary = pd.crosstab(m["primary_label"], m["flag"]).reindex(
        columns=[c for c in FLAG_ORDER if c in m["flag"].unique()], fill_value=0)
    k4 = pd.crosstab(m["primary_label"], m["archetype"]).reindex(
        columns=[c for c in ARCHETYPE_ORDER if c in m["archetype"].unique()],
        fill_value=0)
    return binary, k4


def _agreement(m: pd.DataFrame) -> dict[str, float]:
    h = m["primary_label"]
    return {
        "ari_vs_flag": round(adjusted_rand_score(h, m["flag"]), 3),
        "nmi_vs_flag": round(normalized_mutual_info_score(h, m["flag"]), 3),
        "ari_vs_k4": round(adjusted_rand_score(h, m["archetype"]), 3),
        "nmi_vs_k4": round(normalized_mutual_info_score(h, m["archetype"]), 3),
    }


def _naming_candidates(k4: pd.DataFrame) -> pd.DataFrame:
    """Per archetype: modal human label, its share, and the n it rests on."""
    rows = []
    for arch in k4.columns:
        col = k4[arch]
        n = int(col.sum())
        if n == 0:
            continue
        lab = col.idxmax()
        rows.append({"archetype": arch, "modal_label": lab,
                     "modal_count": int(col.max()), "n": n,
                     "share": round(col.max() / n, 3)})
    return pd.DataFrame(rows)


def _pct_table(ct: pd.DataFrame) -> pd.DataFrame:
    """Column-wise % with small cells (< MIN_CELL_FOR_PCT) suppressed to ''."""
    out = ct.copy().astype(object)
    for c in ct.columns:
        tot = ct[c].sum()
        for r in ct.index:
            v = ct.loc[r, c]
            out.loc[r, c] = f"{v / tot:.0%}" if v >= MIN_CELL_FOR_PCT and tot \
                else ""
    return out


def report_one(name: str, m: pd.DataFrame, lines: list[str],
               rows: list[dict], weak: bool = False) -> None:
    tag = f"[{name}]" + ("  (single-rater — weaker evidence)" if weak else "")
    lines.append(f"\n{'=' * 70}\n{tag}  n={len(m)}\n{'=' * 70}")

    binary, k4 = _crosstabs(m)
    lines.append("\nprimary_label × flag  (HEADLINE — binary partition):")
    lines.append("  " + binary.to_string().replace("\n", "\n  "))
    lines.append("\nprimary_label × archetype  (descriptive; raw counts, "
                 f"% shown only for cells ≥ {MIN_CELL_FOR_PCT}):")
    lines.append("  " + k4.to_string().replace("\n", "\n  "))
    pct = _pct_table(k4)
    if (pct.values != "").any():
        lines.append("  column-% (small cells suppressed):")
        lines.append("  " + pct.to_string().replace("\n", "\n  "))

    ag = _agreement(m)
    lines.append("\npartition agreement (human vs data-driven):")
    for k, v in ag.items():
        lines.append(f"  {k:<14} {v:+.3f}")
        rows.append({"subset": name, "metric": k, "value": v, "n": len(m)})

    cand = _naming_candidates(k4)
    lines.append("\nnaming candidates (modal human label per archetype):")
    lines.append("  " + cand.to_string(index=False).replace("\n", "\n  "))

    # long-format crosstab rows for CSV
    for r in binary.index:
        for c in binary.columns:
            rows.append({"subset": name, "metric": f"count|flag|{r}|{c}",
                         "value": int(binary.loc[r, c]), "n": len(m)})
    for r in k4.index:
        for c in k4.columns:
            rows.append({"subset": name, "metric": f"count|arch|{r}|{c}",
                         "value": int(k4.loc[r, c]), "n": len(m)})


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("sheet")
    ap.add_argument("--second", default=None,
                    help="a second rater's sheet (may be a subset of cards)")
    ap.add_argument("--key", default=str(OUT / "card_key.csv"))
    ap.add_argument("--sample", default=str(OUT / "labelling_sample.csv"))
    args = ap.parse_args()

    key = pd.read_csv(args.key)
    sample = pd.read_csv(args.sample)

    lines: list[str] = []
    rows: list[dict] = []

    r1 = _load_sheet(Path(args.sheet))
    m1 = join_archetypes(r1, key, sample)
    report_one("rater1: all", m1, lines, rows)
    hi1 = m1[m1["confidence"] == "H"]
    if len(hi1):
        report_one("rater1: high-confidence", hi1, lines, rows, weak=True)

    if args.second:
        r2 = _load_sheet(Path(args.second))
        if "adjudicated_label" in r2.columns:
            lines.append("\n(adjudicated_label column found — using it.)")
            r2 = r2.assign(primary_label=r2["adjudicated_label"].str.strip())
            m2 = join_archetypes(r2, key, sample)
            report_one("adjudicated", m2, lines, rows)
        else:
            # No adjudication rule invented: report the second rater separately.
            m2 = join_archetypes(r2, key, sample)
            report_one("rater2: all", m2, lines, rows)
            hi2 = m2[m2["confidence"] == "H"]
            if len(hi2):
                report_one("rater2: high-confidence", hi2, lines, rows, weak=True)

    print("\n".join(lines))

    OUT.mkdir(parents=True, exist_ok=True)
    long = pd.DataFrame(rows)
    long[long["metric"].str.startswith("count|")].to_csv(
        OUT / "naming_crosstab.csv", index=False)
    long[~long["metric"].str.startswith("count|")].to_csv(
        OUT / "naming_agreement.csv", index=False)
    print(f"\nWrote {OUT/'naming_crosstab.csv'} and {OUT/'naming_agreement.csv'}")


if __name__ == "__main__":
    main()

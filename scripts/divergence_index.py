"""RQ4 headline — journal divergence index across the cascade, recomputed.

Per-team divergence index = number of the 9 imbalance/conflict checklist features
present (majority-of-3 shuffled runs), grouped by cascade bucket, Kruskal-Wallis
across buckets + Silent-vs-Standout Mann-Whitney. Mirrors the method in
docs/qualitative/llm-results.md. Written 2026-09-10 to re-confirm the headline after
the 2024_s2 journal-dedup re-mark (docs/qualitative/journal-data-dedup.md).

    python3 -m scripts.divergence_index
"""

from __future__ import annotations

import json
from collections import defaultdict

from scipy.stats import kruskal, mannwhitneyu

from src.qualitative.llm import blobs, marking

# The 9 imbalance/conflict features (the 11 binaries minus the two positive ones).
FEATURES = [f for f in marking.BINARY if f not in ("harmonious_balanced", "mutual_support")]
BUCKET_ORDER = ["Silent", "Contested", "No standout", "Standout"]


def team_divergence() -> dict[tuple[str, str], int]:
    """(cohort, team_label) -> divergence index from majority-of-3 v1 marks."""
    runs: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for f in sorted(marking._OUT.glob("*_r*.json")):
        d = json.loads(f.read_text())
        runs[(d["cohort"], d["team_label"])].append(d["marks"])
    out: dict[tuple[str, str], int] = {}
    for key, marks_list in runs.items():
        idx = 0
        for feat in FEATURES:
            votes = [bool(m.get(feat)) for m in marks_list]
            if sum(votes) >= 2:  # majority of 3
                idx += 1
        out[key] = idx
    return out


def main() -> None:
    div = team_divergence()
    meta = blobs.load_team_meta()
    by_bucket: dict[str, list[int]] = defaultdict(list)
    for (cohort, team), idx in div.items():
        try:
            bucket = str(meta.loc[(cohort, team), "anyflag_bucket"])
        except KeyError:
            continue
        if bucket in BUCKET_ORDER:
            by_bucket[bucket].append(idx)

    import statistics as st
    print(f"{'bucket':<14}{'n':>4}{'mean':>8}{'median':>8}")
    for b in BUCKET_ORDER:
        v = by_bucket[b]
        print(f"{b:<14}{len(v):>4}{st.mean(v):>8.2f}{st.median(v):>8.1f}")

    groups = [by_bucket[b] for b in BUCKET_ORDER]
    H, p = kruskal(*groups)
    print(f"\nKruskal-Wallis across 4 buckets: H={H:.2f}, p={p:.4g}")
    u, pmw = mannwhitneyu(by_bucket["Silent"], by_bucket["Standout"], alternative="two-sided")
    print(f"Silent vs Standout Mann-Whitney: U={u:.0f}, p={pmw:.4g} "
          f"(means {st.mean(by_bucket['Silent']):.2f} vs {st.mean(by_bucket['Standout']):.2f})")


if __name__ == "__main__":
    main()

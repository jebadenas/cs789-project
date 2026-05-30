"""RQ1 robustness across synthetic rater profiles.

Runs the full attack suite on synthetic cohorts for every generator profile
(reliable / noisy / lazy / biased), so the robustness claim is not conditioned
on ideal raters. Writes one tidy CSV: profile × attack × model → mean Attack Δ.

Run:
    python3 -m src.attacks.profile_sweep
"""

from __future__ import annotations

import csv
from pathlib import Path

from src.attacks.runner import run_attacks
from src.attacks.synthetic import PROFILES, generate_cohort

OUTPUT = Path("output/attacks/profile_sweep.csv")


def main(
    teams_per_size: int = 10,
    seed: int = 0,
    n_perms: int = 100,
) -> Path:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []

    for profile in PROFILES:
        print(f"profile={profile} ...", flush=True)
        cohort = generate_cohort(
            teams_per_size=teams_per_size, base_seed=seed, profile=profile,
        )
        batch = run_attacks(
            synthetic=cohort, n_perms=n_perms, seed=seed, progress=False,
        )
        for (atk, mdl), v in sorted(batch.aggregate(source="synthetic").items()):
            rows.append({
                "profile": profile,
                "attack": atk,
                "model": mdl,
                "mean_delta": round(v["mean_delta"], 4),
                "n": v["n"],
                "mc_std": round(v["mc_std"], 4) if v["mc_std"] is not None else "",
            })

    with open(OUTPUT, "w", newline="") as f:
        w = csv.DictWriter(
            f, fieldnames=["profile", "attack", "model", "mean_delta", "n", "mc_std"]
        )
        w.writeheader()
        w.writerows(rows)

    print(f"\nSaved {OUTPUT} ({len(rows)} rows)")
    return OUTPUT


if __name__ == "__main__":
    main()

"""Batch drivers for the LLM pipeline. Resumable: each team writes its own file
and finished teams are skipped, so a pre-empted Slurm job just resumes on
re-submit.

    python3 -m src.qualitative.llm.run notes                 # all prompted cohorts
    python3 -m src.qualitative.llm.run notes --cohort 2024_s2
"""

from __future__ import annotations

import argparse
import sys
import time

from . import blobs, notes


def run_notes(cohorts: list[str], num_ctx: int) -> None:
    tasks = [(c, t) for c in cohorts for t in blobs.team_labels(c)]
    total = len(tasks)
    print(f"notes: {total} teams across {cohorts}", flush=True)
    for i, (cohort, team) in enumerate(tasks, 1):
        t0 = time.time()
        out = notes._OUT / f"{cohort}_{team}.json"
        done = out.exists()
        notes.run_team(cohort, team, num_ctx=num_ctx)
        tag = "skip" if done else f"{time.time() - t0:.0f}s"
        print(f"  [{i}/{total}] {cohort} {team}  ({tag})", flush=True)
    print("notes: complete", flush=True)


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("step", choices=["notes"])
    p.add_argument("--cohort", action="append", help="limit to cohort(s); default all prompted")
    p.add_argument("--num-ctx", type=int, default=49152, help="Ollama only; must exceed largest blob")
    args = p.parse_args(argv)

    cohorts = args.cohort or blobs.PROMPTED
    if args.step == "notes":
        run_notes(cohorts, args.num_ctx)


if __name__ == "__main__":
    main(sys.argv[1:])

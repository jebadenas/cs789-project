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

from . import aggregate, blobs, marking, marking_sprint, marking_summary, marking_v2, notes


def run_notes(cohorts: list[str], num_ctx: int) -> None:
    tasks = [(c, t) for c in cohorts for t in blobs.team_labels(c)]
    total = len(tasks)
    print(f"notes: {total} teams across {cohorts}", flush=True)
    failed = []
    for i, (cohort, team) in enumerate(tasks, 1):
        t0 = time.time()
        out = notes._OUT / f"{cohort}_{team}.json"
        done = out.exists()
        try:
            notes.run_team(cohort, team, num_ctx=num_ctx)
            tag = "skip" if done else f"{time.time() - t0:.0f}s"
        except Exception as e:  # one bad team must not kill the batch — it's resumable
            failed.append((cohort, team))
            tag = f"FAILED after {time.time() - t0:.0f}s: {type(e).__name__}"
        print(f"  [{i}/{total}] {cohort} {team}  ({tag})", flush=True)
    print(f"notes: complete — {total - len(failed)}/{total} ok, {len(failed)} failed", flush=True)
    if failed:
        print("  failed (re-run to retry): " + ", ".join(f"{c}/{t}" for c, t in failed), flush=True)


def run_mark(cohorts: list[str], runs: int = 3) -> None:
    teams = [(c, t) for c in cohorts for t in blobs.team_labels(c)]
    tasks = [(r, c, t) for r in range(runs) for (c, t) in teams]  # run-major
    total = len(tasks)
    print(f"mark: {len(teams)} teams x {runs} runs = {total}", flush=True)
    failed = []
    for i, (r, cohort, team) in enumerate(tasks, 1):
        t0 = time.time()
        out = marking._OUT / f"{cohort}_{team}_r{r}.json"
        done = out.exists()
        try:
            marking.run_team(cohort, team, r)
            tag = "skip" if done else f"{time.time() - t0:.0f}s"
        except Exception as e:
            failed.append((cohort, team, r))
            tag = f"FAILED: {type(e).__name__}"
        print(f"  [{i}/{total}] r{r} {cohort} {team}  ({tag})", flush=True)
    print(f"mark: complete — {total - len(failed)}/{total} ok, {len(failed)} failed", flush=True)
    if failed:
        print("  failed (re-run to retry): " + ", ".join(f"{c}/{t}/r{r}" for c, t, r in failed), flush=True)


def run_mark_v2(cohorts: list[str], runs: int = 3) -> None:
    """Workstream 3 re-run: only the two reworded (gate+follow-up) fields."""
    teams = [(c, t) for c in cohorts for t in blobs.team_labels(c)]
    tasks = [(r, c, t) for r in range(runs) for (c, t) in teams]  # run-major
    total = len(tasks)
    print(f"mark_v2: {len(teams)} teams x {runs} runs = {total}", flush=True)
    failed = []
    for i, (r, cohort, team) in enumerate(tasks, 1):
        t0 = time.time()
        out = marking_v2._OUT / f"{cohort}_{team}_r{r}.json"
        done = out.exists()
        try:
            marking_v2.run_team(cohort, team, r)
            tag = "skip" if done else f"{time.time() - t0:.0f}s"
        except Exception as e:
            failed.append((cohort, team, r))
            tag = f"FAILED: {type(e).__name__}"
        print(f"  [{i}/{total}] r{r} {cohort} {team}  ({tag})", flush=True)
    print(f"mark_v2: complete — {total - len(failed)}/{total} ok, {len(failed)} failed", flush=True)
    if failed:
        print("  failed (re-run to retry): " + ", ".join(f"{c}/{t}/r{r}" for c, t, r in failed), flush=True)


def run_sprint(cohorts: list[str], runs: int = 3) -> None:
    """Per-(team, sprint) coding of the 11 v1 binaries, 3x shuffled for reliability."""
    cells = [(c, t, ji) for c in cohorts for t in blobs.team_labels(c)
             for ji in marking_sprint.sprint_indices(c)]
    tasks = [(r, c, t, ji) for r in range(runs) for (c, t, ji) in cells]  # run-major
    total = len(tasks)
    print(f"sprint: {len(cells)} cells x {runs} runs = {total} across {cohorts}", flush=True)
    failed = []
    for i, (r, cohort, team, ji) in enumerate(tasks, 1):
        t0 = time.time()
        out = marking_sprint._OUT / f"{cohort}_{team}_j{ji}_r{r}.json"
        done = out.exists()
        try:
            marking_sprint.run_team_sprint(cohort, team, ji, r)
            tag = "skip" if done else f"{time.time() - t0:.0f}s"
        except Exception as e:
            failed.append((cohort, team, ji, r))
            tag = f"FAILED: {type(e).__name__}"
        print(f"  [{i}/{total}] r{r} {cohort} {team} j{ji}  ({tag})", flush=True)
    print(f"sprint: complete — {total - len(failed)}/{total} ok, {len(failed)} failed", flush=True)
    if failed:
        print("  failed (re-run to retry): " + ", ".join(f"{c}/{t}/j{ji}/r{r}" for c, t, ji, r in failed), flush=True)


def run_summarize(cohorts: list[str]) -> None:
    """Per-(team, sprint) 72B summary for the dashboard (one call per cell)."""
    tasks = [(c, t, ji) for c in cohorts for t in blobs.team_labels(c)
             for ji in marking_summary.sprint_indices(c)]
    total = len(tasks); failed = []
    print(f"summarize: {total} (team, sprint) cells across {cohorts}", flush=True)
    for i, (cohort, team, ji) in enumerate(tasks, 1):
        t0 = time.time()
        out = marking_summary._OUT / f"{cohort}_{team}_j{ji}.json"
        done = out.exists()
        try:
            marking_summary.run_team_sprint(cohort, team, ji)
            tag = "skip" if done else f"{time.time() - t0:.0f}s"
        except Exception as e:
            failed.append((cohort, team, ji)); tag = f"FAILED: {type(e).__name__}"
        print(f"  [{i}/{total}] {cohort} {team} j{ji}  ({tag})", flush=True)
    print(f"summarize: complete - {total - len(failed)}/{total} ok, {len(failed)} failed", flush=True)


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("step", choices=["notes", "aggregate", "mark", "mark_v2", "sprint", "summarize"])
    p.add_argument("--cohort", action="append", help="limit to cohort(s); default all prompted")
    p.add_argument("--num-ctx", type=int, default=49152, help="Ollama only; must exceed largest blob")
    args = p.parse_args(argv)

    cohorts = args.cohort or blobs.PROMPTED
    if args.step == "notes":
        run_notes(cohorts, args.num_ctx)
    elif args.step == "aggregate":
        aggregate.run_all()
    elif args.step == "mark":
        run_mark(cohorts)
    elif args.step == "mark_v2":
        run_mark_v2(cohorts)
    elif args.step == "sprint":
        run_sprint(cohorts)
    elif args.step == "summarize":
        run_summarize(cohorts)


if __name__ == "__main__":
    main(sys.argv[1:])

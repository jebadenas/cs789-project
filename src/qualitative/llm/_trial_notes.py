"""Throwaway trial: run Step-2 notes on 3 small teams (one per cascade state)
via the local model, timing each, and print the notes for eyeballing.

    python3 -m src.qualitative.llm._trial_notes
"""

import json
import time

from . import blobs, notes

NUM_CTX = 20480  # covers the 3 chosen blobs (max ~16.4k tokens) with headroom


def main() -> None:
    picks = json.load(open("/tmp/trial_picks.json"))
    meta = blobs.load_team_meta()
    for cohort, team in picks:
        state = meta.loc[(cohort, team), "pooled_state"]
        words = len(blobs.build_blob(cohort, team).split())
        print(f"\n{'='*70}\n{state}  |  {cohort} {team}  (~{words} words)\n{'='*70}")
        t0 = time.time()
        rec = notes.run_team(cohort, team, num_ctx=NUM_CTX, force=True)
        print(f"[{time.time()-t0:.0f}s]\n{rec['note']}")


if __name__ == "__main__":
    main()

#!/bin/bash
# LOCAL overnight NOTES run (Step 2) on the 7B — a DRESS REHEARSAL, not final
# results. The 7B is too weak for the definitive notes (it drifts on calm teams);
# this exists only to exercise the full pipeline at scale and produce a
# provisional checklist to eyeball. Freeze the real checklist from the 72B run.
#
# Resumable: one JSON per team under output/qualitative/llm/notes/, finished
# teams are skipped — so if it stops, just run this again.
#
# BEFORE RUNNING: plug in the laptop and leave the LID OPEN (caffeinate stops
# idle sleep, but closing the lid still sleeps the Mac). Make sure Ollama is
# running (the Ollama app, or `ollama serve`).
#
#   bash scripts/notes_overnight_local.sh
#
# ~10-14 h for all 119 teams; an overnight pass gets most, resume to finish.
set -euo pipefail
cd /Users/josbadenas/Documents/git/uni/cs789-project

export OLLAMA_FLASH_ATTENTION=1 OLLAMA_KV_CACHE_TYPE=q8_0
export LLM_BACKEND=ollama LLM_MODEL=qwen2.5:7b

LOG=output/qualitative/llm/notes_local_run.log
mkdir -p output/qualitative/llm/notes

echo "=== local notes rehearsal started $(date) ===" | tee -a "$LOG"
# num_ctx 49152 covers ~113/119 teams fully; the ~6 giant teams (>49k tokens)
# get their tail truncated locally — acceptable for a rehearsal.
caffeinate -i python3 -m src.qualitative.llm.run notes --num-ctx 49152 2>&1 | tee -a "$LOG"
echo "=== finished $(date) ===" | tee -a "$LOG"

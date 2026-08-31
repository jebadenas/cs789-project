#!/bin/bash
# A/B test: run the EXACT same notes prompt on the 72B for two teams the local
# 7B clearly failed on (drifted into activity-recap / verbatim copying):
#   2025_s1 team_05 (No standout) and 2024_s2 team_16 (Contested).
# 72B output goes to output/qualitative/llm/notes_72b_test/ so the 7B rehearsal
# notes are preserved for comparison.
#
#   git pull && sbatch slurm/journal_test_72b.sh && tail -f slurm-journal-test72b-*.log
#
#SBATCH --job-name=journal-test72b
#SBATCH --time=00:40:00
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --open-mode=append
#SBATCH --output=slurm-%x-%j.log
#SBATCH --error=slurm-%x-%j.log

set -euo pipefail
PROJECT=/data/$USER/cs789-project
MODEL_DIR=/data/$USER/models/qwen72b-awq
PORT=8000

cd "$PROJECT"
source .venv/bin/activate

vllm serve "$MODEL_DIR" --served-model-name qwen72b --quantization awq_marlin \
    --max-model-len 73728 --gpu-memory-utilization 0.92 --max-num-seqs 2 --port "$PORT" &
VLLM_PID=$!
trap 'kill $VLLM_PID 2>/dev/null || true' EXIT

for i in $(seq 1 120); do
    curl -sf "http://localhost:${PORT}/health" >/dev/null 2>&1 && { echo "vLLM ready"; break; }
    sleep 10
done

export LLM_BACKEND=openai OPENAI_BASE_URL="http://localhost:${PORT}/v1" \
       OPENAI_API_KEY=EMPTY LLM_MODEL=qwen72b

python3 - <<'PY'
import json, pathlib
from src.qualitative.llm import blobs
from src.qualitative.llm.model import call_model
from src.qualitative.llm.notes import SYSTEM, PROMPT
out = pathlib.Path("output/qualitative/llm/notes_72b_test"); out.mkdir(parents=True, exist_ok=True)
for c, t in [("2025_s1", "team_05"), ("2024_s2", "team_16")]:
    blob = blobs.build_blob(c, t)
    note = call_model(PROMPT.format(blob=blob), system=SYSTEM, temperature=0.2, max_tokens=1500)
    (out / f"{c}_{t}.json").write_text(json.dumps({"cohort": c, "team_label": t, "note": note}, indent=2))
    print(f"\n{'='*70}\n72B — {c} {t}\n{'='*70}\n{note}")
PY

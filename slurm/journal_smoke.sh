#!/bin/bash
# Smoke test: serve the 72B and run the notes prompt on the two teams we already
# ran locally (Contested team_10, Silent-flat team_14) so we can compare the 72B
# to the 7B and confirm the tightened prompt behaves on a strong model.
#
#   sbatch slurm/journal_smoke.sh   &&   tail -f slurm-journal-smoke-*.log
#
#SBATCH --job-name=journal-smoke
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
from src.qualitative.llm import notes
for c, t in [("2023_s2", "team_10"), ("2024_s1", "team_14")]:
    rec = notes.run_team(c, t, num_ctx=49152, force=True)
    print(f"\n{'='*70}\n{c} {t}\n{'='*70}\n{rec['note']}")
PY

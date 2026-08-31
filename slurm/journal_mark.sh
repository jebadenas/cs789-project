#!/bin/bash
# Step 6 (blind marking) on the 72B: score all 119 teams on the frozen checklist,
# 3x each with shuffled member labels = 357 calls. Resumable — re-submit to resume.
#
#   sbatch slurm/journal_mark.sh
#
#SBATCH --job-name=journal-mark
#SBATCH --time=08:00:00
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
export HOME=/data/$USER TMPDIR=/data/$USER/tmp HF_HOME=/data/$USER/hf XDG_CACHE_HOME=/data/$USER/.cache
export no_proxy="localhost,127.0.0.1" NO_PROXY="localhost,127.0.0.1"

vllm serve "$MODEL_DIR" --served-model-name qwen72b --quantization awq_marlin \
    --hf-overrides '{"rope_scaling":{"rope_type":"yarn","factor":4.0,"original_max_position_embeddings":32768}}' \
    --max-model-len 73728 --gpu-memory-utilization 0.92 --max-num-seqs 2 --port "$PORT" &
VLLM_PID=$!
trap 'kill $VLLM_PID 2>/dev/null || true' EXIT

for i in $(seq 1 120); do
    curl -sf "http://localhost:${PORT}/health" >/dev/null 2>&1 && { echo "vLLM ready"; break; }
    sleep 10
done

export LLM_BACKEND=openai OPENAI_BASE_URL="http://localhost:${PORT}/v1" \
       OPENAI_API_KEY=EMPTY LLM_MODEL=qwen72b

python3 -m src.qualitative.llm.run mark

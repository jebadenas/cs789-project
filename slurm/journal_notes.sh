#!/bin/bash
# Step 2 (per-team notes) on the cluster: serve Qwen2.5-72B-AWQ on one GPU with
# vLLM, then run the resumable notes batch against it. Re-submit after a
# pre-emption and it resumes (finished teams are skipped).
#
#   sbatch slurm/journal_notes.sh
#
#SBATCH --job-name=journal-notes
#SBATCH --time=06:00:00
#SBATCH --gres=gpu:1                 # single GPU — no admin approval needed
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --open-mode=append
#SBATCH --output=slurm-%x-%j.log
#SBATCH --error=slurm-%x-%j.log

set -euo pipefail

PROJECT=/data/$USER/cs789-project           # <-- adjust if you cloned elsewhere
MODEL_DIR=/data/$USER/models/qwen72b-awq
PORT=8000

cd "$PROJECT"
source .venv/bin/activate

# --- start vLLM (OpenAI-compatible server), loads the model once -------------
vllm serve "$MODEL_DIR" \
    --served-model-name qwen72b \
    --quantization awq_marlin \
    --max-model-len 73728 \
    --gpu-memory-utilization 0.92 \
    --max-num-seqs 2 \
    --port "$PORT" &
VLLM_PID=$!
trap 'kill $VLLM_PID 2>/dev/null || true' EXIT

# --- wait until it is ready ---------------------------------------------------
echo "waiting for vLLM to load the model..."
for i in $(seq 1 120); do
    if curl -sf "http://localhost:${PORT}/health" >/dev/null 2>&1; then
        echo "vLLM ready after ~$((i*10))s"; break
    fi
    sleep 10
done

# --- run the resumable notes batch against the local server ------------------
export LLM_BACKEND=openai
export OPENAI_BASE_URL="http://localhost:${PORT}/v1"
export OPENAI_API_KEY=EMPTY
export LLM_MODEL=qwen72b

python3 -m src.qualitative.llm.run notes

echo "notes batch finished"

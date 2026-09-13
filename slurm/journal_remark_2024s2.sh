#!/bin/bash
# One-off: re-mark ONLY cohort 2024_s2 (v1 checklist + v2 gate/follow-up) after the
# journal-dedup fix (docs/qualitative/journal-data-dedup.md). 43 teams x 3 runs x 2
# instruments = 258 calls. Resumable — delete a cohort's marks to force recompute.
#
#   sbatch slurm/journal_remark_2024s2.sh
#
#SBATCH --job-name=journal-remark-2024s2
#SBATCH --time=06:00:00
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
export CPATH=/data/$USER/pyhdr/usr/include/python3.11${CPATH:+:$CPATH}
export CUDA_HOME=/data/$USER/cs789-project/.venv/lib/python3.11/site-packages/nvidia/cu13
export PATH=$CUDA_HOME/bin:$PATH
export VLLM_USE_FLASHINFER_SAMPLER=0
export VLLM_ATTENTION_BACKEND=FLASH_ATTN

vllm serve "$MODEL_DIR" --served-model-name qwen72b --quantization awq_marlin \
    --hf-overrides '{"rope_scaling":{"rope_type":"yarn","factor":4.0,"original_max_position_embeddings":32768}}' \
    --max-model-len 73728 --gpu-memory-utilization 0.92 --max-num-seqs 2 --port "$PORT" &
VLLM_PID=$!
trap 'kill $VLLM_PID 2>/dev/null || true' EXIT

READY=0
for i in $(seq 1 360); do
    curl -sf "http://localhost:${PORT}/health" >/dev/null 2>&1 && { echo "vLLM ready after $((i*10))s"; READY=1; break; }
    sleep 10
done
[ "$READY" = 1 ] || { echo "vLLM never became healthy after 60 min — aborting before the client runs (resubmit to retry)"; exit 1; }

export LLM_BACKEND=openai OPENAI_BASE_URL="http://localhost:${PORT}/v1" \
       OPENAI_API_KEY=EMPTY LLM_MODEL=qwen72b

python3 -m src.qualitative.llm.run mark    --cohort 2024_s2
python3 -m src.qualitative.llm.run mark_v2 --cohort 2024_s2

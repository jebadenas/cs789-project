#!/bin/bash
# Per-sprint EVIDENCE-GROUNDED coding (v2) on the 72B: the same 11 binaries as the
# v1 per-sprint run, but a flag fires only with a directly-supporting verbatim quote,
# each quote tagged with its Member, 1-3 per flag. Writes to a NEW dir
# (output/qualitative/llm/marks_sprint_v2/) so v1 vs v2 reliability AND validity can
# be compared. All prompted cohorts x 3 shuffled runs. Resumable — resubmit to resume.
#
#   sbatch slurm/journal_sprint_v2.sh
#   # or a single cohort first:  edit the last line to: ... run sprint_v2 --cohort 2025_s1
#
#SBATCH --job-name=journal-sprint-v2
#SBATCH --time=16:00:00
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
# RHEL8 python3.11 ships no dev headers; triton's runtime C compile of cuda_utils.c
# needs Python.h — point CPATH at the extracted python3.11-devel headers.
export CPATH=/data/$USER/pyhdr/usr/include/python3.11${CPATH:+:$CPATH}
# No system CUDA toolkit — point CUDA_HOME at the pip nvidia-cu13 wheel (full toolkit).
export CUDA_HOME=/data/$USER/cs789-project/.venv/lib/python3.11/site-packages/nvidia/cu13
export PATH=$CUDA_HOME/bin:$PATH
# FlashInfer's bundled headers are incompatible with the cu13 nvcc, so its JIT of the
# sampler fails — use the native sampler + precompiled flash-attn (nothing to compile).
export VLLM_USE_FLASHINFER_SAMPLER=0
export VLLM_ATTENTION_BACKEND=FLASH_ATTN

vllm serve "$MODEL_DIR" --served-model-name qwen72b --quantization awq_marlin \
    --hf-overrides '{"rope_scaling":{"rope_type":"yarn","factor":4.0,"original_max_position_embeddings":32768}}' \
    --max-model-len 73728 --gpu-memory-utilization 0.92 --max-num-seqs 2 --port "$PORT" &
VLLM_PID=$!
trap 'kill $VLLM_PID 2>/dev/null || true' EXIT

# Up to 60 min for the 72B to become healthy (weights + kernel compile under GPU
# contention). Abort cleanly if it never does, rather than fire a doomed client.
READY=0
for i in $(seq 1 360); do
    curl -sf "http://localhost:${PORT}/health" >/dev/null 2>&1 && { echo "vLLM ready after $((i*10))s"; READY=1; break; }
    sleep 10
done
[ "$READY" = 1 ] || { echo "vLLM never became healthy after 60 min — aborting before the client runs (resubmit to retry)"; exit 1; }

export LLM_BACKEND=openai OPENAI_BASE_URL="http://localhost:${PORT}/v1" \
       OPENAI_API_KEY=EMPTY LLM_MODEL=qwen72b

python3 -m src.qualitative.llm.run sprint_v2

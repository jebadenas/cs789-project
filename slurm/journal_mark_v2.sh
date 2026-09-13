#!/bin/bash
# Step 6b (Workstream 3) on the 72B: re-ask ONLY the two reworded fields as
# gate+follow-up, all 119 teams x 3 shuffled runs = 357 calls. v1 marks untouched;
# this writes to output/qualitative/llm/marks_v2/. Resumable — re-submit to resume.
#
#   sbatch slurm/journal_mark_v2.sh
#
#SBATCH --job-name=journal-mark-v2
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
# The stock RHEL8 python3.11 ships no dev headers, so vLLM/triton's runtime C
# compile of cuda_utils.c fails on Python.h. We extracted python3.11-devel headers
# to /data/$USER/pyhdr; put them on the compiler search path so triton can build.
export CPATH=/data/$USER/pyhdr/usr/include/python3.11${CPATH:+:$CPATH}
# No system CUDA toolkit (only a driver), so vLLM's runtime kernel compile can't
# find nvcc. Point CUDA_HOME at the pip nvidia-cu13 wheel, which bundles a full
# matching CUDA 13.3 toolkit (nvcc/ptxas/nvvm/includes).
export CUDA_HOME=/data/$USER/cs789-project/.venv/lib/python3.11/site-packages/nvidia/cu13
export PATH=$CUDA_HOME/bin:$PATH
# This cluster has a driver but no proper CUDA dev toolchain, and FlashInfer's
# bundled headers are incompatible with the cu13 nvcc — so its runtime JIT of the
# sampling kernels fails. Use the native PyTorch sampler and the precompiled
# flash-attn backend so nothing needs compiling at serve time.
export VLLM_USE_FLASHINFER_SAMPLER=0
export VLLM_ATTENTION_BACKEND=FLASH_ATTN

vllm serve "$MODEL_DIR" --served-model-name qwen72b --quantization awq_marlin \
    --hf-overrides '{"rope_scaling":{"rope_type":"yarn","factor":4.0,"original_max_position_embeddings":32768}}' \
    --max-model-len 73728 --gpu-memory-utilization 0.92 --max-num-seqs 2 --port "$PORT" &
VLLM_PID=$!
trap 'kill $VLLM_PID 2>/dev/null || true' EXIT

# Up to 60 min: the 72B (weights + runtime kernel compile) can be slow to become
# healthy under GPU contention. If we DON'T wait long enough, the client fires
# against a dead socket and every call fails with URLError (the misleading
# "0/357" seen in job 16460) — so abort cleanly rather than run a doomed client.
READY=0
for i in $(seq 1 360); do
    curl -sf "http://localhost:${PORT}/health" >/dev/null 2>&1 && { echo "vLLM ready after $((i*10))s"; READY=1; break; }
    sleep 10
done
[ "$READY" = 1 ] || { echo "vLLM never became healthy after 60 min — aborting before the client runs (resubmit to retry)"; exit 1; }

export LLM_BACKEND=openai OPENAI_BASE_URL="http://localhost:${PORT}/v1" \
       OPENAI_API_KEY=EMPTY LLM_MODEL=qwen72b

python3 -m src.qualitative.llm.run mark_v2

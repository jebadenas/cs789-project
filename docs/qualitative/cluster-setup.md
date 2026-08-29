# Cluster setup — LLM journal analysis

Run the notes/marking steps on the CS ML cluster with a local open-weight model
(Qwen2.5-72B-AWQ), so the journals never leave the university. Everything you
run yourself is marked **[you]**; the code/scripts are already in the repo.

Replace `<UPI>` with your username throughout. VPN must be connected.

## 0. What the model actually sees

The blobs are blinded to `Member A/B/...` — but the journal *text* still names
teammates (this is unavoidable; the reflection bodies name people). That's fine
on the in-house cluster. It only matters at the end: **any note or quote you pull
into the dissertation must be name-scrubbed by hand first.**

## 1. Log in **[you]**

```bash
ssh <UPI>@foscsmlprd01.its.auckland.ac.nz     # password is  yourpass:2FAcode  (one string)
```

## 2. One-time environment **[you]**

```bash
export HOME=/data/$USER TMPDIR=/data/$USER/tmp HF_HOME=/data/$USER/hf
export https_proxy=http://squid.auckland.ac.nz:3128 http_proxy=http://squid.auckland.ac.nz:3128
mkdir -p /data/$USER/{tmp,hf,models}

cd /data/$USER
git clone <your-repo-url> cs789-project     # or rsync the repo up (see step 4)
cd cs789-project
python3 -m venv .venv && source .venv/bin/activate
pip install --proxy $https_proxy vllm pandas pyarrow
```

## 3. Download the model (~40 GB, via proxy) **[you]**

```bash
huggingface-cli download Qwen/Qwen2.5-72B-Instruct-AWQ \
    --local-dir /data/$USER/models/qwen72b-awq
```

## 4. Copy the data up — **pseudonymised only, NEVER the crosswalk** **[you]**

From your laptop (not the cluster). These are the only files the pipeline reads:

```bash
rsync -avR \
  data/journals/processed/entries.parquet \
  output/qualitative/reader/team_key_2023_s2.csv \
  output/qualitative/reader/team_key_2024_s1.csv \
  output/qualitative/reader/team_key_2024_s2.csv \
  output/qualitative/reader/team_key_2025_s1.csv \
  output/qualitative/reader/batch_teams_2023_s2.json \
  output/qualitative/reader/batch_teams_2024_s1.json \
  output/qualitative/reader/batch_teams_2024_s2.json \
  output/qualitative/reader/batch_teams_2025_s1.json \
  output/dynamics2/pooled/team_states.csv \
  <UPI>@foscsmlprd01.its.auckland.ac.nz:/data/<UPI>/cs789-project/
```

> ⚠️ Do **not** copy `data/journals/crosswalk/name_to_anon.csv`. The pipeline
> never needs it, and it's the one file that can re-identify students.

## 5. Smoke test — one GPU, two known teams **[you]**

Confirms the 72B loads and lets us compare it to the local 7B on the same two
teams (Contested vs Silent-flat), and whether the tightened prompt behaves.

```bash
sbatch slurm/journal_smoke.sh
squeue -u $USER                               # watch it schedule/run
tail -f slurm-journal-smoke-*.log             # the two notes print at the end
```

If it OOMs, drop `--max-model-len` to `32768` or `--max-num-seqs` to `2` in the
script.

## 6. Full notes run (Step 2, all 119 teams) **[you]**

```bash
sbatch slurm/journal_notes.sh
```

Resumable: if the job is pre-empted, just `sbatch` it again — finished teams are
skipped. Output lands in `output/qualitative/llm/notes/` (one JSON per team).

## 7. Pull results back **[you]**

```bash
# from your laptop
rsync -av <UPI>@foscsmlprd01...:/data/<UPI>/cs789-project/output/qualitative/llm/ output/qualitative/llm/
```

Then Steps 3–8 (group by state, checklist, marking, counting) — marking reuses
the same `slurm/journal_notes.sh` pattern; counting runs on your laptop.

## Backend swap

Nothing in the pipeline changes between machines — only env vars:

| Where | env |
|---|---|
| laptop (trial) | *(defaults)* `LLM_BACKEND=ollama`, `LLM_MODEL=qwen2.5:7b` |
| cluster | `LLM_BACKEND=openai`, `OPENAI_BASE_URL=http://localhost:8000/v1`, `LLM_MODEL=qwen72b` (set by the Slurm scripts) |

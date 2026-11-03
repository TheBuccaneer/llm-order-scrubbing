#!/usr/bin/env bash
set -euo pipefail
cd /home/rock/projects/llm-order-scrubbing
py=/home/rock/projects/porto/.venv-py313-repair/bin/python
model=/home/rock/.cache/huggingface/hub/models--Qwen--Qwen2.5-7B-Instruct/snapshots/a09a35458c702b33eeacc393d103063234e8bc28
base=results/tenant-scheduler-20261103
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export TMPDIR=/home/rock/projects/llm-order-scrubbing/results/tmp
export XDG_CACHE_HOME=/home/rock/projects/llm-order-scrubbing/results/tmp
export TRITON_CACHE_DIR=/home/rock/projects/llm-order-scrubbing/results/tmp/triton
server= proxy=
cleanup() {
  if [[ -n $proxy ]]; then kill -TERM "$proxy" 2>/dev/null || true; wait "$proxy" 2>/dev/null || true; proxy=; fi
  if [[ -n $server ]]; then kill -TERM "$server" 2>/dev/null || true; wait "$server" 2>/dev/null || true; server=; fi
}
trap cleanup EXIT INT TERM
for spec in 'dev 8 2 202611032601' 'holdout 16 4 202611032602'; do
  read -r name pairs controls seed <<< "$spec"
  folder=$base/$name
  mkdir "$folder"
  "$py" -m vllm.entrypoints.openai.api_server \
    --host 127.0.0.1 --port 8765 --model "$model" \
    --served-model-name Qwen/Qwen2.5-7B-Instruct \
    --max-model-len 2048 --gpu-memory-utilization 0.8 --enforce-eager \
    --enable-prefix-caching --enable-prompt-tokens-details \
    --max-num-batched-tokens 256 --long-prefill-token-threshold 64 \
    > "$folder/server.log" 2>&1 &
  server=$!
  ready=0
  for n in $(seq 1 90); do
    if curl -fsS http://127.0.0.1:8765/health >/dev/null 2>&1; then ready=1; break; fi
    if ! kill -0 "$server" 2>/dev/null; then break; fi
    sleep 1
  done
  if [[ $ready -ne 1 ]]; then echo "$name server failed"; exit 1; fi
  "$py" src/order_release_proxy.py "$folder/proxy.jsonl" > "$folder/proxy.log" 2>&1 &
  proxy=$!
  sleep 1
  "$py" src/tenant_scheduler_pilot.py "$folder/trials.jsonl" "$name" "$pairs" "$controls" "$seed" \
    data/document-workload-20261103/prompts.json direct > "$folder/client.log" 2>&1
  echo "$name: $(wc -l < "$folder/trials.jsonl") groups"
  cleanup
done

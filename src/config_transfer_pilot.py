"""Small balanced rank-transfer pilot using the existing Qwen request client."""

import json
import random
import sys
import time
import hashlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event

import cache_order_pilot as base

post = base.post


LABELS = "ABCD"


def request(label, salt, position, start):
    start.wait()
    if position:
        time.sleep(position * 0.010)
    return post(label, salt, max_tokens=16)


def main(output, tag, seed, kind, prompt_file=None):
    prompt_set_sha256 = None
    if prompt_file is not None:
        data = Path(prompt_file).read_bytes()
        prompt_set_sha256 = hashlib.sha256(data).hexdigest()
        base.PROMPTS = json.loads(data)["prompts"]
    rng = random.Random(seed)
    cases = []
    if kind in ("primary", "extend"):
        for warm in LABELS:
            for position in range(4):
                for _ in range(2):
                    cold = [x for x in LABELS if x != warm]
                    rng.shuffle(cold)
                    cases.append((warm, cold[:position] + [warm] + cold[position:]))
        if kind == "primary":
            for _ in range(4):
                order = list(LABELS)
                rng.shuffle(order)
                cases.append((None, order))
    elif kind == "cache_off_control":
        for position, warm in enumerate(LABELS):
            cold = [x for x in LABELS if x != warm]
            rng.shuffle(cold)
            cases.append((warm, cold[:position] + [warm] + cold[position:]))
    else:
        raise ValueError(kind)
    rng.shuffle(cases)

    with output.open("x", encoding="utf-8") as out, ThreadPoolExecutor(max_workers=4) as pool:
        for i, (warm, order) in enumerate(cases):
            salt = f"transfer-{tag}-{i:04d}"
            warmup = post(warm, salt) if warm else None
            start = Event()
            futures = {label: pool.submit(request, label, salt, pos, start)
                       for pos, label in enumerate(order)}
            start.set()
            probes = {label: future.result() for label, future in futures.items()}
            out.write(json.dumps({"trial": i, "tag": tag, "seed": seed, "kind": kind,
                                  "salt": salt, "warm": warm, "send_order": order,
                                  "prompt_set_sha256": prompt_set_sha256,
                                  "warmup": warmup, "probes": probes}) + "\n")
            out.flush()
            print(f"{i+1}/{len(cases)} {kind} warm={warm} order={''.join(order)}", flush=True)


if __name__ == "__main__":
    main(Path(sys.argv[1]), sys.argv[2], int(sys.argv[3]), sys.argv[4],
         sys.argv[5] if len(sys.argv) > 5 else None)

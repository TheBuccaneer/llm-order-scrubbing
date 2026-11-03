"""Frozen document-workload C0/C1 crossover case runner."""

import json
import random
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event

from bos_pilot import post, plan
from cache_order_pilot import post as warmup_post


def cases(seed):
    rng = random.Random(seed)
    rows = plan(1, ("bos4",), controls=2, seed=seed)
    for position, warm in enumerate("ABCD"):
        cold = [label for label in "ABCD" if label != warm]
        rng.shuffle(cold)
        rows.append(("direct", warm, cold[:position] + [warm] + cold[position:]))
    cold = list("ABCD")
    rng.shuffle(cold)
    rows.append(("direct", None, cold))
    rng.shuffle(rows)
    return rows


def main(output, tag, seed, prompts):
    rows = cases(seed)
    assert len(rows) == 23
    with output.open("x") as out, ThreadPoolExecutor(max_workers=4) as pool:
        for index, (mode, warm, order) in enumerate(rows):
            salt = f"doc-{tag}-{index:03d}"
            warmup = warmup_post(warm, salt, prompt=prompts[warm]) if warm else None
            start = Event()
            futures = {
                label: pool.submit(post, label, salt, salt, mode, pos * .010,
                                   start, 16, prompts[label])
                for pos, label in enumerate(order)
            }
            start.set()
            probes = {label: future.result() for label, future in futures.items()}
            out.write(json.dumps({"trial": index, "mode": mode, "warm": warm,
                                  "salt": salt, "group": salt, "send_order": order,
                                  "output_tokens": 16, "case_seed": seed,
                                  "warmup": warmup, "probes": probes}) + "\n")
            out.flush()
            print(f"{index + 1}/23 {mode} {warm} {''.join(order)}", flush=True)


if __name__ == "__main__":
    main(Path(sys.argv[1]), sys.argv[2], int(sys.argv[3]),
         json.loads(Path(sys.argv[4]).read_text()))

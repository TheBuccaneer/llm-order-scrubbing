"""Mixed P0/P1 BOS pilot with paired case sequences and isolated salts."""

import json
import random
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event

from bos_pilot import plan, post
from cache_order_pilot import MODEL, post as warmup_post


def cases(seed):
    base = plan(1, ("bos4",), controls=2, seed=seed)
    rows = [(structure, warm, order) for structure in ("p0", "p1")
            for _, warm, order in base]
    random.Random(seed + 1).shuffle(rows)
    return rows


def main(output, tag, seed, prompts, model=MODEL):
    rows = cases(seed)
    assert len(rows) == 36
    with output.open("x") as out, ThreadPoolExecutor(max_workers=4) as pool:
        for index, (structure, warm, order) in enumerate(rows):
            salt = f"prefix-{tag}-{structure}-{index:03d}"
            group = salt
            prompt_set = prompts[structure]
            warmup = warmup_post(warm, salt, prompt=prompt_set[warm], model=model) if warm else None
            start = Event()
            futures = {label: pool.submit(post, label, salt, group, "bos4", pos * .010,
                                          start, 16, prompt_set[label], model)
                       for pos, label in enumerate(order)}
            start.set()
            probes = {label: future.result() for label, future in futures.items()}
            out.write(json.dumps({"trial": index, "structure": structure,
                                  "mode": "bos4", "warm": warm, "salt": salt,
                                  "group": group, "send_order": order,
                                  "output_tokens": 16, "case_seed": seed,
                                  "warmup": warmup, "probes": probes}) + "\n")
            out.flush()
            print(f"{index+1}/36 {structure} warm={warm} {''.join(order)}", flush=True)


if __name__ == "__main__":
    main(Path(sys.argv[1]), sys.argv[2], int(sys.argv[3]),
         {"p0": json.loads(Path(sys.argv[4]).read_text()),
          "p1": json.loads(Path(sys.argv[5]).read_text())},
         sys.argv[6] if len(sys.argv) > 6 else MODEL)

"""Two controlled BOS groups for opt-in scheduler mechanism tracing."""

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event

from bos_pilot import post
from cache_order_pilot import post as warmup_post


def main(output: Path, tag: str):
    cases = (("A", ("A", "B", "C", "D")),
             ("A", ("B", "C", "D", "A")))
    with output.open("x") as out, ThreadPoolExecutor(max_workers=4) as pool:
        for index, (warm, order) in enumerate(cases):
            salt = f"trace-{tag}-{index}"
            warmup = warmup_post(warm, salt)
            start = Event()
            futures = {label: pool.submit(post, label, salt, salt, "bos4", pos * .010, start, 16)
                       for pos, label in enumerate(order)}
            start.set()
            probes = {label: future.result() for label, future in futures.items()}
            out.write(json.dumps({"group": salt, "mode": "bos4", "warm": warm,
                                  "send_order": order, "output_tokens": 16,
                                  "warmup": warmup, "probes": probes}) + "\n")
            out.flush()


if __name__ == "__main__":
    main(Path(sys.argv[1]), sys.argv[2])

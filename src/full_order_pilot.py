"""Observe four complete HTTP response ranks with one controlled cache hit."""

import json
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event

from cache_order_pilot import post


LABELS = ("A", "B", "C", "D")
STAGGER_S = 0.010


def delayed_probe(label: str, salt: str, delay_s: float, start: Event) -> dict:
    start.wait()
    if delay_s:
        time.sleep(delay_s)
    return post(label, salt)


def main(output: Path) -> None:
    rng = random.Random(20261104)
    cases = []
    for warm in LABELS:
        for warm_position in range(4):
            for _ in range(2):
                cold = [label for label in LABELS if label != warm]
                rng.shuffle(cold)
                order = cold[:warm_position] + [warm] + cold[warm_position:]
                cases.append((warm, order))
    for _ in range(8):
        order = list(LABELS)
        rng.shuffle(order)
        cases.append((None, order))
    rng.shuffle(cases)

    with output.open("x", encoding="utf-8") as out, ThreadPoolExecutor(
        max_workers=4
    ) as pool:
        for index, (warm, order) in enumerate(cases):
            salt = f"full-order-20261104-{index:03d}"
            warmup = post(warm, salt) if warm else None
            start = Event()
            futures = {
                label: pool.submit(
                    delayed_probe, label, salt, position * STAGGER_S, start
                )
                for position, label in enumerate(order)
            }
            start.set()
            probes = {label: future.result() for label, future in futures.items()}
            out.write(
                json.dumps(
                    {
                        "trial": index,
                        "salt": salt,
                        "warm": warm,
                        "send_order": order,
                        "warmup": warmup,
                        "probes": probes,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            out.flush()
            print(f"{index + 1}/{len(cases)} warm={warm} order={''.join(order)}", flush=True)


if __name__ == "__main__":
    main(Path(sys.argv[1]))

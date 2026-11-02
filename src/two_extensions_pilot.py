"""Two paper-motivated checks: 16-token answers and overlapping background work."""

import json
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event

from cache_order_pilot import post


LABELS = ("A", "B", "C", "D")


def probe(label: str, salt: str, tokens: int, delay: float, start: Event) -> dict:
    start.wait()
    if delay:
        time.sleep(delay)
    return post(label, salt, max_tokens=tokens)


def cases() -> list[tuple[str, str | None, list[str]]]:
    rng = random.Random(20261105)
    plans = []
    for mode in ("long_output", "background"):
        for warm in LABELS:
            for position in range(4):
                cold = [label for label in LABELS if label != warm]
                rng.shuffle(cold)
                plans.append((mode, warm, cold[:position] + [warm] + cold[position:]))
        for _ in range(4):
            order = list(LABELS)
            rng.shuffle(order)
            plans.append((mode, None, order))
    rng.shuffle(plans)
    return plans


def main(output: Path, tag: str) -> None:
    plans = cases()
    with output.open("x", encoding="utf-8") as out, ThreadPoolExecutor(
        max_workers=5
    ) as pool:
        for index, (mode, warm, order) in enumerate(plans):
            salt = f"extensions-20261102-{tag}-{index:03d}"
            warmup = post(warm, salt) if warm else None
            background = None
            if mode == "background":
                background = pool.submit(post, "A", salt + "-background", 64)
                time.sleep(0.030)

            tokens = 16 if mode == "long_output" else 1
            start = Event()
            futures = {
                label: pool.submit(probe, label, salt, tokens, pos * 0.010, start)
                for pos, label in enumerate(order)
            }
            start.set()
            probes = {label: future.result() for label, future in futures.items()}
            record = {
                "trial": index,
                "tag": tag,
                "mode": mode,
                "salt": salt,
                "warm": warm,
                "send_order": order,
                "warmup": warmup,
                "background": background.result() if background else None,
                "probes": probes,
            }
            out.write(json.dumps(record, ensure_ascii=False) + "\n")
            out.flush()
            print(
                f"{index + 1}/{len(plans)} mode={mode} warm={warm} "
                f"order={''.join(order)}",
                flush=True,
            )


if __name__ == "__main__":
    main(Path(sys.argv[1]), sys.argv[2])

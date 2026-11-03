"""Send balanced four-probe trials through the local response-release proxy."""

import json
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
from urllib.request import Request, urlopen

from cache_order_pilot import MODEL, PROMPTS, post as warmup_post


URL = "http://127.0.0.1:8766/v1/completions"
LABELS = ("A", "B", "C", "D")
MODES = ("direct", "bos4", "d100", "d250", "slot1050", "slot1200")


def post(label: str, salt: str, group: str, mode: str, delay: float, start: Event,
         tokens: int = 16, prompt: str | None = None, model: str = MODEL) -> dict:
    start.wait()
    if delay:
        time.sleep(delay)
    payload = {
        "model": model,
        "prompt": PROMPTS[label] if prompt is None else prompt,
        "cache_salt": salt,
        "max_tokens": tokens,
        "min_tokens": tokens,
        "temperature": 0,
        "stream": False,
    }
    request = Request(
        URL,
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "X-Pilot-Group": group,
            "X-Pilot-Mode": mode,
            "X-Pilot-Label": label,
        },
    )
    sent_ns = time.perf_counter_ns()
    with urlopen(request, timeout=60) as response:
        body = response.read()
        status = response.status
    received_ns = time.perf_counter_ns()
    data = json.loads(body)
    if status != 200:
        raise RuntimeError(f"HTTP {status}: {data}")
    usage = data["usage"]
    details = usage.get("prompt_tokens_details") or {}
    return {
        "sent_ns": sent_ns,
        "received_ns": received_ns,
        "http_status": status,
        "request_id": data["id"],
        "prompt_tokens": usage["prompt_tokens"],
        "cached_tokens_reported": details.get("cached_tokens"),
        "completion_tokens": usage["completion_tokens"],
    }


def plan(repeats: int, modes: tuple[str, ...], controls: int = 4,
         seed: int | None = None) -> list[tuple[str, str | None, list[str]]]:
    rng = random.Random(20261106 + repeats if seed is None else seed)
    cases = []
    for mode in modes:
        for warm in LABELS:
            for position in range(4):
                for _ in range(repeats):
                    cold = [label for label in LABELS if label != warm]
                    rng.shuffle(cold)
                    cases.append((mode, warm, cold[:position] + [warm] + cold[position:]))
        for _ in range(controls):
            order = list(LABELS)
            rng.shuffle(order)
            cases.append((mode, None, order))
    rng.shuffle(cases)
    return cases


def main(output: Path, tag: str, repeats: int, modes: tuple[str, ...],
         tokens: int = 16, controls: int = 4, seed: int | None = None,
         prompts: dict[str, str] | None = None, model: str = MODEL) -> None:
    cases = plan(repeats, modes, controls, seed)
    with output.open("x", encoding="utf-8") as out, ThreadPoolExecutor(
        max_workers=4
    ) as pool:
        for index, (mode, warm, order) in enumerate(cases):
            salt = f"bos-{tag}-{index:04d}"
            group = salt
            warmup = warmup_post(warm, salt, prompt=prompts[warm] if prompts else None,
                                 model=model) if warm else None
            start = Event()
            futures = {
                label: pool.submit(post, label, salt, group, mode, pos * 0.010, start,
                                   tokens, prompts[label] if prompts else None, model)
                for pos, label in enumerate(order)
            }
            start.set()
            probes = {label: future.result() for label, future in futures.items()}
            out.write(json.dumps({
                "trial": index,
                "mode": mode,
                "warm": warm,
                "salt": salt,
                "group": group,
                "send_order": order,
                "output_tokens": tokens,
                "case_seed": 20261106 + repeats if seed is None else seed,
                "warmup": warmup,
                "probes": probes,
            }, ensure_ascii=False) + "\n")
            out.flush()
            print(
                f"{index + 1}/{len(cases)} mode={mode} warm={warm} "
                f"send={''.join(order)}",
                flush=True,
            )


if __name__ == "__main__":
    selected = tuple(sys.argv[4].split(",")) if len(sys.argv) > 4 else MODES
    if not selected or any(mode not in MODES for mode in selected):
        raise SystemExit("unknown policy mode")
    main(Path(sys.argv[1]), sys.argv[2], int(sys.argv[3]), selected,
         int(sys.argv[5]) if len(sys.argv) > 5 else 16,
         int(sys.argv[6]) if len(sys.argv) > 6 else 4,
         int(sys.argv[7]) if len(sys.argv) > 7 else None,
         json.loads(Path(sys.argv[8]).read_text()) if len(sys.argv) > 8 else None,
         sys.argv[9] if len(sys.argv) > 9 else MODEL)

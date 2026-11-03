"""Small local probe for completion order after controlled prefix warming."""

import json
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
from urllib.request import Request, urlopen


URL = "http://127.0.0.1:8765/v1/completions"
MODEL = "Qwen/Qwen2.5-7B-Instruct"
BASE = (
    "This controlled prefix is identical in length across probes and carries "
    "no private data. "
) * 36 + "Reply with one word: ready"
PROMPTS = {label: f"{label}\n{BASE}" for label in ("A", "B", "C", "D")}
STAGGER_S = 0.010


def post(label: str, salt: str, max_tokens: int = 1, prompt: str | None = None,
         model: str = MODEL) -> dict:
    payload = {
        "model": model,
        "prompt": PROMPTS[label] if prompt is None else prompt,
        "cache_salt": salt,
        "max_tokens": max_tokens,
        "temperature": 0,
        "stream": False,
    }
    if max_tokens > 1:
        payload["min_tokens"] = max_tokens
    request = Request(
        URL,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    sent_ns = time.perf_counter_ns()
    with urlopen(request, timeout=30) as response:
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
        "finish_reason": data["choices"][0]["finish_reason"],
    }


def delayed_probe(label: str, salt: str, delay_s: float, start: Event) -> dict:
    start.wait()
    if delay_s:
        time.sleep(delay_s)
    return post(label, salt)


def main(output: Path, repeat: bool = False) -> None:
    cases = [
        (warm, first)
        for warm in ("A", "B")
        for first in ("A", "B")
        for _ in range(6)
    ] + [(None, first) for first in ("A", "B") for _ in range(6)]
    random.Random(20261103 if repeat else 20261102).shuffle(cases)

    with output.open("x", encoding="utf-8") as out, ThreadPoolExecutor(
        max_workers=2
    ) as pool:
        for index, (warm, first) in enumerate(cases):
            suffix = "repeat-" if repeat else ""
            salt = f"order-pilot-20261102-{suffix}{index:03d}"
            warmup = post(warm, salt) if warm else None
            start = Event()
            futures = {
                label: pool.submit(
                    delayed_probe,
                    label,
                    salt,
                    0 if label == first else STAGGER_S,
                    start,
                )
                for label in ("A", "B")
            }
            start.set()
            probes = {label: future.result() for label, future in futures.items()}
            record = {
                "trial": index,
                "salt": salt,
                "warm": warm,
                "intended_first": first,
                "warmup": warmup,
                "probes": probes,
            }
            out.write(json.dumps(record, ensure_ascii=False) + "\n")
            out.flush()
            print(f"{index + 1}/{len(cases)} warm={warm} first={first}", flush=True)


if __name__ == "__main__":
    main(Path(sys.argv[1]), repeat=len(sys.argv) > 2 and sys.argv[2] == "repeat")

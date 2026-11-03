"""One cache-isolated two-tenant case on a fresh local vLLM backend."""

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event

from bos_pilot import post as b_post
from cache_order_pilot import post as a_post


def victim(label, salt, prompt, offset_ms, start):
    start.wait()
    if offset_ms:
        time.sleep(offset_ms / 1000)
    return a_post(label, salt, max_tokens=16, prompt=prompt)


def main(cases_file, index, salts_file, prompts_file, output):
    case = json.loads(cases_file.read_text())["cases"][index]
    assert case["index"] == index
    salts = json.loads(salts_file.read_text())
    assert salts["tenant_A"] != salts["tenant_B"]
    prompts = json.loads(prompts_file.read_text())
    condition = case["condition"]
    preparation_label = "A" if condition in ("warm", "other_cold") else "D"
    preparation = a_post(preparation_label, salts["tenant_A"],
                         prompt=prompts[preparation_label])
    time.sleep(.250)
    target_label = None if condition == "absent" else (
        "D" if condition == "other_cold" else "A")
    group = f"offset-{index:02d}"
    start = Event()
    with ThreadPoolExecutor(max_workers=5) as pool:
        target = (pool.submit(victim, target_label, salts["tenant_A"],
                              prompts[target_label], case["victim_offset_ms"], start)
                  if target_label else None)
        probes = {label: pool.submit(b_post, label, salts["tenant_B"],
                                    group, "direct", position * .010,
                                    start, 16, prompts[label])
                  for position, label in enumerate(case["send_order"])}
        start.set()
        b = {label: future.result() for label, future in probes.items()}
        a = target.result() if target else None
    row = {**case, "group": group, "a_salt": salts["tenant_A"],
           "b_salt": salts["tenant_B"], "preparation": preparation,
           "victim_target": a, "probes": b, "mode": "direct"}
    with output.open("x") as out:
        json.dump(row, out, indent=2)
        out.write("\n")
    print(f"case {index:02d}: {condition}, offset {case['victim_offset_ms']} ms, B {''.join(case['send_order'])}")


if __name__ == "__main__":
    main(Path(sys.argv[1]), int(sys.argv[2]), Path(sys.argv[3]),
         Path(sys.argv[4]), Path(sys.argv[5]))

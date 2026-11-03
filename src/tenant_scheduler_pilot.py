"""Two synthetic tenants with disjoint salts and one shared vLLM scheduler."""

import json
import random
import secrets
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event

from bos_pilot import post as b_post
from cache_order_pilot import post as a_post


def plan(pairs, controls, seed):
    rng = random.Random(seed)
    matched = []
    for pair in range(pairs):
        order = list("ABCD")
        rng.shuffle(order)
        conditions = ["warm", "cold"]
        rng.shuffle(conditions)
        matched.extend((pair, condition, order) for condition in conditions)
    control_positions = set(rng.sample(range(pairs + 1), controls))
    out = []
    for pair in range(pairs + 1):
        if pair in control_positions:
            order = list("ABCD")
            rng.shuffle(order)
            out.append((None, "absent", order))
        if pair < pairs:
            out.extend(matched[2 * pair:2 * pair + 2])
    return out


def victim_target(salt, prompt, start):
    start.wait()
    time.sleep(.015)
    return a_post("A", salt, max_tokens=16, prompt=prompt)


def main(output, tag, pairs, controls, seed, prompts, mode, salt_scope="fresh_group"):
    cases = plan(pairs, controls, seed)
    fixed_salts = (secrets.token_hex(32), secrets.token_hex(32))
    with output.open("x") as out, ThreadPoolExecutor(max_workers=5) as pool:
        for index, (pair, condition, order) in enumerate(cases):
            a_salt, b_salt = (fixed_salts if salt_scope == "fixed_user" else
                              (secrets.token_hex(32), secrets.token_hex(32)))
            case_prompts = ({label: f"Case {index:03d}\n{prompt}" for label, prompt in prompts.items()}
                            if salt_scope == "fixed_user" else prompts)
            expected_tokens = 554 if salt_scope == "fixed_user" else 548
            prep_label = "A" if condition == "warm" else "D"
            preparation = a_post(prep_label, a_salt, prompt=case_prompts[prep_label])
            time.sleep(.250)
            group = f"tenant-{tag}-{index:03d}"
            start = Event()
            victim = (pool.submit(victim_target, a_salt, case_prompts["A"], start)
                      if condition != "absent" else None)
            probes = {label: pool.submit(b_post, label, b_salt, group, mode,
                                        position * .010, start, 16, case_prompts[label])
                      for position, label in enumerate(order)}
            start.set()
            b = {label: future.result() for label, future in probes.items()}
            a = victim.result() if victim else None
            out.write(json.dumps({"trial": index, "pair": pair,
                                  "condition": condition, "mode": mode,
                                  "group": group, "a_salt": a_salt,
                                  "b_salt": b_salt, "salt_scope": salt_scope,
                                  "prompt_tokens_expected": expected_tokens,
                                  "send_order": order,
                                  "case_seed": seed, "preparation": preparation,
                                  "victim_target": a, "probes": b}) + "\n")
            out.flush()
            print(f"{index+1}/{len(cases)} pair={pair} {condition} B={''.join(order)}", flush=True)


if __name__ == "__main__":
    main(Path(sys.argv[1]), sys.argv[2], int(sys.argv[3]), int(sys.argv[4]),
         int(sys.argv[5]), json.loads(Path(sys.argv[6]).read_text()), sys.argv[7],
         sys.argv[8] if len(sys.argv) > 8 else "fresh_group")

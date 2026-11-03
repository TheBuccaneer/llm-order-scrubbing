"""Opt-in read-only vLLM scheduler trace for two explanatory groups."""

import os


if (trace_file := os.environ.get("SCHED_TRACE_FILE")):
    import json
    import time

    from vllm.v1.core.sched.scheduler import Scheduler

    original_schedule = Scheduler.schedule

    def traced_schedule(self):
        result = original_schedule(self)
        if result.num_scheduled_tokens:
            row = {"time_ns": time.monotonic_ns(), "requests": []}
            for request_id, tokens in result.num_scheduled_tokens.items():
                request = self.requests[request_id]
                before = request.num_computed_tokens - tokens
                row["requests"].append({
                    "request_id": request_id,
                    "scheduled_tokens": tokens,
                    "computed_before": before,
                    "prompt_tokens": request.num_prompt_tokens,
                    "stage": "prefill" if before < request.num_prompt_tokens else "decode",
                })
            with open(trace_file, "a", encoding="utf-8") as out:
                out.write(json.dumps(row) + "\n")
        return result

    Scheduler.schedule = traced_schedule

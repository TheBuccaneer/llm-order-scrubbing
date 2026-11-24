"""Loopback-only HTTP adapter for the bounded two-tenant GPU prototype.

An admin declares one public five-slot cohort. Each tenant submits only its
own slot and receives only its own completion. All engine/CUDA calls stay
on the main thread. This is a local research protocol, not production auth.
"""

import argparse
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import os
from pathlib import Path
import re
import secrets
from threading import Condition, Event, Thread
import time
import traceback

from protected_prefill_pilot import Pilot, gpu_canonical_copy


SLOTS = [("A", "victim", "A"), ("B", "0", "A"), ("B", "1", "B"),
         ("B", "2", "C"), ("B", "3", "D")]
MODES = {"protected", "release1240", "ignore_hits", "direct"}


@dataclass
class Pending:
    tenant: str
    label: str
    accepted_ns: int
    event: Event = field(default_factory=Event)
    status: int = 200
    body: dict = field(default_factory=dict)

    def finish(self, status, body):
        self.status, self.body = status, body
        self.event.set()


class State:
    def __init__(self, pilot, keys):
        self.pilot, self.keys = pilot, keys
        self.cv = Condition()
        self.cohort = None
        self.preparation = None
        self.reset_requested = None
        self.busy = False
        self.fresh_setup = False
        self.prepared = False


class Handler(BaseHTTPRequestHandler):
    server_version = "ProtectedPrefillResearch/1"

    def log_message(self, *_):
        pass

    def send_json(self, status, body):
        data = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        self.send_json(200, {"status": "ready"}) if self.path == "/health" else self.send_json(404, {"error": "not found"})

    def do_POST(self):
        state = self.server.state
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 65536:
                raise ValueError("JSON request body required; maximum 64 KiB")
            body = json.loads(self.rfile.read(size))
            key = self.headers.get("X-Tenant-Token", "")
            if self.path == "/reset":
                if not secrets.compare_digest(key, state.keys["admin"]):
                    self.send_json(403, {"error": "admin token required"}); return
                pending = Pending("admin", "reset", time.perf_counter_ns())
                with state.cv:
                    if state.busy or state.cohort is not None:
                        self.send_json(409, {"error": "reset requires idle engine"}); return
                    state.reset_requested, state.busy = pending, True
                    state.cv.notify()
                pending.event.wait()
                self.send_json(pending.status, pending.body)
                return
            if self.path == "/cohort":
                if not secrets.compare_digest(key, state.keys["admin"]):
                    self.send_json(403, {"error": "admin token required"}); return
                cid, mode = body["id"], body["mode"]
                intake = float(body.get("intake_ms", 250))
                windows = body.get("windows_ms", {"A": [0, 230], "B": [230, 890]})
                join = float(body.get("join_ms", 940))
                if (not isinstance(cid, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", cid)
                    or mode not in MODES or not math.isfinite(intake) or not 50 <= intake <= 5000
                    or not math.isfinite(join) or not 0 < join <= 10000
                    or set(windows) != {"A", "B"}):
                    raise ValueError("invalid bounded cohort configuration")
                ordered = sorted((float(v[0]), float(v[1])) for v in windows.values())
                previous = 0
                for start, end in ordered:
                    if not all(map(math.isfinite, (start, end))) or start < previous or end <= start:
                        raise ValueError("invalid public tenant windows")
                    previous = end
                if join <= previous:
                    raise ValueError("join must follow the last window")
                with state.cv:
                    if state.busy or state.cohort is not None or (state.pilot.output/f"{cid}.json").exists():
                        self.send_json(409, {"error": "busy or reused cohort id"}); return
                    if not state.fresh_setup or not state.prepared:
                        self.send_json(409, {"error": "reset and one standalone A preparation required"}); return
                    deadline = time.perf_counter_ns()+int(intake*1e6)
                    state.cohort = dict(id=cid, mode=mode, deadline_ns=deadline,
                                        windows_ms=windows, join_ms=join, pending={})
                    state.fresh_setup = False
                    state.cv.notify()
                self.send_json(200, dict(id=cid, mode=mode, intake_deadline_ns=deadline,
                                        windows_ms=windows, join_ms=join,
                                        slots=[dict(tenant=t, slot=s, label=l) for t,s,l in SLOTS]))
                return
            if self.path != "/v1/completions":
                self.send_json(404, {"error": "not found"}); return
            tenant = next((t for t in ("A", "B") if secrets.compare_digest(key, state.keys[t])), None)
            if tenant is None:
                self.send_json(403, {"error": "tenant token required"}); return
            label = body["label"]
            if label not in state.pilot.prompts or ("prompt" in body and body["prompt"] != state.pilot.prompts[label]):
                raise ValueError("only the exact declared synthetic document prompts are supported")
            expected_tokens = 1 if body.get("preparation") else 16
            if body.get("stream") or body.get("max_tokens", expected_tokens) != expected_tokens:
                raise ValueError("only non-streaming one-token preparation / 16-token cohort output is supported")
            if (body.get("temperature",0)!=0 or body.get("min_tokens",expected_tokens)!=expected_tokens
                or body.get("stop") or body.get("stop_token_ids")):
                raise ValueError("fixed greedy output without stop rules is required")
            pending = Pending(tenant, label, time.perf_counter_ns())
            with state.cv:
                if body.get("preparation"):
                    if (tenant != "A" or state.busy or state.cohort is not None
                        or not state.fresh_setup or state.prepared):
                        self.send_json(409, {"error": "preparation requires idle tenant A"}); return
                    state.preparation, state.busy = pending, True
                    state.cv.notify()
                else:
                    c = state.cohort
                    slot = str(body["slot"])
                    expected = {(t, s): l for t,s,l in SLOTS}
                    if (c is None or state.busy or body.get("cohort_id") != c["id"]
                        or time.perf_counter_ns() >= c["deadline_ns"]):
                        self.send_json(409, {"error": "no open declared cohort"}); return
                    if expected.get((tenant, slot)) != label or (tenant,slot) in c["pending"]:
                        self.send_json(409, {"error": "invalid or already submitted own slot"}); return
                    c["pending"][(tenant,slot)] = pending
            pending.event.wait()
            self.send_json(pending.status, pending.body)
        except (ValueError, KeyError, TypeError, IndexError) as error:
            self.send_json(400, {"error": str(error)})


def execute(state, cohort=None, preparation=None):
    pilot = state.pilot
    pending = ([preparation] if preparation else
               [cohort["pending"][(t,s)] for t,s,_ in SLOTS])
    submitted = []
    for p in pending:
        record = pilot.add(p.tenant, p.label, f"http-prototype-private-{p.tenant}",
                           tokens=1 if preparation else 16,
                           ignore=bool(cohort and cohort["mode"] == "ignore_hits" and p.tenant == "A"))
        record["engine_submitted_ns"] = record["sent_ns"]
        record["sent_ns"] = p.accepted_ns
        submitted.append(record)
    owners = {r["external_id"]: p for r,p in zip(submitted,pending)}
    def deliver(record):
        owners[record["external_id"]].finish(200, dict(id=record["external_id"], object="text_completion",
            choices=[dict(index=0, text=record["text"], finish_reason=record["finish_reason"])],
            usage=dict(prompt_tokens=record["prompt_tokens"], completion_tokens=len(record["token_ids"]))))
    if cohort and cohort["mode"] == "protected":
        pilot.scheduler.configure_cohort(cohort["deadline_ns"], cohort["windows_ms"], cohort["join_ms"],
            [r["internal_id"] for r in submitted], normalizer=pilot.normalize)
    records = pilot.drain(submitted, 1240 if cohort and cohort["mode"] == "release1240" else 0,
                          on_release=deliver)
    if preparation:
        state.prepared = True
    if cohort:
        protected = pilot.scheduler.end_cohort() if cohort["mode"] == "protected" else None
        log = dict(id=cohort["id"], mode=cohort["mode"], public_intake_deadline_ns=cohort["deadline_ns"],
                   requests=list(records.values()), protected=protected)
        with (pilot.output/f"{cohort['id']}.json").open("x") as fp:
            json.dump(log,fp,indent=2); fp.write("\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--port", type=int, default=8770)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    keys = {role: secrets.token_hex(24) for role in ("admin", "A", "B")}
    key_path = args.output/"local-tokens.json"
    fd = os.open(key_path, os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600)
    with os.fdopen(fd,"w") as fp: json.dump(keys,fp)
    state = State(Pilot(args.output), keys)
    server = ThreadingHTTPServer(("127.0.0.1",args.port), Handler)
    server.state = state
    Thread(target=server.serve_forever, daemon=True).start()
    print(f"READY http://127.0.0.1:{args.port}; local credentials: {key_path}",flush=True)
    try:
        while True:
            with state.cv:
                while state.preparation is None and state.cohort is None and state.reset_requested is None:
                    state.cv.wait()
                prep, cohort, reset = state.preparation, state.cohort, state.reset_requested
                if cohort:
                    left = (cohort["deadline_ns"]-time.perf_counter_ns())/1e9
                    if left > 0:
                        state.cv.wait(left); continue
                    state.busy = True
                state.preparation = None
                state.reset_requested = None
            pending = [reset] if reset else ([prep] if prep else list(cohort["pending"].values()))
            if reset:
                try:
                    plan = state.pilot.pool.reset()
                    plan.update(copy_pairs=[], requests={}, block_size=state.pilot.pool.block_size)
                    state.pilot.engine.collective_rpc(gpu_canonical_copy, args=(plan,))
                    state.fresh_setup, state.prepared = True, False
                    reset.finish(200, {"status": "reset"})
                except Exception:
                    reset.finish(500, {"error": "reset failed; restart server"})
                    raise
            elif cohort and len(pending) != len(SLOTS):
                for p in pending: p.finish(409,{"error":"public cohort intake closed incomplete"})
            else:
                try:
                    execute(state, cohort, prep)
                except Exception:
                    for p in pending: p.finish(500,{"error":"engine phase contract failed; restart server"})
                    (args.output/"fatal-engine-error.txt").write_text(traceback.format_exc())
                    raise
            with state.cv:
                state.cohort, state.busy = None, False
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown(); server.server_close()


if __name__ == "__main__":
    main()

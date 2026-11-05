"""Local completion-response gate for the four-request BOS feasibility pilot."""

import json
import random
import secrets
import sys
import threading
import time
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import Request, urlopen


BACKEND = "http://127.0.0.1:8765/v1/completions"
MODES = {"direct": None, "bos4": None, "d100": 100, "d250": 250,
         "slot1050": None, "slot1200": None}
RELEASE_GAP_S = 0.002
DEADLINE_ADVANCE_MS = 10
SLOT_MS_BY_MODE = {"slot1050": 1050, "slot1200": 1200}


@dataclass
class Job:
    group: str
    mode: str
    label: str
    public_body: bytes
    backend_received_ns: int
    arrival_ns: int
    request_id: str
    cached_tokens: int | None
    release: threading.Event = field(default_factory=threading.Event)
    written: threading.Event = field(default_factory=threading.Event)
    batch: int = 0
    batch_size: int = 0
    release_position: int = 0
    flush_reason: str = ""
    shuffle_seed: int | None = None
    slot_anchor_ns: int | None = None


@dataclass
class Pending:
    batch: int = 0
    jobs: list[Job] = field(default_factory=list)
    timer: threading.Timer | None = None
    first_arrival_ns: int | None = None
    slot_expired: bool = False


class Gate:
    def __init__(self, output: Path):
        self.lock = threading.Lock()
        self.log_lock = threading.Lock()
        self.pending: dict[tuple[str, str], Pending] = {}
        self.log = output.open("x", encoding="utf-8")

    def note_arrival(self, group: str, mode: str, arrival_ns: int) -> None:
        if mode not in SLOT_MS_BY_MODE:
            return
        key = (group, mode)
        with self.lock:
            state = self.pending.setdefault(key, Pending())
            if state.first_arrival_ns is None:
                state.first_arrival_ns = arrival_ns
                state.timer = threading.Timer(
                    SLOT_MS_BY_MODE[mode] / 1000, self.flush,
                    args=(key, state.batch, "slot")
                )
                state.timer.daemon = True
                state.timer.start()

    def submit(self, job: Job) -> None:
        if job.mode == "direct":
            job.batch_size = 1
            job.release_position = 1
            job.flush_reason = "direct"
            job.release.set()
            return

        key = (job.group, job.mode)
        with self.lock:
            state = self.pending.setdefault(key, Pending())
            if job.mode in SLOT_MS_BY_MODE:
                job.slot_anchor_ns = state.first_arrival_ns
                if state.slot_expired:
                    job.batch_size = 1
                    job.release_position = 1
                    job.flush_reason = "late_fallback"
                    job.release.set()
                    return
            job.batch = state.batch
            state.jobs.append(job)
            deadline_ms = MODES[job.mode]
            if len(state.jobs) == 1 and deadline_ms is not None:
                state.timer = threading.Timer(
                    (deadline_ms - DEADLINE_ADVANCE_MS) / 1000,
                    self.flush, args=(key, state.batch, "deadline")
                )
                state.timer.daemon = True
                state.timer.start()
            if len(state.jobs) == 4 and job.mode not in SLOT_MS_BY_MODE:
                self._flush_locked(key, state, "full")
        job.release.wait()

    def flush(self, key: tuple[str, str], batch: int, reason: str) -> None:
        with self.lock:
            state = self.pending.get(key)
            if state is not None and state.batch == batch:
                if state.jobs:
                    self._flush_locked(key, state, reason)
                elif key[1] in SLOT_MS_BY_MODE:
                    state.slot_expired = True

    def _flush_locked(self, key: tuple[str, str], state: Pending, reason: str) -> None:
        if state.timer is not None:
            state.timer.cancel()
            state.timer = None
        jobs = state.jobs
        state.jobs = []
        state.batch += 1
        if key[1] in SLOT_MS_BY_MODE:
            state.slot_expired = True
        seed = secrets.randbits(64)
        random.Random(seed).shuffle(jobs)
        for position, job in enumerate(jobs, 1):
            job.batch_size = len(jobs)
            job.release_position = position
            job.flush_reason = reason
            job.shuffle_seed = seed
        threading.Thread(
            target=self._release_batch, args=(jobs,), daemon=True,
            name=f"release-{key[0]}-{state.batch - 1}",
        ).start()

    @staticmethod
    def _release_batch(jobs: list[Job]) -> None:
        for position, job in enumerate(jobs):
            if position:
                time.sleep(RELEASE_GAP_S)
            job.release.set()
            job.written.wait(timeout=30)

    def record(self, data: dict) -> None:
        with self.log_lock:
            self.log.write(json.dumps(data, ensure_ascii=False) + "\n")
            self.log.flush()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_POST(self) -> None:
        if self.path != "/v1/completions":
            self.send_error(404)
            return
        group = self.headers.get("X-Pilot-Group", "")
        mode = self.headers.get("X-Pilot-Mode", "")
        label = self.headers.get("X-Pilot-Label", "")
        if not group or mode not in MODES or label not in "ABCD":
            self.send_error(400, "invalid pilot headers")
            return
        arrival_ns = time.perf_counter_ns()
        self.server.gate.note_arrival(group, mode, arrival_ns)
        body = self.rfile.read(int(self.headers["Content-Length"]))
        try:
            upstream = Request(
                BACKEND, data=body, headers={"Content-Type": "application/json"}
            )
            with urlopen(upstream, timeout=60) as response:
                backend_body = response.read()
                backend_status = response.status
            backend_received_ns = time.perf_counter_ns()
            payload = json.loads(backend_body)
            if backend_status != 200:
                raise RuntimeError(f"backend HTTP {backend_status}")
            details = payload["usage"].get("prompt_tokens_details") or {}
            cached_tokens = details.get("cached_tokens")
            payload["usage"].pop("prompt_tokens_details", None)
            public_body = json.dumps(payload, ensure_ascii=False,
                                     separators=(",", ":")).encode()
            job = Job(
                group, mode, label, public_body, backend_received_ns,
                arrival_ns, payload["id"], cached_tokens,
            )
            self.server.gate.submit(job)
            release_ns = time.perf_counter_ns()
            try:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(public_body)))
                self.end_headers()
                self.wfile.write(public_body)
                self.wfile.flush()
                sent_ns = time.perf_counter_ns()
            finally:
                job.written.set()
            self.server.gate.record({
                "group": group, "mode": mode, "label": label,
                "request_id": job.request_id,
                "arrival_ns": arrival_ns,
                "backend_received_ns": backend_received_ns,
                "release_ns": release_ns,
                "sent_ns": sent_ns,
                "added_wait_ms": (release_ns - backend_received_ns) / 1e6,
                "cached_tokens_reported": job.cached_tokens,
                "cache_details_removed": True,
                "batch": job.batch,
                "batch_size": job.batch_size,
                "release_position": job.release_position,
                "flush_reason": job.flush_reason,
                "shuffle_seed": job.shuffle_seed,
                "deadline_advance_ms": DEADLINE_ADVANCE_MS if mode in ("d100", "d250") else None,
                "slot_anchor_ns": job.slot_anchor_ns,
                "slot_offset_ms": (
                    (release_ns - job.slot_anchor_ns) / 1e6
                    if job.slot_anchor_ns is not None else None
                ),
            })
        except Exception as exc:
            self.server.gate.record({
                "group": group, "mode": mode, "label": label,
                "error": repr(exc), "arrival_ns": arrival_ns,
            })
            try:
                self.send_error(502, "backend or proxy error")
            except OSError:
                pass

    def log_message(self, format: str, *args: object) -> None:
        return


def main(output: Path) -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 8766), Handler)
    server.daemon_threads = True
    server.gate = Gate(output)
    print("proxy ready 127.0.0.1:8766", flush=True)
    try:
        server.serve_forever(poll_interval=0.2)
    finally:
        server.server_close()
        server.gate.log.close()


if __name__ == "__main__":
    main(Path(sys.argv[1]))

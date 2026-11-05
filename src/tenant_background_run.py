"""Run exactly64 precommitted fresh-backend cases, no retries or model fitting."""
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parents[1]


def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path,obj):
    with path.open("x") as fp: json.dump(obj,fp,indent=2); fp.write("\n")


def stop(process):
    if process is None: return
    try: os.killpg(process.pid,signal.SIGTERM)
    except ProcessLookupError: pass
    try: process.wait(timeout=20)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid,signal.SIGKILL); process.wait(timeout=10)


def main(folder):
    plan=json.loads((folder/"protocol.json").read_text())
    commit=json.loads((folder/"commit.json").read_text())
    for name,h in plan["source_sha256"].items(): assert digest(ROOT/name)==h,name
    for name,h in plan["artifact_sha256"].items(): assert digest(folder/name)==h,name
    assert commit["protocol_sha256"]==digest(folder/"protocol.json")
    rel=str((folder/"protocol.json").relative_to(ROOT))
    committed=subprocess.check_output(["git","show",f"{commit['commit']}:{rel}"],cwd=ROOT)
    assert hashlib.sha256(committed).hexdigest()==digest(folder/"protocol.json")
    write(folder/"run-start.json",dict(utc=datetime.now(timezone.utc).isoformat(),
          protocol_sha256=digest(folder/"protocol.json"),commit=commit["commit"]))
    env=dict(os.environ,HF_HUB_OFFLINE="1",TRANSFORMERS_OFFLINE="1",
             TMPDIR=str(folder/"runtime"),XDG_CACHE_HOME=str(folder/"runtime"),
             TRITON_CACHE_DIR=str(folder/"runtime/triton"))
    (folder/"runtime").mkdir()
    for case in plan["cases"]:
        index=case["index"]; run=folder/f"case-{index:02d}"; run.mkdir()
        write(run/"start.json",dict(utc=datetime.now(timezone.utc).isoformat(),case=case))
        server=proxy=None; status=dict(index=index,backend_ready=False,client_returncode=None)
        try:
            with (run/"server.log").open("x") as log:
                server=subprocess.Popen(plan["server_command"],stdout=log,stderr=log,env=env,start_new_session=True,cwd=ROOT)
            status["server_pid"]=server.pid
            for _ in range(90):
                try:
                    with urlopen("http://127.0.0.1:8765/health",timeout=1) as response:
                        if response.status==200: status["backend_ready"]=True; break
                except Exception: pass
                if server.poll() is not None: break
                time.sleep(1)
            if not status["backend_ready"]: raise RuntimeError("fresh backend not ready within90 seconds")
            status["backend_ready_ns"]=time.perf_counter_ns()
            with (run/"proxy.log").open("x") as log:
                proxy=subprocess.Popen([sys.executable,str(ROOT/"src/order_release_proxy.py"),str(run/"proxy.jsonl")],stdout=log,stderr=log,start_new_session=True,cwd=ROOT)
            time.sleep(1)
            with (run/"client.log").open("x") as log:
                result=subprocess.run([sys.executable,str(ROOT/"src/tenant_background_case.py"),str(folder),str(index)],stdout=log,stderr=log,cwd=ROOT,timeout=180)
            status["client_returncode"]=result.returncode
        except Exception as error: status["error"]=repr(error)
        finally:
            stop(proxy); stop(server)
            status.update(backend_stopped_ns=time.perf_counter_ns(),finished_utc=datetime.now(timezone.utc).isoformat())
            write(run/"status.json",status)
        print("CASE",index,case["condition"],"recorded",status["client_returncode"],flush=True)
    from tenant_background_analysis import analyze
    analyze(folder)
    print("COMPLETE",folder,flush=True)


if __name__=="__main__": main(Path(sys.argv[1]).resolve())

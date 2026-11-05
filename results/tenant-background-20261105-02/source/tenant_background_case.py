"""One C2 HTTP case; unchanged A/B clients plus one fixed streaming C load."""
import json
from pathlib import Path
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from urllib.request import Request, urlopen

from bos_pilot import post as b_post
from cache_order_pilot import post as a_post, MODEL, URL
from tenant_offset_case import victim


def guarded(function, *args):
    before=time.perf_counter_ns()
    try: return function(*args)
    except Exception as error:
        return dict(error=repr(error),call_started_ns=before,error_observed_ns=time.perf_counter_ns())


def background(salt, prompt, start):
    start.wait()
    body=dict(model=MODEL,prompt=prompt,cache_salt=salt,max_tokens=256,min_tokens=256,
              temperature=0,stream=True,stream_options={"include_usage":True})
    request=Request(URL,data=json.dumps(body).encode(),headers={"Content-Type":"application/json"})
    sent=time.perf_counter_ns(); events=[]; usage=None; rid=None; finish=None
    with urlopen(request,timeout=60) as response:
        status=response.status
        for line in response:
            if not line.startswith(b"data: "): continue
            value=line[6:].strip()
            if value==b"[DONE]": break
            item=json.loads(value); rid=item.get("id",rid)
            if item.get("usage"): usage=item["usage"]
            for choice in item.get("choices",[]):
                if choice.get("text"):
                    events.append(dict(received_ns=time.perf_counter_ns(),text_characters=len(choice["text"])))
                if choice.get("finish_reason"): finish=choice["finish_reason"]
    received=time.perf_counter_ns()
    return dict(sent_ns=sent,received_ns=received,http_status=status,request_id=rid,
                usage=usage,token_events=events,finish_reason=finish,
                prompt_label="B",planned_output_tokens=256)


def main(folder,index):
    plan=json.loads((folder/"protocol.json").read_text()); case=plan["cases"][index]
    salts=json.loads((folder/"salts.json").read_text())
    prompts=json.loads((folder/"prompts.json").read_text())
    condition=case["condition"]; prep_label="A" if condition in ("warm","other_cold") else "D"
    preparation=guarded(a_post,prep_label,salts["tenant_A"],1,prompts[prep_label])
    time.sleep(.250)
    label=None if condition=="absent" else ("D" if condition=="other_cold" else "A")
    group=f"background-{index:02d}"; start=Event(); c_start=Event()
    with ThreadPoolExecutor(max_workers=6) as pool:
        c=pool.submit(guarded,background,salts["tenant_C"],prompts["B"],c_start)
        a=pool.submit(guarded,victim,label,salts["tenant_A"],prompts[label],case["victim_offset_ms"],start) if label else None
        probes={label:pool.submit(guarded,b_post,label,salts["tenant_B"],group,"direct",
                    pos*.010,start,16,prompts[label]) for pos,label in enumerate(case["send_order"])}
        c_release=time.perf_counter_ns(); c_start.set()
        time.sleep(.100)
        group_release=time.perf_counter_ns(); start.set()
        b={label:f.result() for label,f in probes.items()}
        target=a.result() if a else None; load=c.result()
    row=dict(**case,group=group,a_salt=salts["tenant_A"],b_salt=salts["tenant_B"],
             c_salt=salts["tenant_C"],preparation=preparation,victim_target=target,
             probes=b,background=load,mode="direct",c_plan_release_ns=c_release,
             group_plan_release_ns=group_release)
    path=folder/f"case-{index:02d}"/"trial.json"
    with path.open("x") as fp: json.dump(row,fp,indent=2); fp.write("\n")
    print("COMPLETE",index,condition,flush=True)


if __name__=="__main__": main(Path(sys.argv[1]),int(sys.argv[2]))

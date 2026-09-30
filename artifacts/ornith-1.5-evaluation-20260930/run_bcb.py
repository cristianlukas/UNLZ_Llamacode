#!/usr/bin/env python3
"""Run the repository's fixed BigCodeBench-Hard-8 set against a local OpenAI endpoint."""
from __future__ import annotations
import argparse, json, re, statistics, subprocess, sys, tempfile, time
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
PACK = ROOT / "artifacts/bigcodebench-hard-ubuntu-8.json"
THINK = re.compile(r"<think>.*?</think>", re.I | re.S)
FENCE = re.compile(r"```(?:python|py)?\s*(.*?)```", re.I | re.S)

def req(url, payload, timeout):
    data=json.dumps(payload, ensure_ascii=False).encode()
    start=time.perf_counter()
    with urlopen(Request(url, data=data, headers={"Content-Type":"application/json"}), timeout=timeout) as r:
        response=json.loads(r.read())
    return response, (time.perf_counter()-start)*1000

def candidate_code(text):
    text=THINK.sub("", text).strip()
    blocks=FENCE.findall(text)
    return max(blocks, key=len).strip() if blocks else text

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--url", default="http://127.0.0.1:8038/v1/chat/completions")
    p.add_argument("--model", default="Swift-Qwen3.8-27B-Genesis-NVFP4-v4")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--budget", type=int, default=2048)
    p.add_argument("--max-tokens", type=int, default=6144)
    a=p.parse_args()
    corpus=json.loads(PACK.read_text())
    rows=[]
    for i,item in enumerate(corpus["items"],1):
        payload={"model":a.model,"messages":[
          {"role":"system","content":"Solve the programming task. Return only a complete Python implementation; do not explain."},
          {"role":"user","content":item["prompt"]}],
          "temperature":0.6,"top_p":0.95,"top_k":20,"min_p":0.0,
          "max_tokens":a.max_tokens,
          "chat_template_kwargs":{"enable_thinking":False},"stream":False}
        start=time.perf_counter()
        try:
            result, wall=req(a.url,payload,900)
            msg=result.get("choices",[{}])[0].get("message",{})
            text=str(msg.get("content", ""))
            code=candidate_code(text)
            with tempfile.TemporaryDirectory(prefix="lc-bcb-") as d:
                directory=Path(d); script=directory/"candidate.py"
                script.write_text(code+"\n\n"+item["tests"]+"\n",encoding="utf-8")
                cmd=["bwrap","--ro-bind","/","/","--dev","/dev","--proc","/proc",
                     "--tmpfs","/tmp","--tmpfs","/home","--tmpfs","/media","--tmpfs","/mnt",
                     "--dir","/mnt/work","--bind",d,"/mnt/work","--chdir","/mnt/work",
                     "--unshare-net","--unshare-pid","--die-with-parent",
                     sys.executable,"-I","/mnt/work/candidate.py"]
                try:
                    grade=subprocess.run(cmd,capture_output=True,text=True,timeout=45)
                    passed=grade.returncode==0
                    detail=(grade.stderr or grade.stdout).strip()[-1200:]
                except subprocess.TimeoutExpired:
                    passed=False; detail="grader timed out after 45s"
            rows.append({"id":item["id"],"transportOk":True,"wallMs":round(wall,2),"passed":passed,
                         "completionTokens":result.get("usage",{}).get("completion_tokens"),
                         "promptTokens":result.get("usage",{}).get("prompt_tokens"),
                         "reasoningTokens":result.get("usage",{}).get("completion_tokens_details",{}).get("reasoning_tokens"),
                         "code":code,"gradeDetail":detail,"rawContent":text[:12000]})
        except Exception as e:
            rows.append({"id":item["id"],"transportOk":False,"wallMs":round((time.perf_counter()-start)*1000,2),
                         "passed":False,"error":f"{type(e).__name__}: {e}"})
        print(f"{i}/{len(corpus['items'])} {item['id']} passed={rows[-1]['passed']} wallMs={rows[-1]['wallMs']}",flush=True)
    out={"benchmark":"BigCodeBench-Hard-8","pack":str(PACK.relative_to(ROOT)),"model":a.model,"url":a.url,
         "reasoning":"off","temperature":0.6,"topP":0.95,"topK":20,"maxTokens":a.max_tokens,
         "runs":len(rows),"transportOk":sum(r["transportOk"] for r in rows),"passed":sum(r["passed"] for r in rows),"rows":rows}
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
    print(f"score={out['passed']}/{out['runs']} transport={out['transportOk']}/{out['runs']} out={a.out}")
    return 0 if out["transportOk"]==out["runs"] else 2
if __name__=="__main__": raise SystemExit(main())

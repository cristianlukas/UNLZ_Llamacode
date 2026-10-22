#!/usr/bin/env python3
from __future__ import annotations
import copy, hashlib, json, os, pathlib, shutil, subprocess, time
ROOT=pathlib.Path("/media/cristian/7CFE1E0FFE1DC1F6/Users/cristian/Documents/LlamaCode")
ATTEMPT=ROOT/"artifacts/evaluacion-modelos-llamacode/Q-20261022-VF-ITERATION-31/attempts/flashnext-bcb2-python-alias-03"
SOURCE_RUNTIME=ROOT/"artifacts/evaluacion-modelos-llamacode/Q-20261021-VF-ITERATION-26/attempts/bcb-01/work/isolated-runtime"
RUNTIME=ATTEMPT/"work/isolated-runtime"
SOURCE_SUITE=SOURCE_RUNTIME/"data/LlamaCode/LlamaCode/benchmarks/custom/05c28394-11d0-41fe-a55f-b3cb69db9c15.json"
Q30_SUITE=ROOT/"artifacts/evaluacion-modelos-llamacode/Q-20261022-VF-ITERATION-30/attempts/flashnext-bcb2-outputcap-01/work/diagnostic-suite.json"
SUITE_ID="vf-q31-flashnext-repair-shell-python-03"
SUITE_NAME="VF FlashNext repair-shell compatibility diagnostic"
LOCK_TOKEN="fb13f0630f802012a3540c90520cf300"
PROMPT_ID="BigCodeBench/765"
def sha_bytes(b:bytes)->str:return hashlib.sha256(b).hexdigest()
def sha(path:pathlib.Path)->str:return sha_bytes(path.read_bytes())
def write_json(path:pathlib.Path,obj:object)->None:
 path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def main()->None:
 lock=json.loads((ROOT/"WORK_QUEUE.lock").read_text())
 if lock.get("token")!=LOCK_TOKEN:raise SystemExit("Lock changed; no preparation performed")
 if not SOURCE_SUITE.is_file() or not SOURCE_RUNTIME.is_dir() or not Q30_SUITE.is_file():raise SystemExit("Pinned local fixture/runtime missing")
 if RUNTIME.exists():raise SystemExit(f"Refusing to overwrite prepared runtime {RUNTIME}")
 source_bytes=SOURCE_SUITE.read_bytes();suite=json.loads(source_bytes)
 if sha_bytes(source_bytes)!="42771136b447b7b5619e04a1ea211f663222cd6752ca38d995083b5a4d207574":raise SystemExit("Pinned source suite hash changed")
 prompt=next((p for p in suite.get("prompts",[]) if p.get("id")==PROMPT_ID),None)
 if prompt is None or prompt.get("maxTokens")!=1200:raise SystemExit("Pinned prompt or original maxTokens changed")
 shutil.copytree(SOURCE_RUNTIME,RUNTIME,copy_function=shutil.copy2)
 variant={"id":SUITE_ID,"name":SUITE_NAME,"description":"One-prompt continuation of Q30 with the original acceptance and 2400-token cap. Only the isolated controller PATH gains python->python3.","source":"VF-20261019-01 / Q31; local pinned BCB fixture, no external download","prompts":[copy.deepcopy(prompt)]}
 variant["prompts"][0]["maxTokens"]=2400
 payload=(json.dumps(variant,ensure_ascii=False,indent=2)+"\n").encode()
 custom=RUNTIME/"data/LlamaCode/LlamaCode/benchmarks/custom";custom.mkdir(parents=True,exist_ok=True)
 (custom/f"{SUITE_ID}.json").write_bytes(payload)
 diag=ATTEMPT/"work/diagnostic-suite.json";diag.parent.mkdir(parents=True,exist_ok=True);diag.write_bytes(payload)
 shim_dir=ATTEMPT/"work/python-bin";shim_dir.mkdir(parents=True,exist_ok=True)
 shim=shim_dir/"python";shim.write_text("#!/bin/sh\nexec /usr/bin/python3 \"$@\"\n",encoding="utf-8");shim.chmod(0o755)
 env=os.environ.copy();env["PATH"]=str(shim_dir)+os.pathsep+env.get("PATH","")
 probe=subprocess.run(["sh","-c","python -c 'import sys; print(sys.executable)'"],env=env,capture_output=True,text=True,timeout=20)
 if probe.returncode!=0 or pathlib.Path(probe.stdout.strip()).resolve()!=pathlib.Path("/usr/bin/python3").resolve():raise SystemExit(f"Isolated shim failed CPU smoke: {probe.returncode} {probe.stdout!r} {probe.stderr!r}")
 q30=json.loads(Q30_SUITE.read_text(encoding="utf-8"))
 same_prompt=q30.get("prompts")==variant["prompts"]
 if not same_prompt:raise SystemExit("Q31 prompt/grader/maxTokens differs from Q30")
 receipt={"prepared_at_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"status":"prepared_no_model_no_gpu","lock_token":LOCK_TOKEN,"source_suite_sha256":sha(SOURCE_SUITE),"source_prompt_id":PROMPT_ID,"source_max_tokens":1200,"variant_suite_id":SUITE_ID,"variant_suite_name":SUITE_NAME,"variant_max_tokens":2400,"variant_suite_sha256":sha(diag),"q30_same_prompt_acceptance_and_max_tokens":same_prompt,"runtime_copy_source":str(SOURCE_RUNTIME),"runtime_copy":str(RUNTIME),"python_alias_path":str(shim),"python_alias_target":"/usr/bin/python3","python_alias_sha256":sha(shim),"python_alias_mode":"0755","python_alias_scope":"PATH prepended only in the isolated LlamaCode controller/server subprocess environment; host and GUI environment unchanged","cpu_smoke":{"command":"sh -c python -c import sys; print(sys.executable)","exit_code":probe.returncode,"stdout":probe.stdout.strip(),"stderr":probe.stderr.strip()},"downloaded":False,"server_started":False,"model_requests":0,"gpu_used":False}
 write_json(ATTEMPT/"receipts/preparation.json",receipt)
 print(json.dumps(receipt,ensure_ascii=False,indent=2))
if __name__=="__main__":main()

#!/usr/bin/env python3
"""Run the fixed BCB-Hard-8 set with an explicit reasoning budget against a local endpoint."""
from __future__ import annotations
import argparse, ctypes, ctypes.util, json, os, re, subprocess, sys, tempfile, time
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[4]
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

NETWORK_SYSCALLS = (
    "socket", "socketpair", "connect", "accept", "accept4", "bind", "listen", "getsockname",
    "getpeername", "shutdown", "sendto", "recvfrom", "sendmsg", "recvmsg", "setsockopt",
    "getsockopt", "sendmmsg", "recvmmsg", "io_uring_setup", "io_uring_enter", "io_uring_register",
)

def seccomp_filter_fd():
    """Return a libseccomp BPF fd that denies network syscalls in the grader child."""
    if os.uname().machine != "x86_64":
        raise RuntimeError("the preregistered seccomp syscall filter is x86_64-only")
    libname = ctypes.util.find_library("seccomp")
    if not libname:
        raise RuntimeError("libseccomp is unavailable")
    library = ctypes.CDLL(libname)
    library.seccomp_init.argtypes = [ctypes.c_uint32]
    library.seccomp_init.restype = ctypes.c_void_p
    library.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    library.seccomp_syscall_resolve_name.restype = ctypes.c_int
    library.seccomp_rule_add.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_uint]
    library.seccomp_rule_add.restype = ctypes.c_int
    library.seccomp_export_bpf.argtypes = [ctypes.c_void_p, ctypes.c_int]
    library.seccomp_export_bpf.restype = ctypes.c_int
    library.seccomp_release.argtypes = [ctypes.c_void_p]
    ctx = library.seccomp_init(0x7FFF0000)  # SCMP_ACT_ALLOW
    if not ctx:
        raise RuntimeError("seccomp_init failed")
    fd = -1
    try:
        added = []
        for name in NETWORK_SYSCALLS:
            syscall = library.seccomp_syscall_resolve_name(name.encode())
            if syscall >= 0:
                rc = library.seccomp_rule_add(ctx, 0x00050001, syscall, 0)  # SCMP_ACT_ERRNO(EPERM)
                if rc != 0:
                    raise OSError(-rc, f"seccomp_rule_add({name}) failed")
                added.append(name)
        if "socket" not in added or "connect" not in added:
            raise RuntimeError("seccomp filter is missing socket/connect rules")
        fd = os.memfd_create("lc-bcb-network-deny.bpf", 0)
        if library.seccomp_export_bpf(ctx, fd) != 0:
            raise OSError("seccomp_export_bpf failed")
        os.lseek(fd, 0, os.SEEK_SET)
        return fd
    except Exception:
        if fd >= 0:
            os.close(fd)
        raise
    finally:
        library.seccomp_release(ctx)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--url", default="http://127.0.0.1:8038/v1/chat/completions")
    p.add_argument("--arm", choices=("astra", "swift"), required=True)
    p.add_argument("--seed", type=int, default=4242)
    p.add_argument("--model", default="Swift-Qwen3.8-27B-Genesis-NVFP4-v4")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--budget", type=int, default=2048)
    p.add_argument("--max-tokens", type=int, default=6144)
    p.add_argument("--limit", type=int, default=0, help="run only the first N fixture tasks; pilot only, not the screen")
    a=p.parse_args()
    corpus=json.loads(PACK.read_text())
    items=corpus["items"][:a.limit] if a.limit else corpus["items"]
    rows=[]
    for i,item in enumerate(items,1):
        payload={"model":a.model,"messages":[
          {"role":"system","content":"Solve the programming task. Return only a complete Python implementation; do not explain."},
          {"role":"user","content":item["prompt"]}],
          "temperature":0.6,"top_p":0.95,"top_k":20,"min_p":0.0,
          "repetition_penalty":1.0,"presence_penalty":0.0,"frequency_penalty":0.0,
          "max_tokens":a.max_tokens,
          "chat_template_kwargs":{"enable_thinking":True},"seed":a.seed,"stream":False}
        payload["reasoning_budget_tokens"] = a.budget
        start=time.perf_counter()
        try:
            result, wall=req(a.url,payload,900)
            msg=result.get("choices",[{}])[0].get("message",{})
            text=str(msg.get("content") or "")
            code=candidate_code(text)
            passed=False; detail=""; grade_status="no_final_content"; grade_exit=None
            if code.strip():
                grade_status="sandbox_error"
                try:
                    with tempfile.TemporaryDirectory(prefix="lc-bcb-") as d:
                        directory=Path(d); script=directory/"candidate.py"
                        script.write_text(code+"\n\n"+item["tests"]+"\n",encoding="utf-8")
                        seccomp_fd=seccomp_filter_fd()
                        cmd=["bwrap","--ro-bind","/","/","--dev","/dev","--proc","/proc",
                             "--tmpfs","/tmp","--tmpfs","/home","--tmpfs","/media","--tmpfs","/mnt",
                             "--tmpfs","/run/user","--dir","/mnt/work","--bind",d,"/mnt/work","--chdir","/mnt/work",
                             "--unshare-pid","--die-with-parent","--clearenv","--setenv","PATH","/usr/bin:/bin",
                             "--setenv","HOME","/tmp","--seccomp",str(seccomp_fd),
                             sys.executable,"-I","/mnt/work/candidate.py"]
                        try:
                            grade=subprocess.run(cmd,capture_output=True,text=True,timeout=45,pass_fds=(seccomp_fd,))
                        finally:
                            os.close(seccomp_fd)
                        grade_exit=grade.returncode
                        detail=(grade.stderr or grade.stdout).strip()[-1200:]
                        if grade.returncode==0:
                            grade_status="ok"; passed=True
                        elif detail.startswith("bwrap:"):
                            grade_status="sandbox_error"
                        else:
                            grade_status="test_failed"
                except subprocess.TimeoutExpired:
                    grade_status="test_timeout"; detail="grader timed out after 45s"
                except Exception as e:
                    grade_status="sandbox_error"; detail=f"{type(e).__name__}: {e}"
            rows.append({"id":item["id"],"transportOk":True,"wallMs":round(wall,2),"passed":passed,
                         "gradeStatus":grade_status,"gradeExitCode":grade_exit,
                         "completionTokens":result.get("usage",{}).get("completion_tokens"),
                         "promptTokens":result.get("usage",{}).get("prompt_tokens"),
                         "reasoningTokens":result.get("usage",{}).get("completion_tokens_details",{}).get("reasoning_tokens"),
                         "reasoningContentChars":len(msg.get("reasoning_content") or ""),
                         "finishReason":result.get("choices",[{}])[0].get("finish_reason"),
                         "timings":result.get("timings"),"code":code,"gradeDetail":detail,"rawContent":text[:12000]})
        except Exception as e:
            rows.append({"id":item["id"],"transportOk":False,"wallMs":round((time.perf_counter()-start)*1000,2),
                         "passed":False,"gradeStatus":"transport_error","error":f"{type(e).__name__}: {e}"})
        print(f"{i}/{len(items)} {item['id']} passed={rows[-1]['passed']} grade={rows[-1].get('gradeStatus')} wallMs={rows[-1]['wallMs']}",flush=True)
    out={"benchmark":"BigCodeBench-Hard-8","arm":a.arm,"seed":a.seed,"pack":str(PACK.relative_to(ROOT)),"model":a.model,"url":a.url,
         "reasoning":"on","reasoningBudgetTokens":a.budget,"reasoningBudgetSent":True,"temperature":0.6,"topP":0.95,"topK":20,"maxTokens":a.max_tokens,
         "runs":len(rows),"transportOk":sum(r["transportOk"] for r in rows),"passed":sum(r["passed"] for r in rows),
         "sandboxErrors":sum(r.get("gradeStatus")=="sandbox_error" for r in rows),"noFinalContent":sum(r.get("gradeStatus")=="no_final_content" for r in rows),"rows":rows}
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
    print(f"score={out['passed']}/{out['runs']} transport={out['transportOk']}/{out['runs']} sandboxErrors={out['sandboxErrors']} noFinalContent={out['noFinalContent']} out={a.out}")
    return 0 if out["transportOk"]==out["runs"] and out["sandboxErrors"]==0 and out["noFinalContent"]==0 else 2
if __name__=="__main__": raise SystemExit(main())

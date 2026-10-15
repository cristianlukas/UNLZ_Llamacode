import json
from urllib.request import Request, urlopen

base = "http://127.0.0.1:8877"
source_id = "sys-bench-qwen38-dflash2-vllm-262k"

def request(path, body=None):
    data = None if body is None else json.dumps(body).encode()
    req = Request(base + path, data=data, headers={"Content-Type": "application/json"} if data else {})
    with urlopen(req, timeout=30) as response:
        payload = response.read()
    return json.loads(payload) if payload else {}

def invoke(target, method, args):
    result = request("/invoke?target=" + target, {"method": method, "args": args})
    if result.get("ok") is False:
        raise RuntimeError(result)
    return result.get("result")

source = invoke("profileManager", "getLaunchProfile", [source_id])
copy_id = invoke("profileManager", "duplicateLaunchProfile", [source_id])
if not copy_id:
    raise RuntimeError("duplicateLaunchProfile returned empty id")
copy = invoke("profileManager", "getLaunchProfile", [copy_id])
backend_id = copy["backendProfileId"]
configured = invoke("profileManager", "setBackendCloud", [
    backend_id, "cloud", "http://127.0.0.1:18888", "", "qwen3.8-27b", 8192
])
if not configured:
    raise RuntimeError("setBackendCloud failed")
invoke("profileManager", "setLaunchAlias", [copy_id, "Q-20261015 W8A16 DFlash2 8k"])
invoke("profileManager", "setLaunchBenchmark", [copy_id, True])
copy = invoke("profileManager", "getLaunchProfile", [copy_id])
backend = invoke("profileManager", "getBackend", [backend_id])
receipt = {
    "sourceLaunch": source,
    "isolatedLaunch": copy,
    "isolatedBackend": backend,
    "serverContextLimit": 4096,
    "note": "User copy in task-specific XDG profile store; source system profile not modified."
}
path = "artifacts/evaluacion-modelos-llamacode/Q-20261015-DUAL5070TI-VLLM/receipts/llamacode-profile.json"
open(path, "w", encoding="utf-8").write(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
print(json.dumps(receipt, ensure_ascii=False, indent=2))

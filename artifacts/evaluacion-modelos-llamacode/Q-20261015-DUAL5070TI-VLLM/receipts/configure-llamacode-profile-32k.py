import json
from pathlib import Path
from urllib.request import Request, urlopen

base = "http://127.0.0.1:8877"
launch_id = "60d6902d-f8c2-481a-84c1-1ef52fa169b4"
backend_id = "f2a2ccf4-dd91-4c58-85a5-4ae6ec7b64e8"
out = Path(__file__).with_name("llamacode-profile-32k.json")


def invoke(method, args):
    request = Request(
        base + "/invoke?target=profileManager",
        data=json.dumps({"method": method, "args": args}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urlopen(request, timeout=30) as response:
        result = json.loads(response.read())
    if result.get("ok") is False:
        raise RuntimeError(result)
    return result.get("result")


configured = invoke("setBackendCloud", [
    backend_id, "cloud", "http://127.0.0.1:18888", "", "qwen3.8-27b", 32768
])
if not configured:
    raise RuntimeError("setBackendCloud failed")
invoke("setLaunchAlias", [launch_id, "Q-20261015 W8A16 DFlash2 32k"])
launch = invoke("getLaunchProfile", [launch_id])
backend = invoke("getBackend", [backend_id])
receipt = {
    "launch": launch,
    "backend": backend,
    "serverContextLimit": 32768,
    "note": "Existing task-isolated profile updated through the LlamaCode control API; product profiles unchanged.",
}
out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(receipt, ensure_ascii=False, indent=2))

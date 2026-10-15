import datetime
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
container = "llamacode-anyjev-eval-20261015"
attempt = int(sys.argv[1]) if len(sys.argv) > 1 else 1
deadline = time.monotonic() + 25.0
response = None
status = "unknown"
while time.monotonic() < deadline:
    inspect = subprocess.run(
        ["docker", "inspect", "--format", "{{.State.Status}}", container],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    status = inspect.stdout.strip() if inspect.returncode == 0 else "missing"
    if status != "running":
        break
    try:
        with urllib.request.urlopen("http://127.0.0.1:8117/v1/models", timeout=2) as r:
            response = json.load(r)
        break
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        time.sleep(2)

logs = subprocess.run(["docker", "logs", container], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False).stdout
(ROOT / f"receipts/server-startup-attempt{attempt}.log").write_text(logs)
record = {
    "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "container": container,
    "container_status": status,
    "api_ready": response is not None,
    "models_response": response,
}
(ROOT / f"receipts/vllm-ready-attempt{attempt}.json").write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps(record, indent=2))

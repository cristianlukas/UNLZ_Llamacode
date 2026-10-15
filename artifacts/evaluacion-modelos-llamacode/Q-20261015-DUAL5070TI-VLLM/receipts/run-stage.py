import argparse, json, time
from pathlib import Path
from urllib.request import Request, urlopen

parser = argparse.ArgumentParser()
parser.add_argument("--suite-id", required=True)
parser.add_argument("--stage", required=True)
parser.add_argument("--out-dir", required=True)
parser.add_argument("--max-wait", type=int, default=1800)
args = parser.parse_args()
base = "http://127.0.0.1:8877"
launch_id = "60d6902d-f8c2-481a-84c1-1ef52fa169b4"
out = Path(args.out_dir)
out.mkdir(parents=True, exist_ok=True)
events_path = out / "events.jsonl"

def request(path, body=None):
    data = None if body is None else json.dumps(body).encode()
    req = Request(base + path, data=data,
                  headers={"Content-Type": "application/json"} if data else {})
    with urlopen(req, timeout=30) as response:
        raw = response.read()
    return json.loads(raw) if raw else {}

def prop(name):
    return request("/prop?name=" + name).get("value")

def invoke(method, args):
    response = request("/invoke", {"method": method, "args": args})
    if response.get("ok") is False:
        raise RuntimeError(response)
    return response.get("result")

def record(event, **values):
    row = {"time_unix": time.time(), "event": event, **values}
    with events_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(json.dumps(row, ensure_ascii=False), flush=True)

if prop("benchmarkRunning"):
    raise SystemExit("benchmark already running")
if prop("serverState") != "running" or not prop("serverReady") or not prop("agentRunning"):
    raise SystemExit("server/agent not ready")
menu = invoke("launchMenu", [])
launch = next((item for item in menu if item.get("id") == launch_id), None)
if not launch:
    raise SystemExit("isolated launch profile not found")
suites = prop("customBenchmarks") or []
suite = next((item for item in suites if item.get("id") == args.suite_id), None)
if not suite:
    raise SystemExit("suite not imported")
record("preflight", stage=args.stage, launch=launch,
       suite={"id": suite.get("id"), "name": suite.get("name"),
              "prompt_count": len(suite.get("prompts", []))},
       agentProfileId="agent-maximo", target="agent", timeoutSec=1800,
       serverState=prop("serverState"), serverReady=prop("serverReady"),
       agentRunning=prop("agentRunning"))
start_time = time.time()
start = invoke("startCustomBenchmark",
               [[launch_id], args.suite_id, 1, "agent", 1800, "agent-maximo"])
record("benchmark_start", response=start)
if isinstance(start, dict) and start.get("ok") is False:
    raise SystemExit("benchmark rejected")
deadline = time.monotonic() + args.max_wait
while time.monotonic() < deadline:
    running = prop("benchmarkRunning")
    status = prop("benchmarkStatus")
    progress = prop("benchmarkProgress")
    record("benchmark_poll", running=running, status=status, progress=progress)
    if not running:
        break
    time.sleep(5)
else:
    record("benchmark_wait_timeout", max_waitSec=args.max_wait)
    raise SystemExit("benchmark did not finish before wait limit")
results = prop("benchmarkResults") or []
coverage = prop("benchmarkCoverage") or []
all_path = out / "app-benchmark-results-all.json"
all_path.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n")
matching = [r for r in results if r.get("profileId") == launch_id
            and float(r.get("timestamp", 0)) / 1000.0 >= start_time]
matching.sort(key=lambda item: float(item.get("timestamp", 0)), reverse=True)
filtered_coverage = [r for r in coverage if r.get("profileId") == launch_id]
summary = {
    "stage": args.stage,
    "suiteId": args.suite_id,
    "startUnix": start_time,
    "finishUnix": time.time(),
    "elapsedWallSec": time.time() - start_time,
    "benchmarkStatus": prop("benchmarkStatus"),
    "benchmarkProgress": prop("benchmarkProgress"),
    "serverState": prop("serverState"),
    "serverReady": prop("serverReady"),
    "agentRunning": prop("agentRunning"),
    "resultCount": len(matching),
    "results": matching,
    "coverage": filtered_coverage,
    "resultsFile": str(all_path),
}
(out / "result.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
record("benchmark_complete", result_count=len(matching),
       result=[{k: r.get(k) for k in ("benchmarkName", "qualityScore", "qualityTotal",
               "firstAttemptScore", "repairAttempts", "elapsedSec", "timedOut",
               "failed", "failureKind", "profileConfigFingerprint", "harnessSpecHash")}
               for r in matching], coverage=filtered_coverage)

import json,time
from pathlib import Path
from urllib.request import Request,urlopen

base="http://127.0.0.1:8877"
launch_id="60d6902d-f8c2-481a-84c1-1ef52fa169b4"
out=Path("artifacts/evaluacion-modelos-llamacode/Q-20261015-DUAL5070TI-VLLM/receipts/llamacode-agent-start.json")

def request(path,body=None):
 data=None if body is None else json.dumps(body).encode()
 req=Request(base+path,data=data,headers={"Content-Type":"application/json"} if data else {})
 with urlopen(req,timeout=30) as r:
  raw=r.read()
 return json.loads(raw) if raw else {}
def invoke(method,args):
 x=request("/invoke",{"method":method,"args":args})
 if x.get("ok") is False: raise RuntimeError(x)
 return x.get("result")
def setprop(name,value):
 x=request("/setprop",{"name":name,"value":value})
 if x.get("ok") is False: raise RuntimeError(x)
 return x
def prop(name): return request("/prop?name="+name).get("value")

events=[]
events.append({"event":"approval","result":setprop("agentApprovalMode","super")})
events.append({"event":"thinking","result":setprop("agentThinkingEnabled",True)})
events.append({"event":"active_agent_profile","result":setprop("activeAgentProfileId","agent-maximo")})
events.append({"event":"start","result":invoke("startServerAndAgent",[launch_id])})
deadline=time.monotonic()+240
while time.monotonic()<deadline:
 row={"event":"poll","serverState":prop("serverState"),"serverReady":prop("serverReady"),"agentRunning":prop("agentRunning"),"agentStarting":prop("agentStarting")}
 events.append(row)
 if row["agentRunning"]: break
 time.sleep(3)
result={"launchProfileId":launch_id,"events":events,"serverState":prop("serverState"),"serverReady":prop("serverReady"),"agentRunning":prop("agentRunning"),"agentStarting":prop("agentStarting"),"agentLog":prop("agentLog")}
out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({k:v for k,v in result.items() if k!="agentLog"},ensure_ascii=False,indent=2))
if not result["agentRunning"]: raise SystemExit("Agent did not become ready")

#!/usr/bin/env python3
"""Replay the bundled read-then-write tool contract against a local endpoint."""
import argparse, json, time
from pathlib import Path
from urllib.request import Request, urlopen

PROMPT=("En el workspace aislado, usá exactamente dos llamadas de herramienta: "
        "primero read_file para inspeccionar README.md y después write_file para "
        "crear tool_contract.txt con una línea CONTRACT_OK. No uses otras herramientas. "
        "Verificá el archivo y respondé brevemente.")
TOOLS=[
 {"type":"function","function":{"name":"read_file","description":"Read a UTF-8 text file in the workspace.","parameters":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"],"additionalProperties":False}}},
 {"type":"function","function":{"name":"write_file","description":"Write UTF-8 text to a file in the workspace.","parameters":{"type":"object","properties":{"path":{"type":"string"},"content":{"type":"string"}},"required":["path","content"],"additionalProperties":False}}}
]
def request(url,payload,timeout=300):
 b=json.dumps(payload).encode(); req=Request(url,data=b,headers={"Content-Type":"application/json"})
 started=time.perf_counter()
 with urlopen(req,timeout=timeout) as r: data=json.loads(r.read())
 return data,(time.perf_counter()-started)*1000
def calls(data):
 c=(data.get("choices") or [{}])[0].get("message",{}).get("tool_calls",[]) or []
 out=[]
 for item in c:
  fn=item.get("function",{})
  try: args=json.loads(fn.get("arguments","{}"))
  except Exception: args={"_invalid":fn.get("arguments")}
  out.append({"id":item.get("id",""),"name":fn.get("name",""),"arguments":args})
 return out

def main():
 p=argparse.ArgumentParser(); p.add_argument("--url",default="http://127.0.0.1:8038/v1/chat/completions"); p.add_argument("--model",default="Swift-Qwen3.8-27B-Genesis-NVFP4-v4"); p.add_argument("--passes",type=int,default=5); p.add_argument("--out",type=Path,required=True); a=p.parse_args()
 rows=[]
 for run in range(1,a.passes+1):
  msgs=[{"role":"system","content":"Sos un agente que usa herramientas. Seguí literalmente el orden y la cantidad pedidos. No afirmes haber completado una escritura hasta llamar la herramienta."},{"role":"user","content":PROMPT}]
  row={"pass":run,"calls":[],"transportOk":False}
  try:
   payload={"model":a.model,"messages":msgs,"tools":TOOLS,"tool_choice":"auto","parallel_tool_calls":False,"temperature":0.0,"top_p":0.95,"top_k":20,"max_tokens":512,"chat_template_kwargs":{"enable_thinking":False},"stream":False}
   first,t1=request(a.url,payload); c1=calls(first); row["transportOk"]=True; row["firstWallMs"]=round(t1,2); row["calls"].extend(c1)
   if len(c1)==1:
    assistant=(first.get("choices") or [{}])[0].get("message",{})
    msgs += [{"role":"assistant","content":assistant.get("content"),"tool_calls":assistant.get("tool_calls")},
             {"role":"tool","tool_call_id":c1[0]["id"],"content":"# README de prueba\\nContenido de referencia del workspace.\\n"}]
    payload["messages"]=msgs
    second,t2=request(a.url,payload); c2=calls(second); row["secondWallMs"]=round(t2,2); row["calls"].extend(c2)
    row["finalContent"]=(second.get("choices") or [{}])[0].get("message",{}).get("content","")
   row["passed"]=(len(row["calls"])==2 and row["calls"][0]["name"]=="read_file" and row["calls"][0]["arguments"].get("path")=="README.md" and row["calls"][1]["name"]=="write_file" and row["calls"][1]["arguments"].get("path")=="tool_contract.txt" and row["calls"][1]["arguments"].get("content","").strip()=="CONTRACT_OK")
  except Exception as e: row["error"]=f"{type(e).__name__}: {e}"; row["passed"]=False
  rows.append(row); print(f"pass {run}/{a.passes}: passed={row['passed']} calls={[x['name'] for x in row['calls']]}",flush=True)
 report={"benchmark":"harness_tool_contract_v1","model":a.model,"passes":a.passes,"passed":sum(x.get("passed",False) for x in rows),"transportOk":sum(x.get("transportOk",False) for x in rows),"rows":rows}
 a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
 print(f"score={report['passed']}/{a.passes} transport={report['transportOk']}/{a.passes} out={a.out}")
 return 0 if report["transportOk"]==a.passes else 2
if __name__=="__main__": raise SystemExit(main())

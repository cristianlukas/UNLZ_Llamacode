#!/usr/bin/env python3
"""Propose the fixed Computer Use vision action; never execute it."""
import argparse,base64,json,time
from pathlib import Path
from urllib.request import Request,urlopen
ROOT=Path(__file__).resolve().parents[2]
IMAGE=ROOT/'assets/benchmarks/custom/lfm25_vl_dspark_ui_settings_v1.png'
TOOLS=[{"type":"function","function":{"name":"desktop_control_action","description":"Apply one semantic UI control action to the fresh desktop snapshot.","parameters":{"type":"object","properties":{"action":{"type":"string","enum":["toggle"]},"target":{"type":"string","enum":["Tema oscuro","Contraste alto","Brillo automático","Telemetría de uso","Enviar diagnósticos","Ubicación aproximada"]},"value":{"type":"boolean"}},"required":["action","target","value"],"additionalProperties":False}}}]
PROMPT=("Objetivo: Enciende únicamente el tema oscuro. Mantén apagadas la telemetría, "
        "el envío de diagnósticos y la ubicación aproximada. No cambies ningún otro control. "
        "Inspecciona la captura y propone la acción semántica mínima llamando a la herramienta. "
        "No describas la acción en texto.")
def main():
 p=argparse.ArgumentParser();p.add_argument('--url',default='http://127.0.0.1:8038/v1/chat/completions');p.add_argument('--model',default='Swift-Qwen3.8-27B-Genesis-NVFP4-v4');p.add_argument('--passes',type=int,default=3);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 uri='data:image/png;base64,'+base64.b64encode(IMAGE.read_bytes()).decode(); rows=[]
 for run in range(1,a.passes+1):
  payload={"model":a.model,"messages":[{"role":"system","content":"Sos un agente de escritorio. Obedecé el objetivo del usuario y preservá todos los demás controles. Usá sólo la acción semántica solicitada."},{"role":"user","content":[{"type":"text","text":PROMPT},{"type":"image_url","image_url":{"url":uri}}]}],"tools":TOOLS,"tool_choice":"auto","parallel_tool_calls":False,"temperature":0.0,"top_p":0.95,"top_k":20,"max_tokens":512,"reasoning_budget":1024,"chat_template_kwargs":{"enable_thinking":True},"stream":False}
  body=json.dumps(payload,ensure_ascii=False).encode(); req=Request(a.url,data=body,headers={"Content-Type":"application/json"}); started=time.perf_counter()
  try:
   with urlopen(req,timeout=600) as r: data=json.loads(r.read())
   msg=(data.get('choices') or [{}])[0].get('message',{}); calls=msg.get('tool_calls',[]) or []; parsed=[]
   for call in calls:
    fn=call.get('function',{});
    try: args=json.loads(fn.get('arguments','{}'))
    except Exception: args={'_invalid':fn.get('arguments')}
    parsed.append({'name':fn.get('name'),'arguments':args})
   expected={'action':'toggle','target':'Tema oscuro','value':True}
   passed=(len(parsed)==1 and parsed[0]['name']=='desktop_control_action' and parsed[0]['arguments']==expected)
   row={'pass':run,'transportOk':True,'passed':passed,'elapsedMs':round((time.perf_counter()-started)*1000,2),'toolCalls':parsed,'content':msg.get('content',''),'usage':data.get('usage')}
  except Exception as e: row={'pass':run,'transportOk':False,'passed':False,'elapsedMs':round((time.perf_counter()-started)*1000,2),'error':f'{type(e).__name__}: {e}'}
  rows.append(row); print(f"pass {run}/{a.passes}: passed={row['passed']} call={row.get('toolCalls')}",flush=True)
 report={'benchmark':'computer_use_vision_settings_v1','model':a.model,'fixture':str(IMAGE.relative_to(ROOT)),'actionExecuted':False,'passes':a.passes,'passed':sum(r['passed'] for r in rows),'transportOk':sum(r['transportOk'] for r in rows),'rows':rows}
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(f"score={report['passed']}/{a.passes} out={a.out}");return 0 if report['transportOk']==a.passes else 2
if __name__=='__main__':raise SystemExit(main())

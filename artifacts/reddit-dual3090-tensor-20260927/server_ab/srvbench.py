import json,sys,time,urllib.request,base64,os,random
URL=sys.argv[1]; tag=sys.argv[2]
def post(path,body,timeout=900):
    r=urllib.request.Request(URL+path,data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
    return json.load(urllib.request.urlopen(r,timeout=timeout))
def chat(msgs,n=256,**kw):
    t=time.time(); j=post('/v1/chat/completions',dict(model='x',messages=msgs,max_tokens=n,temperature=0,**kw)); dt=time.time()-t
    tm=j.get('timings',{}); return j,dt,tm
res={'tag':tag}
import atexit
atexit.register(lambda: print('PARTIAL',json.dumps(res,ensure_ascii=False)))
# warm
chat([{'role':'user','content':'hola'}],8)
_,dt,tm=chat([{'role':'user','content':'Write a Python function that parses an ISO-8601 duration string like P3DT4H5M into total seconds, with tests.'}],512)
res['code_tg']=tm.get('predicted_per_second'); res['code_draft_acc']=(tm.get('draft_n_accepted',0)/max(1,tm.get('draft_n',1)))
_,dt,tm=chat([{'role':'user','content':'Contame en detalle la historia del puerto de Buenos Aires en unos 6 parrafos.'}],512)
res['narr_tg']=tm.get('predicted_per_second'); res['narr_draft_acc']=(tm.get('draft_n_accepted',0)/max(1,tm.get('draft_n',1)))
# tool call
tools=[{'type':'function','function':{'name':'read_file','description':'Read a file','parameters':{'type':'object','properties':{'path':{'type':'string'}},'required':['path']}}}]
j,_,_=chat([{'role':'user','content':'Read the file src/main.cpp please.'}],256,tools=tools)
tc=j['choices'][0]['message'].get('tool_calls') or []
res['tool_ok']=bool(tc) and tc[0]['function']['name']=='read_file' and 'main.cpp' in tc[0]['function']['arguments']
# vision
img=os.environ.get('LC_IMG')
if img:
    b=base64.b64encode(open(img,'rb').read()).decode()
    try:
        j,_,tm=chat([{'role':'user','content':[{'type':'text','text':'What text is written in this image? Answer only the text.'},{'type':'image_url','image_url':{'url':'data:image/png;base64,'+b}}]}],32)
        res['vision_answer']=j['choices'][0]['message']['content'][-60:]
    except Exception as e: res['vision_answer']='ERR '+str(e)[:100]
# long ctx ~30k tokens with needle
random.seed(1); words=open(__file__).read().split()
filler=' '.join(random.choice(['alpha','river','copper','signal','orbit','lantern','meadow','quartz','harbor','violet']) for _ in range(24000))
mid=len(filler)//2; doc=filler[:mid]+' The secret deployment code is TANGO-7731. '+filler[mid:]
_,dt,tm=chat([{'role':'user','content':doc+'\n\nWhat is the secret deployment code? Answer with the code only.'}],32)
res['long_prompt_n']=tm.get('prompt_n'); res['long_pp']=tm.get('prompt_per_second'); res['long_answer']=_['choices'][0]['message']['content'][-40:]
_,dt,tm=chat([{'role':'user','content':doc+'\n\nWhat is the secret deployment code? Answer with the code only, then write a 300 word essay about rivers.'}],400)
res['long_tg']=tm.get('predicted_per_second')
# stability: short request after long cached prompt
try:
    j,_,tm=chat([{'role':'user','content':'Say OK.'}],8); res['after_long_ok']=True
except Exception as e: res['after_long_ok']=False
print(json.dumps(res,ensure_ascii=False))
open(os.path.join(os.path.dirname(__file__),'srv_'+tag+'.json'),'w').write(json.dumps(res,ensure_ascii=False))

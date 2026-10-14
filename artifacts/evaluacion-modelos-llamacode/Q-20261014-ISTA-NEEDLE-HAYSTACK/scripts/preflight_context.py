#!/usr/bin/env python3
import json, pathlib, socket, subprocess, sys, time
GIB=1024**3
ctx=int(sys.argv[1])
mem={}
for line in pathlib.Path('/proc/meminfo').read_text().splitlines():
    key,value=line.split(':',1)
    if key in ('MemAvailable','SwapTotal','SwapFree'):
        mem[key]=int(value.split()[0])*1024
psi=pathlib.Path('/proc/pressure/memory').read_text()
gpus=subprocess.run(['nvidia-smi','--query-gpu=index,name,memory.used,memory.total,utilization.gpu','--format=csv,noheader,nounits'],capture_output=True,text=True)
compute=subprocess.run(['nvidia-smi','--query-compute-apps=pid,process_name,used_memory','--format=csv,noheader'],capture_output=True,text=True)
pmon=subprocess.run(['nvidia-smi','pmon','-c','1'],capture_output=True,text=True)
ports=subprocess.run(['ss','-ltn'],capture_output=True,text=True)
listeners=[line.strip() for line in ports.stdout.splitlines() if any(f':{port} ' in line for port in ('8350','8898'))]
# The inference front-end listens on 8350; also detect native engine executables.
active=[]
for entry in pathlib.Path('/proc').iterdir():
    if not entry.name.isdigit():
        continue
    try:
        exe=pathlib.Path('/proc',entry.name,'exe').resolve().name
    except (OSError,RuntimeError):
        continue
    if exe in ('strata','llama-server'):
        active.append({'pid':int(entry.name),'exe':exe})
record={'context':ctx,'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'host':socket.gethostname(),'mem_bytes':mem,'mem_available_gib':round(mem.get('MemAvailable',0)/GIB,3),'psi':psi,'gpus':gpus.stdout.splitlines(),'compute_apps':compute.stdout.splitlines(),'gpu_pmon':pmon.stdout,'ports_8350_8898':listeners,'native_inference_processes':active}
reasons=[]
if mem.get('MemAvailable',0)<32*GIB: reasons.append('MemAvailable below 32 GiB')
if listeners: reasons.append('8350 or 8898 listener active')
if compute.stdout.strip(): reasons.append('GPU compute app active')
if active: reasons.append('Strata/llama native inference process active')
record['decision']='continue' if not reasons else 'blocked'
record['block_reasons']=reasons
print(json.dumps(record,indent=2))
sys.exit(0 if not reasons else 2)

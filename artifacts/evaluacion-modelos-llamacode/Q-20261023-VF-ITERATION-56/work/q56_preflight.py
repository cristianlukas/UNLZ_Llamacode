from __future__ import annotations
import datetime, hashlib, importlib.util, json, pathlib, shutil, subprocess, sys
ROOT=pathlib.Path('/media/cristian/7CFE1E0FFE1DC1F6/Users/cristian/Documents/LlamaCode')
TASK=ROOT/'artifacts/evaluacion-modelos-llamacode/Q-20261023-VF-ITERATION-56'
RUNNER=TASK/'work/run_700k_json_schema_ab.py'
REG=TASK/'receipts/preregistration.json'
OUT=TASK/'receipts/preflight.json'
STAGE_RECEIPT=TASK/'receipts/staged-assets.json'
SOURCE_MANIFEST=TASK/'receipts/source-assets-fingerprint.json'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
spec=importlib.util.spec_from_file_location('q56_preflight_runner',RUNNER)
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
reg=json.loads(REG.read_text())
lock=json.loads((ROOT/'WORK_QUEUE.lock').read_text())
assert lock.get('token')==reg['lockToken'], 'lock token mismatch'
assert sha(RUNNER)==reg['runnerSha256'], 'runner SHA mismatch'
assert sha(TASK/'receipts/source55-format-ab-strata-config.json')==reg['modelAndRuntime']['configSha256'], 'config SHA mismatch'
assert sha(TASK/'schemas/response-schemas.json')==reg['modelAndRuntime']['schemaSha256'], 'schema SHA mismatch'
base=mod.load_source55_module().load_base_runner()
snap=base.snapshot()
servers=mod.inference_processes()
listeners=mod.listeners()
port_free=mod.port_free(mod.PORT)
cfg=json.loads(mod.CONFIG.read_text())
s55=json.loads((mod.SOURCE55/'receipts/source-55-strata-config.json').read_text())
reg_stage=reg['modelAndRuntime']
stage_root=pathlib.Path(reg_stage['stagingRootLinux']).resolve()
def normalize_asset_args(args):
    result=list(args)
    for flag in ('--pack','--native','--ple-gguf'):
        index=result.index(flag)+1
        result[index]=f'<staged:{flag}>'
    return result
args_equivalent=normalize_asset_args(cfg['args'])==normalize_asset_args(s55['args']) and cfg['model_name']==s55['model_name'] and cfg['exe']==s55['exe'] and cfg['cwd']==s55['cwd']
pack_path=pathlib.Path(cfg['args'][cfg['args'].index('--pack')+1])
tokenizer_path=pathlib.Path(cfg['tokenizer'])
mtp_path=pathlib.Path(cfg['args'][cfg['args'].index('--mtp')+1])
stage_paths=[pack_path,tokenizer_path]
fp=json.loads(mod.SOURCE55_MODEL_FINGERPRINTS.read_text())
model_checks=[]
for artifact in fp['artifacts']:
    names={'native_model_shard_1_of_2':'--native','native_model_shard_2_of_2':'--ple-gguf'}
    path=pathlib.Path(cfg['args'][cfg['args'].index(names[artifact['role']])+1])
    st=path.stat()
    model_checks.append({'role':artifact['role'],'path':str(path),'bytes':st.st_size,'mtimeNs':st.st_mtime_ns,'expectedBytes':artifact['bytes'],'expectedMtimeNs':artifact['mtimeNs'],'ok':st.st_size==artifact['bytes'] and st.st_mtime_ns==artifact['mtimeNs']})
    stage_paths.append(path)
try:
    staged_copy=json.loads(STAGE_RECEIPT.read_text())
except Exception:
    staged_copy={}
try:
    source_manifest=json.loads(SOURCE_MANIFEST.read_text())
except Exception:
    source_manifest={}
expected_files={x['relativeTarget']:x for x in source_manifest.get('files',[])}
stage_files={x.get('relativeTarget'):x for x in staged_copy.get('files',[])}
stage_copy_verified=(bool(staged_copy.get('verified')) and bool(expected_files)
    and set(expected_files)==set(stage_files)
    and all(stage_files[k].get('ok')
            and stage_files[k].get('bytes')==expected_files[k].get('bytes')
            and stage_files[k].get('sourceSha256')==expected_files[k].get('sourceSha256')
            and stage_files[k].get('expectedSha256')==expected_files[k].get('expectedSha256')
            and stage_files[k].get('targetSha256')==expected_files[k].get('sourceSha256')
            and stage_files[k].get('targetBytes')==expected_files[k].get('bytes')
            for k in expected_files))
all_assets_under_stage=True
for p in stage_paths:
    try: p.resolve(strict=True).relative_to(stage_root)
    except (OSError,ValueError): all_assets_under_stage=False
stage_free=shutil.disk_usage(stage_root).free if stage_root.exists() else 0
min_stage_free=reg_stage['minimumFreeBytesAfterStaging']
mem=snap.get('memAvailableBytes')
psi=snap.get('psiMemory') or {}
gpu_rows=mod.parse_gpus(snap)
checks={
 'lockToken':lock.get('token')==reg['lockToken'],
 'runnerConfigSchemaHashes':True,
 'modelAliasRuntimeAndAllNonAssetArgsIdenticalToS55':args_equivalent,
 'stagedAssetsUnderTemporaryCVolume':all_assets_under_stage,
 'stagedAssetsCopySha256Verified':stage_copy_verified,
 'sourceFingerprintManifestMatchesPrereg':sha(SOURCE_MANIFEST)==reg_stage.get('sourceManifestSha256'),
 'iq3xxsPackAndTokenizerPresent':pack_path.is_dir() and tokenizer_path.is_dir(),
 'mtpRuntimePathPresent':mtp_path.is_dir(),
 'stagedVolumeHasAtLeast40GiBFree':stage_free>=min_stage_free,
 'shardsSizeMtimeMatchS55Receipt':all(x['ok'] for x in model_checks),
 'noInferenceProcesses':not servers,
 'noKnownModelListeners':not listeners,
 'port8352Free':port_free,
 'MemAvailableAtLeast40GiB':mem is not None and mem>=40*1024**3,
 'psiPreflightBelowLimits':psi.get('some',{}).get('avg10',100)<10 and psi.get('full',{}).get('avg10',100)<1,
 'oomCounterAvailable':snap.get('oomKills') is not None,
 'two3090sAtLeast12GiBFree':len(gpu_rows)>=2 and all(x['freeMiB']>=12*1024 for x in gpu_rows[:2]),
}
receipt={'schemaVersion':1,'taskId':reg['taskId'],'experimentId':reg['experimentId'],'atUtc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'gpuStarted':False,'lock':lock,'checks':checks,'snapshot':snap,'inferenceProcesses':servers,'listeners':listeners,'modelFiles':model_checks,'stagedVolumeFreeBytes':stage_free,'stagedCopyReceipt':staged_copy,'configSha256':sha(mod.CONFIG),'runnerSha256':sha(RUNNER),'schemaSha256':sha(mod.SCHEMAS),'runtimeSha256':sha(pathlib.Path(cfg['exe'])),'serverSourceSha256':sha(pathlib.Path(cfg['cwd'])/'serve/server.py'),'passed':all(checks.values())}
OUT.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'passed':receipt['passed'],'checks':checks,'memAvailableGiB':round((mem or 0)/1024**3,2),'psi':psi,'gpus':gpu_rows,'serverCount':len(servers),'listenerCount':len(listeners),'port8352Free':port_free,'receipt':str(OUT)},ensure_ascii=False,indent=2))
if not receipt['passed']: sys.exit(2)

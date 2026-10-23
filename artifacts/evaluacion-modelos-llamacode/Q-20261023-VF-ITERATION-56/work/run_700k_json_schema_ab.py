#!/usr/bin/env python3
"""Paired JSON-schema follow-up to source #55; one pinned Strata server, six requests."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import pathlib
import re
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

ROOT = pathlib.Path('/media/cristian/7CFE1E0FFE1DC1F6/Users/cristian/Documents/LlamaCode')
TASK = ROOT / 'artifacts/evaluacion-modelos-llamacode/Q-20261023-VF-ITERATION-56'
SOURCE55 = ROOT / 'artifacts/evaluacion-modelos-llamacode/Q-20261020-VF-20261019-01'
SOURCE55_RUNNER = SOURCE55 / 'scripts/run_source55_context700k.py'
SOURCE55_RESULT = SOURCE55 / 'receipts/source-55-retrieval700k.json'
SOURCE55_AUDIT = SOURCE55 / 'receipts/source-55-posthoc-audit.json'
SOURCE55_MODEL_FINGERPRINTS = SOURCE55 / 'receipts/source-55-model-fingerprints.json'
CONFIG = TASK / 'receipts/source55-format-ab-strata-config.json'
SCHEMAS = TASK / 'schemas/response-schemas.json'
RESULT = TASK / 'receipts/700k-json-schema-ab-attempt-04.json'
WRAPPER_LOG = TASK / 'receipts/strata-format-ab-wrapper-attempt-04.log'
TOKEN = '0bbd4847-1a31-436c-a45e-785a230d9c8f'
MODEL = 'qwen3.8-flash-next-iq3_xxs-context700k'
PORT = 8352
STAGING_ROOT = pathlib.Path('/media/cristian/7CFE1E0FFE1DC1F6/Users/cristian/Models/LlamaCode-Q56-IQ3XXS-Temp').resolve()
ENDPOINT = f'http://127.0.0.1:{PORT}/v1/chat/completions'
TIMEOUT_S = 1800
MIN_AVAILABLE = 40 * 1024**3
ABORT_AVAILABLE = 32 * 1024**3
HIGH_PSI_SOME = 40.0
HIGH_PSI_FULL = 25.0
HIGH_PSI_SAMPLES = 4
MIN_GPU_FREE_MIB = 12 * 1024
EXPECTED_CONFIG_SHA = '78a5c2791a0637f579d4e562735cf8eaf2a3f205acb735594ac9f9c1afd07407'
EXPECTED_SCHEMA_SHA = '2b6f5d7f2119d05e4aea87d2175bc8d63fff2e79b62e8584d4f6c82eec7cac06'
EXPECTED_SOURCE55_RESULT_SHA = 'fb5db28dad359cb848dd1708586c0236ac8ff9e6e3a53ce870231e3dbae7622c'
EXPECTED_SOURCE55_AUDIT_SHA = '351efd29931e56a495e83c34207671a1a15a36a38cd6bc31dabc006b17901c3e'
EXPECTED_SOURCE55_CONFIG_SHA = '2ba75fce1b8cd9d5c00fe1880052bb1f802e92546b480a9f5d5df0eccf15b42a'
EXPECTED_SOURCE55_RUNNER_SHA = '1d14479ddd1148b18cc665bd3c229907f5fe3bfe9ffee0acbb50bb05df986f93'
EXPECTED_MODEL_FINGERPRINTS_SHA = 'a3949ae5b44f98fa5a61ca005cd8fa91ffb838778a9073de2869faee95d5dfcb'
EXPECTED_MANIFEST_SHA = '3d2918163fdc0162f7ce6154b0490fedd9986ad67cbf85f3b100ae650d077267'
EXPECTED_ANSWER_KEY_SHA = 'c6a53577e2de4436d390628797834a9ad129de911bd7633854499414706c18ca'
EXPECTED_ENGINE_SHA = '770ecf303a4c6271654339c639392ecb455de3a999bf5d2e8dbc73c879103602'
EXPECTED_SERVER_SHA = '017efa1f4e76d72396738555d13eb1f9898d1c1c12730cf046d9b267b29987e5'
KNOWN_MODEL_PORTS = {8350, 8351, 8352, 8354, 8366, 8080, 8000, 11434}


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def save(data: dict) -> None:
    temp = RESULT.with_suffix('.json.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temp.replace(RESULT)


def lock_token() -> str | None:
    try:
        return json.loads((ROOT / 'WORK_QUEUE.lock').read_text(encoding='utf-8')).get('token')
    except (OSError, json.JSONDecodeError):
        return None


def process_argv(pid: int) -> list[str]:
    try:
        return [x.decode(errors='replace') for x in pathlib.Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0') if x]
    except OSError:
        return []


def inference_processes(exclude: set[int] | None = None) -> list[dict]:
    exclude = exclude or set()
    found = []
    for entry in pathlib.Path('/proc').iterdir():
        if not entry.name.isdigit() or int(entry.name) in exclude or int(entry.name) == os.getpid():
            continue
        argv = process_argv(int(entry.name))
        if not argv:
            continue
        executable = pathlib.Path(argv[0]).name.lower()
        args = [x.lower() for x in argv]
        joined = ' '.join(args)
        is_server = (
            executable.startswith('llama-server')
            or (executable == 'ollama' and 'serve' in args[1:])
            or (executable in {'strata', 'strata.exe'} and '--serve' in args)
            or (executable.startswith('python') and 'server.py' in [pathlib.Path(x).name.lower() for x in args]
                and '--engine' in args and 'strata' in args)
            or 'vllm.entrypoints.openai.api_server' in joined
            or 'vllm serve' in joined
            or 'sglang.launch_server' in joined
            or 'lmstudio' in executable
            or 'koboldcpp' in executable
        )
        if is_server:
            found.append({'pid': int(entry.name), 'argv': argv[:12]})
    return found


def listeners() -> list[dict]:
    proc = subprocess.run(['ss', '-ltnpH'], check=True, capture_output=True, text=True, timeout=10)
    rows = []
    for line in proc.stdout.splitlines():
        cols = line.split()
        if len(cols) < 4:
            continue
        try:
            port = int(cols[3].rsplit(':', 1)[1].rstrip(']'))
        except ValueError:
            continue
        if port in KNOWN_MODEL_PORTS:
            owners = [int(x) for x in re.findall(r'pid=(\d+)', line)]
            rows.append({'port': port, 'owners': owners, 'line': line})
    return rows


def parse_gpus(snapshot: dict) -> list[dict]:
    rows = []
    for line in snapshot.get('gpus', []):
        parts = [x.strip() for x in line.split(',')]
        if len(parts) < 5:
            continue
        try:
            used = int(parts[2])
            total = int(parts[3])
            rows.append({'index': int(parts[0]), 'name': parts[1], 'usedMiB': used,
                         'totalMiB': total, 'freeMiB': total - used, 'utilizationPercent': int(parts[4])})
        except ValueError:
            continue
    return rows


def score_response(text: str, expected: dict) -> dict:
    """Strict local JSON shape/value gate; does not strip markdown or coerce values."""
    try:
        parsed = json.loads(text)
        parse_error = None
    except Exception as exc:
        parsed = None
        parse_error = f'{type(exc).__name__}: {exc}'
    if isinstance(parsed, dict):
        exact_keys = sorted(parsed) == sorted(expected)
        string_values = all(isinstance(value, str) for value in parsed.values())
        exact_by_key = {key: parsed.get(key) == value for key, value in expected.items()}
    else:
        exact_keys = False
        string_values = False
        exact_by_key = {key: False for key in expected}
    return {'parsed': parsed, 'parseError': parse_error, 'exactByKey': exact_by_key,
            'exactMatchCount': sum(exact_by_key.values()), 'schemaKeysExact': exact_keys,
            'schemaValuesAreStrings': string_values}


def staged_config_matches_s55(cfg: dict, source_cfg: dict) -> bool:
    """Allow only the preregistered SSD staging paths and isolated log to differ."""
    if any(cfg.get(key) != source_cfg.get(key) for key in ('model_name', 'exe', 'cwd')):
        return False
    for key in (set(cfg) | set(source_cfg)) - {'args', 'tokenizer', 'log'}:
        if cfg.get(key) != source_cfg.get(key):
            return False
    candidate_args = list(cfg.get('args', []))
    source_args = list(source_cfg.get('args', []))
    if len(candidate_args) != len(source_args):
        return False
    staged_relatives = {
        '--pack': pathlib.Path('strata-data/packs/iq3_xxs'),
        '--native': pathlib.Path('models/IQ3_XXS/Qwen3.8-Flash-Next-GSQ-RCO-IQ3_XXS-00001-of-00002.gguf'),
        '--ple-gguf': pathlib.Path('models/IQ3_XXS/Qwen3.8-Flash-Next-GSQ-RCO-IQ3_XXS-00002-of-00002.gguf'),
    }
    pack_candidate = None
    pack_source = None
    for flag, relative in staged_relatives.items():
        if candidate_args.count(flag) != 1 or source_args.count(flag) != 1:
            return False
        ci, si = candidate_args.index(flag), source_args.index(flag)
        if ci != si or ci + 1 >= len(candidate_args) or si + 1 >= len(source_args):
            return False
        candidate_path = pathlib.Path(candidate_args[ci + 1]).resolve()
        try:
            candidate_relative = candidate_path.relative_to(STAGING_ROOT)
        except ValueError:
            return False
        if candidate_relative != relative:
            return False
        if flag == '--pack':
            pack_candidate = candidate_path
            pack_source = pathlib.Path(source_args[si + 1]).resolve()
        candidate_args[ci + 1] = f'<staged:{flag}>'
        source_args[si + 1] = f'<staged:{flag}>'
    if candidate_args != source_args or pack_candidate is None or pack_source is None:
        return False
    return (pathlib.Path(cfg.get('tokenizer', '')).resolve() == pack_candidate / 'tokenizer'
            and pathlib.Path(source_cfg.get('tokenizer', '')).resolve() == pack_source / 'tokenizer')


def structured_api_probe() -> dict:
    with urllib.request.urlopen(f'http://127.0.0.1:{PORT}/v1/status', timeout=3) as response:
        data = json.loads(response.read().decode('utf-8'))
    so = data.get('structured_output') or data.get('data', {}).get('structured_output')
    if not isinstance(so, dict) or 'json_schema' not in so.get('formats', []):
        raise RuntimeError(f'pinned server does not advertise json_schema: {data}')
    return so


def parse_stream_request(prompt: str, seed: int, mode: str, schema: dict | None,
                         base, before_oom: int, server_pid: int, own_ids: set[int], run: dict, result: dict) -> dict:
    body = {
        'model': MODEL,
        'messages': [{'role': 'user', 'content': prompt}],
        'temperature': 0.0,
        'top_p': 1.0,
        'top_k': 20,
        'seed': seed,
        'max_tokens': 768,
        'stream': True,
        'reasoning_effort': 'none',
        'chat_template_kwargs': {'enable_thinking': False},
        'cache_prompt': False,
        'return_progress': True,
    }
    if mode == 'json_schema':
        body['response_format'] = {'type': 'json_schema', 'json_schema': {
            'name': 'orbit_retrieval', 'strict': True, 'schema': schema}}
    payload = json.dumps(body, ensure_ascii=False).encode('utf-8')
    request = urllib.request.Request(ENDPOINT, data=payload,
                                    headers={'Content-Type': 'application/json'}, method='POST')
    chunks, usage, timings, progress, finish = [], None, None, None, None
    error_event = None
    started = time.monotonic()
    last_sample = 0.0
    low_since = None
    high_psi_count = 0
    status = None
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            status = response.status
            response.fp.raw._sock.settimeout(5)
            while True:
                if time.monotonic() - started > TIMEOUT_S:
                    raise TimeoutError(f'{mode} request exceeded {TIMEOUT_S} seconds')
                try:
                    line = response.readline()
                except (TimeoutError, socket.timeout):
                    line = None
                now = time.monotonic()
                if now - last_sample >= 5:
                    check_runtime(base, before_oom, server_pid, own_ids)
                    snap = base.snapshot()
                    sample = {k: snap.get(k) for k in ('atUtc', 'memAvailableBytes', 'swapUsedBytes', 'oomKills', 'psiMemory', 'gpus', 'compute_apps')}
                    run.setdefault('resourceSamples', []).append(sample)
                    save(result)
                    last_sample = now
                    psi = snap.get('psiMemory') or {}
                    some = psi.get('some', {}).get('avg10', 0.0)
                    full = psi.get('full', {}).get('avg10', 0.0)
                    high_psi_count = high_psi_count + 1 if some >= HIGH_PSI_SOME or full >= HIGH_PSI_FULL else 0
                    if high_psi_count >= HIGH_PSI_SAMPLES:
                        raise RuntimeError(f'memory PSI guard exceeded: some={some}, full={full}')
                    available = snap.get('memAvailableBytes')
                    if available is None:
                        raise RuntimeError('MemAvailable disappeared during inference')
                    low_since = (low_since or now) if available < ABORT_AVAILABLE else None
                    if low_since is not None and now - low_since >= 15:
                        raise RuntimeError('MemAvailable remained below 32 GiB for at least 15 seconds')
                if line is None:
                    continue
                if not line:
                    break
                if not line.startswith(b'data: '):
                    continue
                raw = line[6:].strip()
                if raw == b'[DONE]':
                    break
                try:
                    item = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                usage = item.get('usage') or usage
                timings = item.get('timings') or timings
                progress = item.get('prompt_progress') or progress
                if item.get('error'):
                    error_event = item['error']
                for choice in item.get('choices', []):
                    if choice.get('finish_reason'):
                        finish = choice['finish_reason']
                    delta = choice.get('delta') or {}
                    content = delta.get('content', '')
                    if content:
                        chunks.append(content)
    except urllib.error.HTTPError as exc:
        status = exc.code
        error_text = exc.read().decode('utf-8', errors='replace')
        try:
            error_event = json.loads(error_text)
        except json.JSONDecodeError:
            error_event = {'raw': error_text[:2000]}
    text = ''.join(chunks)
    score = score_response(text, run['expected'])
    parsed = score['parsed']
    parse_error = score['parseError']
    exact_by_key = score['exactByKey']
    exact_count = score['exactMatchCount']
    api_tokens = (usage or {}).get('prompt_tokens', 0)
    output_valid = (
        status == 200 and finish == 'stop' and 679_000 <= api_tokens <= 699_000
        and exact_count == 5 and parse_error is None and score['schemaKeysExact'] and score['schemaValuesAreStrings']
    )
    return {
        'mode': mode, 'seed': seed, 'httpStatus': status, 'text': text,
        'parsed': parsed, 'parseError': parse_error, 'errorEvent': error_event,
        'usage': usage, 'timings': timings, 'lastPromptProgress': progress,
        'finishReason': finish, 'streamChunkCount': len(chunks),
        'elapsedSeconds': round(time.monotonic() - started, 3),
        'exactByKey': exact_by_key, 'exactMatchCount': exact_count,
        'schemaKeysExact': score['schemaKeysExact'], 'schemaValuesAreStrings': score['schemaValuesAreStrings'],
        'valid': output_valid,
    }


def check_runtime(base, baseline_oom: int, server_pid: int, own_ids: set[int]) -> dict:
    if lock_token() != TOKEN:
        raise RuntimeError('work-queue lock token changed')
    external = inference_processes(exclude=own_ids)
    if external:
        raise RuntimeError(f'external inference server appeared: {external}')
    occupied = [row for row in listeners() if not set(row['owners']).issubset(own_ids)]
    if occupied:
        raise RuntimeError(f'external model listener appeared: {occupied}')
    snap = base.snapshot()
    if baseline_oom is not None and snap.get('oomKills') is not None and snap['oomKills'] > baseline_oom:
        raise RuntimeError('host OOM-kill counter increased')
    return snap


def stop_server(proc: subprocess.Popen | None) -> dict:
    if proc is None or proc.poll() is not None:
        return {'returnCode': proc.returncode if proc else None, 'forcedKill': False}
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        return {'returnCode': proc.wait(timeout=30), 'forcedKill': False}
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        return {'returnCode': proc.wait(timeout=10), 'forcedKill': True}


def load_source55_module():
    spec = importlib.util.spec_from_file_location('source55_context_runner', SOURCE55_RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError('could not import pinned source #55 runner helpers')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.TOKEN = TOKEN
    module.CONFIG = CONFIG
    module.RECEIPT = RESULT
    module.SERVER_LOG = WRAPPER_LOG
    module.MODEL = MODEL
    return module


def main() -> int:
    if RESULT.exists():
        raise RuntimeError(f'refusing to overwrite existing result: {RESULT}')
    if lock_token() != TOKEN:
        raise RuntimeError('work-queue lock token is not this Q56 task')
    if sha256(CONFIG) != EXPECTED_CONFIG_SHA:
        raise RuntimeError('isolated config fingerprint changed')
    if sha256(SCHEMAS) != EXPECTED_SCHEMA_SHA:
        raise RuntimeError('response-schema fingerprint changed')
    if sha256(SOURCE55_RESULT) != EXPECTED_SOURCE55_RESULT_SHA:
        raise RuntimeError('source55 baseline receipt changed after preregistration')
    if sha256(SOURCE55_AUDIT) != EXPECTED_SOURCE55_AUDIT_SHA:
        raise RuntimeError('source55 posthoc content audit changed after preregistration')
    if sha256(SOURCE55/'receipts/source-55-strata-config.json') != EXPECTED_SOURCE55_CONFIG_SHA:
        raise RuntimeError('source55 runtime config changed after preregistration')
    if sha256(SOURCE55_RUNNER) != EXPECTED_SOURCE55_RUNNER_SHA:
        raise RuntimeError('source55 runner helpers changed after preregistration')
    if sha256(SOURCE55_MODEL_FINGERPRINTS) != EXPECTED_MODEL_FINGERPRINTS_SHA:
        raise RuntimeError('source55 model fingerprint receipt changed after preregistration')

    source55 = json.loads(SOURCE55_RESULT.read_text(encoding='utf-8'))
    source55_audit = json.loads(SOURCE55_AUDIT.read_text(encoding='utf-8'))
    cfg = json.loads(CONFIG.read_text(encoding='utf-8'))
    source55_cfg = json.loads((SOURCE55 / 'receipts/source-55-strata-config.json').read_text(encoding='utf-8'))
    schema_by_prompt = json.loads(SCHEMAS.read_text(encoding='utf-8'))
    manifest = json.loads((SOURCE55 / 'fixtures/source-55/manifest.json').read_text(encoding='utf-8'))
    answer_key = json.loads((SOURCE55 / 'fixtures/source-55/answer-key.json').read_text(encoding='utf-8'))
    model_hashes = json.loads(SOURCE55_MODEL_FINGERPRINTS.read_text(encoding='utf-8'))
    if sha256(SOURCE55/'fixtures/source-55/manifest.json') != EXPECTED_MANIFEST_SHA:
        raise RuntimeError('source55 prompt manifest changed after preregistration')
    if sha256(SOURCE55/'fixtures/source-55/answer-key.json') != EXPECTED_ANSWER_KEY_SHA:
        raise RuntimeError('source55 answer key changed after preregistration')
    if cfg.get('model_name') != MODEL or cfg.get('log') != str(TASK / 'receipts/strata-format-ab-attempt-04.log'):
        raise RuntimeError('isolated config changed beyond its preregistered name/log fields')
    engine_path = pathlib.Path(cfg['exe'])
    server_root = pathlib.Path(cfg['cwd'])
    server_python = server_root / '.venv/bin/python'
    server_script = server_root / 'serve/server.py'
    tokenizer_module = server_root / 'tools/strata_tokenizer.py'
    cfg_args = cfg['args']
    if not staged_config_matches_s55(cfg, source55_cfg):
        raise RuntimeError('Q56 config differs from S55 beyond the preregistered temporary SSD staging paths')
    def option_path(name: str) -> pathlib.Path:
        try:
            return pathlib.Path(cfg_args[cfg_args.index(name) + 1])
        except (ValueError, IndexError) as exc:
            raise RuntimeError(f'missing path option {name} in pinned config') from exc
    required_paths = (engine_path, server_python, server_script, tokenizer_module,
                      pathlib.Path(cfg['tokenizer']), option_path('--pack'), option_path('--mtp'))
    if not all(path.exists() for path in required_paths):
        missing = [str(path) for path in required_paths if not path.exists()]
        raise FileNotFoundError(f'pinned Strata/model assets are missing: {missing}')
    if sha256(engine_path) != EXPECTED_ENGINE_SHA or sha256(server_script) != EXPECTED_SERVER_SHA:
        raise RuntimeError('Strata engine/server source fingerprint changed since S55')
    configured_model_paths = {
        'native_model_shard_1_of_2': option_path('--native'),
        'native_model_shard_2_of_2': option_path('--ple-gguf'),
    }
    model_artifacts = []
    for old in model_hashes.get('artifacts', []):
        path = configured_model_paths.get(old['role'])
        if path is None:
            raise RuntimeError(f'unrecognized model shard role in pinned receipt: {old.get("role")}')
        stat = path.stat()
        if stat.st_size != old['bytes'] or stat.st_mtime_ns != old['mtimeNs']:
            raise RuntimeError(f'model shard size/mtime differs from pinned receipt: {path}')
        model_artifacts.append({**old, 'sourcePath':old['path'], 'path':str(path),
                                'verifiedBy': 'size+mtime against prior SHA-256 receipt; model remains in quarantine'})
    if len(model_artifacts) != 2:
        raise RuntimeError('expected exactly two model shards from S55')
    prompts = manifest.get('prompts', [])
    if len(prompts) != 3 or len(answer_key) != 3 or len(schema_by_prompt) != 3:
        raise RuntimeError('expected exactly three paired prompt/schema/answer records')
    for fixture in prompts:
        prompt_path = SOURCE55 / 'fixtures/source-55' / fixture['file']
        if sha256(prompt_path) != fixture['sha256']:
            raise RuntimeError(f'prompt changed since S55: {fixture["file"]}')
        if sorted(schema_by_prompt[fixture['file']]['required']) != sorted(answer_key[fixture['file']]):
            raise RuntimeError(f'schema keys differ from prompt fact-key list: {fixture["file"]}')

    s55_helpers = load_source55_module()
    base = s55_helpers.load_base_runner()
    base.ABORT_AVAILABLE = ABORT_AVAILABLE
    active = inference_processes()
    listening = listeners()
    if active or listening:
        raise RuntimeError(f'inference service or model listener is already active: processes={active}; listeners={listening}')
    if not port_free(PORT):
        raise RuntimeError(f'loopback port {PORT} is not free')
    before = base.snapshot()
    gpu_rows = parse_gpus(before)
    if before.get('memAvailableBytes', 0) < MIN_AVAILABLE:
        raise RuntimeError('MemAvailable below the preregistered 40 GiB floor')
    psi = before.get('psiMemory') or {}
    if psi.get('some', {}).get('avg10', 0.0) >= 10.0 or psi.get('full', {}).get('avg10', 0.0) >= 1.0:
        raise RuntimeError(f'memory PSI exceeds preflight thresholds: {psi}')
    if before.get('oomKills') is None:
        raise RuntimeError('host OOM-kill counter unavailable')
    if len(gpu_rows) < 2 or any(row['freeMiB'] < MIN_GPU_FREE_MIB for row in gpu_rows[:2]):
        raise RuntimeError(f'less than 12 GiB VRAM free on an RTX 3090 before model load: {gpu_rows}')
    flags = {cfg_args[i]: cfg_args[i+1] for i in range(len(cfg_args)-1)
             if cfg_args[i] in ('--max-context','--rope-scaling','--rope-scale','--yarn-orig-ctx','--kv')}
    if flags != {'--max-context':'700000','--rope-scaling':'yarn','--rope-scale':'4','--yarn-orig-ctx':'262144','--kv':'int8'}:
        raise RuntimeError(f'context/rope/KV flags differ from S55: {flags}')

    result = {
        'schemaVersion': 1,
        'taskId': 'Q-20261023-VF-ITERATION-56',
        'batchId': 'VF-20261019-01',
        'experimentId': 'VF-20261019-01-S55-IQ3XXS-YARN700K-JSON-SCHEMA-AB-SSD',
        'status': 'starting',
        'lockToken': TOKEN,
        'startedAtUtc': utcnow(),
        'context': {'maxContext':700000,'originalContext':262144,'ropeScaling':'yarn','ropeScale':4,'kv':'int8'},
        'model': MODEL,
        'modelShards': model_artifacts,
        'configPath': str(CONFIG),
        'configSha256': EXPECTED_CONFIG_SHA,
        'schemaPath': str(SCHEMAS),
        'schemaSha256': EXPECTED_SCHEMA_SHA,
        'runtime': {'enginePath':str(engine_path),'engineSha256':EXPECTED_ENGINE_SHA,
                    'serverScript':str(server_script),'serverScriptSha256':EXPECTED_SERVER_SHA,
                    'serverPython':str(server_python)},
        'structuredOutputSupport': {'mode':'json_schema prompt + response validation, not constrained decoding',
                                    'runtimeJsonschemaInstalled':False,
                                    'runtimeScope':'object-only validation; exact schema checked by this runner'},
        'resourcePolicy': {'guiAllowed':True,'otherNonInferenceProcessesDoNotBlock':True,
                           'inferenceProcessesBeforeStart':active,'knownInferenceListenersBeforeStart':listening,
                           'preflight':before,'minimumAvailableBytes':MIN_AVAILABLE,
                           'abortAvailableBytes':ABORT_AVAILABLE,'memoryPsiAbort':{'someAvg10':HIGH_PSI_SOME,'fullAvg10':HIGH_PSI_FULL,'samples':HIGH_PSI_SAMPLES},
                           'minimumGpuFreeMiBPer3090BeforeStart':MIN_GPU_FREE_MIB},
        'network': {'bindHost':'127.0.0.1','port':PORT,'externalCalls':0,'fixture':'synthetic only'},
        'design': {'pairs':3,'requests':6,'order':['plain','json_schema','json_schema','plain','plain','json_schema'],
                   'seeds':[2026101956,2026101957,2026101958],
                   'temperature':0.0,'top_p':1.0,'top_k':20,'reasoning_effort':'none',
                   'enable_thinking':False,'max_tokens':768,'cache_prompt':False,
                   'onlyVariable':'response_format'},
        'source55BaselineReceiptSha256':EXPECTED_SOURCE55_RESULT_SHA,
        'source55PosthocAuditSha256':EXPECTED_SOURCE55_AUDIT_SHA,
        'source55PriorStatus':source55.get('status'),
        'source55PriorRawJsonValidCount':sum(bool(run.get('valid')) for run in source55.get('runs',[])),
        'source55PriorContentExactCount':source55_audit.get('contentRetrievalExactFacts'),
        'source55PriorContentTotal':source55_audit.get('contentRetrievalFactsTotal'),
        'fixtures': {'manifestSha256':EXPECTED_MANIFEST_SHA,
                     'answerKeySha256':EXPECTED_ANSWER_KEY_SHA,
                     'promptStored':False,'runs':[]},
        'serverCommand':[str(server_python),str(server_script),'--engine','strata','--config',str(CONFIG),
                         '--host','127.0.0.1','--port',str(PORT),'--gpu','0,1'],
        'noProductionChanges':True,
    }
    save(result)
    if lock_token() != TOKEN:
        raise RuntimeError('work-queue lock changed immediately before server start')

    server = None
    log_handle = None
    try:
        log_handle = WRAPPER_LOG.open('w',encoding='utf-8')
        start = time.monotonic()
        server = subprocess.Popen(result['serverCommand'],cwd=str(server_root),stdout=log_handle,
                                  stderr=subprocess.STDOUT,start_new_session=True)
        result['serverPid'] = server.pid
        result['status'] = 'loading'
        result['serverStartedAtUtc'] = utcnow()
        save(result)
        high_psi_count = 0
        low_since = None
        ready = False
        deadline = time.monotonic()+1800
        while time.monotonic()<deadline:
            own_ids = base.process_tree(server.pid)
            if lock_token()!=TOKEN:
                raise RuntimeError('work-queue lock changed during model load')
            if server.poll() is not None:
                raise RuntimeError(f'Strata exited before READY with code {server.returncode}')
            snap = check_runtime(base,before['oomKills'],server.pid,own_ids)
            available=snap.get('memAvailableBytes')
            if available is None:
                raise RuntimeError('MemAvailable unavailable during model loading')
            low_since=(low_since or time.monotonic()) if available<ABORT_AVAILABLE else None
            if low_since is not None and time.monotonic()-low_since>=15:
                raise RuntimeError('MemAvailable remained below 32 GiB for at least 15 seconds during load')
            p= snap.get('psiMemory') or {}
            high_psi_count=high_psi_count+1 if p.get('some',{}).get('avg10',0.0)>=HIGH_PSI_SOME or p.get('full',{}).get('avg10',0.0)>=HIGH_PSI_FULL else 0
            if high_psi_count>=HIGH_PSI_SAMPLES:
                raise RuntimeError(f'memory PSI load guard exceeded: {p}')
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{PORT}/v1/models',timeout=2) as response:
                    models=json.loads(response.read().decode('utf-8'))
                    if response.status==200 and any(row.get('id')==MODEL for row in models.get('data',[])):
                        ready=True
                        break
            except Exception:
                pass
            time.sleep(5)
        if not ready:
            raise TimeoutError('pinned Strata model did not become READY within 30 minutes')
        result['readyAtUtc']=utcnow()
        result['loadSeconds']=round(time.monotonic()-start,3)
        result['processTreeAtReady']=s55_helpers.tree_cmdlines(server.pid)
        result['statusEndpoint']=structured_api_probe()
        result['status']='ready'
        tokenizer,tokenizer_dir=base.load_tokenizer(cfg['tokenizer'],server_root/'tools/strata_tokenizer.py')
        result['tokenizerHashes']={name:sha256(tokenizer_dir/name) for name in ('tokenizer.json','vocab.json','merges.txt','token_type.json')}
        if result['tokenizerHashes'] != source55.get('tokenizerHashes'):
            raise RuntimeError('tokenizer assets differ from the pinned S55 baseline')
        orders=[('plain','json_schema'),('json_schema','plain'),('plain','json_schema')]
        prompt_meta={row['file']:row for row in manifest['prompts']}
        seed_by_file={row['file']:seed for row,seed in zip(manifest['prompts'],(2026101956,2026101957,2026101958))}
        base_order=[]
        for prompt_index, fixture in enumerate(manifest['prompts']):
            prompt_name=fixture['file']
            prompt_path=SOURCE55/'fixtures/source-55'/prompt_name
            prompt=prompt_path.read_text(encoding='ascii')
            runtime_tokens=len(tokenizer.encode(prompt))
            if runtime_tokens!=fixture['runtimeOfflineBodyTokens']:
                raise RuntimeError(f'offline tokenizer count mismatch for {prompt_name}: {runtime_tokens}')
            expected=answer_key[prompt_name]
            schema=schema_by_prompt[prompt_name]
            for mode in orders[prompt_index]:
                if lock_token()!=TOKEN:
                    raise RuntimeError('work-queue lock changed before next request')
                own_ids=base.process_tree(server.pid)
                run={'pair':prompt_index+1,'mode':mode,'promptFile':prompt_name,
                     'promptSha256':fixture['sha256'],'bodyTokensRuntimeOffline':runtime_tokens,
                     'seed':seed_by_file[prompt_name],'expected':expected,'promptStored':False,
                     'responseSchemaSha256':sha256(SCHEMAS),'startedAtUtc':utcnow()}
                result['fixtures']['runs'].append(run)
                save(result)
                response=parse_stream_request(prompt,run['seed'],mode,schema if mode=='json_schema' else None,
                                              base,before['oomKills'],server.pid,own_ids,run,result)
                run.update(response)
                run['completedAtUtc']=utcnow()
                run['valid']=(response.get('valid') is True and (mode!='json_schema' or response.get('schemaKeysExact') is True))
                base_order.append(run)
                save(result)
            del prompt
        control=[r for r in base_order if r['mode']=='plain']
        candidate=[r for r in base_order if r['mode']=='json_schema']
        result['armSummary']={
            'plain':{'validRuns':sum(bool(x['valid']) for x in control),'runs':len(control),
                     'exactFacts':sum(x.get('exactMatchCount',0) for x in control)},
            'json_schema':{'validRuns':sum(bool(x['valid']) for x in candidate),'runs':len(candidate),
                           'exactFacts':sum(x.get('exactMatchCount',0) for x in candidate)},
        }
        result['candidateGatePass']=(len(candidate)==3 and all(x['valid'] for x in candidate)
                                     and sum(x.get('exactMatchCount',0) for x in candidate)==15)
        result['status']='completed_candidate_gate_pass' if result['candidateGatePass'] else 'completed_candidate_gate_failed'
    except Exception as exc:
        result['status']='aborted_or_error'
        result['error']=f'{type(exc).__name__}: {exc}'
    finally:
        result['stoppedAtUtc']=utcnow()
        result['afterStop']=stop_server(server)
        if log_handle:
            log_handle.close()
        try:
            result['postflight']=base.snapshot()
        except Exception as exc:
            result['postflightError']=f'{type(exc).__name__}: {exc}'
        result['remainingInferenceProcesses']=inference_processes()
        result['remainingKnownListeners']=listeners()
        result['port8352Free']=port_free(PORT)
        save(result)
    summary={'status':result.get('status'),'candidateGatePass':result.get('candidateGatePass'),
             'error':result.get('error'),'armSummary':result.get('armSummary'),
             'postflight':result.get('postflight'),'remainingInferenceProcesses':result.get('remainingInferenceProcesses'),
             'port8352Free':result.get('port8352Free')}
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    return 0 if result.get('candidateGatePass') else 1


def port_free(port:int)->bool:
    with socket.socket() as sock:
        return sock.connect_ex(('127.0.0.1',port))!=0


if __name__=='__main__':
    raise SystemExit(main())

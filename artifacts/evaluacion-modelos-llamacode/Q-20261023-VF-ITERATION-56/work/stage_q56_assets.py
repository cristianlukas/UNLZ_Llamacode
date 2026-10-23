from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path('/media/cristian/7CFE1E0FFE1DC1F6/Users/cristian/Documents/LlamaCode')
TASK = ROOT / 'artifacts/evaluacion-modelos-llamacode/Q-20261023-VF-ITERATION-56'
REG_PATH = TASK / 'receipts/preregistration.json'
SOURCE_MANIFEST = TASK / 'receipts/source-assets-fingerprint.json'
COPY_RECEIPT = TASK / 'receipts/staged-assets.json'
SHARD_NAMES = [
    'Qwen3.8-Flash-Next-GSQ-RCO-IQ3_XXS-00001-of-00002.gguf',
    'Qwen3.8-Flash-Next-GSQ-RCO-IQ3_XXS-00002-of-00002.gguf',
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb', buffering=0) as f:
        while chunk := f.read(8 * 1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    reg = json.loads(REG_PATH.read_text())
    mr = reg['modelAndRuntime']
    stage = Path(mr['stagingRootLinux'])
    source_root = Path(mr['sourceRootHdd'])
    partial = stage.with_name(stage.name + '.partial-Q56')
    source = json.loads(SOURCE_MANIFEST.read_text())
    files = source['files']
    expected_bytes = sum(item['bytes'] for item in files)
    manifest_sha = hashlib.sha256(SOURCE_MANIFEST.read_bytes()).hexdigest()
    expected_shards = dict(zip(SHARD_NAMES, mr['modelShardsSha256']))
    manifest_shards = {Path(x['sourcePath']).name:x['sourceSha256'] for x in files if x['kind']=='model-shard'}
    free_before = shutil.disk_usage(stage.parent).free
    min_free = int(mr['minimumFreeBytesAfterStaging'])
    checks = {
        'sourceRootMatchesPrereg': str(source_root) == source['sourceRootHdd'],
        'stageAbsent': not stage.exists(),
        'partialAbsent': not partial.exists(),
        'copyReceiptAbsent': not COPY_RECEIPT.exists(),
        'sourceManifestHashMatchesPrereg': manifest_sha == mr['sourceManifestSha256'],
        'sourceShardHashesMatchS55': manifest_shards == expected_shards,
        'sourceBytesMatchPrereg': expected_bytes == int(mr['sourceBytesExpected']),
        'freeSpaceProjectionSafe': free_before - expected_bytes >= min_free,
        'allSourcesPresentAndUnchanged': all(
            Path(item['sourcePath']).is_file()
            and Path(item['sourcePath']).stat().st_size == item['bytes']
            and Path(item['sourcePath']).stat().st_mtime_ns == item['sourceMtimeNs']
            for item in files
        ),
    }
    if not all(checks.values()):
        print(json.dumps({'passed': False, 'checks': checks, 'freeBeforeBytes': free_before,
                          'expectedBytes': expected_bytes, 'minFreeBytes': min_free}, indent=2))
        return 2
    if args.dry_run:
        print(json.dumps({'passed': True, 'dryRun': True, 'checks': checks,
                          'freeBeforeBytes': free_before, 'expectedBytes': expected_bytes,
                          'projectedFreeBytes': free_before - expected_bytes,
                          'minFreeBytes': min_free, 'stage': str(stage)}, indent=2))
        return 0

    partial.mkdir(parents=False)
    try:
        for item in files:
            src = Path(item['sourcePath'])
            dst = partial / item['relativeTarget']
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        copied = []
        for item in files:
            src = Path(item['sourcePath'])
            dst = partial / item['relativeTarget']
            src_stat, dst_stat = src.stat(), dst.stat()
            dst_hash = sha256(dst)
            copied.append({
                **item,
                'targetPath': str(stage / item['relativeTarget']),
                'targetBytes': dst_stat.st_size,
                'targetMtimeNs': dst_stat.st_mtime_ns,
                'targetSha256': dst_hash,
                'ok': (dst_stat.st_size == item['bytes']
                       and dst_hash == item['sourceSha256']
                       and src_stat.st_size == item['bytes']
                       and src_stat.st_mtime_ns == item['sourceMtimeNs']),
            })
        if not all(item['ok'] for item in copied):
            raise RuntimeError('staged file hash/size/mtime verification failed')
        shutil.copystat(source_root / 'models/IQ3_XXS', partial / 'models/IQ3_XXS', follow_symlinks=True)
        shutil.copystat(source_root / 'strata-data/packs/iq3_xxs',
                        partial / 'strata-data/packs/iq3_xxs', follow_symlinks=True)
        free_after = shutil.disk_usage(stage.parent).free
        if free_after < min_free:
            raise RuntimeError(f'post-copy free space {free_after} is below {min_free}')
        os.replace(partial, stage)
        receipt = {
            'schemaVersion': 1,
            'taskId': reg['taskId'],
            'experimentId': reg['experimentId'],
            'verifiedAtUtc': dt.datetime.now(dt.timezone.utc).isoformat(),
            'sourceRootHdd': str(source_root),
            'stagingRootLinux': str(stage),
            'stagingRootWindows': mr['stagingRootWindows'],
            'freeBeforeBytes': free_before,
            'freeAfterBytes': free_after,
            'minimumFreeBytes': min_free,
            'files': copied,
            'verified': True,
            'sourcePreserved': True,
        }
        COPY_RECEIPT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps({'passed': True, 'receipt': str(COPY_RECEIPT),
                          'freeBeforeBytes': free_before, 'freeAfterBytes': free_after,
                          'verifiedFiles': len(copied)}, indent=2))
        return 0
    except Exception:
        # Roll back only the temporary directory created by this invocation.
        if partial.exists():
            shutil.rmtree(partial)
        raise


if __name__ == '__main__':
    raise SystemExit(main())

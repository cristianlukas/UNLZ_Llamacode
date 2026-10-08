"""Compare Strata's default PLE disk reads with --ple-io ram on the local IQ3_S rig."""
import json
import statistics
import sys
import time
from pathlib import Path
ROOT = Path('/home/cristian/.cache/strata-review-20261002/Strata-0.1.35')
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT))
import calibrate as CAL
import strata_tokenizer as ST
from serve.server import StrataEngine, child_env
cfg = json.loads((ROOT / 'strata-iq3_s.json').read_text())
tpath = Path(cfg['tokenizer'])
vocab = json.loads((tpath / 'vocab.json').read_text())
toks = [None] * len(vocab)
for t, i in vocab.items(): toks[i] = t
tok = ST.Tokenizer(toks, (tpath / 'merges.txt').read_text().split('\n'), json.loads((tpath / 'token_type.json').read_text()))
ids_list = [CAL.chat_ids(tok, p) for p in CAL.PROMPTS]
base_args = CAL.apply(CAL.engine_args(cfg), {'--pcie-frac':'0.00','--spec-min-p':'0.70'})
results = {'createdAt':time.strftime('%Y-%m-%d %H:%M:%S'), 'settings':{'--pcie-frac':'0.00','--spec-min-p':'0.70'}, 'measurement':'3 calibration prompts, greedy 128-token decode; 2 warmups then 3 rate rounds per mode', 'modes':{}}
for mode in ['direct','ram']:
    args = CAL.with_arg(base_args, '--ple-io', None if mode == 'direct' else 'ram')
    print(f'LOAD {mode}', flush=True)
    eng = StrataEngine(cfg['exe'], args, cwd=cfg.get('cwd'), log=cfg.get('log'), env=child_env(cfg))
    try:
        session = CAL.Session(eng, ids_list)
        session.warm_up(2)
        vals = [session.rate() for _ in range(3)]
        results['modes'][mode] = {'runsTokS':vals, 'medianTokS':statistics.median(vals)}
        print(mode, results['modes'][mode], flush=True)
    finally:
        CAL.close(eng)
out=Path(__file__).with_name('ple_io_measurements.json')
out.write_text(json.dumps(results, indent=2)+'\n')
print('SAVED',out,flush=True)

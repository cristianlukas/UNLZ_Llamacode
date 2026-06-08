import json, os, sys, time, shutil

BASE = r"C:\Users\cristian\AppData\Roaming\LlamaCode\LlamaCode"  # binary_registry stays here
PROF = r"C:\Users\cristian\Documents\LlamaCode\profiles"          # profiles moved to project root
APPLY = "--apply" in sys.argv
NODEDUP = "--nodedup" in sys.argv
SRC = None
for i,a in enumerate(sys.argv):
    if a == "--from" and i+1 < len(sys.argv): SRC = sys.argv[i+1]

def load(p):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

launches = load(SRC or os.path.join(PROF, "launches.json"))
backends = {b["id"]: b for b in load(os.path.join(PROF, "backends.json"))}
models   = {m["id"]: m for m in load(os.path.join(PROF, "models.json"))}
runtimes = {r["id"]: r for r in load(os.path.join(PROF, "runtimes.json"))}
binaries = {b["id"]: b for b in load(os.path.join(BASE, "binary_registry.json"))}

# ---- binary -> short binary label (real mapping) ----
def bin_label(launch):
    be = backends.get(launch.get("backendProfileId"), {})
    binr = binaries.get(be.get("binaryId"), {})
    name = (binr.get("name") or "") + " " + (binr.get("path") or "")
    n = name.lower()
    if "beellama" in n and "0.3.2" in n: return "Bellama0.3.2"
    if "beellama" in n and "0.3.1" in n: return "Bellama0.3.1"
    if "ik_llama" in n or "ik-llama" in n: return "IK_Llama"
    return "Llama.cpp"

# ---- model profile -> (modelo, quant, has_mmproj) ----
QUANT = {"iq4_xs":"Q4XS","q4_k_m":"Q4KM","q5_k_xl":"Q5XL","q5_k_m":"Q5KM",
         "q4_0":"Q4_0","q6_0":"Q6_0","q8_0":"Q8_0"}
def model_info(launch):
    mp = models.get(launch.get("modelProfileId"), {})
    nm = (mp.get("name") or "").lower()
    has_mm = bool(mp.get("mmprojId"))
    # modelo family
    if "35b-a3b" in nm or "35b a3b" in nm or "a3b" in nm:
        modelo = "Qwen_35A3B"
    elif "27b" in nm or "qwen" in nm:
        modelo = "Qwen_27b"
    elif "gemma" in nm and "31b" in nm:
        modelo = "Gemma4_31B"
    else:
        modelo = "Qwen_27b"  # junk models reference base qwen gguf
    # quant
    quant = None
    for k,v in QUANT.items():
        if k.replace("_"," ") in nm or k in nm:
            quant = v; break
    if quant is None:
        if "iq4" in nm or "q4_xs" in nm: quant = "Q4XS"
        elif "qat" in nm: quant = "Q4_0"
        else: quant = "Q4XS"
    return modelo, quant, has_mm

# ---- parse extraArgs into dict (last wins), keep flags ----
def parse_args(args):
    d = {}; i = 0
    while i < len(args):
        a = args[i]
        if a.startswith("-"):
            if i+1 < len(args) and not args[i+1].startswith("-"):
                d[a] = args[i+1]; i += 2
            else:
                d[a] = True; i += 1
        else:
            i += 1
    return d

ALIAS = {"-ctk":"--cache-type-k","-ctv":"--cache-type-v","-c":"--ctx-size","-ub":"--ubatch-size"}
def getarg(d, *keys):
    for k in keys:
        if k in d: return d[k]
    return None

CACHE = {"q4_0":"Q4","q4_1":"Q41","q5_0":"Q5","q5_1":"Q51","q6_0":"Q6","q8_0":"Q8","f16":"F16",
         "kvarn6":"KVN6","kvarn5":"KVN5","kvarn4":"KVN4","kvarn3":"KVN3",
         "turbo3_tcq":"T3TCQ","turbo2_tcq":"T2TCQ","turbo3":"T3"}
def cache_code(v):
    if not v: return None
    return CACHE.get(str(v).lower(), str(v))

def ctx_label(v):
    try: v = int(v)
    except: return None
    return f"{int(v/1000)}k"

def build_name(launch):
    d = parse_args(launch.get("extraArgs", []))
    rt = runtimes.get(launch.get("runtimePresetId"), {})
    binl = bin_label(launch)
    modelo, quant, has_mm = model_info(launch)
    # context
    ctxv = getarg(d, "--ctx-size", "-c") or rt.get("ctx")
    ctx = ctx_label(ctxv) or "?"
    # cache k/v
    kc = getarg(d, "--cache-type-k", "-ctk")
    vc = getarg(d, "--cache-type-v", "-ctv")
    rtc = rt.get("cacheType")
    if kc is None: kc = rtc
    if vc is None: vc = rtc
    qcK, qcV = cache_code(kc), cache_code(vc)
    quantcache = None
    if qcK and qcV:
        quantcache = f"{qcK}k-{qcV}v" if qcK != qcV else f"{qcK}kv"
    elif qcK or qcV:
        quantcache = f"{qcK or qcV}"
    # techs
    spec = (getarg(d, "--spec-type") or "").lower()
    techs = []
    if "draft-mtp" in spec or "mtp" in spec: techs.append("MTP")
    if "ngram" in spec: techs.append("NGRAM")
    if "dflash" in spec: techs.append("DFLASH")
    if has_mm: techs.append("MMPROJ")
    # micro-experiment disambiguators
    ub = rt.get("ubatch")
    if ub and ub != 64: techs.append(f"UB{ub}")
    dn = getarg(d, "--spec-draft-n-max")
    if dn and str(dn) != "3": techs.append(f"D{dn}")
    mm = getarg(d, "--spec-ngram-mod-n-match")
    if mm and str(mm) != "24": techs.append(f"M{mm}")
    wmin = getarg(d, "--spec-ngram-mod-n-min")
    wmax = getarg(d, "--spec-ngram-mod-n-max")
    if (wmin and str(wmin) != "16") or (wmax and str(wmax) != "32"):
        techs.append(f"W{wmin}-{wmax}")
    parts = [binl, modelo, quant, ctx]
    if quantcache: parts.append(quantcache)
    parts.extend(techs)
    return "_".join(parts)

# ---- dedup by functional signature ----
def signature(launch):
    args = [a for a in launch.get("extraArgs", [])]
    # drop alias value (positional after --alias / -a)
    cleaned = []
    skip = False
    for i,a in enumerate(args):
        if skip:
            skip = False; continue
        if a in ("--alias","-a"):
            skip = True; continue
        cleaned.append(a)
    mp = models.get(launch.get("modelProfileId"), {})
    rt = runtimes.get(launch.get("runtimePresetId"), {})
    be = backends.get(launch.get("backendProfileId"), {})
    return (
        be.get("binaryId"),
        mp.get("modelId"), mp.get("mmprojId"), (mp.get("name") or "").lower(),
        tuple(sorted(cleaned)),
        rt.get("ctx"), rt.get("ubatch"), rt.get("batch"),
        rt.get("cacheType"), rt.get("flashAttention"),
        launch.get("harnessProfileId"),
    )

seen = {}
kept = []
removed = []
for L in launches:
    sig = signature(L)
    if NODEDUP:
        kept.append(L); continue
    if sig in seen:
        removed.append((L.get("name"), seen[sig]))
    else:
        seen[sig] = L.get("name")
        kept.append(L)

# ---- assign names, disambiguate collisions ----
namecount = {}
report = []
for L in kept:
    old = L.get("name")
    new = build_name(L)
    c = namecount.get(new, 0) + 1
    namecount[new] = c
    final = new if c == 1 else f"{new}_v{c}"
    report.append((old, final))
    L["name"] = final

# Prefix each profile's display name with its 1-based order number: "<n>_<name>".
for i, L in enumerate(kept, 1):
    L["name"] = f"{i}_{L['name']}"

print(f"launches: {len(launches)}  kept: {len(kept)}  removed(dups): {len(removed)}")
print("\n--- REMOVED DUPLICATES ---")
for nm, dupof in removed:
    print(f"  x {nm!r}  (dup of {dupof!r})")
print("\n--- RENAMES ---")
for old, new in report:
    print(f"  {old!r}\n   -> {new}")

if APPLY:
    stamp = time.strftime("%Y%m%d_%H%M%S")
    bak = os.path.join(PROF, f"launches.json.prerename.{stamp}")
    shutil.copy2(os.path.join(PROF, "launches.json"), bak)
    with open(os.path.join(PROF, "launches.json"), "w", encoding="utf-8") as f:
        json.dump(kept, f, indent=4, ensure_ascii=False)
        f.write("\n")
    print(f"\nAPPLIED. backup: {bak}")
else:
    print("\nDRY RUN. re-run with --apply to write.")

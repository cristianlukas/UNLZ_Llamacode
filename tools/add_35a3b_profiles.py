#!/usr/bin/env python3
"""Append benchmark launch profiles for Qwen3.6-35B-A3B (MTP IQ4_XS), cloning the
proven Qwen-27b profile 1 (Llama.cpp 262k Q4kv MTP+NGRAM, 15/15) onto the 35B-A3B
model. Run with the app CLOSED. Idempotent (skips names already present)."""
import json, os, sys, uuid, re, datetime

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAUNCHES = os.path.join(REPO, "profiles", "launches.json")

MODEL_35A3B = "6745f7c4-a0ce-4523-938c-e3f34bdc2aab"   # Qwen3.6-35B-A3B MTP IQ4_XS (text)
BASE_ID = "5c3d9bda-8810-4331-a770-1c981461fe17"        # profile 1 (clone source)

def main():
    dry = "--apply" not in sys.argv
    raw = open(LAUNCHES, encoding="utf-8").read()
    data = json.loads(raw)
    items = data if isinstance(data, list) else data.get("items", data.get("profiles"))
    base = next(x for x in items if x["id"] == BASE_ID)
    mx = max((int(m.group(1)) for x in items for m in [re.match(r"^(\d+)_", x.get("name",""))] if m), default=0)

    def clone(name, alias, ctx_override=None, drop_ngram=False):
        c = json.loads(json.dumps(base))   # deep copy
        c["id"] = str(uuid.uuid4())
        c["modelProfileId"] = MODEL_35A3B
        c["name"] = name
        a = c["extraArgs"]
        # swap alias value
        if "--alias" in a:
            a[a.index("--alias") + 1] = alias
        if drop_ngram:
            # remove draft-mtp,ngram-mod -> draft-mtp, and strip ngram tuning flags
            if "--spec-type" in a:
                a[a.index("--spec-type") + 1] = "draft-mtp"
            i = 0
            while i < len(a):
                if a[i].startswith("--spec-ngram-mod"):
                    del a[i:i+2]
                else:
                    i += 1
        if ctx_override:
            a += ["--ctx-size", str(ctx_override)]   # last-wins over runtime preset (262k)
        return c

    plan = [
        clone(f"{mx+1}_Llama.cpp_Qwen_35A3B_Q4XS_262k_Q4kv_MTP_NGRAM", "mtp-35a3b-262k-ngram"),
        clone(f"{mx+2}_Llama.cpp_Qwen_35A3B_Q4XS_262k_Q4kv_MTP",       "mtp-35a3b-262k", drop_ngram=True),
        clone(f"{mx+3}_Llama.cpp_Qwen_35A3B_Q4XS_32k_Q4kv_MTP_NGRAM",  "mtp-35a3b-32k-ngram", ctx_override=32768),
    ]
    existing = {x.get("name") for x in items}
    add = [p for p in plan if p["name"] not in existing]
    print(("DRY-RUN " if dry else "") + "new profiles:")
    for p in add:
        print("  ", p["name"])
        print("     alias/spec:", " ".join(p["extraArgs"][p["extraArgs"].index("--spec-type"):p["extraArgs"].index("--spec-type")+2]))
    if dry:
        print("Re-run with --apply to write.")
        return
    items.extend(add)
    bak = LAUNCHES + ".bak.add35a3b." + datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    open(bak, "w", encoding="utf-8").write(raw)
    with open(LAUNCHES, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    print("added:", len(add), "backup:", bak)

if __name__ == "__main__":
    main()

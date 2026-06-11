#!/usr/bin/env python3
"""Re-link model profiles to deterministic (UUIDv5-by-path) catalog ids.

Background: the GGUF scanner used to mint a random UUID per file on every scan.
A failed catalog load triggered a rescan that overwrote the DB with fresh ids,
orphaning every profile's stored modelId (-> "No model selected" in benchmark).

The scanner now derives the id deterministically:  uuid5(NS, absolute_path).
This script rewrites profiles/models.json so each modelId/mmprojId/draftModelId
points at that same deterministic id. It maps the profile's *old* id -> path via
the catalog DB (which still maps old id -> absolute_path) and recomputes the id.

Idempotent. Writes a .bak before saving.
"""
import json, os, sqlite3, uuid, sys, glob, datetime

NS = uuid.UUID("a1b2c3d4-e5f6-4a5b-8c7d-0e1f2a3b4c5d")  # must match GGUFScanner.cpp

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_JSON = os.path.join(REPO, "profiles", "models.json")

def det_id(path: str) -> str:
    return str(uuid.uuid5(NS, path))

def find_catalog_dbs():
    roam = os.path.expandvars(r"%APPDATA%\LlamaCode\LlamaCode")
    cands = [os.path.join(roam, "model_catalog.db")]
    cands += sorted(glob.glob(os.path.join(roam, "model_catalog.db.bak.*")), reverse=True)
    return [c for c in cands if os.path.exists(c)]

def build_oldid_to_path():
    m = {}
    for db in find_catalog_dbs():
        try:
            cur = sqlite3.connect("file:%s?mode=ro" % db, uri=True).cursor()
            for mid, path in cur.execute("select id, absolute_path from catalog_models"):
                m.setdefault(mid, path)  # newest db wins (listed first)
        except Exception as e:
            print("  warn: cannot read", db, e)
    return m

def main():
    dry = "--apply" not in sys.argv
    oldid2path = build_oldid_to_path()
    print("old id -> path entries:", len(oldid2path))
    raw = open(MODELS_JSON, encoding="utf-8").read()
    data = json.loads(raw)
    items = data if isinstance(data, list) else data.get("items", data.get("profiles"))
    fields = ("modelId", "mmprojId", "draftModelId")
    changed = 0
    unresolved = []
    for mp in items:
        for f in fields:
            old = mp.get(f)
            if not old:
                continue
            path = oldid2path.get(old)
            if not path:
                unresolved.append((mp.get("name", "?"), f, old))
                continue
            new = det_id(path)
            if new != old:
                mp[f] = new
                changed += 1
    print(("DRY-RUN " if dry else "") + "fields to relink:", changed)
    if unresolved:
        print("unresolved (no path in any DB; left as-is):", len(unresolved))
        for n, f, o in unresolved[:20]:
            print("   ", n, f, o)
    if dry:
        print("\nRe-run with --apply to write changes.")
        return
    bak = MODELS_JSON + ".bak.relink." + datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(bak, "w", encoding="utf-8") as fh:
        fh.write(raw)  # original, pre-edit
    with open(MODELS_JSON, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    print("backup:", bak)
    print("written:", MODELS_JSON)

if __name__ == "__main__":
    main()

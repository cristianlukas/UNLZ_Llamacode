#!/usr/bin/env python3
"""Repoint --chat-template-file args from the volatile Roaming path to the
versioned repo copy (chat-templates/ in project root).

The Roaming\\LlamaCode\\LlamaCode\\chat-templates\\*.jinja files went missing from
the real filesystem (llama-server: "failed to open file"). The templates now
live in the repo at chat-templates/, which is stable and versioned. This rewrites
each launch profile's extraArgs so --chat-template-file points there.

Idempotent. Backs up launches.json before writing. Dry-run unless --apply.
"""
import json, os, sys, datetime, ntpath

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAUNCHES = os.path.join(REPO, "profiles", "launches.json")
NEW_DIR = os.path.join(REPO, "chat-templates")  # C:\Users\...\Documents\LlamaCode\chat-templates

def main():
    dry = "--apply" not in sys.argv
    raw = open(LAUNCHES, encoding="utf-8").read()
    data = json.loads(raw)
    items = data if isinstance(data, list) else data.get("items", data.get("profiles"))
    changed = 0
    for lp in items:
        args = lp.get("extraArgs")
        if not isinstance(args, list):
            continue
        for i, a in enumerate(args):
            if isinstance(a, str) and "chat-templates" in a and a.lower().endswith(".jinja"):
                fname = ntpath.basename(a)
                newp = os.path.join(NEW_DIR, fname)
                if not os.path.exists(newp):
                    print("  WARN missing repo template:", newp)
                if a != newp:
                    args[i] = newp
                    changed += 1
    print(("DRY-RUN " if dry else "") + "args repointed:", changed)
    if dry:
        print("Re-run with --apply to write.")
        return
    bak = LAUNCHES + ".bak.tpl." + datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    open(bak, "w", encoding="utf-8").write(raw)
    with open(LAUNCHES, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    print("backup:", bak)
    print("written:", LAUNCHES)

if __name__ == "__main__":
    main()

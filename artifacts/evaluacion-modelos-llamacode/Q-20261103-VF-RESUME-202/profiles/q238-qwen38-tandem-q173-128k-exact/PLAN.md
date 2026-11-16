# Q238 · Qwen3.8-27B Tandem · Q173 exact 128K

- Decision: determine whether this exact dual-3090 profile can sustain a valid 128K throughput point.
- Model/runtime fingerprints are pinned in `receipts/preregistration.json`; same profile as Q234/Q236/Q237.
- Protocol: exact server prompt 131072 + output128, three sequential no-cache runs, seed42. CPU fixture target131060 first.
- GPU0 ASUS + GPU1 PNY, layer split1:1; worker must be detached from Codex and cgroup-bounded.
- No Q172 or quality claim; the existing TC-74 failure remains a separate safety blocker.
- Stop on any preflight failure, exact-token mismatch, OOM, kernel/API fault, timeout or cleanup failure.
- Preregistered UTC: 2026-11-16T13:42:00Z.

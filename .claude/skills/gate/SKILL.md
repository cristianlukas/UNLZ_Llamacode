---
name: gate
description: Quality gate for LlamaCode — runs the full test suite (Release) the canonical way and reports pass/fail. Use before any commit, or when the user says "gate", "run the gate", "quality gate", "check tests before commit", or invokes /gate. Enforces the "sin test = incompleto" policy.
---

# LlamaCode quality gate

Single invocable that runs the test suite exactly the way the project requires,
so conventions never get re-derived. This is the pre-commit gate: **build + all
tests green = OK to commit. Red = stop, do not commit.**

## What this gate guarantees

The policy (CLAUDE.md): every new feature or behavior change ships with its test
(unit + integration when applicable). No test = incomplete. The gate is how that
policy is enforced mechanically.

## Steps

1. **Run the suite (Release-only policy):**
   ```
   tests.bat Release
   ```
   - `tests.bat` configures `BUILD_TESTS=ON`, builds in `build_tests/`, runs
     `ctest`. It has no `pause` → safe to run from a tool. Invoke from the repo
     root via PowerShell: `.\tests.bat Release` (heavy: full Release build +
     ctest, run in background and wait for the notification).
   - Do **not** build Debug (Release-only policy since 2026-06-18).

2. **Read the result:**
   - Configure/Build failure → report the failing target and stop. This is a red
     gate (do not commit).
   - `ctest` runs with `--output-on-failure`. Any failing test → red gate.
     Report which test(s) failed, quote the assertion/output exactly.
   - All green → `=== All tests passed ===`. Green gate.

3. **Report** a one-line verdict first (`GATE GREEN — N/N tests passed` or
   `GATE RED — <test> failed`), then details only if red.

## Conventions the gate assumes (do not re-explain, just honor)

- **Disk isolation:** tests use `QStandardPaths::setTestModeEnabled(true)` to
  redirect AppData/AppLocalData. Profiles use env var `LLAMACODE_PROFILES_DIR`,
  set in `initTestCase` **before** the first `ProfileManager` (root cached in a
  `static`).
- **Clean state:** the catalog DB persists between runs. If a test needs clean
  state it must delete the DB in `initTestCase`. If you see flaky catalog tests,
  that's the cause — fix it in the test, not in the gate.
- **Network backends:** server + client run on the same thread → never
  `waitForReadyRead`; pump the event loop (`QCoreApplication::processEvents`).
- **AgentToolRunner:** `executeTool` emits `toolExecuted`; capture with
  `QSignalSpy`. `run_shell` is async (wait on the spy).
- **One QtTest exe per subsystem** (one `QTEST_MAIN` per binary). New test =
  one file in `tests/` + one `add_lc_test(test_<area> tests/test_<area>.cpp)`
  line in `CMakeLists.txt` (section `if (BUILD_TESTS)`).

## When the gate is red

Do not commit. Either fix the failing test/code or, if a feature is missing its
test, write it (see the module→test map in CLAUDE.md), register it, and re-run
the gate. Loop until green.

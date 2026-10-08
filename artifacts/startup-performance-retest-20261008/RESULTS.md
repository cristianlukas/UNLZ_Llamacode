# LlamaCode startup investigation — 2026-10-08

## Finding from the user's launch

Source log: `/home/cristian/.local/share/LlamaCode/LlamaCode/llamacode.log`.

- QApplication and controllers were ready within 136 ms; the first window became
  visible at 7.712 s.
- The first `Main.qml` prewarm warning appeared at 35.251 s. Startup had already
  triggered the sequential prewarm of all 16 pages, including Ranking.
- The log contained 475 QML binding-loop warnings: 460 from Ranking's `Text.text`
  bindings and 15 from `Loader.active` bindings. Ranking's display helpers were
  writing into QML `property var` caches while their own text bindings ran.
- The reported 69.286 s event-loop pause was not a real pause. Log ampliado was
  activated after the GUI timer had been dormant since process start, so the
  timer counted the dormant interval as a stall. When enabled at launch, the
  monitor could also count the pre-`app.exec()` setup as its first pause.

## Changes

- Removed automatic page prewarming. Each section is constructed the first time
  it is selected, then stays active for the rest of the session.
- Made Ranking's text helpers side-effect free, which removes the binding-loop
  warning storm.
- Reset the GUI heartbeat when its monitor starts, and start the monitor only
  when the Qt event loop is about to run.
- Added normal startup timings to `llamacode.log` for registry refresh,
  hardware dispatch/readiness, catalog diagnostic/scan dispatch, benchmark
  loading/import, custom benchmarks, Research refresh, and total startup.

## Verification

The Debug Linux binary was launched with the user's existing LlamaCode data and
`QT_QPA_PLATFORM=offscreen` after the change. The final run recorded first
window visible at 6.524 s and `startupBusy=false` at 6.622 s (93 ms after the
first-frame callback); no binding-loop warnings or event-loop stall reports
were emitted. Offscreen timing is diagnostic and is not a direct GUI-vs-GUI
benchmark against the original desktop launch.

The expanded-log probe was also launched from an isolated settings/data
directory with logging enabled before startup. It completed startup in 61 ms
after the first-frame callback and emitted no false initial event-loop stall.

Automated verification: `./scripts/build-linux.sh Debug` and
`./scripts/tests-linux.sh Release` passed; 79/79 CTest tests passed, including
`qml_lazy_page_loader` and `qml_ranking_startup`. The Ranking regression test
fails on any `Binding loop detected`, `ReferenceError`, or QML assignment error.

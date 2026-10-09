# LAN gateway password controls

Task: `Q-20261009-LAN-PASSWORD-TOGGLE`

## Behavior

- LAN authentication remains enabled by default.
- The Launch page exposes **Iniciar sin contraseña** before both LAN startup paths (with a selected profile and gateway-only startup).
- When password-free mode is off, the same panel accepts a custom password/API key. A blank field keeps the current secret or generates one when LAN is enabled.
- Password-free mode bypasses gateway authentication for LAN requests even if a key remains stored; it is an explicit, persisted opt-in. Loopback gateway behavior is unchanged.
- UDP discovery continues to omit credentials.

## Verification

- Linux Debug build: OK; `/home/cristian/.cache/llamacode/build_linux/LlamaCode`, SHA-256 `964fdb43e293943265ea762d574d315f111ec9bb71814065f0cd92e293e9d71f`.
- Linux Release tests: PASS, `./scripts/tests-linux.sh Release`, 79/79 (includes the new unauthenticated-mode regression).
- Regression coverage checks that LAN stays protected by default, accepts an entered bearer key, and can be explicitly opened without a key even when a prior key remains configured.

## Files

`qml/pages/LaunchPage.qml`, `src/AppController.{h,cpp}`, `src/core/gateway/LlmGateway.{h,cpp}`, `tests/test_gateway.cpp`, `README.md`, and `docs/astra-strata.md`.

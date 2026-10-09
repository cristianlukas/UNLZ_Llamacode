# LAN authentication pairing

Task: `Q-20261009-LAN-AUTH-PAIRING`

## Diagnosis

LAN discovery found the host and its ASTRA profile, but discovery intentionally omits the host API key. The activation request therefore arrived without `Authorization` and the gateway correctly returned HTTP 401. The client had no key-entry/retry flow. A second issue was that an existing remote launch profile did not update its SecretStore entry when a key was supplied on retry.

## Changes

- Keep UDP discovery credential-free.
- When activation returns HTTP 401, show a password field in the LAN dialog and explain where to copy the key on the host (Settings → Gateway → Copy API key).
- Retry activation with the entered key. Store it under the remote profile's SecretStore reference, including for an already-created profile; later reconnects can resolve and reuse it.
- Do not enable the retry button until a key is entered. The password field masks the key while it is typed.
- Improve the 401 message to identify the authentication requirement and host-side menu path.

## Verification

- Linux Debug build: OK: `/home/cristian/.cache/llamacode/build_linux/LlamaCode`, SHA-256 `b9fd0a552f08477b50fa2ebfe37febf1f3397dd261a74e568093f0233a4e1d25`. The local launcher selects this binary first.
- Linux Release test gate: PASS: `./scripts/tests-linux.sh Release`, 79/79. Regression simulates a gateway that returns 401 without a key and verifies the supplied bearer key is sent on retry and reused on the following retry.
- No real host key was copied into test fixtures or logs. No live server or GPU was started.

## User steps

On the host, copy the key in **Configuración → Gateway → Copiar API key**. On the client, select the discovered server and ASTRA profile, paste the key when prompted after the 401, and connect. The client stores it locally in the OS-backed SecretStore for reconnects. Share the key only with trusted devices; discovery does not transmit it.

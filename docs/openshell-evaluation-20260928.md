# Evaluación de NVIDIA OpenShell para LlamaCode — 2026-09-28

## Conclusión

OpenShell aporta una frontera de ejecución más completa que el sandbox actual
de workers: combina aislamiento de filesystem y procesos, egress de red denegado
por defecto, credenciales inyectadas fuera del workload, políticas auditables y
registros de denegaciones. Es una referencia útil para endurecer el harness,
pero no es un reemplazo directo de LlamaCode: necesita Linux/macOS Apple Silicon
o Windows con WSL2 experimental, más Docker/Podman o virtualización. La
automatización de escritorio necesita interactuar con la sesión del host y no
debe quedar dentro de una caja sin desktop.

No se cambió ningún perfil de modelo, Ingi Charla ni Computer Use. No hay una
medición que demuestre que un modelo o prompt mejora con OpenShell: la ganancia
es de enforcement del runtime. Para un agente local de código, el concepto sí
supera el alcance actual de `worker.sandbox=strong`; la integración sería una
opción de runtime separada, con dependencias explícitas, no un cambio silencioso
del default.

## Qué ya cubren nuestras pruebas

- [`docs/harness.md`](harness.md) describe `worker.sandbox=process|strong`,
  capacidades brokered de workers, timeout, revocación y fail-closed si el
  sandbox pedido no está disponible.
- [`docs/computer-use-sandwich.md`](computer-use-sandwich.md) registra pruebas
  adversariales de Computer Use con instrucciones inyectadas en una página,
  permisos y secretos. En Qwen3.5-9B, `state-first` y `sandwich` obtuvieron
  100% de seguridad en el corpus difícil; el sandwich fue 29,7% más lento.
  Esas pruebas miden decisiones del modelo, no confinamiento del proceso.
- [`docs/opensourcejev-computer-use-audit-20260921.md`](opensourcejev-computer-use-audit-20260921.md)
  y [`docs/row-bot-computer-use-audit-20260918.md`](row-bot-computer-use-audit-20260918.md)
  son auditorías de Computer Use, no pruebas de un sandbox de sistema.
- [`docs/harness-quality-campaign-20260915.md`](harness-quality-campaign-20260915.md)
  mide calidad agentiva y convergencia por modelo; no mide límites de SO.

Esta distinción evita repetir la misma prueba: los corpus de Computer Use no
deben usarse como evidencia de que shell, filesystem o red quedaron aislados.

## Prueba nueva y hallazgos

El 2026-09-28 se ejecutó el layout de bubblewrap equivalente a
`HarnessSandbox::plan()` en este checkout Linux:

```bash
bwrap --die-with-parent --new-session --unshare-pid --unshare-ipc \
  --unshare-uts --unshare-cgroup-try --ro-bind / / --proc /proc --dev /dev \
  --tmpfs /tmp --bind "$PWD" /workspace --chdir /workspace --unshare-net \
  /bin/sh -c 'test -r README.md'
```

Resultado inicial: **no arranca**; bubblewrap informa que no puede crear
`/workspace` porque el root ya está montado de sólo lectura. El mountpoint debe
crearse dentro del `/tmp` tmpfs antes del bind. Se corrigió el plan para montar
el workspace en `/tmp/llamacode-workspace` y se agregó la prueba de regresión
`strongSandboxStartsWithWorkspaceUnderTmpfs()` en
`tests/test_harness_worker_protocol.cpp`.

Una prueba manual con ese orden de mounts pudo leer el workspace y confirmó que
la red externa queda bloqueada con `--unshare-net`. También confirmó que
`/home/cristian/.profile` sigue siendo legible: el root de sólo lectura es todo
el filesystem del host. Por lo tanto, esta corrección repara el arranque pero
no convierte bubblewrap en un sandbox de datos equivalente a OpenShell. Una
futura implementación `strong` debe acotar las rutas visibles a las necesarias
para runtime + workspace, y debe demostrar cómo aplica los límites de memoria,
procesos y CPU antes de prometerlos. La configuración actual no instala una
política de egress por ejecutable ni un broker de secretos.

Después del cambio, `test_harness_worker_protocol` pasó con el caso nuevo de
arranque real de bubblewrap. El gate completo `scripts/tests-linux.sh Release`
pasó **77/77**; el primer intento sobre la caché configurada de la notebook se
atascó porque esa caché resuelve a NTFS, así que se repitió con
`LC_TEST_BUILD_DIR=/tmp/llamacode-tests-linux`. También compiló el binario Debug
Linux en `/tmp/llamacode-build-debug/LlamaCode`.

## Comparación práctica

| Área | LlamaCode hoy | OpenShell (documentación consultada) | Aplicación recomendada |
|---|---|---|---|
| Workers Node/Python | Broker de capabilities y timeout; bubblewrap optativo en Unix; Job Object en Windows | Supervisor separado del agente, Landlock/seccomp, identidad de proceso | Mantener workers nativos; usar OpenShell como backend optativo para tareas de código de mayor riesgo |
| Filesystem | El broker valida tools; el proceso `strong` ve el root host en RO y el workspace en RW | Landlock con paths explícitos de sólo lectura/escritura | No declarar el worker `strong` como equivalente a un filesystem allowlist; cerrar la exposición fuera del workspace |
| Red | `strong` puede descompartir la red; no hay regla por host/binario para workers | Egress denegado por defecto, reglas por host, puerto y binario, inspección L7 opcional | Adoptar el contrato “deny, explicar política y no reintentar” al integrar un gateway real |
| Credenciales | Secretos cifrados para backends cloud, fuera del contrato de worker | Proxy/supervisor inyecta credenciales sólo hacia endpoints autorizados | No pasar tokens al entorno del worker; documentar y probar cualquier excepción |
| Computer Use | UI Automation/browser opera sobre el desktop real; approvals y evidencia | El sandbox contiene procesos, pero no reemplaza el control semántico del desktop | No encerrar el controlador de desktop en un contenedor sin puente explícito a la sesión |
| Ingi Charla | STT/chat/TTS; usa agente si la sesión activa lo tiene | No añade calidad de voz ni selección de modelo | Sin cambio: sólo aplica si Charla invoca tools de agente que ejecutan código |
| Modelos | Evaluaciones de calidad/tool use por perfil | No es un modelo ni un prompt | Sin cambio de modelos/perfiles por esta investigación |

## Recomendación de producto

1. Conservar los resultados de calidad de Computer Use y de modelos como
   evidencia separada de la seguridad del runtime.
2. Corregir y probar el mountpoint de `strong` (incluido en este cambio).
3. Antes de ampliar el uso de `strong`, cerrar y probar acceso a archivos del
   host fuera del workspace y definir enforcement verificable para límites de
   recursos. Si una garantía no está implementada, el perfil debe rechazarla en
   vez de aceptarla silenciosamente.
4. Evaluar un backend OpenShell opcional para el harness de código en un host
   con Docker/Podman, sin activarlo por defecto. Comparar tareas equivalentes:
   lectura/escritura del workspace, lectura fuera del workspace, egress
   permitido/denegado, acceso a secretos y terminación/cancelación. Guardar
   logs y configuración junto al resultado para no confundir fallo de modelo
   con fallo del runtime.
5. Mantener Ingi Charla y Computer Use en el host, limitando sus tools según el
   perfil y la aprobación del usuario. No cambiar sampling ni perfiles de modelo.

## Fuentes primarias consultadas

- [Repositorio NVIDIA/OpenShell](https://github.com/NVIDIA/OpenShell): quickstart,
  plataforma requerida y telemetría (desactivable con
  `OPENSHELL_TELEMETRY_ENABLED=false`).
- [OpenShell Security Best Practices](https://docs.nvidia.com/openshell/latest/security/best-practices):
  capas de red, filesystem, proceso y credenciales; egress por defecto denegado.
- [OpenShell Network Rules](https://docs.nvidia.com/openshell/dev/how-it-works/policies/network-rules):
  reglas por binario/endpoint, denegaciones y controles de requests.

La fuente del producto consultada publica OpenShell `v0.1.2`. Los detalles de
`dev` pueden cambiar; cualquier integración debe fijar una versión, comprobar la
matriz de soporte y revisar los valores por defecto de esa versión antes de
habilitarla.

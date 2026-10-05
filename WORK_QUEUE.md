> Fuente canónica del protocolo/cola para este repo: este archivo. No editar el espejo ext4 salvo migración coordinada.

# Cola secuencial de trabajo

Este archivo es la fuente única de cola y registro. Ruta canónica: `/media/cristian/7CFE1E0FFE1DC1F6/Users/cristian/Documents/LlamaCode/WORK_QUEUE.md`. Sólo una persona/agente puede tener una tarea activa, editar el repo, lanzar pruebas o usar recursos exclusivos (por ejemplo GPU) a la vez.

## Protocolo

1. **Leer primero** este archivo y comprobar que no exista `WORK_QUEUE.lock` junto a él. No empezar trabajo compartido, builds, benchmarks, descargas ni ediciones sin reclamar turno.
2. **Reclamar atómicamente** creando `WORK_QUEUE.lock` con creación exclusiva (`open(..., 'x')` / `O_CREAT|O_EXCL`). Si ya existe, no tocarlo ni trabajar en la tarea compartida; agregar la solicitud a `Pendientes` sólo después de adquirir el lock. El lock registra responsable, host, hora UTC, task id y token; usa id de tarea lógico, no un PID efímero.
3. Con el lock adquirido, editar este archivo: cambiar una fila `Pendiente` a `Activa` y anotar responsable, hora de inicio, alcance y recursos reservados. Sólo el dueño de ese token modifica la cola o libera el lock.
4. Trabajar una tarea completa de punta a punta. Registrar comandos/resultados verificables, archivos modificados, riesgos y punto de reanudación. No lanzar otra tarea concurrente mientras el estado sea `Activa`.
5. Al cerrar, marcar `Completa` o `Bloqueada` con evidencia. En caso de bloqueo, dejar la próxima acción exacta y qué cambio externo la habilita. Luego borrar el lock sólo si su token sigue siendo el propio.
### Reclamo y liberación exactos

Desde la carpeta del archivo, un trabajador genera un token nuevo y ejecuta esto antes de tocar el repo o reservar recursos:

```python
import os, json, uuid, datetime, socket
path = "WORK_QUEUE.lock"
token = str(uuid.uuid4())
record = {"token": token, "worker": "nombre o id de tarea", "host": socket.gethostname(),
          "claimed_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}
fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
os.write(fd, (json.dumps(record, indent=2) + "\n").encode())
os.fsync(fd)
os.close(fd)
print(token)
```

`FileExistsError` significa **esperar**; no borrar, reemplazar ni editar el lock. Una vez tomado, poner ese mismo `token` en la fila de Cola. Al terminar, verificar que el token del archivo siga siendo propio y quitarlo de forma explícita:

```python
import json, pathlib
p = pathlib.Path("WORK_QUEUE.lock")
assert json.loads(p.read_text())["token"] == "TOKEN-DEL-TRABAJADOR"
p.unlink()
```

El token identifica al trabajador lógico; un PID de un comando breve no sirve como dueño del turno. Si el lock queda tras una caída, aplicar recuperación manual del paso 7.

6. Si hay lock y llega una nueva tarea, enviarla al dueño activo para que la agregue como `Pendiente`; no modificar a la vez este archivo. La siguiente tarea sólo cambia a `Activa` después de que el dueño anterior registre su cierre y libere el lock.
7. **No robar locks por antigüedad.** Si queda uno huérfano, verificar que el turno propietario terminó y registrar recuperación en el historial; renombrar el lock a `WORK_QUEUE.stale-<UTC>.lock`, nunca borrarlo silenciosamente. Si no se puede verificar, detenerse y pedir coordinación.
8. Lecturas estrictamente independientes pueden prepararse antes del turno sólo si no consumen GPU, no modifican archivos y no interrumpen al dueño. Para mantener orden estricto, preferir también encolarlas.

### Plantilla de entrada

`Q-YYYYMMDD-NNN | Pendiente | título | solicitante | dependencias | recursos`

## Cola

| ID | Estado | Tarea | Responsable | Inicio UTC | Recursos/dependencias | Resultado / reanudación |
|---|---|---|---|---|---|---|
| Q-20261004-001 | Bloqueada | Completar evaluación Strata/Qwen3.8 NVFP4; corregir informe previo con resultados reproducibles | Codex current conversation | 2026-10-04T05:15:19Z | Próxima reanudación: resolver procedencia del checkpoint local y disponer de ~280 GiB libres (o un volumen alternativo); luego build Linux/CUDA sm_86 y GPU | Prueba parcial: smoke HTTP respondió; HE0 falló 0/1 con watchdog/`Connection refused`; segundo arranque `auto:2048` sin endpoint a ~549 s y detenido. No correr HE20/BCB8/ADV ni promover. Informe `docs/strata-nvfp4-fork-audit-20261004.md`; detalles y artefactos en `artifacts/strata-nvfp4-evaluation-20261003/`. |
| Q-20261004-STRATA | Completa | Reanudar evaluación e integración Strata UD-Q4; completar pruebas válidas y mejoras LlamaCode | Codex current task | 2026-10-04T03:34:41.354661+00:00 | Token `repo-strata-0937b860-61cc-421c-8159-a3f815748833`; GPU/benchmarks reservados por este turno | Build Debug y gate Linux 77/77; thinking igualado; HE0 1/1; HE20 19/20 aceptadas pero timeout a 1801 s (gate inválido, BCB bloqueado); ADV 10/10 tras 2 reparaciones, pero 3.84× más lento que SOL. Informe `docs/strata-udq4-38ram-lch1-20261004.md`; mantener perfil experimental y no promover. |
| Q-20261004-ORCA | Bloqueada | Retomar evaluación `orcarouter/Qwen3.8-Flash-Next-Uncensored-GGUF` IQ3_XXS: reanudar shard 2 si hace falta, verificar hashes, empaquetar con Strata y correr LC-H1 comparable | Codex current conversation | 2026-10-04T06:01:37.589689+00:00 | Token `7832db20-61e0-44d7-a122-90edf551b5eb`; slot GPU liberado al cerrar; requiere corregir el entorno del harness antes de reanudar | Ambos shards descargados y SHA-256 verificado; pack IQ3_XXS y smoke HTTP válidos; HE0 1/1 tras 1 reparación; HE20 timeout duro a 1801.1 s con 8/20 aceptaciones, inválido para el gate; BCB8 no ejecutada por bloqueo; ADV v1 falló infraestructura a 86 s (límite 64K pre-tool e imports ausentes). Informe `docs/orcarouter-qwen38-iq3_xxs-lch1-20261004.md`; siguiente paso: disponibilidad `python`/`python3` e imports en `run_shell`, corregir/entender límite pre-tool y repetir HE20 → BCB8 → ADV con mismo fingerprint. |
| Q-20261004-DUALGPU | Completa | Completar validación LlamaCode LC-H1 del fork Strata-DualGPU (igualar thinking con SOL, HE0→HE20→BCB8 y adversarial; actualizar auditoría; no promover perfiles sin pasar gates) | Codex current conversation | 2026-10-04T07:52:51.275063+00:00 | Token `repo-dualgpu-c943adb2-39cd-452b-83e6-0374c85dbeac`; GPU/benchmarks liberados 2026-10-04T08:58:17+00:00; depende de Q-20261004-STRATA (Completa) | HE0 1/1; HE20 20/20; BCB8 8/8; ADV 10/10; sin timeouts, thinkingEnabled=true y HarnessSpec igual a referencia. Sin promoción: HE20 y ADV más lentos que Strata 0.1.35 en una sola corrida. Informe `docs/strata-dualgpu-lch1-20261004.md`; resultados en `artifacts/strata-dualgpu-lch1-20261004/`. |

| Q-20261005-TABLE | Completa | Sincronizar los resultados finales Strata v0.1.39 Q4/Orca LC-H1 en la tabla comparativa externa | Codex current conversation | 2026-10-05T02:37:55.252839+00:00 | Token `f372fb28-209d-4583-8481-a45ead611fec`; sólo lectura repo y edición del Markdown solicitado; sin GPU | Tabla verificada y complementada con A/B de Q4 vs SOL, tiempos totales, decisión de no promoción y estado NVFP4 sin lock activo; 39 enlaces locales presentes; sin benchmarks/GPU. |

## Historial

- 2026-10-04T07:47:43Z — Q-20261004-ORCA bajo token `7832db20-61e0-44d7-a122-90edf551b5eb`: shards 1 y 2 verificados con LFS SHA-256; creado pack Strata IQ3_XXS y perfil temporal; HE0 1/1 (una reparación), HE20 agotó 1800 s con 8/20 artefactos aceptados y no pasa el gate; BCB8 quedó bloqueada por gate; ADV v1 falló infraestructura al alcanzar 64K de salida previa a herramientas con imports ausentes. Servidor detenido y VRAM libre; perfil temporal eliminado y ASTRA restaurado. Q-ORCA queda Bloqueada; reanudar cuando se corrijan las dependencias/guardas del harness. Informe `docs/orcarouter-qwen38-iq3_xxs-lch1-20261004.md`.

- 2026-10-04T03:20:29.366362+00:00 — creado el protocolo y reclamado Q-20261004-STRATA mediante creación exclusiva del lock.

- 2026-10-04T03:25:23Z — corrección de timestamp registrada bajo lock de seguimiento; protocolo usado con creación exclusiva; no se forzó el montaje NTFS. Suplemento y helper seguro guardados en ext4. Estado `Bloqueada` hasta recuperación del disco; lock liberado después de verificar el token.

- 2026-10-04T03:25:42.502734+00:00 — lock temporal de seguimiento adquirido y liberado por queue-timestamp-correction-8bb19c21-a48a-4b40-ae94-50d101640bc3 tras registrar la corrección.

- 2026-10-04T03:32:53.875352+00:00 — reanudado Q-20261004-STRATA con creación exclusiva del lock `resume-strata-9645efc1-fd84-4a09-b49b-b094ad72e627` después de recuperar los volúmenes.

- 2026-10-04T03:43:40.797739+00:00 — agregado Q-20261004-ORCA como Pendiente a pedido del usuario; lock/dueño activo Q-20261004-STRATA sin cambios.

- 2026-10-04T03:45:21.673835+00:00 — agregado Q-20261004-DUALGPU como Pendiente a pedido del usuario; el lock Q-20261004-STRATA se mantiene.
- 2026-10-04T05:14:16Z — completada Q-20261004-STRATA bajo el token `repo-strata-0937b860-61cc-421c-8159-a3f815748833`: HE0 1/1; HE20 expiró con 19/20 artefactos y no habilita BCB8; ADV 10/10 tras dos reparaciones, 2051.8 s contra SOL 534.9 s. Se documentó la comparación y la corrección del fingerprint de thinking; no se promueve Q4. Daemon cerrado; lock liberado después de verificar su token.
- 2026-10-04T05:15:00Z — Q-20261004-001 reclamada atómicamente por Codex con token `repo-nvfp4-08279a20-178b-443e-9c46-27741d5a263b` tras cerrar y liberar Q-20261004-STRATA.
- 2026-10-04T05:25:05Z — auditada la candidata Strata NVFP4: fork `sergqwer/strata-nvfp4` commit `992195498c16ea2b26c08bf1ba2402291553136f`; rutas RTX 20/30/40 probadas por emulación en RTX 5090, build/release publicado Windows/CUDA 13.3; local CUDA 12.0, Linux, 2×3090 y sólo 27 GiB libres en el volumen de modelos. El staging pide ~280 GiB; no se descarga ni se borran modelos. Pendiente de espacio alternativo para continuar.
- 2026-10-04T05:55:00Z — bajo el token `repo-nvfp4-08279a20-178b-443e-9c46-27741d5a263b` se probó el artefacto NVFP4 ya instalado: smoke HTTP correcto; HE0 aislado 0/1 por watchdog/desconexión; segundo arranque con prefill 2048 sin endpoint a ~549 s, detenido. La procedencia del checkpoint no está demostrada (artefacto local rotulado NVIDIA; tarea de cola refiere OrcaRouter). Se liberaron RAM/VRAM y daemon. Q-001 queda Bloqueada hasta fijar procedencia y resolver el requisito de almacenamiento. Informe actualizado en `docs/strata-nvfp4-fork-audit-20261004.md`; no se ejecutaron suites posteriores ni cambios de producción.

- 2026-10-04T06:01:37.589689+00:00 — Q-20261004-ORCA activada después de que Q-20261004-001 quedó Bloqueada y liberó el lock; token `7832db20-61e0-44d7-a122-90edf551b5eb`. Primero se validan montajes y parcial de descarga; aún no se reservó GPU.

- 2026-10-04T07:52:51.275063+00:00 — Q-20261004-DUALGPU activada tras confirmar que el lock estaba libre y que era la tarea Pendiente más antigua; token `repo-dualgpu-c943adb2-39cd-452b-83e6-0374c85dbeac`.

- 2026-10-04T08:58:17+00:00 — Q-20261004-DUALGPU completada bajo el token `repo-dualgpu-c943adb2-39cd-452b-83e6-0374c85dbeac`. HE0 1/1, HE20 20/20, BCB8 8/8 y ADV 10/10; todas finalizaron sin timeout con thinking activado y HarnessSpec igual a referencia. Sin promoción por menor rendimiento end-to-end en HE20/ADV y falta de A/B repetido; servidor parado y VRAM liberada. Informe `docs/strata-dualgpu-lch1-20261004.md`.

- 2026-10-05T02:37:55.252839+00:00 — Q-20261005-TABLE activada atómicamente por Codex con token `f372fb28-209d-4583-8481-a45ead611fec` para verificar y actualizar la tabla comparativa externa contra los informes/recibos finales Q4/Orca; sin uso de GPU.
- 2026-10-05T02:40:32.031899+00:00 — Q-20261005-TABLE completada bajo token `f372fb28-209d-4583-8481-a45ead611fec`. Se contrastó la tabla externa con `docs/strata-udq4-38ram-lch1-20261004.md`, `docs/orcarouter-qwen38-iq3_xxs-lch1-20261004.md` y el A/B SOL del 3 oct.; se añadió resumen comparable: Q4 30/38 vs SOL 29/38 en primera pasada, 38/38 vs 37/38 final y 5344.735 s vs 1534.200 s (3.484×). Se aclaró que una sola corrida y runtimes distintos no justifican promoción. Se corrigió el estado histórico NVFP4 para no afirmar lock/tarea activos. Markdown verificado y 39 enlaces locales existentes; no se usó GPU ni se repitieron benchmarks. Archivo actualizado: `/home/cristian/.codex/visualizations/2026/10/03/01a102f1-2c06-71d2-89a8-77a0030ac725/comparativa-modelos-lch1-ampliada-20261004.md`.

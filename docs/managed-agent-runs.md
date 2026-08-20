# Corridas administradas de Claude Code y Codex

LlamaCode puede iniciar una corrida larga de un CLI externo desde **Agente →
🚀 Corridas** o mediante `ControlApi`. La corrida no depende de que una ventana
de terminal permanezca abierta: `ManagedAgentRunStore` conserva el proceso,
observa stdout/stderr y publica el mismo estado en QML y en la API headless.

Esto complementa, no reemplaza, el `AgentRunStore` del backend nativo: el
primero supervisa procesos Claude/Codex; el segundo mantiene leases y journal
de los turnos del agente local.

## Contrato

La entrada mínima es:

```json
{
  "runtime": "claude",
  "prompt": "Revisá el diff y devolvé riesgos priorizados.",
  "workspace": "C:/proyectos/app"
}
```

También acepta `codex`, `cliPath`, `ownerId`, `taskId`, `agentProfileId`,
`model`, `applyEdits`, `approvalMode` y `presentation`. El runtime sólo puede
ser `claude` o `codex`; el workspace debe existir y el prompt tiene un límite
de 200000 caracteres.

Cada corrida queda en:

```text
<AppLocalData>/managed-agent-runs/<runId>/
  prompt.md
  manifest.json
  stdout.log
  stderr.log
```

El manifiesto no duplica el prompt: guarda su ruta, tamaño y SHA-256. Al
cerrar la corrida se agrega un registro a `RunHistoryStore`, con metadata de
runtime, workspace, postura de permisos y rutas de artefactos. Por eso una
corrida puede exportarse luego como parte de `llamacode.evidence.v1`.

## Seguridad y visibilidad

- El default es `plan` para Claude y una intención de lectura para Codex.
- `applyEdits` es explícito. Claude usa `acceptEdits`; no se activa
  `bypassPermissions` automáticamente.
- Codex sólo recibe `--full-auto` si además se envían explícitamente
  `approvalMode: "super"` y `allowDangerous: true`.
- `visibleProof` distingue `managed_panel` de una ventana de escritorio. Ver
  un proceso en LlamaCode no se presenta como prueba de que el CLI tenga una
  ventana visible.
- Si LlamaCode se cierra, las corridas que estaban activas se recuperan como
  `stale` al iniciar. No se relanzan solas ni se inventa un resultado final.

La implementación sigue el patrón útil de Hermes Valkyrie —prompt durable,
manifiesto, watcher y closeout— pero usa `QProcess`, `RunHistoryStore` y las
políticas de aprobación propias de LlamaCode, sin depender de tmux ni de
flags de bypass.

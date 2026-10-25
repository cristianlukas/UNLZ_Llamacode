# Q112 · resultado de viabilidad del fixture tenant

**Estado:** bloqueo confirmado por contrato ausente; auditoría estática 6/6 PASS. No se ejecutó prueba de comportamiento, build, servidor, modelo ni GPU.

La revisión de los siete archivos preregistrados confirma que la ruta MCP actual no transporta un principal autenticado ni aplica autorización por recurso/tenant en el dispatcher local. `AgentSession` contiene datos de sesión/proyecto, no identidad autenticada. `McpClient::callTool` envía nombre y argumentos y sólo incluye claves de idempotencia/correlación en `_meta`. `AgentToolRunner` resuelve server/tool, aplica las anotaciones de seguridad y ledger de idempotencia, y luego llama al server; no puede decidir acceso por tenant sin un principal confiable y una policy real.

Q78 ya había documentado este límite. Los hashes del estado actual se registraron en Q112 y no cambiaron entre preregistro y auditoría. No se simula un tenant en argumentos del modelo ni se finge que una prueba local demuestre autorización del servidor MCP. La autorización independiente del MCP server no se inspeccionó y queda desconocida.

**P2.1 sigue abierto y bloqueado.** Para habilitar la prueba hacen falta: (1) principal autenticado provisto por host confiable; (2) propagación no falsificable hasta el ejecutor/server; (3) policy de autorización por recurso; (4) integración que compruebe same-tenant allow y cross-tenant read/write deny antes del side effect, con estado y auditoría verificados. Hasta entonces no hay fixture local válido.

Evidencia: `receipts/q112-static-audit.json`; preregistro Sheets en `Evaluaciones LlamaCode!A333:J333`; Q78 `RESULTS.md` y `receipts/static-audit.json`.

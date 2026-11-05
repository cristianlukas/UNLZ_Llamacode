#pragma once
#include <QByteArray>
#include <QString>
#include <QStringList>
#include <QVariantList>
#include <QVariantMap>

// Adaptador opcional a agent-desktop (github.com/vercel-labs/agent-desktop), un
// CLI de computer use por árbol de accesibilidad con refs estables.
//
// Por qué: el recorrido AT-SPI propio (LinuxDesktopBackend) lanza un `gdbus`
// por cada propiedad de cada nodo y filtra por coordenadas de pantalla, que GTK4
// no publica en X11. Contra la Calculadora de GNOME (GTK4) en Xvfb no encontró
// ni un control en 8 s; agent-desktop 1.2.0 sacó los 36 en 62 ms e hizo 3×3=9
// sin mover el mouse 5/5 (docs/charla-multitarea-computer-use-20261105.md).
//
// Si el binario está instalado, LinuxDesktopBackend lo usa primero y conserva
// AT-SPI como fallback. Los controlId que salen de acá llevan el prefijo "ad:".
namespace AgentDesktopCli {

// Ruta del binario: $LLAMACODE_AGENT_DESKTOP, AppLocalData/tools/agent-desktop/
// o el PATH. Vacío = no instalado.
QString binaryPath();
bool available();

// Corre `agent-desktop <args>` y devuelve el `data` del sobre JSON; ok=false con
// el mensaje de error del sobre (o del proceso) en *error.
QVariant run(const QStringList &args, QString *error = nullptr, int timeoutMs = 8000);

// ── Puras (testeables sin el binario) ──
// Sobre JSON {"ok":..,"data":..,"error":{"message":..}} → data o error.
QVariant parseEnvelope(const QByteArray &json, QString *error);
// Id de ventana de agent-desktop para el proceso dueño de la ventana X11.
QString windowIdForPid(const QVariant &listWindowsData, qint64 pid);
// Árbol de `snapshot --include-bounds` → filas con el formato de
// DesktopAutomationBackend::controls() (controlId "ad:@snap:eN").
QVariantList rowsFromSnapshot(const QVariant &snapshotData, const QString &query, int max);
// Comando y argumentos de agent-desktop para una acción de desktop_control_action.
// Vacío si la acción no tiene equivalente.
QStringList actionArgs(const QString &ref, const QString &action, const QString &value);

inline bool isControlId(const QString &id) { return id.startsWith(QLatin1String("ad:@")); }
inline QString refFromControlId(const QString &id) { return id.mid(3); }

// ── Con el binario ──
QVariantList controlsForPid(qint64 pid, const QString &query, int max, QString *error);
bool controlAction(const QString &controlId, const QString &action, const QString &value,
                   QString *error, QVariantMap *trace);

} // namespace AgentDesktopCli

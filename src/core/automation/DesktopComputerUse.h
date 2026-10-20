#pragma once

#include <QJsonObject>
#include <QList>
#include <QLockFile>
#include <QRect>
#include <QString>
#include <QStringList>
#include <QVariantList>
#include <QVariantMap>

#include <memory>

// Contratos compartidos por la percepción, la ejecución y la auditoría de
// Computer Use. Se mantienen en un módulo pequeño para que AgentToolRunner,
// Teach y Tasks no tengan que inventar formatos levemente distintos.
namespace DesktopComputerUse {

struct TargetRef {
    QString snapshotId;
    QString windowId;
    QString controlId;
    QString automationId;
    QString name;
    QString role;
    QString windowTitle;
    qint64 pid = 0;
    QRect bounds;
    bool enabled = true;
    bool password = false;

    QVariantMap toVariantMap() const;
    static TargetRef fromVariantMap(const QVariantMap &map);
};

struct Snapshot {
    QString snapshotId;
    QString scopeKind;
    QString targetId;
    QString provider;
    QString fingerprint;
    qint64 createdAt = 0;
    QVariantMap target;
    QVariantList windows;
    QVariantList controls;
    QVariantMap focus;
    QVariantMap capture;

    QVariantMap toVariantMap() const;
    QJsonObject toJson() const;
};

struct ActionReceipt {
    QString receiptId;
    QString tool;
    QString status;
    QString strategy;
    QString snapshotId;
    QString sessionId;
    QString correlationId;
    QString payloadHash;
    QString resultHash;
    QString detail;
    qint64 createdAt = 0;
    QVariantMap target;

    QVariantMap toVariantMap() const;
};

struct SessionLease {
    QString leaseId;
    QString sessionId;
    QString scopeKind;
    QString targetId;
    qint64 expiresAt = 0;
    int maxActions = 200;
    int actions = 0;
    bool active = true;

    bool consume();
    QVariantMap toVariantMap() const;
};

// Exclusión entre procesos para el escritorio interactivo. El mutex que
// serializa tools dentro de AgentToolRunner no alcanza cuando conviven una
// instancia GUI y un daemon/Task separado.
class ProcessSessionGuard final
{
public:
    ProcessSessionGuard() = default;
    ~ProcessSessionGuard();

    ProcessSessionGuard(const ProcessSessionGuard &) = delete;
    ProcessSessionGuard &operator=(const ProcessSessionGuard &) = delete;

    bool acquire(QString *error = nullptr);
    void release();
    bool isHeld() const;

    static QString lockPath();

private:
    std::unique_ptr<QLockFile> m_lock;
};

QString stableHash(const QVariantMap &value);
// IDs from desktop_windows/desktop_launch are JSON strings. Small models may
// emit an all-digit HWND as a JSON number; preserve its decimal text so the
// normal window-id parser can still resolve the same hexadecimal handle.
QString targetIdText(const QJsonValue &value);
// UIA control IDs are opaque strings and may contain dots (for example,
// "42.72462"). Some models serialize those IDs as JSON numbers; preserve the
// shortest round-trippable JSON number text so the exact ID can still resolve.
QString controlIdText(const QJsonValue &value);
QString snapshotId(const QString &scopeKind, const QString &targetId,
                   const QVariantMap &target, const QVariantList &windows,
                   const QVariantList &controls);
// A window-scoped snapshot is tied to its selected window and control tree,
// not to unrelated desktop windows whose Z-order can change between calls.
QVariantList snapshotIdentityWindows(const QString &scopeKind,
                                     const QVariantMap &target,
                                     const QVariantList &visibleWindows);
// Presentation may filter the controls sent to the model; snapshot identity
// uses the canonical full-tree controls used again during validation.
QVariantList snapshotIdentityControls(const QVariantList &presentedControls,
                                      const QVariantList &canonicalControls);
bool snapshotMatches(const QString &expected, const QString &actual, QString *error = nullptr);

ActionReceipt makeReceipt(const QString &tool, const QJsonObject &args, bool ok,
                          const QString &result, const QString &sessionId,
                          const QString &correlationId, const QString &strategy = QString(),
                          const QString &snapshot = QString(),
                          const QVariantMap &target = {});

bool isDesktopTool(const QString &name);
// Alcance efectivo de una tool de escritorio. Si el modelo no pasó scope_kind
// pero el target_id es una VENTANA conocida, es "window": con el default
// "screen" desktop_read_text OCReaba la pantalla entera (otras apps incluidas)
// en vez de la ventana pedida.
QString inferScopeKind(const QString &explicitKind, bool targetIsWindow,
                       const QString &fallback);
// ¿Se puede teclear sin target_id? Sólo si la ventana en primer plano es la que
// el agente eligió o pertenece al mismo proceso elegido (p. ej. diálogo modal).
// Un PID conocido distinto siempre bloquea, incluso si Windows reutilizó el HWND.
// foreground vacío = desconocido (Linux): se acepta sólo si el agente enfocó algo.
bool typingTargetAllowed(const QString &foregroundId, const QString &agentFocusedId,
                         qulonglong foregroundPid = 0, qulonglong selectedPid = 0);
// Señal segura para el modelo cuando una tecla activa otra ventana (por ejemplo,
// un diálogo modal). No incluye títulos, HWND ni datos visibles de la ventana.
QString keyFocusChangeHint(const QString &beforeId, qulonglong beforePid,
                           const QString &afterId, qulonglong afterPid,
                           qulonglong selectedPid);
// ¿Hay que volver a enfocar la ventana elegida antes de teclear? Cuando el
// foco se fue a otra (típico: el usuario aprobó la tool en LlamaCode) pero el
// agente YA había elegido una: re-enfocarla escribe donde el agente decidió,
// sin tirar un error que el modelo chico no sabe resolver.
bool typingNeedsRefocus(const QString &foregroundId, const QString &agentFocusedId);
// 1..3 pulsaciones (simple, doble, triple); cualquier otro valor se acota.
int clampClickCount(int clickCount);
// Nombre "humano" de una app → lo que entiende `start` en Windows. El modelo
// pedía desktop_launch "calculator": no es un ejecutable, Windows abría su
// diálogo de error (ventana "calculator" de 572x140) y el agente tecleaba ahí.
// Sin alias conocido devuelve el nombre tal cual.
QString launchAlias(const QString &app);
// Identidad estable de una solicitud de lanzamiento para bloquear sólo
// repeticiones exactas, sin impedir abrir otro documento en la misma app.
QString launchTargetIdentity(const QString &app, const QString &args);
// Separa argumentos extra respetando comillas antes de pasarlos al launcher.
// Mantiene como un solo argumento valores con espacios (por ejemplo, rutas).
QStringList splitLaunchArguments(const QString &args);
// ¿Es una ruta o una URI de shell (ms-settings:, https:...) en vez de un nombre
// a resolver por PATH/App Paths?
bool launchTargetIsPathOrUri(const QString &program);
// Qué ventana abrió un desktop_launch, comparando el inventario de ventanas de
// antes y después de lanzar (filas de DesktopAutomationBackend::windows()):
//  - la ventana NUEVA; si hay varias, la que se parece a la app (título) y si
//    no, la más grande;
//  - un diálogo del sistema (#32770) nuevo es Windows avisando un error, NO la
//    app: se devuelve con "dialog"=true (el agente lo tomaba por la app);
//  - sin ventana nueva, una ya abierta que se parezca a la app ("existing"=true,
//    apps de instancia única).
// Vacío = todavía no hay nada que reportar.
QVariantMap pickLaunchedWindow(const QVariantList &before, const QVariantList &after,
                               const QString &app);
// Si una app reemplaza su splash por un HWND principal, resuelve la ventana
// visible más grande del mismo proceso que el agente ya lanzó/eligió.
QVariantMap largestWindowForProcess(const QVariantList &windows, qulonglong pid,
                                    const QString &excludeId = {});
// Conserva la ventana elegida si el HWND sigue perteneciendo al proceso; si
// Windows lo reemplazó o reutilizó, busca otra ventana sólo en ese proceso.
QVariantMap resolveSelectedWindow(const QVariantList &windows, const QString &selectedId,
                                  qulonglong pid);
// PID de la ventana elegida: conserva el conocido al iniciar una app, aunque
// su HWND haya desaparecido del inventario durante el reemplazo del splash.
qulonglong selectedWindowProcessId(const QVariantList &windows, const QString &selectedId,
                                   qulonglong knownPid = 0);
// Limita el tamaño del árbol UIA que vuelve al contexto del modelo.
int clampControlLimit(int requested, int fallback = 32);
// Texto de desktop_launch para el modelo según la ventana encontrada. *ok=false
// si Windows mostró un diálogo de error en vez de la app.
QString formatLaunchResult(const QString &app, const QVariantMap &window, bool background,
                           bool *ok = nullptr);
// Detects an existing file passed as an application argument. When present,
// interactive input stays blocked until a read-only observation confirms that
// the requested document is actually open in the launched window.
QString expectedDocumentNameFromLaunchArguments(const QString &args,
                                                const QString &workingDirectory = {});
class LaunchDocumentGuard
{
public:
    void reset();
    void arm(const QString &expectedName, const QString &targetId,
             const QString &initialWindowTitle);
    void rebindTarget(const QString &oldTargetId, const QString &newTargetId);
    bool observe(const QString &targetId, const QString &windowTitle,
                 const QString &visibleText);
    bool blocks(const QString &tool) const;
    bool pending() const { return !m_expectedName.isEmpty(); }
    QString expectedName() const { return m_expectedName; }
    QString targetId() const { return m_targetId; }
    QString pendingNote(const QString &windowTitle = {}) const;
    QString blockedActionMessage(const QString &tool) const;

private:
    QString m_expectedName;
    QString m_targetId;
};
// Tools de escritorio que usan el mouse/teclado REALES del usuario (o le cambian
// la ventana activa/el portapapeles). En modo "segundo plano" quedan fuera: el
// agente maneja la app por UI Automation y el usuario sigue usando su PC.
bool usesUserInput(const QString &tool);
// Cómo encarar un pedido de computer use:
//  ""           → el pedido no es de escritorio, no hay nada que decidir;
//  "background" / "foreground" → el modo ya elegido en la sesión;
//  "foreground" → Super Agente sin modo elegido: lo hace directo;
//  "ask"        → preguntarle al usuario antes de arrancar.
QString computerUseChoice(const QString &approvalMode, const QString &sessionMode,
                          bool wantsDesktop);
// Texto OCR de un alcance para el modelo: una línea por renglón leído, con su
// centro NORMALIZADO 0..1 en ese alcance (las mismas coordenadas que acepta
// desktop_click / desktop_hover). Filtra por `query` (contiene, sin acentos ni
// mayúsculas) y corta a maxLines. Así un modelo SIN visión puede leer la
// pantalla y apuntar.
struct TextLine { QString text; QRect rect; };
QString formatReadText(const QList<TextLine> &lines, const QRect &bounds,
                       const QString &query, int maxLines);
// Texto que la ventana expone por UI Automation (role text/edit, no botones):
// "nombre" o "nombre: valor", sin repetidos, filtrado por `query`. Es exacto
// donde el OCR falla (la pantalla de la Calculadora OCReaba "Oció')" y el
// modelo inventaba el resultado); desktop_read_text lo antepone al OCR.
QStringList uiaReadableText(const QVariantList &controls, const QString &query, int max);
// UIA ValuePattern puede reportar éxito aunque la app no haya reflejado el
// cambio. Confirmar el readback antes de devolver una acción set_value exitosa.
bool valueActionReadbackMatches(const QString &requested, const QString &observed);
bool isDesktopReadTool(const QString &name);
bool isDesktopActionTool(const QString &name);
bool isDesktopMutationTool(const QString &name, const QVariantMap &arguments = {});
bool isSensitiveTarget(const QVariantMap &target);
bool isDestructiveLabel(const QString &text);
QString redactForEvidence(const QString &text);
// Some model tool serializers emit a physical line break when they intend the
// Enter key. Canonicalize only a complete CR/LF payload; do not trim arbitrary keys.
bool normalizeKeyName(QString *key);
// Reorders an unambiguous malformed chord such as key=CTRL, modifiers=[S].
// Returns true only when the key and modifier list were normalized.
bool normalizeKeyChord(QString *key, QStringList *modifiers);
// Existing-text protection applies to text editors, not to non-text controls
// such as spreadsheet grids that expose cell contents through UI Automation.
bool shouldBlockTypingIntoExistingText(bool textEntryControl, bool hasText);

} // namespace DesktopComputerUse

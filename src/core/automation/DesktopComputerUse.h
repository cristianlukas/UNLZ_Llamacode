#pragma once

#include <QJsonObject>
#include <QList>
#include <QLockFile>
#include <QRect>
#include <QString>
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
QString snapshotId(const QString &scopeKind, const QString &targetId,
                   const QVariantMap &target, const QVariantList &windows,
                   const QVariantList &controls);
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
// el propio agente enfocó/clickeó en esta sesión. Sin esto desktop_type y
// desktop_key escribían en CUALQUIER app que el usuario tuviera adelante (un
// chat, el navegador...). foreground vacío = desconocido (Linux): se acepta
// sólo si el agente enfocó algo antes.
bool typingTargetAllowed(const QString &foregroundId, const QString &agentFocusedId);
// 1..3 pulsaciones (simple, doble, triple); cualquier otro valor se acota.
int clampClickCount(int clickCount);
// Nombre "humano" de una app → lo que entiende `start` en Windows. El modelo
// pedía desktop_launch "calculator": no es un ejecutable, Windows abría su
// diálogo de error (ventana "calculator" de 572x140) y el agente tecleaba ahí.
// Sin alias conocido devuelve el nombre tal cual.
QString launchAlias(const QString &app);
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
// Texto de desktop_launch para el modelo según la ventana encontrada. *ok=false
// si Windows mostró un diálogo de error en vez de la app.
QString formatLaunchResult(const QString &app, const QVariantMap &window, bool background,
                           bool *ok = nullptr);
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
bool isDesktopReadTool(const QString &name);
bool isDesktopActionTool(const QString &name);
bool isDesktopMutationTool(const QString &name, const QVariantMap &arguments = {});
bool isSensitiveTarget(const QVariantMap &target);
bool isDestructiveLabel(const QString &text);
QString redactForEvidence(const QString &text);

} // namespace DesktopComputerUse

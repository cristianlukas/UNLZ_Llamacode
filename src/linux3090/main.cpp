#include "HealthStatus.h"

#include <QAction>
#include <QApplication>
#include <QClipboard>
#include <QDateTime>
#include <QDialog>
#include <QDir>
#include <QFile>
#include <QFont>
#include <QFutureWatcher>
#include <QHBoxLayout>
#include <QLabel>
#include <QLockFile>
#include <QMenu>
#include <QMessageBox>
#include <QPainter>
#include <QPlainTextEdit>
#include <QProcess>
#include <QProcessEnvironment>
#include <QPushButton>
#include <QRegularExpression>
#include <QStandardPaths>
#include <QSystemTrayIcon>
#include <QTextCursor>
#include <QTextStream>
#include <QTimer>
#include <QVBoxLayout>
#include <QtConcurrent/QtConcurrentRun>

using Gpu3090Helper::Inputs;
using Gpu3090Helper::Snapshot;

namespace {

constexpr auto kAsusUuid = "GPU-af6de4b3-6497-b7f8-796d-6d69cba422e6";
constexpr auto kService = "vram-quarantine@GPU-af6de4b3-6497-b7f8-796d-6d69cba422e6.service";

struct CommandResult {
    QString output;
    int exitCode = -1;
};

CommandResult run(const QString &program, const QStringList &arguments, int timeoutMs = 5000)
{
    QProcess process;
    QProcessEnvironment environment = QProcessEnvironment::systemEnvironment();
    environment.insert(QStringLiteral("LC_ALL"), QStringLiteral("C"));
    process.setProcessEnvironment(environment);
    process.start(program, arguments);
    if (!process.waitForStarted(1500))
        return {QStringLiteral("No se pudo iniciar %1: %2").arg(program, process.errorString()), -1};
    if (!process.waitForFinished(timeoutMs)) {
        process.kill();
        process.waitForFinished(1000);
        return {QStringLiteral("Timeout al ejecutar %1").arg(program), -1};
    }
    const QString output = QString::fromLocal8Bit(process.readAllStandardOutput())
        + QString::fromLocal8Bit(process.readAllStandardError());
    return {output.trimmed(), process.exitCode()};
}

QString readFile(const QString &path)
{
    QFile file(path);
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text))
        return {};
    return QString::fromUtf8(file.readAll()).trimmed();
}

Inputs collectInputs()
{
    Inputs inputs;
    const QString statePath = QStringLiteral("/run/vram-quarantine/%1.json").arg(QLatin1String(kAsusUuid));
    inputs.workerJson = readFile(statePath);
    inputs.workerActive = run(QStringLiteral("/usr/bin/systemctl"),
        {QStringLiteral("is-active"), QLatin1String(kService)}).output == QLatin1String("active");
    inputs.workerEnabled = run(QStringLiteral("/usr/bin/systemctl"),
        {QStringLiteral("is-enabled"), QLatin1String(kService)}).output == QLatin1String("enabled");
    inputs.kernelCommandLine = readFile(QStringLiteral("/proc/cmdline"));
    inputs.unlockModulePresent = QFile::exists(QStringLiteral("/sys/module/gpu_unlock"));
    inputs.unlockModuleTargets = readFile(QStringLiteral("/sys/module/gpu_unlock/parameters/targets"));

    const CommandResult inventory = run(QStringLiteral("/usr/bin/nvidia-smi"), {
        QStringLiteral("--query-gpu=uuid,name,pci.bus_id"), QStringLiteral("--format=csv,noheader")});
    inputs.gpuInventory = inventory.output;
    const CommandResult p2pRead = run(QStringLiteral("/usr/bin/nvidia-smi"),
        {QStringLiteral("topo"), QStringLiteral("-p2p"), QStringLiteral("r")});
    const CommandResult p2pWrite = run(QStringLiteral("/usr/bin/nvidia-smi"),
        {QStringLiteral("topo"), QStringLiteral("-p2p"), QStringLiteral("w")});
    inputs.p2pRead = p2pRead.output;
    inputs.p2pWrite = p2pWrite.output;
    const CommandResult kernelLog = run(QStringLiteral("/usr/bin/journalctl"), {
        QStringLiteral("-k"), QStringLiteral("-b"), QStringLiteral("--no-pager"),
        QStringLiteral("-o"), QStringLiteral("short-iso"), QStringLiteral("-n"), QStringLiteral("500")}, 7000);
    // gpu_unlock runs once during boot. Search matching entries across the
    // whole current boot so the health check does not lose them as the kernel
    // journal grows beyond the recent diagnostics window above.
    const CommandResult unlockLog = run(QStringLiteral("/usr/bin/journalctl"), {
        QStringLiteral("-k"), QStringLiteral("-b"), QStringLiteral("--no-pager"),
        QStringLiteral("-o"), QStringLiteral("short-iso"),
        QStringLiteral("--grep"), QStringLiteral("gpu_unlock: unlocked")}, 7000);
    const CommandResult workerLog = run(QStringLiteral("/usr/bin/journalctl"), {
        QStringLiteral("-u"), QLatin1String(kService), QStringLiteral("-b"),
        QStringLiteral("--no-pager"), QStringLiteral("-o"), QStringLiteral("short-iso"),
        QStringLiteral("-n"), QStringLiteral("120")}, 5000);
    inputs.unlockKernelLog = unlockLog.output;

    QStringList diagnostics;
    diagnostics << QStringLiteral("nvidia-smi GPU inventory:\n%1").arg(inventory.output);
    diagnostics << QStringLiteral("nvidia-smi topo -p2p r:\n%1").arg(p2pRead.output);
    diagnostics << QStringLiteral("nvidia-smi topo -p2p w:\n%1").arg(p2pWrite.output);
    QStringList relevantLines = kernelLog.output.split(QLatin1Char('\n')).filter(
        QRegularExpression(QStringLiteral("gpu_unlock|Xid|NVRM|vram-quarantine"),
                           QRegularExpression::CaseInsensitiveOption));
    relevantLines.append(unlockLog.output.split(QLatin1Char('\n'), Qt::SkipEmptyParts));
    diagnostics << QStringLiteral("Kernel log (boot actual):\n%1")
        .arg(relevantLines.isEmpty() ? QStringLiteral("(sin líneas legibles)")
                                     : relevantLines.join(QLatin1Char('\n')));
    diagnostics << QStringLiteral("Worker systemd log:\n%1")
        .arg(workerLog.output.isEmpty() ? QStringLiteral("(sin líneas legibles)") : workerLog.output);
    const QString privilegedLog = readFile(QStringLiteral("/var/log/3090-helper/repair.log"));
    QStringList privilegedLines = privilegedLog.split(QLatin1Char('\n'));
    if (privilegedLines.size() > 120)
        privilegedLines = privilegedLines.mid(privilegedLines.size() - 120);
    diagnostics << QStringLiteral("Relanzos previos:\n%1")
        .arg(privilegedLog.isEmpty() ? QStringLiteral("(sin registro o sin permiso de lectura)")
                                    : privilegedLines.join(QLatin1Char('\n')));
    diagnostics << QStringLiteral("kernel cmdline: %1").arg(inputs.kernelCommandLine);
    inputs.diagnostics = diagnostics.join(QStringLiteral("\n\n"));
    return inputs;
}

QString logPath()
{
    const QString path = QDir::homePath() + QStringLiteral("/.local/state/3090-helper");
    QDir().mkpath(path);
    return path + QStringLiteral("/diagnostics.log");
}

void appendLog(const QString &text)
{
    const QString path = logPath();
    QFile current(path);
    if (current.exists() && current.size() > 5 * 1024 * 1024) {
        QFile::remove(path + QStringLiteral(".1"));
        QFile::rename(path, path + QStringLiteral(".1"));
    }
    QFile file(path);
    if (!file.open(QIODevice::WriteOnly | QIODevice::Append | QIODevice::Text))
        return;
    QTextStream stream(&file);
    stream << QDateTime::currentDateTime().toString(Qt::ISODateWithMs) << '\n'
           << text << "\n\n";
}

QString exportedReport(const Snapshot &snapshot)
{
    QFile file(logPath());
    QString previous;
    if (file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        file.seek(qMax<qint64>(0, file.size() - 1024 * 1024));
        previous = QString::fromUtf8(file.readAll());
    }
    return snapshot.report() + QStringLiteral("\n\n--- Último MB del log local ---\n") + previous;
}

QIcon statusIcon(bool healthy)
{
    QPixmap pixmap(64, 64);
    pixmap.fill(Qt::transparent);
    QPainter painter(&pixmap);
    painter.setRenderHint(QPainter::Antialiasing);
    painter.setPen(QPen(QColor(QStringLiteral("#e8e8e8")), 3));
    painter.setBrush(QColor(healthy ? QStringLiteral("#1ca45c") : QStringLiteral("#d53032")));
    painter.drawEllipse(QRectF(4, 4, 56, 56));
    painter.setPen(Qt::white);
    QFont font = painter.font();
    font.setBold(true);
    font.setPixelSize(15);
    painter.setFont(font);
    painter.drawText(QRectF(3, 3, 58, 58), Qt::AlignCenter, QStringLiteral("3090"));
    return QIcon(pixmap);
}

class HelperTray final : public QObject
{
public:
    explicit HelperTray(QApplication &app)
        : QObject(&app), m_app(app), m_tray(new QSystemTrayIcon(this)), m_menu(new QMenu),
          m_watcher(new QFutureWatcher<Snapshot>(this)), m_timer(new QTimer(this))
    {
        m_tray->setContextMenu(m_menu);
        m_stateAction = m_menu->addAction(QStringLiteral("3090 HELPER — comprobando…"));
        m_stateAction->setEnabled(false);
        m_menu->addSeparator();
        QAction *details = m_menu->addAction(QStringLiteral("Ver estado y log de fallos"));
        QAction *repair = m_menu->addAction(QStringLiteral("Relanzar arreglos"));
        QAction *copy = m_menu->addAction(QStringLiteral("Copiar informe para IA"));
        m_menu->addSeparator();
        QAction *quit = m_menu->addAction(QStringLiteral("Salir"));
        connect(details, &QAction::triggered, this, [this] { showDetails(); });
        connect(repair, &QAction::triggered, this, [this] { repairSafely(); });
        connect(copy, &QAction::triggered, this, [this] {
            if (!m_hasSnapshot) return;
            m_app.clipboard()->setText(exportedReport(m_snapshot));
            m_tray->showMessage(QStringLiteral("3090 HELPER"),
                                QStringLiteral("Informe copiado al portapapeles."));
        });
        connect(quit, &QAction::triggered, &m_app, &QApplication::quit);
        connect(m_tray, &QSystemTrayIcon::activated, this,
                [this](QSystemTrayIcon::ActivationReason reason) {
            if (reason == QSystemTrayIcon::Trigger || reason == QSystemTrayIcon::DoubleClick)
                showDetails();
        });
        connect(m_watcher, &QFutureWatcher<Snapshot>::finished, this, [this] {
            m_snapshot = m_watcher->result();
            m_hasSnapshot = true;
            const QString report = m_snapshot.report();
            if (report != m_lastLoggedReport) {
                appendLog(report);
                m_lastLoggedReport = report;
            }
            updateStatus();
            if (m_detailsDialog && m_detailsDialog->isVisible())
                refreshDialog();
        });
        connect(m_timer, &QTimer::timeout, this, [this] { refresh(); });
        m_timer->start(30000);
        m_tray->setIcon(statusIcon(false));
        m_tray->setToolTip(QStringLiteral("3090 HELPER — comprobando estado"));
        m_tray->show();
        refresh();
    }

    void refresh()
    {
        if (m_watcher->isRunning())
            return;
        m_watcher->setFuture(QtConcurrent::run([] {
            return Gpu3090Helper::evaluate(collectInputs());
        }));
    }

private:
    void updateStatus()
    {
        const bool ok = m_snapshot.healthy();
        const QString state = ok ? QStringLiteral("VERDE · todo correcto")
                                 : QStringLiteral("ROJO · requiere atención");
        m_tray->setIcon(statusIcon(ok));
        m_tray->setToolTip(QStringLiteral("3090 HELPER — %1").arg(state));
        m_stateAction->setText(QStringLiteral("3090 HELPER — %1").arg(state));
        if (m_lastHealthy != ok && m_hasPreviousState) {
            m_tray->showMessage(QStringLiteral("3090 HELPER"), state,
                ok ? QSystemTrayIcon::Information : QSystemTrayIcon::Warning);
        }
        m_lastHealthy = ok;
        m_hasPreviousState = true;
    }

    void showDetails()
    {
        if (!m_detailsDialog) {
            m_detailsDialog = new QDialog;
            m_detailsDialog->setWindowTitle(QStringLiteral("3090 HELPER — diagnóstico"));
            m_detailsDialog->resize(780, 560);
            auto *layout = new QVBoxLayout(m_detailsDialog);
            m_summary = new QLabel;
            m_summary->setWordWrap(true);
            m_log = new QPlainTextEdit;
            m_log->setReadOnly(true);
            auto *buttons = new QHBoxLayout;
            auto *refreshButton = new QPushButton(QStringLiteral("Actualizar"));
            auto *copyButton = new QPushButton(QStringLiteral("Copiar informe"));
            auto *closeButton = new QPushButton(QStringLiteral("Cerrar"));
            buttons->addWidget(refreshButton);
            buttons->addWidget(copyButton);
            buttons->addStretch();
            buttons->addWidget(closeButton);
            layout->addWidget(m_summary);
            layout->addWidget(m_log, 1);
            layout->addLayout(buttons);
            connect(refreshButton, &QPushButton::clicked, this, [this] { refresh(); });
            connect(copyButton, &QPushButton::clicked, this, [this] {
                if (m_hasSnapshot)
                    m_app.clipboard()->setText(exportedReport(m_snapshot));
            });
            connect(closeButton, &QPushButton::clicked, m_detailsDialog, &QDialog::hide);
        }
        refreshDialog();
        m_detailsDialog->show();
        m_detailsDialog->raise();
        m_detailsDialog->activateWindow();
        refresh();
    }

    void refreshDialog()
    {
        if (!m_detailsDialog || !m_hasSnapshot)
            return;
        m_summary->setText(m_snapshot.healthy()
            ? QStringLiteral("Estado general: VERDE")
            : QStringLiteral("Estado general: ROJO — al menos una protección no está validada."));
        QFile log(logPath());
        QString previous;
        if (log.open(QIODevice::ReadOnly | QIODevice::Text)) {
            log.seek(qMax<qint64>(0, log.size() - 1024 * 1024));
            previous = QString::fromUtf8(log.readAll());
        }
        m_log->setPlainText(m_snapshot.report() + QStringLiteral("\n\n") + previous);
        m_log->moveCursor(QTextCursor::End);
    }

    void repairSafely()
    {
        const auto answer = QMessageBox::question(nullptr, QStringLiteral("Relanzar arreglos"),
            QStringLiteral("Se reiniciará sólo el servicio de reserva VRAM de la ASUS. "
                           "No se tocarán servidores de inferencia. P2P y gpu-unlock "
                           "se validan en el arranque y pueden requerir reiniciar Ubuntu. "
                           "¿Continuar?"));
        if (answer != QMessageBox::Yes)
            return;
        auto *process = new QProcess(this);
        process->setProgram(QStringLiteral("/usr/bin/pkexec"));
        process->setArguments({QStringLiteral(LC_3090_HELPER_ADMIN_PATH), QStringLiteral("repair")});
        connect(process, &QProcess::readyReadStandardOutput, this, [this, process] {
            appendLog(QString::fromLocal8Bit(process->readAllStandardOutput()));
        });
        connect(process, &QProcess::readyReadStandardError, this, [this, process] {
            appendLog(QString::fromLocal8Bit(process->readAllStandardError()));
        });
        connect(process, qOverload<int, QProcess::ExitStatus>(&QProcess::finished), this,
                [this, process](int code, QProcess::ExitStatus status) {
            const bool ok = status != QProcess::CrashExit && code == 0;
            if (!ok) {
                appendLog(QStringLiteral("La acción privilegiada terminó con error %1.").arg(code));
                m_tray->showMessage(QStringLiteral("3090 HELPER"),
                    QStringLiteral("La reparación o alguna verificación falló. Abrí el log para ver el motivo."),
                    QSystemTrayIcon::Warning);
            } else {
                m_tray->showMessage(QStringLiteral("3090 HELPER"),
                    QStringLiteral("Las tres protecciones quedaron verificadas."),
                    QSystemTrayIcon::Information);
            }
            process->deleteLater();
            refresh();
        });
        process->start();
        if (!process->waitForStarted(2000)) {
            appendLog(QStringLiteral("No se pudo iniciar pkexec: %1").arg(process->errorString()));
            process->deleteLater();
        }
    }

    QApplication &m_app;
    QSystemTrayIcon *m_tray;
    QMenu *m_menu;
    QAction *m_stateAction = nullptr;
    QFutureWatcher<Snapshot> *m_watcher;
    QTimer *m_timer;
    QDialog *m_detailsDialog = nullptr;
    QLabel *m_summary = nullptr;
    QPlainTextEdit *m_log = nullptr;
    Snapshot m_snapshot;
    bool m_hasSnapshot = false;
    bool m_lastHealthy = false;
    bool m_hasPreviousState = false;
    QString m_lastLoggedReport;
};

} // namespace

int main(int argc, char **argv)
{
    const bool diagnoseOnly = argc > 1
        && QString::fromLocal8Bit(argv[1]) == QLatin1String("--diagnose");
    if (diagnoseOnly) {
        QCoreApplication app(argc, argv);
        QCoreApplication::setApplicationName(QStringLiteral("3090 HELPER"));
        QCoreApplication::setOrganizationName(QStringLiteral("UNLZ LlamaCode"));
        const Snapshot snapshot = Gpu3090Helper::evaluate(collectInputs());
        QTextStream(stdout) << snapshot.report() << Qt::endl;
        return snapshot.healthy() ? 0 : 1;
    }

    QApplication app(argc, argv);
    QCoreApplication::setApplicationName(QStringLiteral("3090 HELPER"));
    QCoreApplication::setOrganizationName(QStringLiteral("UNLZ LlamaCode"));
    app.setQuitOnLastWindowClosed(false);

    const QString runtime = QStandardPaths::writableLocation(QStandardPaths::RuntimeLocation);
    QLockFile singleInstance(runtime + QStringLiteral("/3090-helper.lock"));
    if (!singleInstance.tryLock(0))
        return 0;
    if (!QSystemTrayIcon::isSystemTrayAvailable()) {
        QMessageBox::critical(nullptr, QStringLiteral("3090 HELPER"),
            QStringLiteral("No hay bandeja de sistema disponible en esta sesión gráfica."));
        return 2;
    }
    HelperTray helper(app);
    return app.exec();
}

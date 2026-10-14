#include "TrayController.h"

#include <QAction>
#include <QMenu>
#include <QSystemTrayIcon>

TrayController::TrayController(const QIcon &icon, QObject *parent)
    : QObject(parent), m_tray(new QSystemTrayIcon(icon, this)), m_menu(new QMenu)
{
    m_tray->setToolTip(QStringLiteral("UNLZ_Llamacode"));
    // Con hoja de estilo Qt dibuja los items sin la columna de iconos/checks que
    // reserva el estilo nativo (Windows 11/Vista): ninguna accion tiene icono y
    // el menu quedaba con un hueco grande a la izquierda del texto.
    m_menu->setStyleSheet(QStringLiteral(
        "QMenu { background: #202020; color: #e8e8e8; border: 1px solid #3a3a3a;"
        " padding: 4px; }"
        "QMenu::item { padding: 6px 16px; border-radius: 4px; background: transparent; }"
        "QMenu::item:selected { background: #333333; }"
        "QMenu::item:disabled { color: #777777; }"
        "QMenu::separator { height: 1px; background: #3a3a3a; margin: 4px 6px; }"));
    m_openAction = m_menu->addAction(m_openText);
    m_pauseAction = m_menu->addAction(m_pauseText);
    m_finishAction = m_menu->addAction(m_finishText);
    m_cancelAction = m_menu->addAction(m_cancelText);
    m_menu->addSeparator();
    m_quitAction = m_menu->addAction(m_quitText);
    m_tray->setContextMenu(m_menu);

    connect(m_openAction, &QAction::triggered, this, &TrayController::openRequested);
    connect(m_quitAction, &QAction::triggered, this, &TrayController::quitRequested);
    connect(m_pauseAction, &QAction::triggered, this, [this]() {
        emit pauseTeachRequested(m_teachState != QLatin1String("paused"));
    });
    connect(m_finishAction, &QAction::triggered, this, &TrayController::finishTeachRequested);
    connect(m_cancelAction, &QAction::triggered, this, &TrayController::cancelTeachRequested);
    connect(m_tray, &QSystemTrayIcon::activated, this,
            [this](QSystemTrayIcon::ActivationReason reason) {
        if (reason == QSystemTrayIcon::Trigger
            || reason == QSystemTrayIcon::DoubleClick)
            emit openRequested();
    });
    rebuildMenu();
    if (isAvailable())
        m_tray->show();
}

TrayController::~TrayController()
{
    m_tray->hide();
    delete m_menu;
}

bool TrayController::isVisible() const
{
    return m_tray->isVisible();
}

bool TrayController::isAvailable() const
{
    return QSystemTrayIcon::isSystemTrayAvailable();
}

void TrayController::setVisible(bool visible)
{
    visible = visible && isAvailable();
    if (visible == isVisible()) return;
    if (visible) m_tray->show();
    else m_tray->hide();
    emit visibleChanged();
}

void TrayController::setTeachState(const QString &state)
{
    if (m_teachState == state) return;
    m_teachState = state;
    rebuildMenu();
}

void TrayController::setMenuTexts(const QString &open, const QString &pause,
                                  const QString &resume, const QString &finish,
                                  const QString &cancel, const QString &quit)
{
    m_openText = open;
    m_pauseText = pause;
    m_resumeText = resume;
    m_finishText = finish;
    m_cancelText = cancel;
    m_quitText = quit;
    rebuildMenu();
}

void TrayController::rebuildMenu()
{
    if (!m_openAction) return;
    const bool teachActive = m_teachState == QLatin1String("recording")
                             || m_teachState == QLatin1String("paused");
    m_openAction->setText(m_openText);
    m_pauseAction->setText(m_teachState == QLatin1String("paused")
                               ? m_resumeText : m_pauseText);
    m_finishAction->setText(m_finishText);
    m_cancelAction->setText(m_cancelText);
    m_quitAction->setText(m_quitText);
    m_pauseAction->setVisible(teachActive);
    m_finishAction->setVisible(teachActive);
    m_cancelAction->setVisible(teachActive);
}

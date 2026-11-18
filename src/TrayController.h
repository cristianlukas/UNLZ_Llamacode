#pragma once

#include <QIcon>
#include <QObject>
#include <optional>

class QMenu;
class QAction;
class QSystemTrayIcon;

class TrayController final : public QObject
{
    Q_OBJECT
    Q_PROPERTY(bool visible READ isVisible WRITE setVisible NOTIFY visibleChanged)
    Q_PROPERTY(bool available READ isAvailable CONSTANT)
public:
    explicit TrayController(const QIcon &icon, QObject *parent = nullptr);
    ~TrayController() override;

    bool isVisible() const;
    bool isAvailable() const;
    void setVisible(bool visible);
    // true desde que se eligió "Salir" en el menú, ANTES de emitir
    // quitRequested: el cierre de ventanas que dispara Qt.quit() puede llegar
    // antes de que corran los demás slots conectados a la señal.
    bool isQuitting() const { return m_quitting; }
    void setAvailableForTest(bool available) { m_availableForTest = available; }

    Q_INVOKABLE void setTeachState(const QString &state);
    void showNotification(const QString &title, const QString &body);
    QMenu *menuForTest() const { return m_menu; }
    Q_INVOKABLE void setMenuTexts(const QString &open, const QString &pause,
                                  const QString &resume, const QString &finish,
                                  const QString &cancel, const QString &quit);

signals:
    void visibleChanged();
    void openRequested();
    void quitRequested();
    void pauseTeachRequested(bool paused);
    void finishTeachRequested();
    void cancelTeachRequested();

private:
    void rebuildMenu();

    bool m_quitting = false;
    std::optional<bool> m_availableForTest;

    QSystemTrayIcon *m_tray = nullptr;
    QMenu *m_menu = nullptr;
    QAction *m_openAction = nullptr;
    QAction *m_pauseAction = nullptr;
    QAction *m_finishAction = nullptr;
    QAction *m_cancelAction = nullptr;
    QAction *m_quitAction = nullptr;
    QString m_teachState;
    QString m_openText = QStringLiteral("Abrir LlamaCode");
    QString m_pauseText = QStringLiteral("Pausar Teach");
    QString m_resumeText = QStringLiteral("Continuar Teach");
    QString m_finishText = QStringLiteral("Finalizar Teach");
    QString m_cancelText = QStringLiteral("Cancelar Teach");
    QString m_quitText = QStringLiteral("Salir");
};

// Con "minimizar a la bandeja", cerrar la ventana la oculta en vez de cerrarla.
// Salvo que se esté saliendo: en Qt 6, QCoreApplication::quit() cierra todas las
// ventanas y, si alguna rechaza el cierre, cancela la salida. Antes este filtro
// se enteraba de "Salir" por un slot que corría DESPUÉS del Qt.quit() de la QML,
// rechazaba el cierre y la app quedaba viva y oculta.
class TrayWindowCloseFilter final : public QObject
{
public:
    explicit TrayWindowCloseFilter(const TrayController *tray, QObject *parent = nullptr)
        : QObject(parent), m_tray(tray) {}

protected:
    bool eventFilter(QObject *watched, QEvent *event) override;

private:
    const TrayController *m_tray = nullptr;
};

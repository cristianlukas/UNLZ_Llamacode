#pragma once
#include <QObject>
#include <QHostAddress>

class QTcpServer;
class QTcpSocket;

// Control API HTTP headless: espeja TODO AppController vía meta-object
// (Q_INVOKABLE + Q_PROPERTY ya expuestos a QML). Permite manejar la app sin GUI
// para tests automatizados. Sólo escucha en localhost.
//
// Endpoints:
//   GET  /methods            → lista de métodos invocables + propiedades (JSON)
//   GET  /prop?name=X        → valor de la propiedad X (JSON)
//   POST /invoke {method,args}→ invoca método en AppController; {ok,result}
//   GET  /health             → {ok:true}
class ControlApi : public QObject
{
    Q_OBJECT
public:
    explicit ControlApi(QObject *target, QObject *parent = nullptr);
    bool start(quint16 port, const QHostAddress &addr = QHostAddress::LocalHost);

private slots:
    void onNewConnection();

private:
    void handleRequest(QTcpSocket *sock, const QByteArray &method,
                       const QString &path, const QByteArray &body);
    QByteArray jsonMethods() const;
    QByteArray jsonProperty(const QString &name) const;
    QByteArray setProperty(const QByteArray &jsonBody, bool *ok) const;
    QByteArray invokeMethod(const QByteArray &jsonBody, bool *ok) const;

    QObject *m_target = nullptr;
    QTcpServer *m_server = nullptr;
};

#pragma once

#include <QObject>
#include <QElapsedTimer>
#include <QPoint>
#include <QTimer>
#include <QVariantList>

class TeachSessionRecorder : public QObject
{
    Q_OBJECT
    Q_PROPERTY(QString state READ state NOTIFY changed)
    Q_PROPERTY(QString error READ error NOTIFY changed)
    Q_PROPERTY(QVariantList timeline READ timeline NOTIFY changed)
public:
    explicit TeachSessionRecorder(QObject *parent = nullptr);

    QString state() const { return m_state; }
    QString error() const { return m_error; }
    QVariantList timeline() const { return m_events; }
    QString artifactId() const { return m_artifactId; }

    QString startDesktop(const QVariantMap &task, const QString &scopeKind,
                         const QString &scopeId);
    QString startBrowser(const QVariantMap &task, const QString &url);
    void setPaused(bool paused);
    void addNote(const QString &note);
    QString finish();
    void cancel();

signals:
    void changed();
    void finished(const QString &artifactId);

private slots:
    void sampleDesktop();

private:
    void appendEvent(const QVariantMap &event, bool captureEvidence);
    QString captureEvidence();
    void reset();

    QString m_state = QStringLiteral("idle");
    QString m_error;
    QString m_mode;
    QString m_scopeKind;
    QString m_scopeId;
    QString m_artifactId;
    QVariantMap m_task;
    QVariantList m_events;
    QStringList m_evidence;
    QTimer m_timer;
    QElapsedTimer m_clock;
    QPoint m_lastCursor;
    bool m_leftDown = false;
    bool m_rightDown = false;
};

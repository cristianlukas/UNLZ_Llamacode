#include "core/automation/DesktopAutomationBackend.h"

#include <QGuiApplication>
#include <QtTest>

#include <limits>

class DesktopBackendTest final : public QObject
{
    Q_OBJECT

private slots:
    void normalizedCoordinatesRejectGridValues()
    {
        QVERIFY(DesktopAutomationBackend::isNormalizedPoint(0.0, 0.0));
        QVERIFY(DesktopAutomationBackend::isNormalizedPoint(1.0, 1.0));
        QVERIFY(!DesktopAutomationBackend::isNormalizedPoint(100.0, 50.0));
        QVERIFY(!DesktopAutomationBackend::isNormalizedPoint(-0.1, 0.5));
        QVERIFY(!DesktopAutomationBackend::isNormalizedPoint(
            std::numeric_limits<double>::quiet_NaN(), 0.5));
    }

    void normalizeRoundTrip()
    {
        const QRect bounds(10, 20, 800, 600);
        const QPoint original(410, 320);
        const QPointF normalized = DesktopAutomationBackend::normalizePoint(original, bounds);
        const QPoint restored = DesktopAutomationBackend::denormalizePoint(normalized, bounds);
        QCOMPARE(restored, original);
    }

    void screenTargetsAreDiscoverable()
    {
        const QVariantList screens = DesktopAutomationBackend::screens();
        QVERIFY(!screens.isEmpty());
        const QVariantMap first = screens.first().toMap();
        QVERIFY(first.value(QStringLiteral("id")).toString() == QLatin1String("0"));
        QVERIFY(first.value(QStringLiteral("width")).toInt() > 0);
        QVERIFY(first.value(QStringLiteral("height")).toInt() > 0);
    }
};

QTEST_MAIN(DesktopBackendTest)
#include "test_desktop_backend.moc"

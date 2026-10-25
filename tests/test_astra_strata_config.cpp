#include <QtTest>

#include "core/profiles/AstraStrataConfig.h"

class AstraStrataConfigTests : public QObject
{
    Q_OBJECT
private slots:
    void changesOnlyMaxContext();
    void acceptsEqualsSyntax();
    void rejectsMissingOrAmbiguousContext();
};

void AstraStrataConfigTests::changesOnlyMaxContext()
{
    const QJsonObject source{
        {QStringLiteral("model_name"), QStringLiteral("flash-next")},
        {QStringLiteral("args"), QJsonArray{
             QStringLiteral("--pack"), QStringLiteral("weights"),
             QStringLiteral("--max-context"), QStringLiteral("1048576"),
             QStringLiteral("--kv"), QStringLiteral("int8")}}
    };
    QString error;
    const QJsonObject result = AstraStrataConfig::withMaxContext(source, 131072, &error);
    QVERIFY2(!result.isEmpty(), qPrintable(error));
    QVERIFY(error.isEmpty());
    QCOMPARE(result.value(QStringLiteral("model_name")), source.value(QStringLiteral("model_name")));
    const QJsonArray args = result.value(QStringLiteral("args")).toArray();
    QCOMPARE(args.at(1).toString(), QStringLiteral("weights"));
    QCOMPARE(args.at(3).toString(), QStringLiteral("131072"));
    QCOMPARE(args.at(4).toString(), QStringLiteral("--kv"));
    QCOMPARE(args.at(5).toString(), QStringLiteral("int8"));
    QCOMPARE(source.value(QStringLiteral("args")).toArray().at(3).toString(),
             QStringLiteral("1048576"));
}

void AstraStrataConfigTests::acceptsEqualsSyntax()
{
    const QJsonObject source{{QStringLiteral("args"), QJsonArray{
        QStringLiteral("--max-context=1048576")}}};
    const QJsonObject result = AstraStrataConfig::withMaxContext(source, 131072);
    QCOMPARE(result.value(QStringLiteral("args")).toArray().first().toString(),
             QStringLiteral("--max-context=131072"));
}

void AstraStrataConfigTests::rejectsMissingOrAmbiguousContext()
{
    QString error;
    QVERIFY(AstraStrataConfig::withMaxContext(
        QJsonObject{{QStringLiteral("args"), QJsonArray{QStringLiteral("--kv"), QStringLiteral("int8")}}},
        131072, &error).isEmpty());
    QVERIFY(error.contains(QStringLiteral("no declara")));

    QVERIFY(AstraStrataConfig::withMaxContext(
        QJsonObject{{QStringLiteral("args"), QJsonArray{
            QStringLiteral("--max-context"), QStringLiteral("131072"),
            QStringLiteral("--max-context=1048576")}}}, 131072, &error).isEmpty());
    QVERIFY(error.contains(QStringLiteral("más de una vez")));

    QVERIFY(AstraStrataConfig::withMaxContext(
        QJsonObject{{QStringLiteral("args"), QJsonArray{
            QStringLiteral("--max-context"), QStringLiteral("not-a-number")}}},
        131072, &error).isEmpty());
    QVERIFY(error.contains(QStringLiteral("valor válido")));
}

QTEST_MAIN(AstraStrataConfigTests)
#include "test_astra_strata_config.moc"

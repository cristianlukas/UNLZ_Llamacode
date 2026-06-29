// Unit tests de EvalSuite: loader desde JSON (string y archivo), categorías
// únicas en orden, manejo de JSON inválido. Reusa el sample real del repo.

#include <QtTest>
#include <QTemporaryDir>
#include <QSet>
#include "AppController.h"
#include "core/eval/EvalSuite.h"

class EvalTests : public QObject
{
    Q_OBJECT
private slots:
    void loadFromJson_parsesTasks();
    void categories_uniqueInOrder();
    void invalidJson_returnsEmptyWithError();
    void loadFromFile_roundTrip();
    void reasoningBiasSuite_isValid();
    void snakeSuite_isValid();
    void agentAcceptance_scoresGeneratedFiles();
};

static QByteArray sampleJson()
{
    return R"({
        "name": "demo",
        "description": "suite de prueba",
        "tasks": [
            {"id":"t1","category":"coding","prompt":"escribe fizzbuzz",
             "acceptance":["FizzBuzz"],"weight":2},
            {"id":"t2","category":"docs","prompt":"resume el doc",
             "acceptance":["resumen"],"attachments":["a.pdf"]},
            {"id":"t3","category":"coding","prompt":"otra de coding",
             "acceptance":[]}
        ]
    })";
}

void EvalTests::loadFromJson_parsesTasks()
{
    QString err;
    const EvalSuite s = EvalSuite::loadFromJson(sampleJson(), &err);
    QVERIFY2(err.isEmpty(), qPrintable(err));
    QCOMPARE(s.name, QStringLiteral("demo"));
    QCOMPARE(s.tasks.size(), 3);
    QCOMPARE(s.tasks.first().category, QStringLiteral("coding"));
    QCOMPARE(s.tasks.first().weight, 2);
    QVERIFY(!s.isEmpty());
}

void EvalTests::categories_uniqueInOrder()
{
    const EvalSuite s = EvalSuite::loadFromJson(sampleJson());
    const QStringList cats = s.categories();
    QCOMPARE(cats, (QStringList{"coding", "docs"}));  // únicas, en orden de aparición
}

void EvalTests::invalidJson_returnsEmptyWithError()
{
    QString err;
    const EvalSuite s = EvalSuite::loadFromJson("{ not json", &err);
    QVERIFY(s.isEmpty());
    QVERIFY(!err.isEmpty());
}

void EvalTests::loadFromFile_roundTrip()
{
    QTemporaryDir dir;
    const QString path = dir.filePath("suite.json");
    QFile f(path);
    QVERIFY(f.open(QIODevice::WriteOnly));
    f.write(sampleJson());
    f.close();
    QString err;
    const EvalSuite s = EvalSuite::loadFromFile(path, &err);
    QVERIFY2(err.isEmpty(), qPrintable(err));
    QCOMPARE(s.tasks.size(), 3);
}

// La suite anti-sesgo bundleada (assets/eval/reasoning_bias.json) debe parsear
// limpia y tener forma sana: trampas con respuesta esperada, controles que son el
// par mínimo de las trampas, y categorías reasoning/normal/chat. Es la red de
// regresión de la directiva antiBias.
void EvalTests::reasoningBiasSuite_isValid()
{
#ifdef LC_REASONING_BIAS_JSON
    QString err;
    const EvalSuite s = EvalSuite::loadFromFile(QStringLiteral(LC_REASONING_BIAS_JSON), &err);
    QVERIFY2(err.isEmpty(), qPrintable(err));
    QVERIFY(!s.isEmpty());
    QVERIFY(s.tasks.size() >= 20);
    // Categorías esperadas presentes.
    const QStringList cats = s.categories();
    for (const QString &c : {"reasoning", "normal", "chat"})
        QVERIFY2(cats.contains(c), qPrintable("falta categoría " + c));
    // Ids únicos; toda tarea reasoning/normal trae al menos un substring esperado
    // (las chat son de eval manual y pueden ir sin acceptance).
    QSet<QString> ids;
    for (const EvalTask &t : s.tasks) {
        QVERIFY2(!ids.contains(t.id), qPrintable("id duplicado " + t.id));
        ids.insert(t.id);
        QVERIFY(!t.prompt.isEmpty());
        if (t.category == QLatin1String("reasoning") || t.category == QLatin1String("normal"))
            QVERIFY2(!t.acceptance.isEmpty(), qPrintable("sin acceptance: " + t.id));
    }
    // Par mínimo trampa↔control: la trampa de la rueda pinchada y su gemelo.
    QVERIFY(ids.contains(QStringLiteral("trap-flat-tyre")));
    QVERIFY(ids.contains(QStringLiteral("ctrl-two-shops")));
#else
    QSKIP("LC_REASONING_BIAS_JSON no definido");
#endif
}

// Suite Snake retro single-file (assets/eval/snake_retro_singlefile.json): la
// tarea autocontenida para comparar NIVELES de agente. Debe parsear y traer la
// tarea con su acceptance (substrings que prueban un Snake jugable en un HTML).
void EvalTests::snakeSuite_isValid()
{
#ifdef LC_SNAKE_SUITE_JSON
    QString err;
    const EvalSuite s = EvalSuite::loadFromFile(QStringLiteral(LC_SNAKE_SUITE_JSON), &err);
    QVERIFY2(err.isEmpty(), qPrintable(err));
    QVERIFY(!s.isEmpty());
    QCOMPARE(s.tasks.size(), 1);
    const EvalTask &t = s.tasks.first();
    QCOMPARE(t.category, QStringLiteral("coding"));
    QVERIFY(t.prompt.contains(QStringLiteral("SNAKE")));
    // Acceptance cubre los marcadores de un Snake jugable en un único HTML.
    for (const QString &need : {"<canvas", "getContext", "keydown", "score"})
        QVERIFY2(t.acceptance.contains(need), qPrintable("falta acceptance " + need));
#else
    QSKIP("LC_SNAKE_SUITE_JSON no definido");
#endif
}

void EvalTests::agentAcceptance_scoresGeneratedFiles()
{
    QTemporaryDir dir;
    QVERIFY(dir.isValid());

    QFile html(dir.filePath("snake_retro.html"));
    QVERIFY(html.open(QIODevice::WriteOnly | QIODevice::Text));
    html.write(R"(<html><head><style></style></head><body>
<canvas id="game"></canvas>
<script>
const ctx = document.getElementById('game').getContext('2d');
document.addEventListener('keydown', () => {});
let score = 0;
</script>
</body></html>)");
    html.close();

    QVariantMap acceptance;
    acceptance["expectSubstrings"] = QVariantList{
        QStringLiteral("<canvas"),
        QStringLiteral("<style"),
        QStringLiteral("<script"),
        QStringLiteral("getContext"),
        QStringLiteral("addEventListener"),
        QStringLiteral("keydown"),
        QStringLiteral("score"),
    };
    QVariantMap task;
    task["id"] = QStringLiteral("snake-singlefile");
    task["acceptance"] = acceptance;

    const QVariantMap scored = AppController::scoreAgentBenchmarkAcceptanceForTest(
        dir.path(),
        QStringLiteral("Creé snake_retro.html y lo verifiqué."),
        QVariantList{task},
        QStringList{QStringLiteral("snake_retro.html")});

    QCOMPARE(scored.value(QStringLiteral("score")).toInt(), 7);
    QCOMPARE(scored.value(QStringLiteral("total")).toInt(), 7);
    const QVariantList rows = scored.value(QStringLiteral("rows")).toList();
    QCOMPARE(rows.size(), 7);
    for (const QVariant &row : rows)
        QVERIFY2(row.toMap().value(QStringLiteral("passed")).toBool(),
                 qPrintable(row.toMap().value(QStringLiteral("name")).toString()));
}

QTEST_MAIN(EvalTests)
#include "test_eval.moc"

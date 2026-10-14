// Tests de ModelLoadProgress: etapas de carga de llama-server leidas del stderr
// y porcentaje (puntos del progress_callback o estimado por tiempo).
#include <QtTest>
#include "core/ModelLoadProgress.h"

class ModelLoadProgressTests : public QObject
{
    Q_OBJECT
private slots:
    void idleHasNoProgress();
    void stagesFromRealServerLog();
    void dotsGiveRealPercent();
    void dotsSplitAcrossChunks();
    void estimateByTimeIsCapped();
    void neverGoesBackwards();
    void readyReportsDuration();
    void failureAndStop();
    void expectedFromFileSize();
    void labels();
};

void ModelLoadProgressTests::idleHasNoProgress()
{
    ModelLoadProgress p;
    QCOMPARE(p.state(), QStringLiteral("idle"));
    QCOMPARE(p.progress(0), -1);
    QVERIFY(!p.active());
    p.feed(QStringLiteral("load_tensors: ...\n......"));   // sin reset no hace nada
    QCOMPARE(p.state(), QStringLiteral("idle"));
}

void ModelLoadProgressTests::stagesFromRealServerLog()
{
    // Lineas tal cual las imprime llama-server con verbosidad 3 (prefijo de tiempo).
    ModelLoadProgress p;
    p.reset(1000, 0);
    QCOMPARE(p.state(), QStringLiteral("starting"));
    QCOMPARE(p.progress(1000), 0);
    p.feed(QStringLiteral("0.00.178.219 I srv  llama_server: loading model\n"
                          "0.00.178.231 I srv    load_model: loading model 'C:/m/Qwen3.5-9B-Q4_K_M.gguf'\n"));
    QCOMPARE(p.state(), QStringLiteral("loading"));
    QCOMPARE(p.progress(1000), 5);
    p.feed(QStringLiteral("0.03.529.704 W llama_context: n_ctx_seq (4096) < n_ctx_train (262144)\n"));
    QCOMPARE(p.state(), QStringLiteral("warmup"));
    QCOMPARE(p.progress(1000), 95);
}

void ModelLoadProgressTests::dotsGiveRealPercent()
{
    ModelLoadProgress p;
    p.reset(0, 0);
    p.feed(QStringLiteral("load_tensors: loading model tensors, this can take a while...\n"));
    p.feed(QString(50, QLatin1Char('.')));
    QVERIFY(!p.estimated());
    QCOMPARE(p.progress(0), 5 + 50 * 85 / 100);
    p.feed(QString(80, QLatin1Char('.')));   // nunca pasa de 100 puntos
    QCOMPARE(p.progress(0), 90);
}

void ModelLoadProgressTests::dotsSplitAcrossChunks()
{
    ModelLoadProgress p;
    p.reset(0, 0);
    p.feed(QStringLiteral("load_tensors: CUDA0 model buffer size = 5000 MiB\n...."));
    p.feed(QStringLiteral("......"));
    p.feed(QStringLiteral("..........\nllama_context: constructing"));
    QCOMPARE(p.state(), QStringLiteral("warmup"));
    // Antes del loader, puntos sueltos de otro log no cuentan.
    ModelLoadProgress q;
    q.reset(0, 0);
    q.feed(QStringLiteral("......"));
    QVERIFY(q.estimated());
    QCOMPARE(q.progress(0), 0);
}

void ModelLoadProgressTests::estimateByTimeIsCapped()
{
    ModelLoadProgress p;
    p.reset(10'000, 20'000);          // la carga anterior tardo 20 s
    p.feed(QStringLiteral("llama_server: loading model\n"));
    QVERIFY(p.estimated());
    QCOMPARE(p.progress(20'000), 45);   // 10 s de 20 s → 50% * 0.9
    // Pasado el tiempo esperado no llega a 100 sin que el log lo confirme.
    QCOMPARE(p.progress(100'000), 89);
    QCOMPARE(p.toJson(20'000).value(QStringLiteral("estimated")).toBool(), true);
}

void ModelLoadProgressTests::neverGoesBackwards()
{
    ModelLoadProgress p;
    p.reset(0, 0);
    p.feed(QStringLiteral("llama_context: n_ctx = 4096\n"));
    // El draft/mmproj vuelve a loguear el loader despues.
    p.feed(QStringLiteral("load_model: loading model 'draft.gguf'\n"));
    QCOMPARE(p.state(), QStringLiteral("warmup"));
}

void ModelLoadProgressTests::readyReportsDuration()
{
    ModelLoadProgress p;
    p.reset(5'000, 0);
    QCOMPARE(p.markReady(17'000), qint64(12'000));
    QCOMPARE(p.state(), QStringLiteral("ready"));
    QCOMPARE(p.progress(0), 100);
    QVERIFY(!p.active());
    // Un segundo ready (health repetido) no mide nada.
    QCOMPARE(p.markReady(30'000), qint64(0));
}

void ModelLoadProgressTests::failureAndStop()
{
    ModelLoadProgress p;
    p.reset(0, 0);
    p.markFailed(QStringLiteral("crash"));
    QCOMPARE(p.state(), QStringLiteral("failed"));
    QCOMPARE(p.toJson(0).value(QStringLiteral("detail")).toString(), QStringLiteral("crash"));
    p.markIdle();
    QCOMPARE(p.state(), QStringLiteral("idle"));
    QCOMPARE(p.progress(0), -1);
}

void ModelLoadProgressTests::expectedFromFileSize()
{
    QCOMPARE(ModelLoadProgress::expectedMsForFileSize(0), qint64(0));
    QCOMPARE(ModelLoadProgress::expectedMsForFileSize(qint64(5) * 1024 * 1024 * 1024),
             qint64(3000 + 5 * 1024));
}

void ModelLoadProgressTests::labels()
{
    QCOMPARE(ModelLoadProgress::label(QStringLiteral("loading"), 42, false),
             QStringLiteral("Cargando modelo 42%"));
    QCOMPARE(ModelLoadProgress::label(QStringLiteral("loading"), 42, true),
             QStringLiteral("Cargando modelo remoto 42%"));
    QCOMPARE(ModelLoadProgress::label(QStringLiteral("connecting"), -1, true),
             QStringLiteral("Conectando con el servidor LAN..."));
    QCOMPARE(ModelLoadProgress::label(QStringLiteral("idle"), -1, false), QString());
}

QTEST_MAIN(ModelLoadProgressTests)
#include "test_model_load_progress.moc"

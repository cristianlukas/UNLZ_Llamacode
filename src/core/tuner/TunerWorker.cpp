#include "TunerWorker.h"

TunerWorker::TunerWorker(TunerJob job, QObject *parent)
    : QObject(parent), m_job(std::move(job))
{
}

void TunerWorker::run()
{
    // TunerEngine se crea en este hilo: su QNetworkAccessManager y los QProcess
    // de cada trial quedan con la afinidad correcta.
    TunerEngine engine;
    m_engine = &engine;
    QObject::connect(&engine, &TunerEngine::trialDone, this,
                     [this](int i, int n, double tps, double q, const QString &s) {
                         emit trial(i, n, tps, q, s);
                     });

    const tuner::Trial best = engine.run(m_job);
    m_engine = nullptr;
    const bool ok = !best.result.failed && best.result.throughput > 0.0;
    const QStringList bestArgs =
        ok ? TunerEngine::tunedArgs(m_job.params, best.config) : QStringList{};
    emit finished(ok, bestArgs, best.result.throughput, best.result.quality);
}

void TunerWorker::cancel()
{
    if (m_engine) m_engine->cancel();  // sólo setea un atomic; thread-safe
}

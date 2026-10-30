#include <QtTest>
#include <QJsonArray>
#include <QJsonObject>

#include "core/ServerMonitor.h"

// Pantalla Monitor: lo que se deriva de /slots, del log de carga y de
// nvidia-smi / /proc. Las muestras copian el formato real de llama-server.
class TestServerMonitor : public QObject
{
    Q_OBJECT

    static QJsonObject slot(int id, int task, bool processing, int prompt, int processed,
                            int cached, int decoded, int nCtx = 8192)
    {
        QJsonObject o{{"id", id}, {"n_ctx", nCtx}, {"speculative", false},
                      {"is_processing", processing}};
        if (task >= 0) {
            o["id_task"] = task;
            o["n_prompt_tokens"] = prompt;
            o["n_prompt_tokens_processed"] = processed;
            o["n_prompt_tokens_cache"] = cached;
            o["next_token"] = QJsonArray{QJsonObject{{"has_next_token", processing},
                                                     {"n_remain", -1},
                                                     {"n_decoded", decoded}}};
        }
        return o;
    }

private slots:
    void firstPollIsBaseline()
    {
        // Lo que ya había terminado antes de abrir el monitor no cuenta.
        ServerMonitor m;
        m.ingestSlots({slot(0, 7, false, 1000, 200, 800, 50)}, 0);
        QVERIFY(m.hasSlots());
        QCOMPARE(m.snapshot().value("requestsServed").toInt(), 0);
        QCOMPARE(m.snapshot().value("state").toString(), QString("idle"));
        // El contexto igual muestra el último request.
        QCOMPARE(m.snapshot().value("context").toMap().value("used").toInt(), 1050);
    }

    void tracksReadingWritingAndFinalizes()
    {
        ServerMonitor m;
        m.ingestSlots({slot(0, -1, false, 0, 0, 0, 0)}, 0);
        // Leyendo el prompt (sin tokens generados todavía).
        m.ingestSlots({slot(0, 1, true, 2716, 100, 2211, 0)}, 1000);
        QCOMPARE(m.snapshot().value("state").toString(), QString("reading"));
        m.ingestSlots({slot(0, 1, true, 2716, 505, 2211, 0)}, 2000);
        QCOMPARE(m.snapshot().value("prefillTps").toDouble(), 405.0);
        // Escribiendo: 40 tokens en 1 s.
        m.ingestSlots({slot(0, 1, true, 2716, 505, 2211, 10)}, 3000);
        QCOMPARE(m.snapshot().value("state").toString(), QString("writing"));
        m.ingestSlots({slot(0, 1, true, 2716, 505, 2211, 50)}, 4000);
        QVariantMap s = m.snapshot();
        QCOMPARE(s.value("decodeTps").toDouble(), 40.0);
        QCOMPARE(s.value("msPerToken").toDouble(), 25.0);
        QCOMPARE(s.value("peakDecodeTps").toDouble(), 40.0);
        const QVariantMap ctx = s.value("context").toMap();
        QCOMPARE(ctx.value("prompt").toInt(), 2716);
        QCOMPARE(ctx.value("written").toInt(), 50);
        QVERIFY(ctx.value("active").toBool());

        // Termina entre dos polls.
        m.ingestSlots({slot(0, 1, false, 2716, 505, 2211, 70)}, 5000);
        s = m.snapshot();
        QCOMPARE(s.value("state").toString(), QString("idle"));
        QCOMPARE(s.value("requestsServed").toInt(), 1);
        const QVariantList reqs = m.recentRequests();
        QCOMPARE(reqs.size(), 1);
        const QVariantMap r = reqs.first().toMap();
        QCOMPARE(r.value("prompt").toInt(), 2716);
        QCOMPARE(r.value("reused").toInt(), 2211);
        QCOMPARE(r.value("prefill").toInt(), 505);
        QCOMPARE(r.value("output").toInt(), 70);
        // fin estimado = 4500 ms; decode desde 3000 ms con 10 tokens → 60/1.5 s
        QCOMPARE(r.value("decodeTps").toDouble(), 40.0);
        QCOMPARE(r.value("tookMs").toDouble(), 3500.0);
        QCOMPARE(m.snapshot().value("cacheReusePct").toDouble(), 2211 * 100.0 / 2716);
        // Repetir el mismo estado no duplica el request.
        m.ingestSlots({slot(0, 1, false, 2716, 505, 2211, 70)}, 6000);
        QCOMPARE(m.recentRequests().size(), 1);
    }

    void countsTasksThatStartAndEndBetweenPolls()
    {
        ServerMonitor m;
        m.ingestSlots({slot(0, 1, false, 10, 10, 0, 5)}, 0);
        // Tarea 2 corrió entera entre polls; tarea 3 reemplazó a una en curso.
        m.ingestSlots({slot(0, 2, false, 500, 100, 400, 30)}, 1000);
        QCOMPARE(m.recentRequests().size(), 1);
        QCOMPARE(m.recentRequests().first().toMap().value("tookMs").toDouble(), -1.0);
        m.ingestSlots({slot(0, 3, true, 600, 600, 0, 0)}, 2000);
        m.ingestSlots({slot(0, 4, true, 700, 0, 0, 0)}, 3000);
        QCOMPARE(m.snapshot().value("requestsServed").toInt(), 2);
        QCOMPARE(m.recentRequests().first().toMap().value("task").toInt(), 3);
    }

    void prefersActiveSlotForContext()
    {
        ServerMonitor m;
        m.ingestSlots({slot(0, 1, false, 100, 0, 0, 0), slot(1, 2, true, 900, 0, 0, 0)}, 0);
        QCOMPARE(m.snapshot().value("context").toMap().value("slot").toInt(), 1);
        QCOMPARE(m.snapshot().value("processing").toInt(), 1);
    }

    void historyIsBounded()
    {
        ServerMonitor m;
        for (int i = 0; i < ServerMonitor::kHistory + 30; ++i)
            m.ingestHardware({{"cpu", double(i)}, {"skip", -1.0}});
        const QVariantMap h = m.snapshot().value("history").toMap();
        QCOMPARE(h.value("cpu").toList().size(), ServerMonitor::kHistory);
        QCOMPARE(h.value("cpu").toList().last().toDouble(), double(ServerMonitor::kHistory + 29));
        QVERIFY(h.value("skip").toList().isEmpty()); // negativo = sin dato
    }

    void parsesBufferLinesAcrossChunks()
    {
        QCOMPARE(ServerMonitor::parseBufferLine(
                     "load_tensors:        CUDA0 model buffer size =  7890.12 MiB")
                     .value("kind").toString(), QString("model"));
        QCOMPARE(ServerMonitor::parseBufferLine(
                     "llama_kv_cache:      CUDA1 KV buffer size =   234.00 MiB")
                     .value("kind").toString(), QString("kv"));
        QVERIFY(ServerMonitor::parseBufferLine("load_tensors: offloaded 41/41 layers to GPU").isEmpty());

        ServerMonitor m;
        // La línea llega partida en dos lecturas de stderr.
        m.ingestServerLog("load_tensors:   CUDA0 model buf");
        m.ingestServerLog("fer size =  1000.00 MiB\nload_tensors: CPU_Mapped model buffer size = 50.0 MiB\n");
        m.ingestServerLog("llama_context:  CUDA0 compute buffer size =   100.50 MiB\n"
                          "llama_kv_cache: CUDA0 KV buffer size = 200 MiB\n"
                          "llama_memory_recurrent: CUDA0 RS buffer size = 20 MiB\n");
        const QVariantMap b = m.snapshot().value("buffers").toMap();
        const QVariantMap cuda0 = b.value("CUDA0").toMap();
        QCOMPARE(cuda0.value("model").toDouble(), 1000.0);
        QCOMPARE(cuda0.value("compute").toDouble(), 100.5);
        QCOMPARE(cuda0.value("kv").toDouble(), 220.0);
        QVERIFY(b.contains("CPU_Mapped"));
    }

    void mapsDevicesToGpuIndex()
    {
        QCOMPARE(ServerMonitor::gpuIndexForDevice("CUDA1"), 1);
        QCOMPARE(ServerMonitor::gpuIndexForDevice("ROCm0"), 0);
        QCOMPARE(ServerMonitor::gpuIndexForDevice("Vulkan2"), 2);
        QCOMPARE(ServerMonitor::gpuIndexForDevice("CUDA_Host"), -1);
        QCOMPARE(ServerMonitor::gpuIndexForDevice("CPU_Mapped"), -1);
    }

    void parsesNvidiaSmiWithTelemetryAndNa()
    {
        const QString csv =
            "0, NVIDIA GeForce RTX 3090, 24576, 23500, 1076, 243.12, 250.00, GPU-aaa, 60, 68, 4, 8\n"
            "1, NVIDIA GeForce RTX 3090, 24576, 23700, 876, [N/A], [N/A], GPU-bbb, 40, 72, 4, 8\n"
            "garbage\n";
        const QVariantMap s = ServerMonitor::parseNvidiaSmiGpus(csv);
        const QVariantList gpus = s.value("gpus").toList();
        QCOMPARE(gpus.size(), 2);
        const QVariantMap g0 = gpus.at(0).toMap();
        QCOMPARE(g0.value("uuid").toString(), QString("GPU-aaa"));
        QCOMPARE(g0.value("util").toDouble(), 60.0);
        QCOMPARE(g0.value("tempC").toDouble(), 68.0);
        QCOMPARE(g0.value("pcieGen").toDouble(), 4.0);
        QCOMPARE(gpus.at(1).toMap().value("drawW").toDouble(), 0.0);
        QCOMPARE(s.value("usedMb").toDouble(), 47200.0);
        QCOMPARE(s.value("utilPct").toDouble(), 50.0);
        QCOMPARE(s.value("maxTempC").toDouble(), 72.0);
        // Formato viejo (7 campos) sigue andando: sin telemetría extra.
        const QVariantMap old = ServerMonitor::parseNvidiaSmiGpus("0, X, 1000, 500, 500, 10, 20\n");
        QCOMPARE(old.value("gpus").toList().first().toMap().value("util").toDouble(), -1.0);
    }

    void breaksDownGpuMemory()
    {
        const QVariantMap stats = ServerMonitor::parseNvidiaSmiGpus(
            "0, RTX, 24576, 20000, 4576, 100, 250, GPU-aaa, 50, 60, 4, 16\n");
        const QVariantMap buffers{{"CUDA0", QVariantMap{{"model", 8000.0}, {"kv", 2000.0},
                                                        {"compute", 500.0}, {"output", 100.0}}},
                                  {"CUDA1", QVariantMap{{"model", 9999.0}}},
                                  {"CUDA_Host", QVariantMap{{"model", 50.0}}}};
        const auto apps = ServerMonitor::parseComputeApps(
            "1234, GPU-aaa, 18000\n999, GPU-aaa, 1500\n77, GPU-zzz, [N/A]\n");
        QVariantMap g = ServerMonitor::gpuBreakdown(stats, buffers, apps, 1234).first().toMap();
        QCOMPARE(g.value("weightsMb").toDouble(), 8000.0);
        QCOMPARE(g.value("kvMb").toDouble(), 2000.0);
        QCOMPARE(g.value("computeMb").toDouble(), 600.0);
        QCOMPARE(g.value("othersMb").toDouble(), 1500.0);
        QVERIFY(g.value("othersKnown").toBool());
        QCOMPARE(g.value("restMb").toDouble(), 20000.0 - 10600.0 - 1500.0);

        // Sin datos de procesos (WDDM): todo lo no explicado va a "resto".
        g = ServerMonitor::gpuBreakdown(stats, buffers, {}, 1234).first().toMap();
        QVERIFY(!g.value("othersKnown").toBool());
        QCOMPARE(g.value("restMb").toDouble(), 20000.0 - 10600.0);
    }

    void parsesProcFiles()
    {
        const auto cpu = ServerMonitor::parseProcStatCpu(
            "cpu  100 0 50 800 50 0 0 0 0 0\ncpu0 1 2 3 4\n");
        QCOMPARE(cpu.first, quint64(1000));
        QCOMPARE(cpu.second, quint64(850));
        const QVariantMap mem = ServerMonitor::parseMeminfo(
            "MemTotal:       131072000 kB\nMemFree: 1 kB\nMemAvailable:    40960000 kB\n");
        QCOMPARE(mem.value("totalMb").toDouble(), 128000.0);
        QCOMPARE(mem.value("availableMb").toDouble(), 40000.0);
        const auto disk = ServerMonitor::parseDiskstats(
            " 259       0 nvme0n1 100 0 2000 0 50 0 400 0 0 0 0\n"
            " 259       1 nvme0n1p1 100 0 9999 0 50 0 9999 0 0 0 0\n"
            "   8       0 sda 1 0 10 0 1 0 20 0 0 0 0\n"
            "   7       0 loop0 1 0 5000 0 1 0 5000 0 0 0 0\n");
        QCOMPARE(disk.first, quint64(2010));
        QCOMPARE(disk.second, quint64(420));
    }

    void parsesPrometheus()
    {
        const auto m = ServerMonitor::parsePrometheus(
            "# HELP llamacpp:requests_deferred x\n# TYPE llamacpp:requests_deferred gauge\n"
            "llamacpp:requests_deferred 2\nllamacpp:prompt_tokens_total 1234\n"
            "llamacpp:spec_decode_num_accepted_tokens_per_pos_total{position=\"0\"} 5\n");
        QCOMPARE(m.value("requests_deferred"), 2.0);
        QCOMPARE(m.value("prompt_tokens_total"), 1234.0);
        QCOMPARE(m.size(), 2);
        ServerMonitor mon;
        QCOMPARE(mon.snapshot().value("deferred").toDouble(), -1.0);
        mon.ingestMetrics("llamacpp:requests_deferred 3\n");
        QCOMPARE(mon.snapshot().value("deferred").toDouble(), 3.0);
    }

    void reportHasTheKeyNumbers()
    {
        ServerMonitor m;
        m.ingestSlots({slot(0, 1, false, 1, 1, 0, 1)}, 0);
        m.ingestSlots({slot(0, 2, true, 3000, 3000, 0, 0)}, 1000);
        m.ingestSlots({slot(0, 2, false, 3000, 3000, 0, 20)}, 2000);
        const QString text = ServerMonitor::report(
            m.snapshot(),
            ServerMonitor::parseNvidiaSmiGpus("0, RTX 3090, 24576, 20480, 4096, 200, 250, GPU-a, 55, 66, 4, 8\n"),
            {{"cpuPct", 28.0}, {"ramUsedGb", 90.4}, {"ramTotalGb", 124.0}},
            m.recentRequests(), "Qwen3 30B");
        QVERIFY(text.contains("Modelo: Qwen3 30B"));
        QVERIFY(text.contains("GPU 0 RTX 3090: 20.0/24.0 GB · 55% carga · 200 W · 66 °C"));
        QVERIFY(text.contains("CPU: 28% · RAM: 90.4/124.0 GB"));
        QVERIFY(text.contains("3000 / 0 / 3000 / 20"));
        QVERIFY(text.contains("Contexto: 3020 / 8192"));
    }

    void resetClearsEverything()
    {
        ServerMonitor m;
        m.ingestServerLog("x: CUDA0 model buffer size = 1 MiB\n");
        m.ingestSlots({slot(0, 1, true, 1, 1, 0, 0)}, 0);
        m.reset();
        QVERIFY(!m.hasSlots());
        QVERIFY(m.snapshot().value("buffers").toMap().isEmpty());
    }
};

QTEST_MAIN(TestServerMonitor)
#include "test_server_monitor.moc"

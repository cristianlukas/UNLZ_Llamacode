#include <QtTest>
#include <QDir>
#include <QTemporaryFile>
#include <QJsonObject>
#include <QJsonDocument>
#include "core/voice/VoiceTypes.h"
#include "core/voice/AudioCodec.h"
#include "core/voice/SttEngine.h"
#include "core/voice/TtsEngine.h"
#include "core/voice/VoiceController.h"
#include "core/profiles/ProfileTypes.h"
#include "core/voice/VoiceServerManager.h"

// Tests del modo Charla. Solo funciones puras (sin micrófono/red/playback):
// round-trip de config, codec WAV/RMS, builders de request STT/TTS, lógica VAD.
class TestVoice : public QObject
{
    Q_OBJECT
private slots:
    void configRoundTrip();
    void wavHeaderAndExtract();
    void rmsLevels();
    void sttMultipart();
    void sttParseTranscript();
    void ttsSpeechBody();
    void ttsPiperJsonLine();
    void ttsPiperResidentArgs();
    void ttsPiperAvailability();
    void vadTurnEnded();
    void ttsSentenceSplit();
    void ttsStreamingSentences();
    void ttsSanitizeForSpeech();
    void voiceInLaunchProfile();
    void sttServerCatalog();
    void voiceBinaryUrls();
    void managedBinaryLookup();
    void ttsVoiceCatalog();
    void ttsVoiceForLang();
};

void TestVoice::configRoundTrip()
{
    VoiceConfig c;
    c.enabled = true;
    c.sttProvider = "cloud";
    c.sttBaseUrl = "https://api.openai.com";
    c.sttModel = "whisper-1";
    c.sttKeyRef = "voice/openai";
    c.sttLanguage = "es";
    c.ttsProvider = "local";
    c.ttsVoice = "nova";
    c.ttsFormat = "mp3";
    c.vadSilenceMs = 1200;
    c.bargeIn = false;

    const VoiceConfig r = VoiceConfig::fromJson(c.toJson());
    QCOMPARE(r.enabled, true);
    QCOMPARE(r.sttProvider, QString("cloud"));
    QVERIFY(r.sttIsCloud());
    QCOMPARE(r.sttKeyRef, QString("voice/openai"));
    QCOMPARE(r.sttLanguage, QString("es"));
    QCOMPARE(r.ttsVoice, QString("nova"));
    QCOMPARE(r.ttsMode, QString("piper"));
    QCOMPARE(r.ttsFormat, QString("mp3"));
    QCOMPARE(r.vadSilenceMs, 1200);
    QCOMPARE(r.bargeIn, false);
    QVERIFY(!r.ttsIsCloud());
}

void TestVoice::wavHeaderAndExtract()
{
    QByteArray pcm;
    for (int i = 0; i < 100; ++i) {
        qint16 s = qint16(i * 100);
        pcm.append(char(s & 0xFF));
        pcm.append(char((s >> 8) & 0xFF));
    }
    const QByteArray wav = AudioCodec::pcm16ToWav(pcm, 16000);
    QVERIFY(wav.startsWith("RIFF"));
    QCOMPARE(wav.mid(8, 4), QByteArray("WAVE"));
    QCOMPARE(wav.size(), 44 + pcm.size());      // header de 44 bytes + datos
    // Round-trip: extraer el PCM debe devolver lo original.
    QCOMPARE(AudioCodec::wavExtractPcm(wav), pcm);
    // Entrada no-WAV: se devuelve tal cual.
    QCOMPARE(AudioCodec::wavExtractPcm(pcm), pcm);
}

void TestVoice::rmsLevels()
{
    QByteArray silence(800, '\0');
    QCOMPARE(AudioCodec::rmsBytes(silence), 0.0);

    QByteArray loud;
    for (int i = 0; i < 400; ++i) {
        qint16 s = (i % 2) ? 30000 : -30000;
        loud.append(char(s & 0xFF));
        loud.append(char((s >> 8) & 0xFF));
    }
    QVERIFY(AudioCodec::rmsBytes(loud) > 0.85);
}

void TestVoice::sttMultipart()
{
    const QByteArray wav = AudioCodec::pcm16ToWav(QByteArray(20, '\1'), 16000);
    QByteArray body = SttEngine::buildMultipart("BND", wav, "whisper-1", "es");
    QVERIFY(body.contains("name=\"file\""));
    QVERIFY(body.contains("name=\"model\""));
    QVERIFY(body.contains("whisper-1"));
    QVERIFY(body.contains("name=\"language\""));
    QVERIFY(body.contains("--BND--"));

    // language="auto" no debe emitir el campo language.
    QByteArray body2 = SttEngine::buildMultipart("BND", wav, "whisper-1", "auto");
    QVERIFY(!body2.contains("name=\"language\""));
}

void TestVoice::sttParseTranscript()
{
    QCOMPARE(SttEngine::parseTranscript("{\"text\":\"  hola mundo \"}"), QString("hola mundo"));
    QCOMPARE(SttEngine::parseTranscript("{\"error\":{\"message\":\"x\"}}"), QString());
    QCOMPARE(SttEngine::parseTranscript("garbage"), QString());
}

void TestVoice::ttsSpeechBody()
{
    const QByteArray body = TtsEngine::buildSpeechBody("tts-1", "alloy", "hola", "wav");
    const QJsonObject o = QJsonDocument::fromJson(body).object();
    QCOMPARE(o.value("model").toString(), QString("tts-1"));
    QCOMPARE(o.value("voice").toString(), QString("alloy"));
    QCOMPARE(o.value("input").toString(), QString("hola"));
    QCOMPARE(o.value("response_format").toString(), QString("wav"));
}

void TestVoice::ttsPiperJsonLine()
{
    // Línea JSON para piper residente (--json-input): un objeto por línea, con
    // text + output_file, terminado en '\n'.
    const QByteArray line = TtsEngine::buildPiperJsonLine("hola mundo", "C:/tmp/a.wav");
    QVERIFY(line.endsWith('\n'));
    const QJsonObject o = QJsonDocument::fromJson(line.trimmed()).object();
    QCOMPARE(o.value("text").toString(), QString("hola mundo"));
    QCOMPARE(o.value("output_file").toString(), QString("C:/tmp/a.wav"));

    // Caracteres especiales se escapan (sigue siendo una sola línea JSON válida).
    const QByteArray line2 = TtsEngine::buildPiperJsonLine("a\nb \"x\"", "o.wav");
    QCOMPARE(line2.count('\n'), 1);   // solo el terminador
    const QJsonObject o2 = QJsonDocument::fromJson(line2.trimmed()).object();
    QCOMPARE(o2.value("text").toString(), QString("a\nb \"x\""));
}

void TestVoice::ttsPiperResidentArgs()
{
    // Args del piper residente: -m <model> --json-input --output_dir <dir>.
    const QStringList a = VoiceServerManager::buildPiperResidentArgs("v.onnx", "C:/tmp");
    QVERIFY(a.contains("-m")); QVERIFY(a.contains("v.onnx"));
    QVERIFY(a.contains("--json-input"));
    const int idx = a.indexOf("--output_dir");
    QVERIFY(idx >= 0);
    QCOMPARE(a.value(idx + 1), QString("C:/tmp"));
    // No usa -f (eso es el modo per-call/fallback).
    QVERIFY(!a.contains("-f"));
}

void TestVoice::ttsPiperAvailability()
{
    // Fallback HTTP→piper: piperAvailable() refleja si el modelo .onnx existe.
    TtsEngine eng;
    const QString missing = QDir::temp().filePath("lc-no-such-voice.onnx");
    QFile::remove(missing);
    eng.setPiper(QString(), missing);
    QVERIFY(!eng.piperAvailable());

    QTemporaryFile voice(QDir::temp().filePath("lc-voice-XXXXXX.onnx"));
    QVERIFY(voice.open());
    eng.setPiper(QString(), voice.fileName());
    QVERIFY(eng.piperAvailable());
}

void TestVoice::vadTurnEnded()
{
    // Sin voz (peak bajo): nunca termina aunque haya silencio.
    QVERIFY(!VoiceController::turnEnded(0.01, 0.03, 2000, 800));
    // Hubo voz pero el silencio aún no llega al umbral.
    QVERIFY(!VoiceController::turnEnded(0.10, 0.03, 500, 800));
    // Hubo voz y silencio suficiente → fin de turno.
    QVERIFY(VoiceController::turnEnded(0.10, 0.03, 900, 800));
}

void TestVoice::ttsSentenceSplit()
{
    // Texto corto (< minLen): un solo chunk.
    QCOMPARE(VoiceController::splitSentences("Hola.", 40),
             QStringList{QStringLiteral("Hola.")});

    // Varias oraciones largas: se separan por cierre (.!?) superando minLen.
    const QString t = QStringLiteral(
        "Voy a abrir el navegador ahora mismo para vos. "
        "Después busco la página que pediste. ¿Te parece bien así?");
    const QStringList parts = VoiceController::splitSentences(t, 20);
    QCOMPARE(parts.size(), 3);
    QVERIFY(parts.first().startsWith("Voy a abrir"));
    QVERIFY(parts.last().endsWith("?"));

    // Fragmentos cortos se acumulan hasta superar minLen (no spawnea por "Sí.").
    // Ningún cierre intermedio alcanza minLen → todo queda en un solo chunk.
    const QStringList merged = VoiceController::splitSentences(
        QStringLiteral("Sí. No. Tal vez. Lo voy a pensar con calma un rato."), 30);
    QCOMPARE(merged.size(), 1);

    // Solo espacios → sin chunks. Texto sin puntuación final → un chunk.
    QVERIFY(VoiceController::splitSentences("   ", 40).isEmpty());
    QCOMPARE(VoiceController::splitSentences("texto sin puntuacion final largo", 40).size(), 1);
}

void TestVoice::ttsStreamingSentences()
{
    // Solo emite oraciones YA cerradas; el fragmento incompleto queda sin consumir.
    int consumed = -1;
    QStringList s = VoiceController::splitCompleteSentences(
        QStringLiteral("Voy a abrir el navegador ahora. Después busc"), 20, &consumed);
    QCOMPARE(s, QStringList{QStringLiteral("Voy a abrir el navegador ahora.")});
    // consumed apunta justo después de la oración cerrada; el resto se reacumula.
    QCOMPARE(QStringLiteral("Voy a abrir el navegador ahora. Después busc").mid(consumed),
             QStringLiteral(" Después busc"));

    // Sin ningún cierre que supere minLen → nada emitido, consumed 0.
    consumed = -1;
    QVERIFY(VoiceController::splitCompleteSentences(QStringLiteral("hola"), 20, &consumed).isEmpty());
    QCOMPARE(consumed, 0);

    // Simulación de streaming incremental: alimentar prefijos crecientes y juntar
    // lo emitido debe reconstruir el texto sin duplicar ni perder oraciones.
    const QString finalText = QStringLiteral(
        "Abro el navegador para vos. Busco la página pedida. ¿Algo más?");
    const QList<int> cuts = {10, 28, 45, 55, int(finalText.size())};
    int off = 0;                      // chars ya consumidos (como m_streamConsumed)
    QStringList spoken;
    for (int cut : cuts) {
        const QString accumulated = finalText.left(cut);   // texto recibido hasta ahora
        int c = 0;
        spoken += VoiceController::splitCompleteSentences(accumulated.mid(off), 20, &c);
        off += c;
    }
    // Cola final (sin terminador "?" cerrado por minLen quizá) se encola al flush.
    const QString tail = finalText.mid(off).trimmed();
    if (!tail.isEmpty()) spoken += VoiceController::splitSentences(tail);
    // Reconstrucción: las dos primeras oraciones y la pregunta final, en orden.
    QCOMPARE(spoken.size(), 3);
    QVERIFY(spoken.at(0).startsWith("Abro el navegador"));
    QVERIFY(spoken.at(1).startsWith("Busco la página"));
    QVERIFY(spoken.last().endsWith("?"));
}

void TestVoice::ttsSanitizeForSpeech()
{
    // Bloque <think> cerrado: se quita, queda solo la respuesta.
    QCOMPARE(VoiceController::sanitizeForSpeech(
                 QStringLiteral("<think>razono esto</think>\nHola, abro el navegador.")),
             QStringLiteral("Hola, abro el navegador."));
    // <think> abierto sin cerrar (razonamiento en vuelo): cortar desde ahí.
    QCOMPARE(VoiceController::sanitizeForSpeech(
                 QStringLiteral("Dale. <think>todavía pensando")),
             QStringLiteral("Dale."));
    // Indicador transitorio de tool ⏳: se descarta esa línea, queda el texto.
    QCOMPARE(VoiceController::sanitizeForSpeech(
                 QStringLiteral("Abro el navegador.\n⏳ preparando `open_url`… (~12 tokens generados)")),
             QStringLiteral("Abro el navegador."));
    // Texto limpio pasa intacto (modo chat sin thinking).
    QCOMPARE(VoiceController::sanitizeForSpeech(QStringLiteral("Listo, ya está.")),
             QStringLiteral("Listo, ya está."));
}

void TestVoice::voiceInLaunchProfile()
{
    // La config de voz viaja dentro del LaunchProfile (round-trip JSON).
    LaunchProfile p;
    p.id = "lp1"; p.name = "1_test";
    p.voice.sttProvider = "cloud";
    p.voice.sttBaseUrl = "https://stt.example";
    p.voice.ttsVoice = "nova";
    p.voice.vadSegmentMs = 420;
    const LaunchProfile r = LaunchProfile::fromJson(p.toJson());
    QCOMPARE(r.voice.sttProvider, QString("cloud"));
    QCOMPARE(r.voice.sttBaseUrl, QString("https://stt.example"));
    QCOMPARE(r.voice.ttsVoice, QString("nova"));
    QCOMPARE(r.voice.vadSegmentMs, 420);
}

void TestVoice::sttServerCatalog()
{
    const QVariantList cat = VoiceServerManager::sttCatalog();
    QVERIFY(cat.size() >= 1);
    // El motor base existe y es whisper.cpp (endpoint /inference).
    const QVariantMap base = VoiceServerManager::sttEngine("whisper-base");
    QVERIFY(!base.isEmpty());
    QCOMPARE(VoiceServerManager::endpointPath("whisper-base"), QString("/inference"));
    QVERIFY(VoiceServerManager::modelPath("whisper-base").endsWith("ggml-base.bin"));
    QVERIFY(VoiceServerManager::sttEngine("inexistente").isEmpty());

    // Args de whisper-server: modelo + host + port, y -l solo si lang != auto.
    QStringList a = VoiceServerManager::buildWhisperArgs("m.bin", "127.0.0.1", 8081, "auto");
    QVERIFY(a.contains("-m")); QVERIFY(a.contains("m.bin"));
    QVERIFY(a.contains("--port")); QVERIFY(a.contains("8081"));
    QVERIFY(!a.contains("-l"));
    QStringList b = VoiceServerManager::buildWhisperArgs("m.bin", "127.0.0.1", 8081, "es");
    QVERIFY(b.contains("-l")); QVERIFY(b.contains("es"));
}

void TestVoice::voiceBinaryUrls()
{
#ifdef Q_OS_WIN
    const QString whisperUrl = VoiceServerManager::defaultBinaryUrl("whisper-server");
    QVERIFY(whisperUrl.startsWith("https://github.com/ggml-org/whisper.cpp/"));
    QVERIFY(whisperUrl.contains("/releases/latest/download/"));
    QVERIFY(whisperUrl.endsWith("/whisper-bin-x64.zip"));
    const QString piperUrl = VoiceServerManager::defaultBinaryUrl("piper");
    QVERIFY(piperUrl.startsWith("https://github.com/rhasspy/piper/releases/download/"));
    QVERIFY(piperUrl.endsWith("/piper_windows_amd64.zip"));
#endif
}

void TestVoice::managedBinaryLookup()
{
    const QString path = VoiceServerManager::installedBinaryPath("unknown-kind");
    QVERIFY(path.isEmpty());
}

void TestVoice::ttsVoiceCatalog()
{
    const QVariantList cat = VoiceServerManager::ttsCatalog();
    QVERIFY(cat.size() >= 1);
    const QVariantMap v = VoiceServerManager::ttsVoice("es_ES-davefx-medium");
    QVERIFY(!v.isEmpty());
    QCOMPARE(v.value("lang").toString(), QString("es"));
    QVERIFY(VoiceServerManager::ttsModelPath("es_ES-davefx-medium").endsWith(".onnx"));
    QVERIFY(VoiceServerManager::ttsVoice("nope").isEmpty());

    // piper args: -m model -f out.
    const QStringList a = VoiceServerManager::buildPiperArgs("v.onnx", "out.wav");
    QVERIFY(a.contains("-m")); QVERIFY(a.contains("v.onnx"));
    QVERIFY(a.contains("-f")); QVERIFY(a.contains("out.wav"));
}

void TestVoice::ttsVoiceForLang()
{
    // Voz piper por idioma de la app: es→española, en→inglesa, idioma sin voz o
    // vacío → cae a la española base.
    QCOMPARE(VoiceServerManager::defaultTtsVoiceForLang("es"), QString("es_ES-davefx-medium"));
    QCOMPARE(VoiceServerManager::defaultTtsVoiceForLang("en"), QString("en_US-amy-medium"));
    QCOMPARE(VoiceServerManager::defaultTtsVoiceForLang("zh"), QString("es_ES-davefx-medium"));
    QCOMPARE(VoiceServerManager::defaultTtsVoiceForLang(QString()), QString("es_ES-davefx-medium"));
}

QTEST_MAIN(TestVoice)
#include "test_voice.moc"

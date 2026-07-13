// Tests unitarios de la lógica pura del núcleo:
//   - GGUFScanner: inferencia familia/quant/vision/draft por nombre de archivo.
//   - EffectiveProfileBuilder: composición de args + degradación/bloqueo por flags.
//
// Build: cmake -DBUILD_TESTS=ON ...  → target LlamaCodeTests.
// Run:   ctest --test-dir build  (o ejecutar LlamaCodeTests directo).

#include <QtTest>
#include "core/GGUFScanner.h"
#include "core/profiles/EffectiveProfileBuilder.h"
#include "core/profiles/ProfileTypes.h"
#include "core/profiles/MtpDetection.h"
#include "core/LlamaBinary.h"
#include "core/CatalogModel.h"

class CoreTests : public QObject
{
    Q_OBJECT

private slots:
    // ── GGUFScanner::inferFamily ──
    void inferFamily_data();
    void inferFamily();

    // ── GGUFScanner::inferQuant ──
    void inferQuant_data();
    void inferQuant();

    // ── GGUFScanner candidatos vision/draft ──
    void visionCandidate();
    void draftCandidate();

    // ── GGUFScanner::readComposition (parser binario) ──
    void readComposition_realTensors();
    void readComposition_metadata();
    void readComposition_rejectsGarbage();

    // ── GGUFScanner::isDegradedQatQuant ──
    void degradedQat_data();
    void degradedQat();

    // ── EffectiveProfileBuilder ──
    void builder_emitsHostPort();
    void builder_dropsUnsupportedFlag();
    void builder_missingModelIsBlocking();
    void builder_emitsSpecFlags();
    void builder_missingDraftIsBlocking();
    void builder_rawDraftMtpRequiresDraftModel();
    void builder_emitsSelfContainedMtpFlags();
    void builder_dropsGemmaDraftOnOldBinary();
    void builder_forcesF16KvWithDraft();
    void builder_appliesQwenCodingSamplingPreset();
    void builder_warnsOnManualQwenSampling();
    void builder_emitsTensorOverrides();
    void builder_warnsOnMalformedTensorOverride();
    void runtimePreset_roundtripsTensorOverrides();
};

void CoreTests::inferFamily_data()
{
    QTest::addColumn<QString>("file");
    QTest::addColumn<QString>("family");
    QTest::newRow("qwen")    << "Qwen2.5-7B-Instruct-Q4_K_M.gguf" << "qwen";
    QTest::newRow("llama")   << "Meta-Llama-3.1-8B.Q5_K_M.gguf"   << "llama";
    QTest::newRow("mistral") << "Mistral-7B-v0.3-Q6_K.gguf"       << "mistral";
    QTest::newRow("gemma")   << "gemma-2-9b-it-Q4_0.gguf"         << "gemma";
    QTest::newRow("phi")     << "Phi-3.5-mini-instruct-Q8_0.gguf" << "phi";
    QTest::newRow("deepseek")<< "DeepSeek-Coder-V2-Q4_K_M.gguf"   << "deepseek";
}

void CoreTests::inferFamily()
{
    QFETCH(QString, file);
    QFETCH(QString, family);
    QCOMPARE(GGUFScanner::inferFamily(file).toLower(), family);
}

void CoreTests::inferQuant_data()
{
    QTest::addColumn<QString>("file");
    QTest::addColumn<QString>("quant");
    QTest::newRow("q4km") << "model-Q4_K_M.gguf" << "Q4_K_M";
    QTest::newRow("q8")   << "model-Q8_0.gguf"   << "Q8_0";
    QTest::newRow("iq3")  << "model-IQ3_XS.gguf" << "IQ3_XS";
    QTest::newRow("bf16") << "model-BF16.gguf"   << "BF16";
}

void CoreTests::inferQuant()
{
    QFETCH(QString, file);
    QFETCH(QString, quant);
    QCOMPARE(GGUFScanner::inferQuant(file).toUpper(), quant);
}

void CoreTests::visionCandidate()
{
    QVERIFY(GGUFScanner::isVisionCandidate("llava-v1.6-mmproj-f16.gguf"));
    QVERIFY(!GGUFScanner::isVisionCandidate("Qwen2.5-7B-Q4_K_M.gguf"));
}

void CoreTests::draftCandidate()
{
    // "draft" en el nombre, o tamaño chico (<2GB).
    QVERIFY(GGUFScanner::isDraftCandidate("qwen-0.5b-draft-Q4.gguf", 400LL * 1024 * 1024));
    QVERIFY(GGUFScanner::isDraftCandidate("tiny.gguf", 1LL * 1024 * 1024 * 1024));
    QVERIFY(!GGUFScanner::isDraftCandidate("Qwen2.5-32B-Q5_K_M.gguf", 20LL * 1024 * 1024 * 1024));
    QVERIFY(MtpDetection::isSelfContained("ThinkingCap-Qwen3.6-27B-Q3_K_M-MTP.gguf"));
    QVERIFY(!MtpDetection::isSelfContained("Qwen3.6-27B-Q3_K_M.gguf"));
}

// ── Helpers para construir un GGUF sintético en disco ──────────────────────
namespace {
void putU32(QByteArray &b, quint32 v) {
    for (int i = 0; i < 4; ++i) b.append(char((v >> (8*i)) & 0xFF));
}
void putU64(QByteArray &b, quint64 v) {
    for (int i = 0; i < 8; ++i) b.append(char((v >> (8*i)) & 0xFF));
}
void putStr(QByteArray &b, const QByteArray &s) {
    putU64(b, quint64(s.size()));
    b.append(s);
}
void putMetaString(QByteArray &b, const QByteArray &key, const QByteArray &value) {
    putStr(b, key); putU32(b, 8); putStr(b, value);
}
void putMetaU32(QByteArray &b, const QByteArray &key, quint32 value) {
    putStr(b, key); putU32(b, 4); putU32(b, value);
}
void putMetaU64(QByteArray &b, const QByteArray &key, quint64 value) {
    putStr(b, key); putU32(b, 10); putU64(b, value);
}
// Escribe un tensor info: name, n_dims, dims[], type, offset.
void putTensor(QByteArray &b, const QByteArray &name,
               const QList<quint64> &dims, quint32 type) {
    putStr(b, name);
    putU32(b, quint32(dims.size()));
    for (quint64 d : dims) putU64(b, d);
    putU32(b, type);
    putU64(b, 0); // offset
}
// GGUF v3 mínimo: magic, version, tensorCount, kvCount=0, luego tensor infos.
QString writeGgufFixture(const QString &name, const QList<QPair<quint32, quint64>> &tensors)
{
    QByteArray b;
    putU32(b, 0x46554747u); // "GGUF"
    putU32(b, 3);           // version
    putU64(b, quint64(tensors.size()));
    putU64(b, 0);           // kv count
    int idx = 0;
    for (const auto &t : tensors)
        putTensor(b, QByteArray("t") + QByteArray::number(idx++),
                  {t.second}, t.first);
    const QString path = QDir(QDir::tempPath()).filePath(name);
    QFile f(path);
    if (f.open(QIODevice::WriteOnly)) { f.write(b); f.close(); }
    return path;
}
} // namespace

void CoreTests::readComposition_realTensors()
{
    // Archivo llamado "Q4_K_XL" pero contenido = mayoría q4_0 (caso unsloth).
    // type ids: 2=q4_0, 14=q6_k, 0=f32.
    const QString path = writeGgufFixture(
        "gemma-fake-Q4_K_XL.gguf",
        { {2, 1000000}, {2, 2000000}, {14, 50000}, {0, 1000} });

    const auto c = GGUFScanner::readComposition(path, QFileInfo(path).size());
    QVERIFY(c.valid);
    QCOMPARE(c.dominantQuant, QStringLiteral("q4_0")); // por elementos, no por nombre
    QCOMPARE(c.typeTensors.value("q4_0"), 2);
    QCOMPARE(c.typeTensors.value("q6_k"), 1);
    QVERIFY(c.totalElements == 3051000);
    QVERIFY(c.bpw > 0.0);
    QVERIFY(c.breakdown().contains("q4_0:2"));
}

void CoreTests::readComposition_metadata()
{
    QByteArray b;
    putU32(b, 0x46554747u); putU32(b, 3);
    putU64(b, 1); putU64(b, 3);
    putMetaString(b, "general.architecture", "qwen2");
    putMetaU64(b, "general.parameter_count", 7000000000ULL);
    putMetaU32(b, "qwen2.context_length", 131072);
    putTensor(b, "token_embd.weight", {1024, 1024}, 2);
    const QString path = QDir(QDir::tempPath()).filePath("metadata-fixture.gguf");
    QFile f(path); QVERIFY(f.open(QIODevice::WriteOnly)); f.write(b); f.close();

    const auto c = GGUFScanner::readComposition(path, QFileInfo(path).size());
    QVERIFY(c.valid);
    QCOMPARE(c.architecture, QStringLiteral("qwen2"));
    QCOMPARE(c.parameterCount, 7000000000LL);
    QCOMPARE(c.trainedContext, 131072);
}

void CoreTests::readComposition_rejectsGarbage()
{
    const QString path = QDir(QDir::tempPath()).filePath("not_a_gguf.bin");
    QFile f(path);
    QVERIFY(f.open(QIODevice::WriteOnly));
    f.write("this is definitely not a gguf header at all");
    f.close();
    const auto c = GGUFScanner::readComposition(path, QFileInfo(path).size());
    QVERIFY(!c.valid);
}

void CoreTests::degradedQat_data()
{
    QTest::addColumn<QString>("file");
    QTest::addColumn<QString>("family");
    QTest::addColumn<QString>("quantReal");
    QTest::addColumn<bool>("degraded");

    QTest::newRow("google-raw")  << "gemma-4-E4B_q4_0-it-qat.gguf" << "gemma" << "q4_0" << true;
    QTest::newRow("unsloth-ud")  << "gemma-4-E4B-it-qat-UD-Q4_K_XL.gguf" << "gemma" << "q4_0" << false;
    QTest::newRow("unsloth-name")<< "gemma-4-qat-unsloth.gguf" << "gemma" << "q4_0" << false;
    QTest::newRow("not-qat")     << "gemma-4-E4B-it-Q4_0.gguf" << "gemma" << "q4_0" << false;
    QTest::newRow("not-gemma")   << "qwen-qat-q4_0.gguf" << "qwen" << "q4_0" << false;
    QTest::newRow("not-q4_0")    << "gemma-qat-Q6_K.gguf" << "gemma" << "q6_k" << false;
}

void CoreTests::degradedQat()
{
    QFETCH(QString, file);
    QFETCH(QString, family);
    QFETCH(QString, quantReal);
    QFETCH(bool, degraded);
    QCOMPARE(GGUFScanner::isDegradedQatQuant(file, family, quantReal), degraded);
}

// build() valida que el binario exista en disco → necesitamos un archivo real.
static QString existingBinaryPath()
{
    static QString p;
    if (p.isEmpty()) {
        p = QDir(QDir::tempPath()).filePath("llamacode_test_bin.exe");
        QFile f(p);
        if (f.open(QIODevice::WriteOnly)) { f.write("x"); f.close(); }
    }
    return p;
}

// Construye un Context mínimo válido (binario + modelo presentes).
static EffectiveProfileBuilder::Context makeCtx()
{
    EffectiveProfileBuilder::Context ctx;
    ctx.binary.id = "bin1";
    ctx.binary.path = existingBinaryPath();
    ctx.binary.name = "test";
    ctx.backend.host = "127.0.0.1";
    ctx.backend.port = 9099;
    ctx.backend.binaryId = "bin1";
    ctx.catalogModel.id = "m1";
    ctx.catalogModel.absolutePath = "C:/models/test.gguf";
    ctx.model.modelId = "m1";
    return ctx;
}

void CoreTests::builder_emitsHostPort()
{
    auto ctx = makeCtx();
    const EffectiveProfile ep = EffectiveProfileBuilder::build(ctx);
    const int hi = ep.effectiveArgs.indexOf("--host");
    const int pi = ep.effectiveArgs.indexOf("--port");
    QVERIFY(hi >= 0 && hi + 1 < ep.effectiveArgs.size());
    QCOMPARE(ep.effectiveArgs[hi + 1], QStringLiteral("127.0.0.1"));
    QVERIFY(pi >= 0 && pi + 1 < ep.effectiveArgs.size());
    QCOMPARE(ep.effectiveArgs[pi + 1], QStringLiteral("9099"));
}

void CoreTests::builder_dropsUnsupportedFlag()
{
    auto ctx = makeCtx();
    // Binario que sólo soporta --host/--port/--model → flash-attn debe dropearse.
    ctx.binary.supportedFlags = QStringList{"--host", "--port", "--model"};
    ctx.runtime.flashAttention = true;
    const EffectiveProfile ep = EffectiveProfileBuilder::build(ctx);
    QVERIFY(!ep.effectiveArgs.contains("--flash-attn"));
    QVERIFY(!ep.warnings.isEmpty());  // degradación reportada
}

void CoreTests::builder_missingModelIsBlocking()
{
    auto ctx = makeCtx();
    ctx.model.modelId.clear();
    ctx.catalogModel = CatalogModel{};  // sin modelo resuelto
    const EffectiveProfile ep = EffectiveProfileBuilder::build(ctx);
    QVERIFY(!ep.blockingErrors.isEmpty());
}

// Con draft model resuelto, los flags spec-draft seteados deben emitirse.
void CoreTests::builder_emitsSpecFlags()
{
    auto ctx = makeCtx();
    ctx.model.draftModelId = "d1";
    ctx.model.specType = "draft-mtp";
    ctx.model.specDraftNMax = 3;
    ctx.model.specDraftNgl = "all";
    ctx.model.specDraftTypeK = "q8_0";
    ctx.model.specDraftTypeV = "q8_0";
    ctx.draftModel.id = "d1";
    ctx.draftModel.isAvailable = true;
    ctx.draftModel.absolutePath = "C:/models/draft.gguf";

    const EffectiveProfile ep = EffectiveProfileBuilder::build(ctx);
    const QStringList &a = ep.effectiveArgs;
    // Con specType seteado (MTP/DFlash) el draft va por --spec-draft-model.
    // --spec-type es sólo para modos sin draft model (ngram-*); emitir
    // "draft-mtp" rompe llama-server actual.
    QVERIFY(a.contains("--spec-draft-model"));
    QVERIFY(!a.contains("--spec-type"));
    int i = a.indexOf("--spec-draft-n-max");
    QVERIFY(i >= 0 && a[i + 1] == "3");
    i = a.indexOf("--spec-draft-ngl");
    QVERIFY(i >= 0 && a[i + 1] == "all");
    QVERIFY(a.contains("--spec-draft-type-k"));
    QVERIFY(a.contains("--spec-draft-type-v"));
}

void CoreTests::builder_missingDraftIsBlocking()
{
    auto ctx = makeCtx();
    ctx.model.draftModelId = "d1";
    ctx.model.specType = "draft-mtp";
    ctx.model.specDraftNMax = 3;
    ctx.model.specDraftNgl = "all";
    ctx.draftModel = CatalogModel{};

    const EffectiveProfile ep = EffectiveProfileBuilder::build(ctx);
    QVERIFY(!ep.blockingErrors.isEmpty());
    bool mentionsDraft = false;
    for (const QString &e : ep.blockingErrors)
        if (e.contains(QStringLiteral("Draft model"), Qt::CaseInsensitive))
            mentionsDraft = true;
    QVERIFY2(mentionsDraft, qPrintable(ep.blockingErrors.join(QStringLiteral("\n"))));
    QVERIFY(!ep.effectiveArgs.contains(QStringLiteral("--spec-draft-model")));
}

void CoreTests::builder_rawDraftMtpRequiresDraftModel()
{
    auto ctx = makeCtx();
    ctx.launch.extraArgs = {
        QStringLiteral("--spec-type"),
        QStringLiteral("draft-mtp"),
        QStringLiteral("--spec-draft-n-max"),
        QStringLiteral("3")
    };

    const EffectiveProfile ep = EffectiveProfileBuilder::build(ctx);
    QVERIFY(!ep.blockingErrors.isEmpty());
    bool mentionsProfileDraft = false;
    for (const QString &e : ep.blockingErrors)
        if (e.contains(QStringLiteral("draftModel"), Qt::CaseInsensitive))
            mentionsProfileDraft = true;
    QVERIFY2(mentionsProfileDraft, qPrintable(ep.blockingErrors.join(QStringLiteral("\n"))));
}

void CoreTests::builder_emitsSelfContainedMtpFlags()
{
    auto ctx = makeCtx();
    ctx.catalogModel.fileName = "ThinkingCap-Qwen3.6-27B-Q3_K_M-MTP.gguf";
    ctx.model.specType = "draft-mtp";
    ctx.model.specDraftNMax = 3;

    const EffectiveProfile ep = EffectiveProfileBuilder::build(ctx);
    QVERIFY(ep.blockingErrors.isEmpty());
    const int type = ep.effectiveArgs.indexOf("--spec-type");
    QVERIFY(type >= 0 && ep.effectiveArgs.value(type + 1) == "draft-mtp");
    const int nmax = ep.effectiveArgs.indexOf("--spec-draft-n-max");
    QVERIFY(nmax >= 0 && ep.effectiveArgs.value(nmax + 1) == "3");
    QVERIFY(!ep.effectiveArgs.contains("--spec-draft-model"));
}

void CoreTests::builder_dropsGemmaDraftOnOldBinary()
{
    auto ctx = makeCtx();
    ctx.binary.versionHint = "b9045";
    ctx.model.draftModelId = "d1";
    ctx.model.specType = "draft-mtp";
    ctx.model.specDraftNMax = 3;
    ctx.model.specDraftNgl = "all";
    ctx.draftModel.id = "d1";
    ctx.draftModel.isAvailable = true;
    ctx.draftModel.absolutePath = "C:/models/mtp-gemma-4-12b-it.gguf";

    const EffectiveProfile ep = EffectiveProfileBuilder::build(ctx);
    const QStringList &a = ep.effectiveArgs;
    QVERIFY(!ep.blockingErrors.isEmpty());
    QVERIFY(!a.contains("--spec-draft-model"));
    QVERIFY(!a.contains("--spec-draft-n-max"));
    QVERIFY(!a.contains("--spec-draft-ngl"));
}

// Spec decoding activo + KV cache cuantizado → forzar f16 (no emitir el flag) y
// avisar. Sin draft, el quant pasa normal.
void CoreTests::builder_forcesF16KvWithDraft()
{
    // Caso sin draft: el quant se emite.
    {
        auto ctx = makeCtx();
        ctx.runtime.cacheType = "q4_0";
        const EffectiveProfile ep = EffectiveProfileBuilder::build(ctx);
        QVERIFY(ep.effectiveArgs.contains("--cache-type-k"));
    }
    // Caso con draft disponible: se descarta el quant y se avisa.
    {
        auto ctx = makeCtx();
        ctx.runtime.cacheType = "q4_0";
        ctx.model.draftModelId = "d1";
        ctx.draftModel.id = "d1";
        ctx.draftModel.isAvailable = true;
        ctx.draftModel.absolutePath = "C:/models/draft.gguf";
        const EffectiveProfile ep = EffectiveProfileBuilder::build(ctx);
        QVERIFY(!ep.effectiveArgs.contains("--cache-type-k"));
        bool warned = false;
        for (const QString &w : ep.warnings)
            if (w.contains("f16")) warned = true;
        QVERIFY(warned);
    }
}

void CoreTests::builder_appliesQwenCodingSamplingPreset()
{
    auto ctx = makeCtx();
    ctx.catalogModel.fileName = "Qwen3.6-27B-Coder-Q5_K_M.gguf";
    ctx.catalogModel.familyHint = "qwen";

    const EffectiveProfile ep = EffectiveProfileBuilder::build(ctx);
    const QStringList &a = ep.effectiveArgs;

    int i = a.indexOf("--temp");
    QVERIFY(i >= 0 && i + 1 < a.size());
    QCOMPARE(a[i + 1], QStringLiteral("0.6"));
    i = a.indexOf("--top-k");
    QVERIFY(i >= 0 && i + 1 < a.size());
    QCOMPARE(a[i + 1], QStringLiteral("20"));
    i = a.indexOf("--min-p");
    QVERIFY(i >= 0 && i + 1 < a.size());
    QCOMPARE(a[i + 1], QStringLiteral("0.0"));
}

void CoreTests::builder_warnsOnManualQwenSampling()
{
    auto ctx = makeCtx();
    ctx.catalogModel.fileName = "Qwen3.6-27B-Coder-Q5_K_M.gguf";
    ctx.catalogModel.familyHint = "qwen";
    ctx.launch.extraArgs = {"--temp 1.0 --top-k 64"};

    const EffectiveProfile ep = EffectiveProfileBuilder::build(ctx);
    QCOMPARE(ep.effectiveArgs.count("--temp"), 1);
    QCOMPARE(ep.effectiveArgs.count("--top-k"), 1);

    bool tempWarn = false;
    bool topKWarn = false;
    for (const QString &w : ep.warnings) {
        if (w.contains("--temp=1.0"))
            tempWarn = true;
        if (w.contains("--top-k=64"))
            topKWarn = true;
    }
    QVERIFY(tempWarn);
    QVERIFY(topKWarn);
}

// Role-aware per-tensor quant: cada spec válido se emite como --override-tensor.
void CoreTests::builder_emitsTensorOverrides()
{
    auto ctx = makeCtx();
    ctx.runtime.tensorOverrides = {"ffn_.*=Q4_K", "attn_.*=Q8_0"};
    const EffectiveProfile ep = EffectiveProfileBuilder::build(ctx);
    const QStringList &a = ep.effectiveArgs;
    QCOMPARE(a.count("--override-tensor"), 2);
    int i = a.indexOf("--override-tensor");
    QVERIFY(i >= 0 && i + 1 < a.size());
    QCOMPARE(a[i + 1], QStringLiteral("ffn_.*=Q4_K"));
}

// Spec sin '=' se descarta con warning, sin emitir el flag.
void CoreTests::builder_warnsOnMalformedTensorOverride()
{
    auto ctx = makeCtx();
    ctx.runtime.tensorOverrides = {"ffn_only_no_type", "  ", "ffn_.*=Q4_K"};
    const EffectiveProfile ep = EffectiveProfileBuilder::build(ctx);
    QCOMPARE(ep.effectiveArgs.count("--override-tensor"), 1);
    bool warned = false;
    for (const QString &w : ep.warnings)
        if (w.contains("ffn_only_no_type")) warned = true;
    QVERIFY(warned);
}

// Persistencia: tensorOverrides sobrevive toJson→fromJson; entries vacías se filtran.
void CoreTests::runtimePreset_roundtripsTensorOverrides()
{
    RuntimePreset p;
    p.tensorOverrides = {"ffn_.*=Q4_K", "  ", "attn_.*=Q8_0"};
    const RuntimePreset r = RuntimePreset::fromJson(p.toJson());
    QCOMPARE(r.tensorOverrides.size(), 2);
    QCOMPARE(r.tensorOverrides[0], QStringLiteral("ffn_.*=Q4_K"));
    QCOMPARE(r.tensorOverrides[1], QStringLiteral("attn_.*=Q8_0"));

    // Vacío no debe escribir la key.
    RuntimePreset empty;
    QVERIFY(!empty.toJson().contains("tensorOverrides"));
}

QTEST_MAIN(CoreTests)
#include "test_gguf_profiles.moc"

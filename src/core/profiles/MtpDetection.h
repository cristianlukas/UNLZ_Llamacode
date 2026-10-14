#pragma once

#include <QFileInfo>
#include <QRegularExpression>
#include <QString>
#include <QStringList>

namespace MtpDetection {

// Heurística conservadora para GGUFs que transportan un speculator (MTP/DSpark)
// junto al modelo principal. La mayoría de publishers marca MTP en el filename.
// BottleCapAI publica ThinkingCap con el cabezal integrado pero conserva nombres
// de quant estándar (p. ej. ThinkingCap-Qwen3.6-27B-Q4_K_M.gguf).
// DeepSeek-V4-Flash-0731 es el checkpoint oficial con cabezal DSpark integrado.
inline bool isSelfContained(const QString &fileName)
{
    const QString base = QFileInfo(fileName).completeBaseName();
    static const QRegularExpression marker(
        QStringLiteral(R"((^|[-_.])mtp($|[-_.]))"),
        QRegularExpression::CaseInsensitiveOption);
    static const QRegularExpression thinkingCapQwen36(
        QStringLiteral(R"((^|[-_.])thinkingcap[-_.]qwen3[._-]?6($|[-_.]))"),
        QRegularExpression::CaseInsensitiveOption);
    static const QRegularExpression deepSeekV4Flash0731(
        QStringLiteral(R"((^|[-_.])deepseek[-_.]?v4[-_.]flash[-_.]0731($|[-_.]))"),
        QRegularExpression::CaseInsensitiveOption);
    static const QRegularExpression bigBangV1(
        QStringLiteral("(^|[-_.])bigbang[-_.]?v1($|[-_.])"),
        QRegularExpression::CaseInsensitiveOption);
    static const QRegularExpression qwen38(
        QStringLiteral(R"((^|[-_.])qwen3[._-]?8[-_.]27b($|[-_.]))"),
        QRegularExpression::CaseInsensitiveOption);
    static const QRegularExpression katCoderApexMtp(
        QStringLiteral(R"((^|[-_.])kat[-_.]?coder[-_.]?v2[._-]?5[-_.]?dev[-_.]?mtp[-_.]?apex($|[-_.]))"),
        QRegularExpression::CaseInsensitiveOption);
    // Los artefactos MTP de Qwen3.5 publicados por Unsloth conservan el
    // nombre de quant estándar y distinguen la variante por repositorio/
    // carpeta. En los perfiles bundled el specType ya expresa esa intención.
    static const QRegularExpression qwen35Mtp(
        QStringLiteral(R"(^qwen3[._-]?5[-_.](?:2b|4b|9b)(?:[-_.].*)?$)"),
        QRegularExpression::CaseInsensitiveOption);
    return marker.match(base).hasMatch()
        || thinkingCapQwen36.match(base).hasMatch()
        || deepSeekV4Flash0731.match(base).hasMatch()
        || bigBangV1.match(base).hasMatch()
        || qwen38.match(base).hasMatch()
        || katCoderApexMtp.match(base).hasMatch()
        || qwen35Mtp.match(base).hasMatch();
}

// ¿El stderr de llama-server dice que no pudo cargar/crear el speculator?
// Gemma 4 + MTP externo con b9763 falla a veces con "invalid vector subscript"
// al cargar el borrador (mismos args que andan en otro arranque: el fitting de
// memoria le pasa params del modelo principal; arreglado aguas arriba). El
// watchdog reintentaba 3 veces lo mismo y el perfil quedaba caído.
inline bool draftLoadFailed(const QString &serverStderr)
{
    return serverStderr.contains(QLatin1String("failed to load draft model"))
        || serverStderr.contains(QLatin1String("failed to create MTP context"))
        || serverStderr.contains(QLatin1String("MTP requested but model doesn't contain MTP layers"));
}

// Los args sin speculative decoding (borrador externo, MTP embebido, DSpark):
// el modelo principal arranca igual, sólo que genera sin acelerar.
inline QStringList withoutSpeculativeDraft(const QStringList &args)
{
    static const QStringList draftFlags{
        QStringLiteral("-md"), QStringLiteral("-ngld"), QStringLiteral("-devd"),
        QStringLiteral("-cd"), QStringLiteral("-ctkd"), QStringLiteral("-ctvd"),
        QStringLiteral("--model-draft"), QStringLiteral("--gpu-layers-draft"),
        QStringLiteral("--n-gpu-layers-draft"), QStringLiteral("--device-draft"),
        QStringLiteral("--ctx-size-draft")};
    static const QRegularExpression flagLike(QStringLiteral(R"(^-{1,2}[A-Za-z])"));
    QStringList out;
    for (int i = 0; i < args.size(); ++i) {
        const QString &a = args.at(i);
        const bool draftFlag = a.startsWith(QLatin1String("--spec-"))
            || a.startsWith(QLatin1String("--draft")) || draftFlags.contains(a);
        if (!draftFlag) { out << a; continue; }
        // Flag con valor (o switch como --spec-draft-adaptive): saltear el valor.
        if (i + 1 < args.size() && !flagLike.match(args.at(i + 1)).hasMatch()) ++i;
    }
    return out;
}

} // namespace MtpDetection

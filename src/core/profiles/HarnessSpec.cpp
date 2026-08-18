#include "HarnessSpec.h"
#include "core/agent/LlamaAgentBackend.h"

#include <QJsonArray>
#include <QSet>

namespace {

QStringList toStringList(const QJsonValue &v)
{
    QStringList out;
    for (const QJsonValue &item : v.toArray()) {
        const QString s = item.toString().trimmed();
        if (!s.isEmpty()) out << s;
    }
    return out;
}

QJsonArray fromStringList(const QStringList &list)
{
    QJsonArray arr;
    for (const QString &s : list) arr.append(s);
    return arr;
}

int boundedInt(const QJsonObject &o, const char *key, int def, int lo, int hi)
{
    const QJsonValue v = o.value(QLatin1String(key));
    if (!v.isDouble()) return def;
    return qBound(lo, v.toInt(def), hi);
}

double boundedDouble(const QJsonObject &o, const char *key, double def, double lo, double hi)
{
    const QJsonValue v = o.value(QLatin1String(key));
    if (!v.isDouble()) return def;
    return qBound(lo, v.toDouble(def), hi);
}

void addDiff(QVariantList &out, const char *module, const char *field,
             const QVariant &baseValue, const QVariant &value)
{
    if (baseValue == value) return;
    out.append(QVariantMap{{QStringLiteral("module"), QString::fromLatin1(module)},
                           {QStringLiteral("field"), QString::fromLatin1(field)},
                           {QStringLiteral("base"), baseValue},
                           {QStringLiteral("value"), value}});
}

}  // namespace

// ---------------------------------------------------------------------------
// Modulos
// ---------------------------------------------------------------------------

QJsonObject HarnessToolsModule::toJson() const
{
    QJsonObject o;
    o[QStringLiteral("packs")] = fromStringList(packs);
    o[QStringLiteral("include")] = fromStringList(include);
    o[QStringLiteral("exclude")] = fromStringList(exclude);
    o[QStringLiteral("mcpTools")] = mcpToolsEnabled;
    return o;
}

HarnessToolsModule HarnessToolsModule::fromJson(const QJsonObject &o)
{
    HarnessToolsModule m;
    m.set = true;
    m.packs = toStringList(o.value(QStringLiteral("packs")));
    m.include = toStringList(o.value(QStringLiteral("include")));
    m.exclude = toStringList(o.value(QStringLiteral("exclude")));
    m.mcpToolsEnabled = o.value(QStringLiteral("mcpTools")).toBool(true);
    return m;
}

QJsonObject HarnessPromptModule::toJson() const
{
    QJsonObject o;
    o[QStringLiteral("builtin")] = fromStringList(builtin);
    o[QStringLiteral("custom")] = fromStringList(custom);
    o[QStringLiteral("systemExtra")] = systemExtra;
    o[QStringLiteral("maxChars")] = maxChars;
    return o;
}

HarnessPromptModule HarnessPromptModule::fromJson(const QJsonObject &o)
{
    HarnessPromptModule m;
    m.set = true;
    m.builtin = toStringList(o.value(QStringLiteral("builtin")));
    m.custom = toStringList(o.value(QStringLiteral("custom")));
    m.systemExtra = o.value(QStringLiteral("systemExtra")).toString();
    m.maxChars = boundedInt(o, "maxChars", 24000, 1000, 400000);
    return m;
}

QJsonObject HarnessLoopModule::toJson() const
{
    QJsonObject o;
    o[QStringLiteral("credits")] = credits;
    o[QStringLiteral("maxCredits")] = maxCredits;
    o[QStringLiteral("replanAfter")] = replanAfter;
    o[QStringLiteral("stopAfter")] = stopAfter;
    o[QStringLiteral("maxDistinctWrites")] = maxDistinctWrites;
    o[QStringLiteral("sameCallLimit")] = sameCallLimit;
    o[QStringLiteral("failureSpiral")] = failureSpiral;
    o[QStringLiteral("transportRetries")] = transportRetries;
    o[QStringLiteral("quickToolTimeoutSec")] = quickToolTimeoutSec;
    o[QStringLiteral("webToolTimeoutSec")] = webToolTimeoutSec;
    o[QStringLiteral("streamIdleTimeoutSec")] = streamIdleTimeoutSec;
    return o;
}

HarnessLoopModule HarnessLoopModule::fromJson(const QJsonObject &o)
{
    HarnessLoopModule m;
    m.set = true;
    m.credits = boundedInt(o, "credits", 8, 1, 200);
    m.maxCredits = boundedInt(o, "maxCredits", 16, 1, 400);
    m.replanAfter = boundedInt(o, "replanAfter", 3, 1, 100);
    m.stopAfter = boundedInt(o, "stopAfter", 5, 1, 200);
    m.maxDistinctWrites = boundedInt(o, "maxDistinctWrites", 24, 1, 500);
    m.sameCallLimit = boundedInt(o, "sameCallLimit", 3, 1, 50);
    m.failureSpiral = boundedInt(o, "failureSpiral", 3, 1, 50);
    m.transportRetries = boundedInt(o, "transportRetries", 60, 0, 600);
    m.quickToolTimeoutSec = boundedInt(o, "quickToolTimeoutSec", 15, 5, 120);
    m.webToolTimeoutSec = boundedInt(o, "webToolTimeoutSec", 180, 10, 1800);
    m.streamIdleTimeoutSec = boundedInt(o, "streamIdleTimeoutSec", 0, 0, 24 * 60 * 60);
    if (m.maxCredits < m.credits) m.maxCredits = m.credits;
    return m;
}

QJsonObject HarnessContextModule::toJson() const
{
    QJsonObject o;
    o[QStringLiteral("compaction")] = compaction;
    o[QStringLiteral("compactionTrigger")] = compactionTrigger;
    o[QStringLiteral("tailRatio")] = tailRatio;
    o[QStringLiteral("prune")] = prune;
    o[QStringLiteral("keepLastImages")] = keepLastImages;
    o[QStringLiteral("readDedup")] = readDedup;
    o[QStringLiteral("preflight")] = preflight;
    o[QStringLiteral("warmup")] = warmup;
    return o;
}

HarnessContextModule HarnessContextModule::fromJson(const QJsonObject &o)
{
    HarnessContextModule m;
    m.set = true;
    m.compaction = o.value(QStringLiteral("compaction")).toBool(true);
    m.compactionTrigger = boundedDouble(o, "compactionTrigger", 0.90, 0.30, 0.99);
    m.tailRatio = boundedDouble(o, "tailRatio", 0.60, 0.10, 0.95);
    m.prune = o.value(QStringLiteral("prune")).toBool(true);
    m.keepLastImages = boundedInt(o, "keepLastImages", 1, 0, 20);
    m.readDedup = o.value(QStringLiteral("readDedup")).toBool(true);
    m.preflight = o.value(QStringLiteral("preflight")).toBool(false);
    m.warmup = o.value(QStringLiteral("warmup")).toBool(true);
    return m;
}

QJsonObject HarnessPermissionsModule::toJson() const
{
    QJsonObject o;
    o[QStringLiteral("approvalMode")] = approvalMode;
    o[QStringLiteral("rules")] = fromStringList(rules);
    // Sólo serializamos fsScope si fue declarado: escribirlo siempre convertiría
    // un perfil legacy en uno que estrecha el alcance de las Tasks.
    if (fsScopeDeclared) o[QStringLiteral("fsScope")] = fsScope;
    o[QStringLiteral("folders")] = fromStringList(folders);
    o[QStringLiteral("hitlDestructive")] = hitlDestructive;
    o[QStringLiteral("mailAutoSend")] = mailAutoSend;
    return o;
}

HarnessPermissionsModule HarnessPermissionsModule::fromJson(const QJsonObject &o)
{
    HarnessPermissionsModule m;
    m.set = true;
    m.approvalMode = o.value(QStringLiteral("approvalMode")).toString(QStringLiteral("ask"));
    m.rules = toStringList(o.value(QStringLiteral("rules")));
    m.fsScope = o.value(QStringLiteral("fsScope")).toString(QStringLiteral("project"));
    m.fsScopeDeclared = o.contains(QStringLiteral("fsScope"));
    m.folders = toStringList(o.value(QStringLiteral("folders")));
    m.hitlDestructive = o.value(QStringLiteral("hitlDestructive")).toBool(true);
    m.mailAutoSend = o.value(QStringLiteral("mailAutoSend")).toBool(false);
    // El guardrail Zero-Autonomy solo se puede bajar en modo super declarado. Un
    // perfil no puede desactivarlo "de costado" (invariante testeada).
    if (!m.hitlDestructive && m.approvalMode != QLatin1String("super"))
        m.hitlDestructive = true;
    return m;
}

QJsonObject HarnessEscalationModule::toJson() const
{
    QJsonObject o;
    o[QStringLiteral("maxParallelSubagents")] = maxParallelSubagents;
    o[QStringLiteral("isolateSubagents")] = isolateSubagents;
    o[QStringLiteral("masterEscalation")] = masterEscalation;
    o[QStringLiteral("masterAutoAfterFails")] = masterAutoAfterFails;
    if (!masterFallbacks.isEmpty()) o[QStringLiteral("masterFallbacks")] = masterFallbacks;
    o[QStringLiteral("routerFilesAffected")] = routerFilesAffected;
    o[QStringLiteral("routerContextTokens")] = routerContextTokens;
    o[QStringLiteral("routerRepeatedFailures")] = routerRepeatedFailures;
    o[QStringLiteral("routerAgentCycles")] = routerAgentCycles;
    o[QStringLiteral("routerConfidenceFloor")] = routerConfidenceFloor;
    return o;
}

HarnessEscalationModule HarnessEscalationModule::fromJson(const QJsonObject &o)
{
    HarnessEscalationModule m;
    m.set = true;
    m.maxParallelSubagents = boundedInt(o, "maxParallelSubagents", 5, 1, 5);
    m.isolateSubagents = o.value(QStringLiteral("isolateSubagents")).toBool(true);
    m.masterEscalation = o.value(QStringLiteral("masterEscalation")).toString();
    m.masterAutoAfterFails = boundedInt(o, "masterAutoAfterFails", 0, 0, 100);
    m.masterFallbacks = o.value(QStringLiteral("masterFallbacks")).toArray();
    m.routerFilesAffected = boundedInt(o, "routerFilesAffected", 8, 1, 500);
    m.routerContextTokens = boundedInt(o, "routerContextTokens", 24000, 1000, 1000000);
    m.routerRepeatedFailures = boundedInt(o, "routerRepeatedFailures", 3, 1, 50);
    m.routerAgentCycles = boundedInt(o, "routerAgentCycles", 5, 1, 100);
    m.routerConfidenceFloor = boundedDouble(o, "routerConfidenceFloor", 0.3, 0.0, 1.0);
    return m;
}

QJsonObject HarnessProtocolModule::toJson() const
{
    QJsonObject o;
    o[QStringLiteral("toolProtocol")] = toolProtocol;
    o[QStringLiteral("thinking")] = thinking;
    o[QStringLiteral("thinkingLeakGuard")] = thinkingLeakGuard;
    o[QStringLiteral("temperature")] = temperature;
    o[QStringLiteral("reasoningEffort")] = reasoningEffort;
    o[QStringLiteral("reasoningBudget")] = reasoningBudget;
    return o;
}

HarnessProtocolModule HarnessProtocolModule::fromJson(const QJsonObject &o)
{
    HarnessProtocolModule m;
    m.set = true;
    m.toolProtocol = o.value(QStringLiteral("toolProtocol")).toString(QStringLiteral("auto"));
    if (m.toolProtocol != QLatin1String("native") && m.toolProtocol != QLatin1String("text"))
        m.toolProtocol = QStringLiteral("auto");
    m.thinking = o.value(QStringLiteral("thinking")).toBool(false);
    m.thinkingLeakGuard = o.value(QStringLiteral("thinkingLeakGuard")).toBool(false);
    m.temperature = o.value(QStringLiteral("temperature")).toDouble(-1.0);
    m.reasoningEffort = o.value(QStringLiteral("reasoningEffort")).toString();
    m.reasoningBudget = o.value(QStringLiteral("reasoningBudget")).toInt(-1);
    return m;
}

// ---------------------------------------------------------------------------
// HarnessSpec
// ---------------------------------------------------------------------------

bool HarnessSpec::isEmpty() const
{
    return extends.isEmpty() && !tools.set && !prompt.set && !loop.set && !context.set
           && !permissions.set && !escalation.set && !protocol.set && phases.isEmpty();
}

QJsonObject HarnessSpec::toJson() const
{
    QJsonObject o;
    if (!extends.isEmpty()) o[QStringLiteral("extends")] = extends;
    if (tools.set) o[QStringLiteral("tools")] = tools.toJson();
    if (prompt.set) o[QStringLiteral("prompt")] = prompt.toJson();
    if (loop.set) o[QStringLiteral("loop")] = loop.toJson();
    if (context.set) o[QStringLiteral("context")] = context.toJson();
    if (permissions.set) o[QStringLiteral("permissions")] = permissions.toJson();
    if (escalation.set) o[QStringLiteral("escalation")] = escalation.toJson();
    if (protocol.set) o[QStringLiteral("protocol")] = protocol.toJson();
    if (!phases.isEmpty()) {
        QJsonObject ph;
        for (auto it = phases.cbegin(); it != phases.cend(); ++it)
            ph[it.key()] = it.value();
        o[QStringLiteral("phases")] = ph;
    }
    return o;
}

HarnessSpec HarnessSpec::fromJson(const QJsonObject &o)
{
    HarnessSpec s;
    s.extends = o.value(QStringLiteral("extends")).toString();
    if (o.value(QStringLiteral("tools")).isObject())
        s.tools = HarnessToolsModule::fromJson(o.value(QStringLiteral("tools")).toObject());
    if (o.value(QStringLiteral("prompt")).isObject())
        s.prompt = HarnessPromptModule::fromJson(o.value(QStringLiteral("prompt")).toObject());
    if (o.value(QStringLiteral("loop")).isObject())
        s.loop = HarnessLoopModule::fromJson(o.value(QStringLiteral("loop")).toObject());
    if (o.value(QStringLiteral("context")).isObject())
        s.context = HarnessContextModule::fromJson(o.value(QStringLiteral("context")).toObject());
    if (o.value(QStringLiteral("permissions")).isObject())
        s.permissions = HarnessPermissionsModule::fromJson(
            o.value(QStringLiteral("permissions")).toObject());
    if (o.value(QStringLiteral("escalation")).isObject())
        s.escalation = HarnessEscalationModule::fromJson(
            o.value(QStringLiteral("escalation")).toObject());
    if (o.value(QStringLiteral("protocol")).isObject())
        s.protocol = HarnessProtocolModule::fromJson(
            o.value(QStringLiteral("protocol")).toObject());
    const QJsonObject ph = o.value(QStringLiteral("phases")).toObject();
    for (auto it = ph.constBegin(); it != ph.constEnd(); ++it)
        if (it.value().isObject()) s.phases.insert(it.key(), it.value().toObject());
    return s;
}

HarnessSpec HarnessSpec::resolve(const HarnessSpec &base, const HarnessSpec &override)
{
    HarnessSpec out = base;
    // extends del hijo se conserva como metadato de linaje (quien resuelve la
    // cadena es ProfileManager); el resuelto ya no hereda de nadie mas.
    out.extends = base.extends;
    if (override.tools.set) out.tools = override.tools;
    if (override.prompt.set) out.prompt = override.prompt;
    if (override.loop.set) out.loop = override.loop;
    if (override.context.set) out.context = override.context;
    if (override.permissions.set) out.permissions = override.permissions;
    if (override.escalation.set) out.escalation = override.escalation;
    if (override.protocol.set) out.protocol = override.protocol;
    for (auto it = override.phases.cbegin(); it != override.phases.cend(); ++it)
        out.phases.insert(it.key(), it.value());
    return out;
}

HarnessSpec HarnessSpec::forPhase(const HarnessSpec &spec, const QString &phase)
{
    const auto it = spec.phases.constFind(phase);
    if (it == spec.phases.constEnd()) return spec;
    HarnessSpec patch = HarnessSpec::fromJson(it.value());
    patch.phases.clear();                 // una fase no define fases
    HarnessSpec out = resolve(spec, patch);
    out.phases = spec.phases;             // conservar el mapa original
    return out;
}

QVariantList HarnessSpec::diff(const HarnessSpec &base) const
{
    QVariantList out;
    addDiff(out, "tools", "packs", base.tools.packs, tools.packs);
    addDiff(out, "tools", "include", base.tools.include, tools.include);
    addDiff(out, "tools", "exclude", base.tools.exclude, tools.exclude);
    addDiff(out, "tools", "mcpTools", base.tools.mcpToolsEnabled, tools.mcpToolsEnabled);

    addDiff(out, "prompt", "builtin", base.prompt.builtin, prompt.builtin);
    addDiff(out, "prompt", "custom", base.prompt.custom, prompt.custom);
    addDiff(out, "prompt", "systemExtra", base.prompt.systemExtra, prompt.systemExtra);
    addDiff(out, "prompt", "maxChars", base.prompt.maxChars, prompt.maxChars);

    addDiff(out, "loop", "credits", base.loop.credits, loop.credits);
    addDiff(out, "loop", "maxCredits", base.loop.maxCredits, loop.maxCredits);
    addDiff(out, "loop", "replanAfter", base.loop.replanAfter, loop.replanAfter);
    addDiff(out, "loop", "stopAfter", base.loop.stopAfter, loop.stopAfter);
    addDiff(out, "loop", "maxDistinctWrites", base.loop.maxDistinctWrites, loop.maxDistinctWrites);
    addDiff(out, "loop", "sameCallLimit", base.loop.sameCallLimit, loop.sameCallLimit);
    addDiff(out, "loop", "failureSpiral", base.loop.failureSpiral, loop.failureSpiral);
    addDiff(out, "loop", "transportRetries", base.loop.transportRetries, loop.transportRetries);
    addDiff(out, "loop", "quickToolTimeoutSec", base.loop.quickToolTimeoutSec,
            loop.quickToolTimeoutSec);
    addDiff(out, "loop", "webToolTimeoutSec", base.loop.webToolTimeoutSec, loop.webToolTimeoutSec);
    addDiff(out, "loop", "streamIdleTimeoutSec", base.loop.streamIdleTimeoutSec,
            loop.streamIdleTimeoutSec);

    addDiff(out, "context", "compaction", base.context.compaction, context.compaction);
    addDiff(out, "context", "compactionTrigger", base.context.compactionTrigger,
            context.compactionTrigger);
    addDiff(out, "context", "tailRatio", base.context.tailRatio, context.tailRatio);
    addDiff(out, "context", "prune", base.context.prune, context.prune);
    addDiff(out, "context", "keepLastImages", base.context.keepLastImages, context.keepLastImages);
    addDiff(out, "context", "readDedup", base.context.readDedup, context.readDedup);
    addDiff(out, "context", "preflight", base.context.preflight, context.preflight);
    addDiff(out, "context", "warmup", base.context.warmup, context.warmup);

    addDiff(out, "permissions", "approvalMode", base.permissions.approvalMode,
            permissions.approvalMode);
    addDiff(out, "permissions", "rules", base.permissions.rules, permissions.rules);
    addDiff(out, "permissions", "fsScope", base.permissions.fsScope, permissions.fsScope);
    addDiff(out, "permissions", "folders", base.permissions.folders, permissions.folders);
    addDiff(out, "permissions", "hitlDestructive", base.permissions.hitlDestructive,
            permissions.hitlDestructive);
    addDiff(out, "permissions", "mailAutoSend", base.permissions.mailAutoSend,
            permissions.mailAutoSend);

    addDiff(out, "escalation", "maxParallelSubagents", base.escalation.maxParallelSubagents,
            escalation.maxParallelSubagents);
    addDiff(out, "escalation", "isolateSubagents", base.escalation.isolateSubagents,
            escalation.isolateSubagents);
    addDiff(out, "escalation", "masterEscalation", base.escalation.masterEscalation,
            escalation.masterEscalation);
    addDiff(out, "escalation", "masterAutoAfterFails", base.escalation.masterAutoAfterFails,
            escalation.masterAutoAfterFails);
    addDiff(out, "escalation", "masterFallbacks", base.escalation.masterFallbacks.size(),
            escalation.masterFallbacks.size());
    addDiff(out, "escalation", "routerFilesAffected", base.escalation.routerFilesAffected,
            escalation.routerFilesAffected);
    addDiff(out, "escalation", "routerContextTokens", base.escalation.routerContextTokens,
            escalation.routerContextTokens);
    addDiff(out, "escalation", "routerRepeatedFailures", base.escalation.routerRepeatedFailures,
            escalation.routerRepeatedFailures);
    addDiff(out, "escalation", "routerAgentCycles", base.escalation.routerAgentCycles,
            escalation.routerAgentCycles);
    addDiff(out, "escalation", "routerConfidenceFloor", base.escalation.routerConfidenceFloor,
            escalation.routerConfidenceFloor);

    addDiff(out, "protocol", "toolProtocol", base.protocol.toolProtocol, protocol.toolProtocol);
    addDiff(out, "protocol", "thinking", base.protocol.thinking, protocol.thinking);
    addDiff(out, "protocol", "thinkingLeakGuard", base.protocol.thinkingLeakGuard,
            protocol.thinkingLeakGuard);
    addDiff(out, "protocol", "temperature", base.protocol.temperature, protocol.temperature);
    addDiff(out, "protocol", "reasoningEffort", base.protocol.reasoningEffort,
            protocol.reasoningEffort);
    addDiff(out, "protocol", "reasoningBudget", base.protocol.reasoningBudget,
            protocol.reasoningBudget);
    return out;
}

// ---------------------------------------------------------------------------
// Packs
// ---------------------------------------------------------------------------

namespace {

// Slug ASCII de un grupo del toolCatalog ("Multi-Agente" -> "multi-agente").
QString groupKey(const QString &group)
{
    // Normalizacion NFD + descarte de marcas de acento: evita literales acentuados
    // en el fuente (los .cpp del repo se compilan con /utf-8, pero un literal
    // acentuado dentro de una comparacion es justo el tipo de cosa que falla mudo
    // si alguien recompila sin la flag). "Busqueda" -> "busqueda".
    const QString decomposed = group.normalized(QString::NormalizationForm_D);
    QString out;
    for (const QChar &c : decomposed) {
        if (c.category() == QChar::Mark_NonSpacing) continue;
        if (c.isLetterOrNumber()) out += c.toLower();
        else if (c == QLatin1Char('-') || c.isSpace()) out += QLatin1Char('-');
    }
    return out;
}

QStringList toolsOfGroup(const QString &group)
{
    QStringList out;
    for (const QVariant &v : LlamaAgentBackend::toolCatalog()) {
        const QVariantMap m = v.toMap();
        if (groupKey(m.value(QStringLiteral("group")).toString()) == group)
            out << m.value(QStringLiteral("name")).toString();
    }
    return out;
}

QStringList allToolNames()
{
    QStringList out;
    for (const QVariant &v : LlamaAgentBackend::toolCatalog())
        out << v.toMap().value(QStringLiteral("name")).toString();
    return out;
}

QVariantMap mkPack(const QString &key, const QString &name, const QString &desc,
                   const QStringList &tools)
{
    return QVariantMap{{QStringLiteral("key"), key},
                       {QStringLiteral("name"), name},
                       {QStringLiteral("description"), desc},
                       {QStringLiteral("tools"), tools}};
}

}  // namespace

QVariantList HarnessTools::packCatalog()
{
    QVariantList out;
    // Packs compuestos: la escalera historica de niveles, ahora nombrable.
    out << mkPack(QStringLiteral("chat"), QStringLiteral("Chat"),
                  QStringLiteral("Set minimo para chatear y editar codigo."),
                  {QStringLiteral("read_file"), QStringLiteral("list_dir"),
                   QStringLiteral("grep"), QStringLiteral("write_file"),
                   QStringLiteral("edit_file")});
    out << mkPack(QStringLiteral("core"), QStringLiteral("Core"),
                  QStringLiteral("Archivos + busqueda + shell: el piso de un agente de codigo."),
                  {QStringLiteral("read_file"), QStringLiteral("list_dir"),
                   QStringLiteral("glob"), QStringLiteral("grep"),
                   QStringLiteral("write_file"), QStringLiteral("edit_file"),
                   QStringLiteral("run_shell")});
    out << mkPack(QStringLiteral("rag"), QStringLiteral("RAG / conocimiento"),
                  QStringLiteral("Busqueda semantica, hibrida, memoria y grafo."),
                  {QStringLiteral("search_docs"), QStringLiteral("semantic_search"),
                   QStringLiteral("hybrid_search"), QStringLiteral("repo_slice"),
                   QStringLiteral("verify_claims"), QStringLiteral("memory"),
                   QStringLiteral("graph"), QStringLiteral("project_brain")});
    out << mkPack(QStringLiteral("web"), QStringLiteral("Web"),
                  QStringLiteral("Busqueda y descarga de paginas."),
                  toolsOfGroup(QStringLiteral("web")));
    out << mkPack(QStringLiteral("rpa"), QStringLiteral("Escritorio (RPA)"),
                  QStringLiteral("Automatizacion de apps nativas por UIA y vision."),
                  toolsOfGroup(QStringLiteral("escritorio")));
    out << mkPack(QStringLiteral("multiagente"), QStringLiteral("Multi-agente"),
                  QStringLiteral("Sub-agentes en worktree y escalado al maestro."),
                  toolsOfGroup(QStringLiteral("multi-agente")));
    out << mkPack(QStringLiteral("browser"), QStringLiteral("Browser"),
                  QStringLiteral("Skills grabados de browser y evidencia de red."),
                  toolsOfGroup(QStringLiteral("browser")));
    out << mkPack(QStringLiteral("mail"), QStringLiteral("Correo"),
                  QStringLiteral("Leer y enviar correo (SMTP/IMAP)."),
                  toolsOfGroup(QStringLiteral("correo")));
    out << mkPack(QStringLiteral("skills"), QStringLiteral("Habilidades"),
                  QStringLiteral("Catalogo de skills portables bajo demanda."),
                  toolsOfGroup(QStringLiteral("habilidades")));
    out << mkPack(QStringLiteral("all"), QStringLiteral("Todo"),
                  QStringLiteral("Todas las tools del catalogo."), allToolNames());

    // Un pack por grupo del catalogo (los que no quedaron ya cubiertos arriba).
    QStringList seen{QStringLiteral("web"), QStringLiteral("escritorio"),
                     QStringLiteral("multi-agente"), QStringLiteral("browser"),
                     QStringLiteral("correo"), QStringLiteral("habilidades")};
    QStringList groupsInOrder;
    QMap<QString, QString> labelOf;
    for (const QVariant &v : LlamaAgentBackend::toolCatalog()) {
        const QString label = v.toMap().value(QStringLiteral("group")).toString();
        const QString key = groupKey(label);
        if (seen.contains(key) || groupsInOrder.contains(key)) continue;
        groupsInOrder << key;
        labelOf.insert(key, label);
    }
    for (const QString &key : groupsInOrder)
        out << mkPack(key, labelOf.value(key),
                      QStringLiteral("Grupo del catalogo: %1.").arg(labelOf.value(key)),
                      toolsOfGroup(key));
    return out;
}

QStringList HarnessTools::resolve(const HarnessToolsModule &module)
{
    QSet<QString> on;
    const bool includeAll = module.include.contains(QStringLiteral("*"))
                            || module.packs.contains(QStringLiteral("all"));
    if (includeAll) {
        const QStringList all = allToolNames();
        on = QSet<QString>(all.cbegin(), all.cend());
    } else {
        QMap<QString, QStringList> packs;
        for (const QVariant &v : packCatalog()) {
            const QVariantMap m = v.toMap();
            packs.insert(m.value(QStringLiteral("key")).toString(),
                         m.value(QStringLiteral("tools")).toStringList());
        }
        for (const QString &p : module.packs)
            for (const QString &t : packs.value(p.trimmed().toLower()))
                on.insert(t);
        for (const QString &t : module.include) on.insert(t);
    }
    for (const QString &t : module.exclude) on.remove(t);

    // Orden estable = orden del catalogo (la UI y los tests dependen de esto).
    QStringList out;
    for (const QString &name : allToolNames())
        if (on.contains(name)) out << name;
    return out;
}

QStringList HarnessTools::disabledFrom(const QStringList &enabled)
{
    const QSet<QString> on(enabled.cbegin(), enabled.cend());
    QStringList out;
    for (const QString &name : allToolNames())
        if (!on.contains(name)) out << name;
    return out;
}

int HarnessTools::approxTokens(const QStringList &enabled)
{
    const QSet<QString> on(enabled.cbegin(), enabled.cend());
    int total = 0;
    for (const QVariant &v : LlamaAgentBackend::toolCatalog()) {
        const QVariantMap m = v.toMap();
        if (on.contains(m.value(QStringLiteral("name")).toString()))
            total += m.value(QStringLiteral("approxTokens")).toInt();
    }
    return total;
}

QStringList HarnessTools::dependencyWarnings(const QStringList &enabled,
                                             const Environment &env)
{
    const QSet<QString> on(enabled.cbegin(), enabled.cend());
    QStringList out;
    auto anyOn = [&on](const QStringList &names) {
        for (const QString &n : names)
            if (on.contains(n)) return true;
        return false;
    };
    if (!env.hasGit && on.contains(QStringLiteral("task")))
        out << QStringLiteral("task: sin git no se pueden crear worktrees para sub-agentes.");
    if (!env.hasGit && on.contains(QStringLiteral("code_hotspots")))
        out << QStringLiteral("code_hotspots: necesita historial git para calcular churn.");
    if (!env.hasEmbeddings
        && anyOn({QStringLiteral("semantic_search"), QStringLiteral("hybrid_search")}))
        out << QStringLiteral("semantic_search/hybrid_search: el server activo no expone "
                              "/v1/embeddings.");
    if (!env.hasDesktop && anyOn(toolsOfGroup(QStringLiteral("escritorio"))))
        out << QStringLiteral("desktop_*: no hay sesion de escritorio interactiva.");
    if (!env.hasMailAccount && anyOn(toolsOfGroup(QStringLiteral("correo"))))
        out << QStringLiteral("email_*: no hay cuentas de correo configuradas.");
    if (!env.hasBrowser && anyOn(toolsOfGroup(QStringLiteral("browser"))))
        out << QStringLiteral("browser_*: la automatizacion de browser esta apagada en el perfil.");
    return out;
}

// ---------------------------------------------------------------------------
// Politica
// ---------------------------------------------------------------------------

namespace {
int scopeRank(const QString &scope)
{
    if (scope == QLatin1String("full")) return 2;
    if (scope == QLatin1String("folder")) return 1;
    return 0;   // project (el mas restrictivo)
}
}  // namespace

QString HarnessPolicy::narrowerScope(const QString &a, const QString &b)
{
    return scopeRank(a) <= scopeRank(b) ? a : b;
}

QStringList HarnessPolicy::intersectFolders(const QString &scopeA, const QStringList &a,
                                            const QString &scopeB, const QStringList &b)
{
    // "full" no aporta restriccion: la lista del otro manda.
    if (scopeA == QLatin1String("full")) return b;
    if (scopeB == QLatin1String("full")) return a;
    if (scopeA != QLatin1String("folder")) return {};
    if (scopeB != QLatin1String("folder")) return {};
    const QSet<QString> setB(b.cbegin(), b.cend());
    QStringList out;
    for (const QString &f : a)
        if (setB.contains(f)) out << f;
    return out;
}

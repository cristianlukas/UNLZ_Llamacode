#include "CodeGraphIndexer.h"

#include "GraphStore.h"

#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QHash>
#include <QRegularExpression>
#include <QSet>

namespace {

// Carpetas que NO recorremos (ruido + lentitud). Mismo criterio que el walker de
// AgentToolRunner (no parsea .gitignore completo).
bool isIgnoredDir(const QString &name)
{
    static const QSet<QString> ig{
        QStringLiteral("node_modules"), QStringLiteral(".git"), QStringLiteral("build"),
        QStringLiteral("build2"), QStringLiteral("build_tests"), QStringLiteral("dist"),
        QStringLiteral(".venv"), QStringLiteral("venv"), QStringLiteral("__pycache__"),
        QStringLiteral(".next"), QStringLiteral(".turbo"), QStringLiteral("coverage"),
        QStringLiteral("target"), QStringLiteral(".cache"), QStringLiteral(".idea"),
        QStringLiteral(".vs"), QStringLiteral(".gradle"), QStringLiteral("bin"),
        QStringLiteral("obj"), QStringLiteral(".llamacode")};
    return ig.contains(name);
}

// Familia de lenguaje por extensión. "" = no soportado (lo salteamos).
QString langOf(const QString &ext)
{
    const QString e = ext.toLower();
    if (e == QLatin1String("h") || e == QLatin1String("hpp") || e == QLatin1String("hh")
        || e == QLatin1String("hxx") || e == QLatin1String("c") || e == QLatin1String("cc")
        || e == QLatin1String("cpp") || e == QLatin1String("cxx"))
        return QStringLiteral("cpp");
    if (e == QLatin1String("qml")) return QStringLiteral("qml");
    if (e == QLatin1String("js") || e == QLatin1String("jsx") || e == QLatin1String("mjs"))
        return QStringLiteral("js");
    if (e == QLatin1String("ts") || e == QLatin1String("tsx")) return QStringLiteral("ts");
    if (e == QLatin1String("py")) return QStringLiteral("py");
    return QString();
}

// Palabras que NO son nombres de símbolo (keywords/control que matchean los
// patrones tipo 'foo(' en C++). Filtra el ruido más común.
bool isNoiseSymbol(const QString &s)
{
    static const QSet<QString> kw{
        QStringLiteral("if"), QStringLiteral("for"), QStringLiteral("while"),
        QStringLiteral("switch"), QStringLiteral("catch"), QStringLiteral("return"),
        QStringLiteral("sizeof"), QStringLiteral("do"), QStringLiteral("else"),
        QStringLiteral("case"), QStringLiteral("new"), QStringLiteral("delete"),
        QStringLiteral("and"), QStringLiteral("or"), QStringLiteral("not"),
        QStringLiteral("typedef"), QStringLiteral("template")};
    return s.size() < 2 || kw.contains(s.toLower());
}

// Extrae los símbolos (clases/funciones) de 'text' según la familia 'lang'.
// Regex conservadora por lenguaje; deduplica por nombre. Cap a 'maxSyms'.
QStringList extractSymbols(const QString &lang, const QString &text, int maxSyms)
{
    QStringList out;
    QSet<QString> seen;
    auto push = [&](const QString &raw) {
        const QString s = raw.trimmed();
        if (isNoiseSymbol(s) || seen.contains(s)) return;
        if (out.size() >= maxSyms) return;
        seen.insert(s);
        out << s;
    };
    auto runRe = [&](const QRegularExpression &re) {
        auto it = re.globalMatch(text);
        while (it.hasNext() && out.size() < maxSyms) push(it.next().captured(1));
    };

    if (lang == QLatin1String("cpp")) {
        static const QRegularExpression reType(
            QStringLiteral("\\b(?:class|struct)\\s+(\\w+)"));
        // Definición de función/método: tipo de retorno + nombre( ... ) {  (con cuerpo).
        static const QRegularExpression reFunc(
            QStringLiteral("(?m)^[A-Za-z_][\\w:\\*&<>,\\s]*?\\b(\\w+)\\s*\\([^;{}]*\\)\\s*"
                           "(?:const\\s*)?(?:noexcept\\s*)?(?:override\\s*)?\\{"));
        runRe(reType);
        runRe(reFunc);
    } else if (lang == QLatin1String("py")) {
        static const QRegularExpression rePy(
            QStringLiteral("(?m)^\\s*(?:def|class)\\s+(\\w+)"));
        runRe(rePy);
    } else if (lang == QLatin1String("js") || lang == QLatin1String("ts")) {
        static const QRegularExpression reFn(QStringLiteral("\\bfunction\\s+(\\w+)"));
        static const QRegularExpression reClass(QStringLiteral("\\bclass\\s+(\\w+)"));
        static const QRegularExpression reArrow(
            QStringLiteral("(?m)^\\s*(?:export\\s+)?(?:const|let|var)\\s+(\\w+)\\s*="
                           "\\s*(?:async\\s*)?\\([^)]*\\)\\s*=>"));
        runRe(reFn);
        runRe(reClass);
        runRe(reArrow);
    } else if (lang == QLatin1String("qml")) {
        static const QRegularExpression reFn(QStringLiteral("\\bfunction\\s+(\\w+)"));
        // ids declarados: 'id: foo'
        static const QRegularExpression reId(
            QStringLiteral("(?m)^\\s*id\\s*:\\s*(\\w+)"));
        runRe(reFn);
        runRe(reId);
    }
    return out;
}

// Extrae referencias de import/include como basenames normalizados (sin ext, en
// minúscula). Equivalente al expandidor de dep-graph de hybrid_search; lo
// replicamos acá para que el indexador sea autónomo (no toca AgentToolRunner).
QSet<QString> extractImportRefs(const QString &text)
{
    QSet<QString> refs;
    static const QRegularExpression reC(
        QStringLiteral("#\\s*include\\s*[\"<]([^\">]+)[\">]"));
    static const QRegularExpression reFrom(
        QStringLiteral("(?:from|import|require)\\s*\\(?\\s*[\"']([^\"']+)[\"']"));
    static const QRegularExpression rePy(
        QStringLiteral("^\\s*(?:from|import)\\s+([\\w.]+)"),
        QRegularExpression::MultilineOption);
    static const QRegularExpression reQml(
        QStringLiteral("^\\s*import\\s+([\\w.]+)"),
        QRegularExpression::MultilineOption);
    static const QRegularExpression reCodeExt(
        QStringLiteral("\\.(h|hpp|hh|hxx|c|cc|cpp|cxx|js|jsx|mjs|ts|tsx|py|qml|java|go|rs|kt)$"),
        QRegularExpression::CaseInsensitiveOption);
    auto add = [&](const QString &raw) {
        QString s = raw;
        s.replace(QLatin1Char('\\'), QLatin1Char('/'));
        s = s.section(QLatin1Char('/'), -1).trimmed();
        if (reCodeExt.match(s).hasMatch())
            s = s.section(QLatin1Char('.'), 0, -2);
        else if (s.contains(QLatin1Char('.')))
            s = s.section(QLatin1Char('.'), -1);
        s = s.toLower();
        if (s.size() >= 2) refs.insert(s);
    };
    for (const QRegularExpression *re : {&reC, &reFrom, &rePy, &reQml}) {
        auto it = re->globalMatch(text);
        while (it.hasNext()) add(it.next().captured(1));
    }
    return refs;
}

}  // namespace

namespace CodeGraphIndexer {

Stats build(const QString &rootCwd, const QStringList &langs, QString *report)
{
    Stats st;
    const QString rootAbs = QDir(rootCwd).absolutePath();
    QDir base(rootAbs);

    // Set de lenguajes pedido (vacío = todos). Normalizado a minúscula.
    QSet<QString> wantLang;
    for (const QString &l : langs) {
        const QString v = l.trimmed().toLower();
        if (!v.isEmpty()) wantLang.insert(v);
    }

    // 1. Recolectar archivos soportados (cap defensivo).
    constexpr int kMaxFiles = 5000;
    struct Indexed { QString rel; QString lang; QString text; };
    QList<Indexed> docs;
    QHash<QString, QString> byBase;   // basename(sin ext, lower) -> rel (para imports)

    QStringList stack{rootAbs};
    while (!stack.isEmpty() && docs.size() < kMaxFiles) {
        QDir d(stack.takeLast());
        const auto entries = d.entryInfoList(
            QDir::NoDotAndDotDot | QDir::Files | QDir::Dirs, QDir::Name);
        for (const QFileInfo &fi : entries) {
            if (fi.isDir()) {
                if (!isIgnoredDir(fi.fileName())) stack << fi.absoluteFilePath();
                continue;
            }
            const QString lang = langOf(fi.suffix());
            if (lang.isEmpty()) continue;
            if (!wantLang.isEmpty() && !wantLang.contains(lang)) continue;

            QFile f(fi.absoluteFilePath());
            if (!f.open(QIODevice::ReadOnly)) continue;
            const QString text = QString::fromUtf8(f.read(512 * 1024));  // cap por archivo
            f.close();

            const QString rel = base.relativeFilePath(fi.absoluteFilePath());
            docs.append({rel, lang, text});
            const QString b = fi.completeBaseName().toLower();
            if (!b.isEmpty() && !byBase.contains(b)) byBase.insert(b, rel);
            if (docs.size() >= kMaxFiles) break;
        }
    }

    // 2. Construir entidades + relaciones.
    QVector<QPair<QString, QString>> entities;
    QVector<GraphStore::Triple> relations;
    QSet<QString> distinctSyms;
    constexpr int kMaxSymsPerFile = 80;

    for (const Indexed &doc : docs) {
        entities.append({doc.rel, QStringLiteral("file")});

        for (const QString &sym : extractSymbols(doc.lang, doc.text, kMaxSymsPerFile)) {
            entities.append({sym, QStringLiteral("concept")});
            relations.append({doc.rel, QStringLiteral("defines"), sym});
            distinctSyms.insert(sym);
        }

        QSet<QString> selfBase;
        selfBase.insert(QFileInfo(doc.rel).completeBaseName().toLower());
        for (const QString &refb : extractImportRefs(doc.text)) {
            if (selfBase.contains(refb)) continue;        // no auto-import
            const QString target = byBase.value(refb);
            if (target.isEmpty() || target == doc.rel) continue;
            relations.append({doc.rel, QStringLiteral("imports"), target});
        }
    }

    st.files = docs.size();
    st.symbols = distinctSyms.size();

    // 3. Volcado masivo (una sola pasada de escritura).
    int addedEnt = 0, addedRel = 0;
    GraphStore::addBatch(rootCwd, entities, relations, &addedEnt, &addedRel);
    st.edges = addedRel;

    if (report) {
        *report = QStringLiteral(
            "[code_graph: %1 archivos indexados · %2 símbolos · +%3 entidades · "
            "+%4 relaciones (defines/imports) en .llamacode/graph.jsonl]\n"
            "Consultá el mapa con la tool 'graph' (action='query', name=<archivo o símbolo>).")
            .arg(st.files).arg(st.symbols).arg(addedEnt).arg(addedRel);
    }
    return st;
}

}  // namespace CodeGraphIndexer

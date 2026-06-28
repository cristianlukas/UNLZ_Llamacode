// Unit tests del indexador determinista repo→grafo:
//   - GraphStore::addBatch: inserción masiva + dedupe (entidades y relaciones).
//   - CodeGraphIndexer::build: extrae símbolos (clases/funciones) e imports/
//     includes de un repo fixture y los vuelca como file-[defines]->símbolo y
//     file-[imports]->file; idempotente; respeta el filtro de lenguajes.
// Cada test usa un cwd temporal aislado.

#include <QtTest>
#include <QTemporaryDir>
#include <QDir>
#include <QFile>
#include "core/agent/GraphStore.h"
#include "core/agent/CodeGraphIndexer.h"

class CodeGraphTests : public QObject
{
    Q_OBJECT
private slots:
    void addBatch_insertsAndDedupes();
    void index_extractsSymbols();
    void index_extractsImports();
    void index_idempotent();
    void index_langFilter();

private:
    // Escribe un archivo bajo dir.path() (creando subcarpetas) con 'content'.
    static void writeFile(const QString &root, const QString &rel, const QString &content)
    {
        const QString abs = QDir(root).absoluteFilePath(rel);
        QDir().mkpath(QFileInfo(abs).absolutePath());
        QFile f(abs);
        QVERIFY(f.open(QIODevice::WriteOnly | QIODevice::Text));
        f.write(content.toUtf8());
        f.close();
    }
};

void CodeGraphTests::addBatch_insertsAndDedupes()
{
    QTemporaryDir dir;
    QVector<QPair<QString, QString>> ents{{"Foo", "file"}, {"Bar", "concept"}};
    QVector<GraphStore::Triple> rels{{"Foo", "defines", "Bar"}};
    int e1 = 0, r1 = 0;
    GraphStore::addBatch(dir.path(), ents, rels, &e1, &r1);
    QCOMPARE(e1, 2);
    QCOMPARE(r1, 1);

    // Segundo batch idéntico: nada nuevo (dedupe contra lo ya escrito).
    int e2 = 0, r2 = 0;
    GraphStore::addBatch(dir.path(), ents, rels, &e2, &r2);
    QCOMPARE(e2, 0);
    QCOMPARE(r2, 0);

    const QString out = GraphStore::query(dir.path(), "Foo", 1);
    QVERIFY(out.contains("Bar"));
    QVERIFY(out.contains("defines"));
}

void CodeGraphTests::index_extractsSymbols()
{
    QTemporaryDir dir;
    writeFile(dir.path(), "src/widget.cpp",
              "#include \"widget.h\"\n"
              "class Widget {\n};\n"
              "void doStuff(int a) {\n  return;\n}\n"
              "int main() {\n  return 0;\n}\n");

    QString report;
    const CodeGraphIndexer::Stats st = CodeGraphIndexer::build(dir.path(), {}, &report);
    QCOMPARE(st.files, 1);
    QVERIFY(st.symbols >= 2);   // Widget, doStuff, main (al menos 2)

    const QString out = GraphStore::query(dir.path(), "src/widget.cpp", 1);
    QVERIFY(out.contains("Widget"));
    QVERIFY(out.contains("doStuff"));
    QVERIFY(out.contains("defines"));
    QVERIFY(report.contains("code_graph"));
}

void CodeGraphTests::index_extractsImports()
{
    QTemporaryDir dir;
    // Nombres de >=2 chars: extractImportRefs descarta basenames de 1 char.
    writeFile(dir.path(), "src/alpha.cpp", "#include \"beta.h\"\nvoid fa() {}\n");
    writeFile(dir.path(), "src/beta.h", "class Beta {};\n");

    CodeGraphIndexer::build(dir.path(), {}, nullptr);

    // alpha.cpp importa beta (resuelto por basename → src/beta.h).
    const QString out = GraphStore::query(dir.path(), "src/alpha.cpp", 1);
    QVERIFY(out.contains("imports"));
    QVERIFY(out.contains("beta.h"));
}

void CodeGraphTests::index_idempotent()
{
    QTemporaryDir dir;
    writeFile(dir.path(), "m.py", "def foo():\n    pass\nclass Bar:\n    pass\n");

    const CodeGraphIndexer::Stats s1 = CodeGraphIndexer::build(dir.path(), {}, nullptr);
    QVERIFY(s1.edges > 0);
    // Segunda corrida: mismo contenido → 0 relaciones nuevas (dedupe).
    const CodeGraphIndexer::Stats s2 = CodeGraphIndexer::build(dir.path(), {}, nullptr);
    QCOMPARE(s2.edges, 0);
}

void CodeGraphTests::index_langFilter()
{
    QTemporaryDir dir;
    writeFile(dir.path(), "keep.cpp", "void cppFn() {}\n");
    writeFile(dir.path(), "skip.py", "def pyFn():\n    pass\n");

    // Sólo cpp: el símbolo de python NO debe entrar al grafo.
    const CodeGraphIndexer::Stats st = CodeGraphIndexer::build(
        dir.path(), QStringList{QStringLiteral("cpp")}, nullptr);
    QCOMPARE(st.files, 1);

    QFile f(GraphStore::jsonlPath(dir.path()));
    QVERIFY(f.open(QIODevice::ReadOnly));
    const QString content = QString::fromUtf8(f.readAll());
    QVERIFY(content.contains("cppFn"));
    QVERIFY(!content.contains("pyFn"));
}

QTEST_MAIN(CodeGraphTests)
#include "test_code_graph.moc"

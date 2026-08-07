#pragma once
#include <QByteArray>
#include <QString>
#include <QStringList>
#include <QVector>

// Importa benchmarks PÚBLICOS estándar (GSM8K, HumanEval, MMLU, AIME…) para no
// depender de tareas caseras.
//
// El motivo es concreto: las suites propias se saturaron. En el barrido del
// 2026-08-07 un Qwen de 27B sacó 14/14 en todo lo que se pudo construir Y
// verificar con certeza, así que dejaron de separar modelos. Los sets públicos
// tienen dificultad calibrada y resultados comparables con los que publica cada
// modelo.
//
// Cada suite trae su formato, así que el import normaliza a un ítem único y la
// corrección se decide por `grade`, que es pura y testeable: el parseo de la
// respuesta de un LLM es donde se cometen los errores caros (medir el formato en
// vez del contenido, o dar por incorrecta una respuesta correcta escrita
// distinto).
struct BenchmarkItem {
    QString id;
    QString prompt;
    // multiple_choice: la respuesta es una letra (A-Z).
    // numeric:         un número; tolera separadores de miles y unidades.
    // code_tests:      el modelo devuelve código y `tests` lo verifica al correr.
    // contains:        alguna de las variantes de `expected` aparece en la respuesta.
    QString type;
    QString expected;
    QString tests;          // sólo code_tests: asserts que se ejecutan aparte
    QStringList choices;    // sólo multiple_choice, para armar el prompt
};

struct BenchmarkPack {
    QString id;
    QString name;
    QString source;         // URL de origen, para poder rastrear qué se corrió
    QString license;
    QVector<BenchmarkItem> items;

    bool isEmpty() const { return items.isEmpty(); }

    // ── Import de los formatos públicos, tal cual se descargan ───────────────
    // GSM8K: JSONL con {question, answer} y la respuesta final tras "#### ".
    static BenchmarkPack fromGsm8kJsonl(const QByteArray &jsonl, QString *err = nullptr);
    // HumanEval: JSONL con {task_id, prompt, test, entry_point}.
    static BenchmarkPack fromHumanEvalJsonl(const QByteArray &jsonl, QString *err = nullptr);
    // MMLU: JSONL con {question, choices[], answer} (answer = índice o letra).
    static BenchmarkPack fromMmluJsonl(const QByteArray &jsonl, QString *err = nullptr);
    // Formato propio ya normalizado (el que guarda LlamaCode en disco).
    static BenchmarkPack fromPackJson(const QByteArray &json, QString *err = nullptr);
    QByteArray toPackJson() const;

    // Detecta el formato por las claves de la primera línea y delega.
    static BenchmarkPack autoImport(const QByteArray &data, const QString &hintName,
                                    QString *err = nullptr);

    // ¿La respuesta del modelo es correcta? Pura: sin red, sin disco, sin
    // ejecutar nada. Para code_tests devuelve false — esos necesitan correr el
    // código y eso lo hace el runner.
    static bool grade(const BenchmarkItem &item, const QString &response);

    // Helpers expuestos porque son donde se cometen los errores de medición.
    static QString extractChoice(const QString &response);   // "B" o vacío
    static QString extractNumber(const QString &response);   // normalizado, o vacío
    static QString extractCode(const QString &response);     // sin cercas markdown
};

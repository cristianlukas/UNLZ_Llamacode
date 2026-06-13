#pragma once
#include <QString>
#include <QStringList>
#include <QVector>

// Suite de evaluación propia: tareas REALES del usuario (coding, pericial,
// búsqueda en expedientes, docs largos, multimodal) con criterios de aceptación.
// Se carga desde JSON y el runner reutiliza el sistema de benchmark existente
// (AppController::runAgentBenchmark) para medir calidad / tiempo / reparaciones
// por perfil de inferencia. Esto es el esqueleto del harness (punto 4): el modelo
// de datos + loader; la integración con la UI de benchmark se hace aparte.
struct EvalTask {
    QString id;
    QString category;        // coding | pericial | search | docs | multimodal
    QString prompt;
    QStringList acceptance;  // checks: substrings esperados o comandos del runner
    QStringList attachments; // rutas de docs/imágenes para tareas docs/multimodal
    int weight = 1;
};

struct EvalSuite {
    QString name;
    QString description;
    QVector<EvalTask> tasks;

    // Carga una suite desde JSON. err recibe el motivo si falla (suite vacía).
    static EvalSuite loadFromFile(const QString &path, QString *err = nullptr);
    static EvalSuite loadFromJson(const QByteArray &json, QString *err = nullptr);

    // Categorías presentes (únicas, en orden de aparición).
    QStringList categories() const;
    bool isEmpty() const { return tasks.isEmpty(); }
};

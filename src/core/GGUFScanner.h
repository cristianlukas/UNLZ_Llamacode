#pragma once
#include "ModelRoot.h"
#include "CatalogModel.h"
#include <QList>
#include <QMap>
#include <QObject>

class GGUFScanner : public QObject
{
    Q_OBJECT
public:
    explicit GGUFScanner(QObject *parent = nullptr);

    // Synchronous scan — call from thread pool. Rutea por root.kind:
    // "ollama" → blobs del store de Ollama; cualquier otro → *.gguf en disco.
    QList<CatalogModel> scan(const ModelRoot &root);

    // Inferencia pura sobre el nombre de archivo (públicas para tests).
    static QString inferFamily(const QString &fileName);
    static QString inferQuant(const QString &fileName);
    static bool isVisionCandidate(const QString &fileName);
    static bool isDraftCandidate(const QString &fileName, qint64 sizeBytes);

    // Lectura de composición real de tensores desde el header GGUF.
    struct Composition {
        bool valid = false;
        QMap<QString, int> typeTensors;     // nombre dtype -> nº de tensores
        QMap<QString, qint64> typeElements; // nombre dtype -> nº de elementos
        qint64 totalElements = 0;
        QString dominantQuant;              // dtype cuantizado con más elementos
        double bpw = 0.0;                   // file_size*8 / totalElements
        QString architecture;               // general.architecture
        qint64 parameterCount = 0;           // general.parameter_count
        int trainedContext = 0;              // *.context_length
        QString breakdown() const;          // "q4_0:265, q6_k:1, f32:392"
    };
    static Composition readComposition(const QString &filePath, qint64 fileSizeBytes);
    static QString ggmlTypeName(quint32 t);

    // True si el modelo es un Gemma QAT con quant real q4_0 "crudo" (Google-style):
    // llama.cpp aplica scales fp16 sobre un QAT entrenado con scales bf16 → clipping
    // de los pesos grandes → degradación (peor a partir de ~50-100k ctx). Los dynamic
    // quants de unsloth (UD-* / *K_XL) corrigen esto, así que se excluyen.
    static bool isDegradedQatQuant(const QString &fileName, const QString &family,
                                   const QString &quantReal);

signals:
    void progress(const QString &rootId, int found);
};

#pragma once
#include <QString>
#include <QDateTime>

struct CatalogModel {
    QString id;
    QString rootId;
    QString absolutePath;
    QString fileName;
    qint64 sizeBytes = 0;
    QDateTime mtime;
    QString familyHint;
    QString quantHint;          // inferido del nombre de archivo
    QString quantReal;          // derivado de composición real de tensores ("" si no leído)
    QString tensorBreakdown;    // ej "q4_0:265, q6_k:1, f32:392" (por nº de tensores)
    double  bpw = 0.0;          // bits-per-weight efectivo (0 si desconocido)
    bool    quantMismatch = false; // nombre de archivo != composición real
    QString architecture;       // general.architecture del header GGUF
    qint64  parameterCount = 0; // general.parameter_count (0 si no está presente)
    int     trainedContext = 0; // <architecture>.context_length (0 si desconocido)
    bool isVisionCandidate = false;
    bool isDraftCandidate = false;
    QString sha256;
    bool isAvailable = true;

    QString sizeLabel() const;
};

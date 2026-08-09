#pragma once

#include <QJsonArray>
#include <QJsonObject>
#include <QStringList>

// Expande variantes declarativas de benchmark sin duplicar en el bundle todos los
// metadatos del modelo, descarga y binario. Cada variante hereda la entrada base y
// puede sobreescribir runtime y flags con valor; JSON null elimina el flag.
inline QJsonArray expandSystemProfileVariants(const QJsonArray &source)
{
    QJsonArray expanded;
    for (const QJsonValue &value : source) {
        QJsonObject base = value.toObject();
        const QJsonArray variants = base.take(QStringLiteral("benchmarkVariants")).toArray();
        expanded.append(base);

        for (const QJsonValue &variantValue : variants) {
            const QJsonObject variant = variantValue.toObject();
            const QString id = variant.value(QStringLiteral("id")).toString();
            if (id.isEmpty())
                continue;

            QJsonObject derived = base;
            derived[QStringLiteral("id")] = id;
            derived[QStringLiteral("displayName")] =
                variant.value(QStringLiteral("displayName")).toString();
            // Una variante de tuning no hereda las insignias obtenidas por el
            // perfil base: debe medirse y marcarse de forma explicita.
            derived[QStringLiteral("favorite")] = variant.value(QStringLiteral("favorite")).toBool(false);
            derived[QStringLiteral("benchmark")] = variant.value(QStringLiteral("benchmark")).toBool(false);
            if (variant.contains(QStringLiteral("order")))
                derived[QStringLiteral("order")] = variant.value(QStringLiteral("order"));
            derived.remove(QStringLiteral("contextPresets"));

            QJsonObject runtime = derived.value(QStringLiteral("runtime")).toObject();
            const QJsonObject runtimeOverrides = variant.value(QStringLiteral("runtime")).toObject();
            for (auto it = runtimeOverrides.begin(); it != runtimeOverrides.end(); ++it)
                runtime[it.key()] = it.value();
            derived[QStringLiteral("runtime")] = runtime;

            QStringList args;
            for (const QJsonValue &arg : derived.value(QStringLiteral("extraArgs")).toArray())
                args.append(arg.toString());
            const QJsonObject flagOverrides =
                variant.value(QStringLiteral("extraArgOverrides")).toObject();
            for (auto it = flagOverrides.begin(); it != flagOverrides.end(); ++it) {
                const int index = args.indexOf(it.key());
                if (index >= 0) {
                    args.removeAt(index);
                    if (index < args.size() && !args.at(index).startsWith(u'-'))
                        args.removeAt(index);
                }
                if (!it.value().isNull())
                    args << it.key() << it.value().toVariant().toString();
            }
            QJsonArray extraArgs;
            for (const QString &arg : args)
                extraArgs.append(arg);
            derived[QStringLiteral("extraArgs")] = extraArgs;
            derived[QStringLiteral("comment")] =
                variant.value(QStringLiteral("comment")).toString();
            expanded.append(derived);
        }
    }
    return expanded;
}

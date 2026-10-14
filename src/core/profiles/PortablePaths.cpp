#include "PortablePaths.h"

#include <QRegularExpression>

namespace {

const QString kWindowsHome = QStringLiteral("C:/Users/cristian");

QString withoutTrailingSlash(QString root)
{
    root = root.trimmed();
    while (root.size() > 1 && root.endsWith(QLatin1Char('/')))
        root.chop(1);
    return root;
}

// "D:////x" -> "D:/x". Repara archivos que ya acumularon barras. Sólo una
// letra de unidad suelta: "http://" o "file:///" no son unidades y no se tocan.
QString collapseDriveSlashes(QString value)
{
    static const QRegularExpression re(QStringLiteral("(?<![A-Za-z])([CcDd]:)/{2,}"));
    return value.replace(re, QStringLiteral("\\1/"));
}

QString replaceCaseInsensitive(QString value, const QString &from, const QString &to)
{
    if (from.isEmpty()) return value;
    int pos = 0;
    while ((pos = value.indexOf(from, pos, Qt::CaseInsensitive)) >= 0) {
        value.replace(pos, from.size(), to);
        pos += to.size();
    }
    return value;
}

// Reemplaza root sólo donde termina un componente de ruta: "/mnt/d" no debe
// tocar "/mnt/data". "<root>/x" -> "<prefix>x"; "<root>" solo -> alone.
QString replaceRoot(QString value, const QString &root, const QString &prefix,
                    const QString &alone)
{
    if (root.isEmpty()) return value;
    const QString escaped = QRegularExpression::escape(root);
    value.replace(QRegularExpression(escaped + QStringLiteral("/")), prefix);
    value.replace(QRegularExpression(escaped + QStringLiteral("(?=$|[\\s\"',;=])")), alone);
    return value;
}

} // namespace

namespace PortablePaths {

QString translate(const QString &input, bool toRuntime,
                  const QString &cRootIn, const QString &dRootIn)
{
    const QString cRoot = withoutTrailingSlash(cRootIn);
    const QString dRoot = withoutTrailingSlash(dRootIn);
    if (cRoot.isEmpty() && dRoot.isEmpty()) return input;

    QString value = input;
    if (toRuntime) {
        static const QRegularExpression drive(QStringLiteral("[CcDd]:[/\\\\]"));
        if (!value.contains(drive)) return value;
        value.replace(QLatin1Char('\\'), QLatin1Char('/'));
        value = collapseDriveSlashes(value);
        if (!cRoot.isEmpty()) {
            static const QRegularExpression home(QStringLiteral("C:/Users/cristian(?=$|[/\\s\"',;=])"),
                                                 QRegularExpression::CaseInsensitiveOption);
            value.replace(home, cRoot);
        }
        if (!dRoot.isEmpty())
            value = replaceCaseInsensitive(value, QStringLiteral("D:/"), dRoot + QLatin1Char('/'));
        return value;
    }

    // La raíz más larga primero, por si una contuviera a la otra.
    const auto mapC = [&] { value = replaceRoot(value, cRoot, kWindowsHome + QLatin1Char('/'), kWindowsHome); };
    const auto mapD = [&] { value = replaceRoot(value, dRoot, QStringLiteral("D:/"), QStringLiteral("D:/")); };
    if (cRoot.size() >= dRoot.size()) { mapC(); mapD(); }
    else                              { mapD(); mapC(); }
    return collapseDriveSlashes(value);
}

QString translateFromEnv(const QString &value, bool toRuntime)
{
#ifdef Q_OS_WIN
    Q_UNUSED(toRuntime);
    return value;
#else
    if (qgetenv("LLAMACODE_SHARED_PORTABLE_CONFIG").isEmpty()) return value;
    return translate(value, toRuntime,
                     QString::fromLocal8Bit(qgetenv("LLAMACODE_WINDOWS_C_ROOT")),
                     QString::fromLocal8Bit(qgetenv("LLAMACODE_WINDOWS_D_ROOT")));
#endif
}

} // namespace PortablePaths

#include "ThemeProvider.h"
#include <QSettings>

ThemeProvider::ThemeProvider(QObject *parent) : QObject(parent) {
    QSettings s;
    m_theme = s.value(QStringLiteral("theme"), QStringLiteral("dark")).toString();
}

void ThemeProvider::setTheme(const QString &t) {
    if (m_theme == t) return;
    m_theme = t;
    QSettings s;
    s.setValue(QStringLiteral("theme"), t);
    emit themeChanged();
}

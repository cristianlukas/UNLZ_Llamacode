#pragma once

#include <QChar>
#include <QString>
#include <QStringList>
#include <QVariantList>
#include <QVariantMap>

// Acumula el tipeo del usuario durante una sesión Teach y lo convierte en pasos
// de timeline. Los caracteres imprimibles se juntan en un único paso
// `[type "..."]`; una tecla "límite" (ENTER, TAB, ESC, flechas, F1..F12) o un
// atajo (Ctrl/Alt/Win + algo) primero VACÍA el texto pendiente como un paso
// `[type]` y luego emite su propio paso `[key]`, preservando el orden real.
//
// Es PURA y testeable: no toca el SO ni captura pantalla. El recorder le pasa
// los eventos crudos (desde el hook de teclado) y appendea los pasos devueltos.
class TeachKeyBuffer
{
public:
    // Agrega un carácter imprimible al texto pendiente.
    void feedChar(QChar c);
    // Procesa una tecla nombrada (no imprimible) o un atajo. Devuelve los pasos
    // a emitir: primero el `[type]` pendiente (si hay), luego el `[key]`.
    QVariantList feedKey(const QString &keyName, const QStringList &modifiers = {});
    // Vacía el texto pendiente como un único paso `[type]` (lista vacía si no hay).
    QVariantList flush();

    bool hasPending() const { return !m_text.isEmpty(); }
    QString pendingText() const { return m_text; }
    void clear() { m_text.clear(); }

    // Constructores de paso (públicos para reuso/test).
    static QVariantMap typeStep(const QString &text);
    static QVariantMap keyStep(const QString &keyName, const QStringList &modifiers = {});

private:
    QString m_text;
};

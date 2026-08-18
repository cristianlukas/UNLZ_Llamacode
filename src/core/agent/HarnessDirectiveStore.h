#pragma once
#include <QString>
#include <QVariantList>
#include <QVariantMap>

// Directivas de usuario para el system prompt (packs del harness modular).
// Misma convención que PortableSkillStore, pero el cuerpo se inyecta en el
// prompt en vez de cargarse bajo demanda:
//   <AppLocalData>/harness/directives/<slug>.md
//   <workspace>/.llamacode/directives/<slug>.md      (pisa a la global)
//
// Frontmatter YAML mínimo:
//   ---
//   name: mi-directiva          (debe coincidir con el archivo, kebab-case)
//   description: una línea      (obligatoria; la ve el editor)
//   when: tools.desktop         (opcional; gate declarativo, ver
//                                LlamaAgentBackend::directiveConditionMet)
//   ---
//   <cuerpo que se inyecta>
//
// El cuerpo tiene tope de tamaño: una directiva de 8 KB es una regresión de
// contexto silenciosa, y el perfil ya paga tokens por cada tool que habilita.
namespace HarnessDirectiveStore {

QString globalRoot();
QString projectRoot(const QString &workspace);

// Metadata de todas las directivas visibles (sin cuerpo): {name, description,
// when, scope, path, bytes}. Ordenadas por nombre.
QVariantList list(const QString &workspace = QString());

// Una directiva con cuerpo: agrega {body}. `ok=false` + `error` si no existe o
// es inválida.
QVariantMap load(const QString &name, const QString &workspace = QString());

// Carga varias por slug, en el orden pedido, salteando las inválidas. Devuelve
// {slug, body, when} — el formato que consume LlamaAgentBackend::setCustomDirectives.
QVariantList loadMany(const QStringList &names, const QString &workspace = QString());

constexpr qint64 kMaxDirectiveBytes = 32 * 1024;

}  // namespace HarnessDirectiveStore

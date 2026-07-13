#include "ProfileHealthChecker.h"
#include "ProfileManager.h"
#include "../BinaryRegistry.h"
#include "../ModelCatalog.h"
#include "MtpDetection.h"

QVariantMap HealthIssue::toMap() const
{
    QVariantMap m;
    m["severity"] = severity;
    m["launchId"] = launchId;
    m["entity"]   = entity;
    m["code"]     = code;
    m["message"]  = message;
    m["fix"]      = fix;
    return m;
}

static HealthIssue mk(const QString &sev, const QString &launchId,
                      const QString &entity, const QString &code,
                      const QString &msg, const QString &fix)
{
    HealthIssue i;
    i.severity = sev;
    i.launchId = launchId;
    i.entity   = entity;
    i.code     = code;
    i.message  = msg;
    i.fix      = fix;
    return i;
}

QList<HealthIssue> ProfileHealthChecker::checkLaunch(const Refs &r)
{
    QList<HealthIssue> out;
    const QString id = r.launch.id;

    // --- Backend ---
    if (r.launch.backendProfileId.isEmpty()) {
        out << mk("error", id, "backend", "backend-unset",
                  "El perfil no tiene backend asignado.",
                  "Asignar un backend en el perfil de lanzamiento.");
    } else if (!r.backendFound) {
        out << mk("error", id, "backend", "backend-missing",
                  "Referencia a un backend inexistente.",
                  "Re-asignar un backend válido o recrearlo.");
    } else if (r.backend.isCloud()) {
        // Cloud: no binario; validar endpoint + secreto + modelo.
        if (r.backend.cloudBaseUrl.isEmpty())
            out << mk("error", id, "cloud", "cloud-url-missing",
                      "Backend cloud sin URL base.",
                      "Setear la URL base del proveedor (sin /v1).");
        if (r.backend.cloudKeyRef.isEmpty())
            out << mk("warning", id, "cloud", "cloud-key-unset",
                      "Backend cloud sin referencia de secreto (API key).",
                      "Configurar la referencia de secreto en SecretStore.");
        if (r.backend.cloudModel.isEmpty())
            out << mk("warning", id, "cloud", "cloud-model-unset",
                      "Backend cloud sin modelo especificado.",
                      "Indicar el nombre del modelo a enviar.");
    } else {
        // Local: requiere binario válido.
        if (r.backend.binaryId.isEmpty())
            out << mk("error", id, "binary", "binary-unset",
                      "Backend local sin binario asignado.",
                      "Asignar un binario de llama-server al backend.");
        else if (!r.binaryFound)
            out << mk("error", id, "binary", "binary-missing",
                      "Referencia a un binario inexistente.",
                      "Re-asignar un binario válido en Binarios.");
        else if (!r.binary.pathValid)
            out << mk("error", id, "binary", "binary-path-invalid",
                      "El ejecutable del binario no existe en su ruta.",
                      "Corregir la ruta del binario o re-agregarlo.");
    }

    // --- Modelo (no aplica a cloud) ---
    const bool cloud = r.backendFound && r.backend.isCloud();
    if (!cloud) {
        if (r.launch.modelProfileId.isEmpty()) {
            out << mk("error", id, "model", "model-unset",
                      "El perfil no tiene modelo asignado.",
                      "Asignar un perfil de modelo.");
        } else if (!r.modelRefFound) {
            out << mk("error", id, "model", "model-ref-missing",
                      "Referencia a un perfil de modelo inexistente.",
                      "Re-asignar un perfil de modelo válido.");
        } else if (r.model.modelId.isEmpty()) {
            out << mk("error", id, "model", "model-file-unset",
                      "El perfil de modelo no apunta a ningún .gguf.",
                      "Elegir un modelo del catálogo.");
        } else if (!r.modelFileExists) {
            out << mk("error", id, "model", "model-file-missing",
                      "El archivo .gguf del modelo no está en disco.",
                      "Re-escanear el root o descargar el modelo.");
        }

        // mmproj (visión): referenciado pero ausente = pierde visión.
        if (r.modelRefFound && !r.model.mmprojId.isEmpty() && !r.mmprojFileExists)
            out << mk("warning", id, "mmproj", "mmproj-file-missing",
                      "El mmproj de visión no está en disco; se pierde la visión.",
                      "Re-escanear o descargar el mmproj.");

        // draft / spec decoding.
        if (r.modelRefFound && !r.model.draftModelId.isEmpty() && !r.draftFileExists)
            out << mk("warning", id, "draft", "draft-file-missing",
                      "El modelo draft (spec decoding) no está en disco.",
                      "Re-escanear o descargar el draft, o desactivar spec.");
        const bool selfContainedMtp = r.model.specType == QLatin1String("draft-mtp")
            && MtpDetection::isSelfContained(r.modelFileName);
        if (r.modelRefFound && !r.model.specType.isEmpty()
            && r.model.draftModelId.isEmpty() && !selfContainedMtp)
            out << mk("warning", id, "draft", "spec-without-draft",
                      "Speculative decoding activado sin modelo draft.",
                      "Asignar un draft o limpiar specType.");
    }

    // --- Runtime preset ---
    if (!r.launch.runtimePresetId.isEmpty() && !r.runtimeFound)
        out << mk("warning", id, "runtime", "runtime-missing",
                  "Referencia a un runtime preset inexistente; se usan defaults.",
                  "Re-asignar un runtime preset.");

    // --- Agent profile ---
    if (!r.launch.agentProfileId.isEmpty() && !r.agentRefFound)
        out << mk("warning", id, "agent", "agent-missing",
                  "Referencia a un perfil de agente inexistente; se usa el default.",
                  "Re-asignar un perfil de agente.");

    return out;
}

QList<HealthIssue> ProfileHealthChecker::checkAll(ProfileManager *profiles,
                                                  BinaryRegistry *binaries,
                                                  ModelCatalog *catalog)
{
    QList<HealthIssue> out;
    if (!profiles) return out;

    // launchProfiles() devuelve &m_launches, que es exactamente este tipo concreto.
    // ProfileListModel<T> es un template sin Q_OBJECT, así que no se puede
    // qobject_cast; el static_cast es seguro por el tipo dinámico conocido.
    auto *launchModel = static_cast<ProfileListModel<LaunchProfile>*>(profiles->launchProfiles());
    if (!launchModel) return out;

    auto fileExists = [catalog](const QString &catalogId) -> bool {
        if (!catalog || catalogId.isEmpty()) return false;
        const CatalogModel m = catalog->findById(catalogId);
        return !m.id.isEmpty() && m.isAvailable;
    };

    for (const LaunchProfile &launch : launchModel->items()) {
        Refs r;
        r.launch = launch;

        if (!launch.backendProfileId.isEmpty()) {
            r.backend = profiles->resolveBackend(launch.backendProfileId);
            r.backendFound = !r.backend.id.isEmpty();
        }
        if (r.backendFound && !r.backend.isCloud() && !r.backend.binaryId.isEmpty() && binaries) {
            r.binary = binaries->findById(r.backend.binaryId);
            r.binaryFound = !r.binary.id.isEmpty();
        }
        if (!launch.modelProfileId.isEmpty()) {
            r.model = profiles->resolveModelProfile(launch.modelProfileId);
            r.modelRefFound = !r.model.id.isEmpty();
            if (r.modelRefFound) {
                const CatalogModel mainModel = catalog
                    ? catalog->findById(r.model.modelId) : CatalogModel{};
                r.modelFileExists  = !mainModel.id.isEmpty() && mainModel.isAvailable;
                r.modelFileName = mainModel.fileName;
                r.mmprojFileExists = fileExists(r.model.mmprojId);
                r.draftFileExists  = fileExists(r.model.draftModelId);
            }
        }
        if (!launch.runtimePresetId.isEmpty()) {
            const RuntimePreset rt = profiles->resolveRuntime(launch.runtimePresetId);
            r.runtimeFound = !rt.id.isEmpty();
        }
        if (!launch.agentProfileId.isEmpty()) {
            const AgentProfile ap = profiles->resolveAgentProfile(launch.agentProfileId);
            r.agentRefFound = !ap.id.isEmpty();
        }

        out << checkLaunch(r);
    }
    return out;
}

QVariantList ProfileHealthChecker::checkAllAsVariant(ProfileManager *profiles,
                                                     BinaryRegistry *binaries,
                                                     ModelCatalog *catalog)
{
    QVariantList list;
    const auto issues = checkAll(profiles, binaries, catalog);
    for (const HealthIssue &i : issues) list << i.toMap();
    return list;
}

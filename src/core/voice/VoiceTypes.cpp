#include "VoiceTypes.h"

QJsonObject VoiceConfig::toJson() const
{
    QJsonObject o;
    o["enabled"]        = enabled;
    o["sttProvider"]    = sttProvider;
    o["sttBaseUrl"]     = sttBaseUrl;
    o["sttModel"]       = sttModel;
    o["sttKeyRef"]      = sttKeyRef;
    o["sttLanguage"]    = sttLanguage;
    o["sttEndpointPath"] = sttEndpointPath;
    o["sttManagedEngine"] = sttManagedEngine;
    o["ttsProvider"]    = ttsProvider;
    o["ttsBaseUrl"]     = ttsBaseUrl;
    o["ttsModel"]       = ttsModel;
    o["ttsVoice"]       = ttsVoice;
    o["ttsKeyRef"]      = ttsKeyRef;
    o["ttsFormat"]      = ttsFormat;
    o["vadThreshold"]   = vadThreshold;
    o["vadSilenceMs"]   = vadSilenceMs;
    o["vadSegmentMs"]   = vadSegmentMs;
    o["vadActivationLevel"] = vadActivationLevel;
    o["autoListen"]     = autoListen;
    o["bargeIn"]        = bargeIn;
    return o;
}

VoiceConfig VoiceConfig::fromJson(const QJsonObject &o)
{
    VoiceConfig c;
    c.enabled     = o.value("enabled").toBool(c.enabled);
    c.sttProvider = o.value("sttProvider").toString(c.sttProvider);
    c.sttBaseUrl  = o.value("sttBaseUrl").toString(c.sttBaseUrl);
    c.sttModel    = o.value("sttModel").toString(c.sttModel);
    c.sttKeyRef   = o.value("sttKeyRef").toString(c.sttKeyRef);
    c.sttLanguage = o.value("sttLanguage").toString(c.sttLanguage);
    c.sttEndpointPath = o.value("sttEndpointPath").toString(c.sttEndpointPath);
    if (c.sttEndpointPath.isEmpty()) c.sttEndpointPath = QStringLiteral("/v1/audio/transcriptions");
    c.sttManagedEngine = o.value("sttManagedEngine").toString(c.sttManagedEngine);
    c.ttsProvider = o.value("ttsProvider").toString(c.ttsProvider);
    c.ttsBaseUrl  = o.value("ttsBaseUrl").toString(c.ttsBaseUrl);
    c.ttsModel    = o.value("ttsModel").toString(c.ttsModel);
    c.ttsVoice    = o.value("ttsVoice").toString(c.ttsVoice);
    c.ttsKeyRef   = o.value("ttsKeyRef").toString(c.ttsKeyRef);
    c.ttsFormat   = o.value("ttsFormat").toString(c.ttsFormat);
    c.vadThreshold = o.value("vadThreshold").toDouble(c.vadThreshold);
    c.vadSilenceMs = o.value("vadSilenceMs").toInt(c.vadSilenceMs);
    c.vadSegmentMs = o.value("vadSegmentMs").toInt(c.vadSegmentMs);
    c.vadActivationLevel = o.value("vadActivationLevel").toDouble(c.vadActivationLevel);
    c.autoListen  = o.value("autoListen").toBool(c.autoListen);
    c.bargeIn     = o.value("bargeIn").toBool(c.bargeIn);
    return c;
}

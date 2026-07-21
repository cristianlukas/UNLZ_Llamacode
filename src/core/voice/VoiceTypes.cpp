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
    o["ttsMode"]        = ttsMode;
    o["ttsStreamAudio"] = ttsStreamAudio;
    o["ttsPcmSampleRate"] = ttsPcmSampleRate;
    o["ttsPcmChannels"] = ttsPcmChannels;
    o["ttsManagedVoice"]= ttsManagedVoice;
    o["ttsFallbackMode"] = ttsFallbackMode;
    o["qwenBinaryPath"] = qwenBinaryPath;
    o["qwenModelDir"] = qwenModelDir;
    o["qwenModelName"] = qwenModelName;
    o["qwenSpeakerEmbedding"] = qwenSpeakerEmbedding;
    o["qwenReferenceWav"] = qwenReferenceWav;
    o["qwenReferenceText"] = qwenReferenceText;
    o["qwenSpeaker"] = qwenSpeaker;
    o["qwenInstruction"] = qwenInstruction;
    o["qwenLanguage"] = qwenLanguage;
    o["qwenThreads"] = qwenThreads;
    o["ttsAutoConfigure"] = ttsAutoConfigure;
    o["vadThreshold"]   = vadThreshold;
    o["vadSilenceMs"]   = vadSilenceMs;
    o["vadSegmentMs"]   = vadSegmentMs;
    o["vadActivationLevel"] = vadActivationLevel;
    o["vadAdaptive"]    = vadAdaptive;
    o["smartTurn"]      = smartTurn;
    o["autoListen"]     = autoListen;
    o["bargeIn"]        = bargeIn;
    o["cursorOcr"]      = cursorOcr;
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
    c.ttsMode     = o.value("ttsMode").toString(c.ttsMode);
    if (c.ttsMode.isEmpty()) c.ttsMode = QStringLiteral("auto");
    c.ttsStreamAudio = o.value("ttsStreamAudio").toBool(c.ttsStreamAudio);
    c.ttsPcmSampleRate = qBound(8000, o.value("ttsPcmSampleRate").toInt(c.ttsPcmSampleRate), 192000);
    c.ttsPcmChannels = qBound(1, o.value("ttsPcmChannels").toInt(c.ttsPcmChannels), 2);
    c.ttsManagedVoice = o.value("ttsManagedVoice").toString(c.ttsManagedVoice);
    c.ttsFallbackMode = o.value("ttsFallbackMode").toString(c.ttsFallbackMode);
    c.qwenBinaryPath = o.value("qwenBinaryPath").toString();
    c.qwenModelDir = o.value("qwenModelDir").toString();
    c.qwenModelName = o.value("qwenModelName").toString(c.qwenModelName);
    c.qwenSpeakerEmbedding = o.value("qwenSpeakerEmbedding").toString();
    c.qwenReferenceWav = o.value("qwenReferenceWav").toString();
    c.qwenReferenceText = o.value("qwenReferenceText").toString();
    c.qwenSpeaker = o.value("qwenSpeaker").toString();
    c.qwenInstruction = o.value("qwenInstruction").toString();
    c.qwenLanguage = o.value("qwenLanguage").toString(c.qwenLanguage);
    c.qwenThreads = o.value("qwenThreads").toInt(c.qwenThreads);
    c.ttsAutoConfigure = o.value("ttsAutoConfigure").toBool(c.ttsAutoConfigure);
    c.vadThreshold = o.value("vadThreshold").toDouble(c.vadThreshold);
    c.vadSilenceMs = o.value("vadSilenceMs").toInt(c.vadSilenceMs);
    c.vadSegmentMs = o.value("vadSegmentMs").toInt(c.vadSegmentMs);
    c.vadActivationLevel = o.value("vadActivationLevel").toDouble(c.vadActivationLevel);
    c.vadAdaptive = o.value("vadAdaptive").toBool(c.vadAdaptive);
    c.smartTurn   = o.value("smartTurn").toBool(c.smartTurn);
    c.autoListen  = o.value("autoListen").toBool(c.autoListen);
    c.bargeIn     = o.value("bargeIn").toBool(c.bargeIn);
    // Sin la clave queda en false (el default del struct): un config viejo NO
    // estrena la captura de pantalla por actualizar la app.
    c.cursorOcr   = o.value("cursorOcr").toBool(c.cursorOcr);
    return c;
}

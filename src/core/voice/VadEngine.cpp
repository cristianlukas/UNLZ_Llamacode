#include "VadEngine.h"
#include <algorithm>

VadEngine::VadEngine(const VadTuning &t) : m_t(t) {}

void VadEngine::reset()
{
    m_floor = 0.0;
    m_seeded = false;
    m_speech = false;
    m_sawSpeech = false;
    m_hangMs = 0;
    m_onsetRun = 0;
    m_speechMs = 0;
    m_sawSpeechBeforeRun = false;
    m_recent.clear();
    m_recentMs = 0;
}

VadEngine::Frame VadEngine::push(double rms, int frameMs)
{
    if (rms < 0.0) rms = 0.0;
    if (frameMs < 0) frameMs = 0;

    // El primer frame siembra el piso: sin esto el piso arranca en 0 y el frame
    // inicial siempre supera el umbral relativo (falso onset al abrir el mic).
    if (!m_seeded) { m_floor = rms; m_seeded = true; }

    const double floorNow = std::max(m_floor, m_t.absFloor);
    const double onTh  = floorNow * m_t.onFactor;
    const double offTh = floorNow * m_t.offFactor;

    Frame f;
    f.level = rms;
    f.floor = floorNow;
    f.snr   = floorNow > 0.0 ? rms / floorNow : 0.0;

    const bool wasSpeech = m_speech;

    m_recent.emplace_back(rms, frameMs);
    m_recentMs += frameMs;
    while (m_recent.size() > 1 && m_recentMs - m_recent.front().second >= m_t.minWindowMs) {
        m_recentMs -= m_recent.front().second;
        m_recent.pop_front();
    }

    if (!m_speech) {
        // Silencio: exigir onsetFrames consecutivos por encima de onTh. Un
        // click aislado (golpe de teclado) no alcanza a abrir el turno.
        if (rms >= onTh) {
            ++m_onsetRun;
            if (m_onsetRun >= std::max(1, m_t.onsetFrames)) {
                m_speech = true;
                m_hangMs = m_t.hangoverMs;
                m_sawSpeechBeforeRun = m_sawSpeech;
                m_sawSpeech = true;
                m_speechMs = 0;
            }
        } else {
            m_onsetRun = 0;
        }
    } else {
        if (rms >= offTh) {
            m_hangMs = m_t.hangoverMs;   // sigue habiendo voz: recargar hangover
        } else {
            m_hangMs -= frameMs;
            if (m_hangMs <= 0) { m_speech = false; m_hangMs = 0; m_onsetRun = 0; }
        }
        m_speechMs += frameMs;
        if (m_speech && m_t.stuckSpeechMs > 0 && m_speechMs >= m_t.stuckSpeechMs
            && m_recentMs >= m_t.minWindowMs) {
            double windowMin = m_recent.front().first;
            for (const auto &r : m_recent) windowMin = std::min(windowMin, r.first);
            if (windowMin >= offTh) {
                m_floor = windowMin;
                m_speech = false;
                m_hangMs = 0;
                m_onsetRun = 0;
                m_speechMs = 0;
                m_sawSpeech = m_sawSpeechBeforeRun;
                f.recalibrated = true;
            }
        }
    }

    // El piso solo aprende del ruido: si el frame es voz —o pinta de serlo, como
    // el click aislado que no llegó a abrir onset— congelarlo. Si no, la voz
    // sostenida sube su propio umbral y se auto-silencia.
    if (!m_speech && rms < onTh && !f.recalibrated) {
        const double a = (rms < m_floor) ? m_t.floorDown : m_t.floorUp;
        m_floor += (rms - m_floor) * a;
        if (m_floor < 0.0) m_floor = 0.0;
    }

    f.speech = m_speech;
    f.onset  = m_speech && !wasSpeech;
    return f;
}

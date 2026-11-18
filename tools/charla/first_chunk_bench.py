#!/usr/bin/env python3
"""Tiempo hasta el primer fragmento hablable de Charla (sin audio).
Uso: llama-server con el modelo de Charla en LC_BENCH_URL (default
http://127.0.0.1:18777); `python3 tools/charla/first_chunk_bench.py [pasadas]`.
Compara el MODO VOZ de antes con el de la primera frase corta.

Replica la regla de VoiceController::speakStreaming: la primera oración sale
cuando hay >=12 chars y un fin de oración (.!?… o \n; el punto necesita un
espacio detrás) o, si no, una coma/;/: seguida de espacio a partir de
`clause_min` chars (hoy 40; no corta "3, 4").
"""
import json, sys, time, urllib.request, statistics, re

import os
URL = os.environ.get("LC_BENCH_URL", "http://127.0.0.1:18777") + "/v1/chat/completions"

VOICE = (
    "MODO VOZ (Ingi Charla): todo lo que escribas se convierte en audio con "
    "TTS en tiempo real, oración por oración.\n"
    "- Respondé como en una conversación hablada: 1 a 3 frases cortas, "
    "naturales y directas. Nada de markdown, listas, tablas, emojis, bloques "
    "de código ni URLs largas: no se pueden escuchar. Si hay mucho detalle, "
    "decí lo esencial y ofrecé ampliar.\n"
    "- Si es charla o una pregunta que sabés responder, contestá directo sin "
    "tools: la latencia importa.\n"
    "- El texto del usuario viene de reconocimiento de voz y puede tener "
    "errores; interpretá la intención más probable.\n")
SHORT = (
    "- La primera frase es lo que suena primero: que sea corta (de 3 a 8 "
    "palabras) y ya conteste o encamine la respuesta; el detalle va después.\n")
IDENT = "Sos Ingi, un asistente de voz en español rioplatense que ayuda al usuario con su computadora.\n"

PROMPTS = [
    "¿Qué diferencia hay entre un virus y una bacteria?",
    "Contame un dato curioso del espacio",
    "¿Cómo hago para que el pan casero quede más esponjoso?",
    "Explicame qué es la inflación",
    "¿Qué me recomendás para dormir mejor?",
    "¿Cuál es la capital de Australia?",
    "¿Cuánto es doce por treinta y siete?",
    "Resumime la historia de Roma en pocas palabras",
    "¿Por qué el cielo es azul?",
    "Dame una idea para cenar hoy",
    "¿Qué conviene más, alquilar o comprar una casa?",
    "¿Cómo funciona una heladera?",
]


def sentence_end(t, i):
    c = t[i]
    if c in "!?…\n":
        return True
    if c != ".":
        return False
    return i + 1 < len(t) and t[i + 1].isspace()


def first_chunk_len(t, clause_min):
    cur = 0
    for i in range(len(t)):
        if sentence_end(t, i) and len(t[: i + 1].strip()) >= 12:
            return i + 1
    for i in range(clause_min, len(t) - 1):
        if t[i] in ",;:" and t[i + 1].isspace():
            if i > 0 and t[i - 1].isdigit():
                continue
            if not t[i + 1:].strip():
                return None
            return i + 1
    return None


def run(system, prompt):
    body = {"messages": [{"role": "system", "content": system},
                         {"role": "user", "content": prompt}],
            "stream": True, "max_tokens": 200,
            "chat_template_kwargs": {"enable_thinking": False}}
    req = urllib.request.Request(URL, json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    t0 = time.perf_counter()
    text, stamps, first = "", [], None
    with urllib.request.urlopen(req, timeout=120) as r:
        for raw in r:
            line = raw.decode().strip()
            if not line.startswith("data: ") or line == "data: [DONE]":
                continue
            d = json.loads(line[6:])
            delta = d["choices"][0]["delta"].get("content") or ""
            if not delta:
                continue
            now = time.perf_counter() - t0
            if first is None:
                first = now
            text += delta
            stamps.append((len(text), now))
    return text, stamps, first


def time_to(stamps, n):
    if n is None:
        return None
    for ln, t in stamps:
        # el fragmento se habla cuando llega el delta SIGUIENTE al que cerró
        # la oración (el punto necesita ver el espacio): ln > n
        if ln > n:
            return t
    return stamps[-1][1] if stamps else None


def main():
    reps = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    variants = {"actual": IDENT + VOICE, "corta": IDENT + VOICE + SHORT}
    res = {k: {"40": [], "20": [], "first": [], "words": []} for k in variants}
    # warm
    run(variants["actual"], "Hola")
    for rep in range(reps):
        for p in PROMPTS:
            for name, system in variants.items():
                text, stamps, first = run(system, p)
                for cm in (40, 20):
                    n = first_chunk_len(text, cm)
                    t = time_to(stamps, n)
                    res[name][str(cm)].append((t - first) if t is not None and first else None)
                res[name]["first"].append(first)
                res[name]["words"].append(len(text.split()))
                n = first_chunk_len(text, 40)
                print(f"[{name}] {p[:30]:30s} | {text[:n].strip() if n else text[:60]!r}"
                      f" | resp={len(text.split())}w", flush=True)
    print()
    for name, r in res.items():
        for cm in ("40", "20"):
            vals = [v for v in r[cm] if v is not None]
            miss = len(r[cm]) - len(vals)
            print(f"{name:7s} clause>={cm}: 1er texto→1er fragmento mediana "
                  f"{statistics.median(vals)*1000:.0f} ms, p90 "
                  f"{sorted(vals)[int(len(vals)*0.9)-1]*1000:.0f} ms"
                  f" (sin corte: {miss})")
        print(f"{name:7s} TTFT mediana {statistics.median(r['first'])*1000:.0f} ms, "
              f"largo respuesta mediana {statistics.median(r['words'])} palabras")


if __name__ == "__main__":
    main()

# Flash-Next en Computer Use — 6 oct. 2026

Comparativa nueva de ASTRA IQ3_S calibrado frente a Swift 1.5 IQ3_XXS. Cada perfil completó 216 solicitudes del corpus `computer_use_prompt_order_hard_v1` (24 estados × 3 órdenes × 3 pasadas): ambos obtuvieron 100% de exactitud, validez y seguridad. Swift redujo la mediana de latencia 22,8–23,9% en estas decisiones textuales cortas. No se ejecutaron acciones sobre escritorio, no hubo screenshots y la prueba no mide OCR/UIA ni recuperación E2E.

La variante de prompt `sandwich` falló la compuerta de latencia >5% respecto a `state-first` en ambos perfiles. No se cambia el prompt ni el harness. ASTRA sigue como perfil general recomendado por las corridas repetidas LC-H1; Swift queda como alternativa rápida para decisiones cortas de Computer Use. El empate de exactitud no demuestra superioridad de calidad ni justifica borrar pesos.

Ingi-Charla no se evaluó: Flash-Next no provee ASR/TTS y un corpus de respuestas de texto no mide voz. Para una comparación acústica hacen falta los mismos audios en español, WER/CER, fin de habla a primer audio y uso de recursos.

- Informe y valores: [`artifacts/flashnext-computer-use-20261006/report.md`](../artifacts/flashnext-computer-use-20261006/report.md).
- Recibos crudos: [`astra-iq3s-calibrated.json`](../artifacts/flashnext-computer-use-20261006/astra-iq3s-calibrated.json) y [`swift-iq3xxs.json`](../artifacts/flashnext-computer-use-20261006/swift-iq3xxs.json).
- Protocolo, configuraciones y hashes: [`manifest.json`](../artifacts/flashnext-computer-use-20261006/manifest.json).

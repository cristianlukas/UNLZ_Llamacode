# GPU0 (ASUS RTX 3090): VRAM defectuosa — informe y réplica en Windows

Fecha: 2026-09-27. Detectado en Ubuntu mientras se evaluaba
Qwen3.8-Flash-Next W4A16-FP8PLE (albucino / runtime DominikBucko v0.3.0).

## Resumen

La RTX 3090 **ASUS** en el bus PCIe `01:00.0` (GPU0, slot superior, la que
maneja el monitor) tiene **1.636 palabras de 32 bits con bits clavados en 1** en
su VRAM. La falla es determinística: mismas direcciones físicas en cada
corrida, mismos bits, independiente de la temperatura, de la potencia y del
contenido escrito. La RTX 3090 **PNY** (`03:00.0`, GPU1) da 0 errores con la
misma prueba.

No es PCIe, ni la bifurcación x8/x8, ni drivers, ni la memoria del host: la
prueba que lo demuestra escribe y lee dentro de la GPU, sin tráfico por el bus.

## Placa afectada

| Campo | GPU0 (falla) | GPU1 (sana) |
|---|---|---|
| Bus PCIe | `01:00.0` (root port CPU `00:01.1`) | `03:00.0` (root port CPU `00:01.3`) |
| Marca (subsistema PCI) | **ASUS** `1043:87b3` | PNY `196e:136c` |
| Modelo | ASUS RTX 3090, variante a confirmar (ver paso 1 de Windows) | PNY RTX 3090 |
| GPU | GA102 `10de:2204` rev a1, part `2204-300-A1` | GA102 `10de:2204` rev a1 |
| VBIOS | `94.02.42.00.B4` | `94.02.42.80.1E` |
| InfoROM | `G001.0000.03.03` | — |
| UUID | `GPU-af6de4b3-6497-b7f8-796d-6d69cba422e6` | — |
| Enlace | Gen4 x8 (slot x16 bifurcado; es lo esperado) | Gen4 x8 |
| Overclock | offsets de reloj y memoria = 0 | offsets = 0 |

El subsistema `87b3` no figura en `pci.ids`, y la base de VBIOS de TechPowerUp
bloquea el acceso automático. El modelo comercial (TUF, TUF OC, Strix, etc.) se
confirma con GPU-Z o con la etiqueta de la placa, que además trae el número de
serie para una garantía.

## Evidencia

### Cómo apareció

El runtime de Flash-Next copia los expertos del MoE entre RAM y VRAM y verifica
byte a byte cada copia. En GPU0 siempre cortaba cerca de la capa 32 con
`tiered packed-byte mismatch`; en GPU1 completaba las 48 capas. Con el orden de
GPUs invertido (`CUDA_VISIBLE_DEVICES=1,0`) el fallo **siguió a la placa física
GPU0** y no al rank del proceso. Antes se descartaron: configuración del modelo
(hot80/84/88), filesystem (NTFS y ext4), swap (28 y 64 GiB) y presión de RAM.

### Test de VRAM dentro de la GPU (sin PCIe)

`tools/vram_integrity_test.py`: llena ~20 GiB con 6 patrones, relee y compara
dentro de la GPU.

| Patrón | GPU0 palabras malas | GPU1 |
|---|---:|---:|
| aleatorio A | 1.636 | 0 |
| aleatorio B | 1.636 | 0 |
| `0x55AA55AA` | 1.636 | 0 |
| `0x2A55AA55` | 1.636 | 0 |
| **todo unos** | **0** | 0 |
| todo ceros | 1.636 | 0 |

Huella de la falla:

- **Bits clavados en 1: 25, 27, 29 y 31 → máscara `0xAA000000`** en las 1.636
  palabras. Por eso el patrón de todo unos "pasa": esos bits ya valen 1.
- Siempre el byte alto de la palabra: un solo carril de datos (byte lane) de un
  chip GDDR6X o su pista/soldadura.
- Mismas direcciones en procesos distintos, con distinta base virtual. El hash
  de posiciones `e6be70f6d82fe90b` se repitió, así que está atado a direcciones
  físicas.
- En orden de reserva, concentrado entre ≈14 y 16 GiB de la VRAM libre, con
  12 palabras sueltas cerca de ≈3,5 GiB. Son posiciones aproximadas: el driver
  no expone la dirección física exacta.
- No cambió con ventiladores al 100 % y límite de 250 W (8.180 contra 8.157 en
  total antes del cambio). No es térmico.

Complementario: una copia RAM → GPU0 → RAM de 2 GiB devolvió siempre los mismos
12 elementos alterados. Es la misma falla vista desde el bus, no un error de
PCIe. `lspci` marca además `CorrErr+ BadTLP+` en ambas placas: son errores
corregibles del enlace, se repiten en la placa sana y no explican la corrupción.

Artefactos: `artifacts/flashnext-albucino-20260927/vram_integrity_linux_20260927.json`
y los logs `server-*.log` de ese directorio.

## Réplica en Windows

Conviene hacerlo con **el monitor conectado a la PNY o al iGPU**: así GPU0 queda
libre y se puede testear casi toda su VRAM. Con el monitor en GPU0, Windows
reserva parte de la memoria y el test puede no alcanzar la zona dañada.

### 1. Identificar la placa

- **Administrador de dispositivos** → Adaptadores de pantalla → cada RTX 3090 →
  Propiedades → Detalles → *Id. de hardware*. La dañada contiene
  `SUBSYS_87B31043`; la PNY contiene `SUBSYS_136C196E`. En *Información de
  ubicación* debería figurar `bus PCI 1` para la ASUS.
- **GPU-Z** (TechPowerUp): elegí la placa con `Subvendor: ASUS`; anotá *Device
  name*, *BIOS Version* (esperado `94.02.42.00.B4`) y *Bus Interface*. Con el
  botón de guardar BIOS exportás la VBIOS si la necesitás para soporte.
- `nvidia-smi --query-gpu=index,pci.bus_id,name,vbios_version,uuid --format=csv`
  para ubicar la ASUS: `00000000:01:00.0`, UUID `GPU-af6de4b3-…`.

### 2. memtest_vulkan (herramienta independiente, recomendada para garantía)

1. Bajá `memtest_vulkan-*.exe` de las
   [releases](https://github.com/GpuZelenograd/memtest_vulkan/releases). No
   requiere instalación ni admin.
2. Ejecutalo desde una consola. Con dos GPUs muestra una lista: elegí la de
   `Bus=0x01` (ASUS) escribiendo su número.
3. Dejalo **al menos 6 minutos** y cortalo con `Ctrl+C`.
4. Esperado en la ASUS: `Error found. Mode ...` con estadísticas de bits
   concentradas en los bits altos (25/27/29/31). Esperado en la PNY:
   `memtest_vulkan: no any errors, testing PASSed.`
5. Guardá la salida completa (captura o `memtest_vulkan.exe > asus.txt`) como
   evidencia.

### 3. El mismo test de este informe (PyTorch)

En PowerShell, desde la carpeta del repo:

```powershell
py -3.12 -m venv $env:TEMP\vramtest
& $env:TEMP\vramtest\Scripts\python.exe -m pip install torch --index-url https://download.pytorch.org/whl/cu126
& $env:TEMP\vramtest\Scripts\python.exe tools\vram_integrity_test.py --reserve-mib 1024 --json $env:USERPROFILE\Desktop\vram_windows.json
```

- Usa el orden por bus PCI (`CUDA_DEVICE_ORDER=PCI_BUS_ID`), igual que
  `nvidia-smi`: GPU0 = ASUS.
- Tarda segundos. Sale con código 1 si alguna GPU falla.
- Resultado que replica Linux: `[FAIL] GPU0 ... bus=1`, **1.636 palabras por
  patrón** (menos si Windows reservó la zona alta), `all_ones` sin errores y
  `stuck_mask=0xaa000000`. `[PASS] GPU1 ... bus=3`.
- Si GPU0 da `PASS` con el monitor conectado ahí, repetí con el monitor en la
  PNY: la zona dañada está alta y puede haber quedado reservada.

### 4. Temperatura de memoria (opcional)

En Linux no se lee la temperatura de la GDDR6X; en Windows sí.
**HWiNFO64** → Sensors → *GPU Memory Junction Temperature* de la ASUS durante
memtest_vulkan. La falla no depende del calor, pero el dato sirve para el
servicio técnico: más de ~100 °C sostenidos indica pads gastados.

## Qué hacer

1. **Garantía/RMA con ASUS**, si sigue vigente (número de serie en la etiqueta).
   Adjuntá la salida de memtest_vulkan y este informe.
2. **Reparación de placa**: la falla está en un solo carril de un chip, que es
   el caso típico de reemplazo de un módulo GDDR6X en un servicio técnico con
   estación de reballing. Las GeForce no tienen el remapeo de filas de las
   placas de datacenter: no hay arreglo por software.
3. **Mientras tanto**: cualquier carga que ocupe la zona alta de la VRAM de
   GPU0 puede corromperse sin aviso (pesos, KV cache). Los perfiles de una GPU
   conviene correrlos en GPU1 (PNY). Los perfiles dual-GPU que ya dieron bien
   (SOL: HE0 1/1, HE20 20/20, BCB8 8/8, ADV 10/10 con graders corregidos, el 2026-09-27) no garantizan
   que no haya degradación silenciosa en otras distribuciones de memoria.
4. Repetir `tools/vram_integrity_test.py` después de cualquier reparación antes
   de volver a confiar en GPU0.

## Fuentes

- [memtest_vulkan (GitHub)](https://github.com/GpuZelenograd/memtest_vulkan) y su
  [Readme](https://github.com/GpuZelenograd/memtest_vulkan/blob/main/Readme.md):
  uso en Windows, formato de errores, 6 minutos mínimos.
- [GIGAZINE: guía de memtest_vulkan](https://gigazine.net/gsc_news/en/20260621-gpu-vram-check-memtest-vulkan/)
- [Registros de error por placa (discusiones de memtest_vulkan)](https://github.com/GpuZelenograd/memtest_vulkan/discussions/categories/card-specific-memtest_vulkan-error-logs)
- [ASUS TUF RTX 3090 OC: soporte y BIOS](https://www.asus.com/motherboards-components/graphics-cards/tuf-gaming/tuf-rtx3090-o24g-gaming/helpdesk_bios?model2Name=TUF-RTX3090-O24G-GAMING)
- Runtime donde apareció: [DominikBucko/qwen38-flash-next-2x3090](https://github.com/DominikBucko/qwen38-flash-next-2x3090)

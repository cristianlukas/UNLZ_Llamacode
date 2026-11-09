# 3090 HELPER (Ubuntu)

`3090 HELPER` es una aplicación de bandeja independiente de LlamaCode. La
instalación habilita un verificador systemd de una sola ejecución en cada boot
y el ícono de bandeja se abre al iniciar la sesión gráfica. La bandeja repite
el chequeo cada 30 segundos. El icono queda verde sólo si las tres
verificaciones pasan; ante cualquier dato ausente, incompatibilidad o fallo
queda rojo.

1. **Reserva VRAM:** servicio de systemd habilitado y activo para el UUID de la
   ASUS, estado `protected`, todos los marcos esperados retenidos, cero
   pendientes y versión del worker igual a la del driver.
2. **P2P:** inventario confirma las RTX 3090 ASUS/PNY esperadas y
   `nvidia-smi topo -p2p r` y `w` informan `OK` en ambas direcciones.
3. **gpu-unlock:** módulo cargado, `targets` efectivos y línea de kernel
   solicitan únicamente `0000:01:00.0,0000:03:00.0`, y el journal del boot
   actual confirma `gpu_unlock: unlocked` en ambas PCI. Esta evidencia se
   busca en todo el journal del boot actual; el recorte de 500 líneas se usa
   sólo para los diagnósticos recientes y no puede ocultar un desbloqueo que
   ocurrió al iniciar.

En cada boot, `3090-helper-verify-boot.service` espera hasta 30 segundos a que
NVIDIA publique las GPU y registra el informe completo en el journal y en
`/var/log/3090-helper/repair.log`; el servicio queda `failed` si alguna
protección no pasa. Así la comprobación ocurre aunque nadie haya iniciado
sesión gráfica. La bandeja muestra el estado vivo y ofrece el mismo detalle.

Al hacer clic en el ícono se abre el menú con el estado general y los tres
checks individuales: reserva VRAM, P2P y `gpu-unlock`. Cada check muestra un
ícono verde o rojo, el resultado en texto y el detalle como ayuda emergente; el
menú actualiza el diagnóstico al abrirse. Al seleccionar un check o hacer doble
clic en el ícono se abre el diagnóstico completo. El menú también permite
ver/copiar un informe y **Relanzar arreglos**.
La interfaz se auto inicia como el usuario de la sesión gráfica; no necesita
privilegios de administrador. Polkit autoriza sin diálogo únicamente el
ejecutable root-owned `3090-helper-admin repair` dentro de una sesión local
activa. No autoriza una shell ni otros programas o subcomandos; en sesiones
remotas/inactivas la acción se deniega. La acción se niega a actuar si encuentra
un servidor de inferencia, reinicia únicamente la reserva de memoria ASUS y
luego vuelve a comprobar las tres protecciones. P2P y gpu-unlock deben ejecutarse
antes de que NVIDIA inicialice las tarjetas; si faltan en el boot actual, el
botón lo deja en el log y notifica que se necesita reiniciar Ubuntu. No descarga
ni recarga drivers en caliente.

El registro local se guarda en
`~/.local/state/3090-helper/diagnostics.log`; la acción privilegiada agrega un
registro a `/var/log/3090-helper/repair.log`. «Copiar informe para IA» incluye
las comprobaciones del boot actual y el último MB del log local, sin prompts ni
contenido de modelos.

Compilar con `scripts/build-linux.sh Debug`, que produce
`~/.cache/llamacode/build_linux/3090-helper`, e instalar con
`scripts/install-3090-helper.sh`. El instalador habilita el verificador
systemd `3090-helper-verify-boot.service`, la regla Polkit acotada a
`repair` y el acceso gráfico `~/.config/autostart/3090-helper.desktop`. Para comprobar el estado desde una
terminal: `~/.cache/llamacode/build_linux/3090-helper --diagnose`; para leer
el último chequeo de boot: `journalctl -u 3090-helper-verify-boot.service -b`.

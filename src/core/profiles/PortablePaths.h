#pragma once

#include <QString>

// Traducción de rutas de la config compartida Windows/Linux.
//
// Los archivos de perfiles y model roots viven en el volumen NTFS en forma
// canónica de Windows (C:/Users/cristian/..., D:/...). En Linux, con
// LLAMACODE_SHARED_PORTABLE_CONFIG, se traducen al cargar (toRuntime=true) a
// las raíces LLAMACODE_WINDOWS_C_ROOT / LLAMACODE_WINDOWS_D_ROOT y de vuelta al
// guardar (toRuntime=false).
//
// La ida y vuelta TIENE que ser estable: antes "D:/x" volvía como "D://x" y
// cada guardado sumaba barras (D:////////////Models en launches.json).
namespace PortablePaths {

// Pura: las raíces vienen por parámetro. Raíz vacía = esa unidad no se traduce.
QString translate(const QString &value, bool toRuntime,
                  const QString &cRoot, const QString &dRoot);

// Lee el flag y las raíces del entorno. Sin flag (o en Windows) devuelve value.
QString translateFromEnv(const QString &value, bool toRuntime);

} // namespace PortablePaths

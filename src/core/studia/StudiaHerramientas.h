#pragma once
#include <QString>
#include <QVariantList>

// Que herramientas externas hay en esta maquina y que funcion habilita cada una.
//
// StudIA anda sin ninguna: el chat, la busqueda y los modos funcionan igual.
// Lo que se apaga son funciones puntuales —adjuntar bibliografia, graficar,
// dibujar diagramas, leer PDFs escaneados—, y hasta ahora se apagaban EN
// SILENCIO: el estudiante veia que el boton no hacia nada y no tenia como
// saber por que.
//
// Esto le da a la UI la lista completa, con el nombre de la funcion que se
// pierde en cada caso, para poder ofrecerle correr el instalador.
namespace StudiaHerramientas {

struct Herramienta {
    QString id;          // "python", "matplotlib", "mermaid", "tesseract"
    QString nombre;      // como se llama, para mostrar
    QString habilita;    // que deja de andar si falta
    bool    presente = false;
};

QVector<Herramienta> revisar();
// Para QML: lista de mapas con las mismas claves.
QVariantList paraQml();
// Cuantas faltan (0 = todo listo).
int faltantes();

// Ruta del instalador: junto al ejecutable si la app viene empaquetada, o en
// tools/studia/ si se esta corriendo desde el repositorio. "" si no aparece.
QString rutaInstalador();

// Ruta de un script de tools/studia (ingest.py, graficar.py...). Busca junto al
// ejecutable (paquete binario: <exe>/tools/studia), en el checkout relativo al
// build de Windows (build/Release/..) y por último en el árbol de fuente con el
// que se compiló (LC_STUDIA_TOOLS_DIR): en Linux el build vive en ~/.cache y no
// hay ruta relativa que llegue al repo. "" si no aparece.
QString rutaScript(const QString &archivo);

// Intérprete de Python: `python`, `python3` o `py`, el primero que esté en el
// PATH. En Ubuntu sólo existe `python3`. "" si no hay ninguno.
QString python();

// Ejecutable de Tesseract. El instalador de Windows no siempre lo agrega al
// PATH, asi que ademas se lo busca donde suele quedar. "" si no esta.
QString rutaTesseract();

}  // namespace StudiaHerramientas

#include "StudiaEmbedServer.h"

#include <QCoreApplication>
#include <QDir>
#include <QFileInfo>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QProcess>
#include <QStandardPaths>
#include <QTcpSocket>
#include <QTimer>

#include <functional>

namespace {

// Cuantas veces se pregunta si ya esta listo, y cada cuanto. bge-m3 tarda unos
// segundos en cargar (mas desde un disco lento); mas alla de esto es que algo
// no anda.
constexpr int kMaxIntentos = 120;
constexpr int kIntervaloMs = 500;

// ¿Hay algo escuchando en ese puerto? Se usa para no levantar un segundo
// servidor sobre uno que ya esta andando.
bool puertoOcupado(quint16 puerto)
{
    QTcpSocket s;
    s.connectToHost(QStringLiteral("127.0.0.1"), puerto);
    return s.waitForConnected(300);
}

// El primer archivo que matchee, buscando en varias carpetas.
QString primerArchivo(const QStringList &carpetas, const QStringList &patrones)
{
    for (const QString &c : carpetas) {
        QDir d(c);
        if (!d.exists())
            continue;
        const QFileInfoList fs = d.entryInfoList(patrones, QDir::Files, QDir::Name);
        if (!fs.isEmpty())
            return fs.first().absoluteFilePath();
    }
    return QString();
}

}  // namespace


StudiaEmbedServer::StudiaEmbedServer(QObject *parent) : QObject(parent) {}

StudiaEmbedServer::~StudiaEmbedServer() { detener(); }

QString StudiaEmbedServer::url()
{
    return QStringLiteral("http://127.0.0.1:%1").arg(kPuerto);
}

QString StudiaEmbedServer::carpetaEmpaquetada()
{
    return QCoreApplication::applicationDirPath() + QStringLiteral("/StudIA");
}

QString StudiaEmbedServer::rutaModelo()
{
    // Primero el que viaja con la app: es el caso del estudiante que la recibe
    // ya armada. Despues el que haya bajado a mano.
    // LLAMACODE_MODELS_DIR: la biblioteca de modelos de LlamaCode, si se movió.
    // Es donde deja el archivo "Descargar modelo" de StudIA (gestor de
    // descargas de la app), igual que la carpeta por defecto de abajo.
    const QString biblioteca = QString::fromLocal8Bit(qgetenv("LLAMACODE_MODELS_DIR"));
    return primerArchivo({carpetaEmpaquetada() + QStringLiteral("/modelos"),
                          biblioteca,
                          QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation)
                              + QStringLiteral("/models"),
                          QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation)
                              + QStringLiteral("/LlamaCode/models")},
                         {QStringLiteral("bge-m3*.gguf"),
                          QStringLiteral("*embed*.gguf")});
}

namespace {
QList<StudiaEmbedServer::BinarioRegistrado> &binariosRegistrados()
{
    static QList<StudiaEmbedServer::BinarioRegistrado> lista;
    return lista;
}
}  // namespace

void StudiaEmbedServer::setBinariosRegistrados(const QList<BinarioRegistrado> &binarios)
{
    binariosRegistrados() = binarios;
}

QString StudiaEmbedServer::elegirBinarioRegistrado(const QList<BinarioRegistrado> &binarios)
{
    auto primero = [&](const std::function<bool(const BinarioRegistrado &)> &ok) {
        for (const BinarioRegistrado &b : binarios)
            if (!b.ruta.isEmpty() && QFileInfo(b.ruta).isFile() && ok(b))
                return b.ruta;
        return QString();
    };
    QString r = primero([](const BinarioRegistrado &b) {
        return b.backend.compare(QLatin1String("cpu"), Qt::CaseInsensitive) == 0; });
    if (r.isEmpty())
        r = primero([](const BinarioRegistrado &b) {
            return b.variante.compare(QLatin1String("official"), Qt::CaseInsensitive) == 0; });
    if (r.isEmpty())
        r = primero([](const BinarioRegistrado &) { return true; });
    return r;
}

QString StudiaEmbedServer::rutaBinario()
{
#ifdef Q_OS_WIN
    const QString exeName = QStringLiteral("llama-server.exe");
#else
    const QString exeName = QStringLiteral("llama-server");
#endif
    // El que instala LlamaCode queda en tools/llama.cpp-install-<fecha>/extract.
    // Se toma el mas reciente por nombre, que lleva la fecha adelante.
    const QString tools =
        QStandardPaths::writableLocation(QStandardPaths::AppDataLocation)
        + QStringLiteral("/tools");
    QDir d(tools);
    if (d.exists()) {
        const QStringList inst = d.entryList({QStringLiteral("llama.cpp-install-*")},
                                             QDir::Dirs, QDir::Name | QDir::Reversed);
        for (const QString &i : inst) {
            const QString exe = tools + QLatin1Char('/') + i
                                + QStringLiteral("/extract/") + exeName;
            if (QFileInfo::exists(exe))
                return exe;
        }
    }
    // Junto al ejecutable, para una copia portable.
    const QString local = QCoreApplication::applicationDirPath()
                          + QLatin1Char('/') + exeName;
    if (QFileInfo::exists(local))
        return local;
    const QString registrado = elegirBinarioRegistrado(binariosRegistrados());
    if (!registrado.isEmpty())
        return registrado;
    return QStandardPaths::findExecutable(QStringLiteral("llama-server"));
}

void StudiaEmbedServer::marcar(bool activo, const QString &motivo)
{
    if (m_activo == activo && m_motivo == motivo)
        return;
    m_activo = activo;
    m_motivo = motivo;
    emit estadoCambiado();
    if (activo)
        emit listo();
}

void StudiaEmbedServer::iniciar()
{
    if (m_activo || m_proc || m_externo)
        return;

    // Ya hay uno andando (el .bat, o una corrida anterior): se usa ese. Levantar
    // otro sobre el mismo puerto fallaria y dejaria un proceso zombi. Puede
    // estar todavia cargando el modelo: se espera a que /health diga 200.
    if (puertoOcupado(kPuerto)) {
        m_externo = true;
        m_intentos = 0;
        comprobarSalud();
        return;
    }

    const QString modelo = rutaModelo();
    if (modelo.isEmpty()) {
        marcar(false, QStringLiteral("Falta el modelo de embeddings (bge-m3). "
                                     "La búsqueda funciona igual, por palabras."));
        return;
    }
    const QString binario = rutaBinario();
    if (binario.isEmpty()) {
        marcar(false, QStringLiteral("Falta llama-server para la búsqueda semántica. "
                                     "La búsqueda funciona igual, por palabras."));
        return;
    }

    m_proc = new QProcess(this);
    m_proc->setProgram(binario);
    // --pooling cls es el que corresponde a bge-m3. Con otro el servidor
    // responde igual pero los vectores son peores, y nada lo avisa.
    // --n-gpu-layers 0: en CPU, para no pelearle la VRAM al modelo de chat.
    m_proc->setArguments({
        QStringLiteral("--host"), QStringLiteral("127.0.0.1"),
        QStringLiteral("--port"), QString::number(kPuerto),
        QStringLiteral("--model"), modelo,
        QStringLiteral("--embeddings"),
        QStringLiteral("--pooling"), QStringLiteral("cls"),
        QStringLiteral("--ctx-size"), QStringLiteral("8192"),
        QStringLiteral("--batch-size"), QStringLiteral("2048"),
        QStringLiteral("--ubatch-size"), QStringLiteral("2048"),
        QStringLiteral("--n-gpu-layers"), QStringLiteral("0"),
    });
    m_proc->setProcessChannelMode(QProcess::MergedChannels);

    connect(m_proc, &QProcess::finished, this, [this](int code, QProcess::ExitStatus) {
        if (m_proc) { m_proc->deleteLater(); m_proc = nullptr; }
        if (m_activo || code != 0)
            marcar(false, QStringLiteral("El servidor de búsqueda semántica se cerró."));
    });
    connect(m_proc, &QProcess::errorOccurred, this, [this](QProcess::ProcessError) {
        marcar(false, QStringLiteral("No se pudo iniciar el servidor de búsqueda semántica."));
    });

    m_proc->start();
    m_intentos = 0;
    QTimer::singleShot(kIntervaloMs, this, &StudiaEmbedServer::comprobarSalud);
}

void StudiaEmbedServer::comprobarSalud()
{
    if (m_activo)
        return;
    if (!m_proc && !m_externo) {         // se cayo mientras cargaba
        marcar(false, m_motivo);
        return;
    }
    // llama-server abre el puerto ANTES de cargar el modelo y mientras tanto
    // contesta 503. Con "puerto abierto = listo" la vectorizacion arrancaba en
    // esa ventana, fallaba la conexion y el indice quedaba sin semantica.
    // Async: un servidor en el mismo hilo (los tests) no podria contestar.
    if (!m_red)
        m_red = new QNetworkAccessManager(this);
    QNetworkRequest req(QUrl(url() + QStringLiteral("/health")));
    req.setTransferTimeout(2000);
    QNetworkReply *r = m_red->get(req);
    connect(r, &QNetworkReply::finished, this, [this, r] {
        r->deleteLater();
        if (m_activo || (!m_proc && !m_externo))
            return;
        if (r->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt() == 200) {
            m_externo = false;
            marcar(true, QString());
            return;
        }
        if (++m_intentos >= kMaxIntentos) {
            m_externo = false;
            marcar(false, QStringLiteral("El servidor de búsqueda semántica tardó demasiado "
                                         "en arrancar."));
            return;
        }
        QTimer::singleShot(kIntervaloMs, this, &StudiaEmbedServer::comprobarSalud);
    });
}

void StudiaEmbedServer::detener()
{
    m_externo = false;
    if (!m_proc)
        return;
    QProcess *p = m_proc;
    m_proc = nullptr;
    p->disconnect(this);
    p->terminate();
    if (!p->waitForFinished(3000))
        p->kill();
    p->deleteLater();
    m_activo = false;
}

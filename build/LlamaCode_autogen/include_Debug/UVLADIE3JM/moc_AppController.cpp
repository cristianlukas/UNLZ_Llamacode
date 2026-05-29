/****************************************************************************
** Meta object code from reading C++ file 'AppController.h'
**
** Created by: The Qt Meta Object Compiler version 68 (Qt 6.8.3)
**
** WARNING! All changes made in this file will be lost!
*****************************************************************************/

#include "../../../../src/AppController.h"
#include <QtNetwork/QSslError>
#include <QtCore/qmetatype.h>

#include <QtCore/qtmochelpers.h>

#include <memory>


#include <QtCore/qxptype_traits.h>
#if !defined(Q_MOC_OUTPUT_REVISION)
#error "The header file 'AppController.h' doesn't include <QObject>."
#elif Q_MOC_OUTPUT_REVISION != 68
#error "This file was generated using the moc from 6.8.3. It"
#error "cannot be used with the include files from this version of Qt."
#error "(The moc has changed too much.)"
#endif

#ifndef Q_CONSTINIT
#define Q_CONSTINIT
#endif

QT_WARNING_PUSH
QT_WARNING_DISABLE_DEPRECATED
QT_WARNING_DISABLE_GCC("-Wuseless-cast")
namespace {
struct qt_meta_tag_ZN13AppControllerE_t {};
} // unnamed namespace


#ifdef QT_MOC_HAS_STRINGDATA
static constexpr auto qt_meta_stringdata_ZN13AppControllerE = QtMocHelpers::stringData(
    "AppController",
    "serverRunningChanged",
    "",
    "serverLogChanged",
    "activeLaunchIdChanged",
    "effectiveProfileChanged",
    "setupStateChanged",
    "installingOfficialBinaryChanged",
    "officialBinaryInstallStatusChanged",
    "officialBinaryInstallLogChanged",
    "officialBinaryInstallFinished",
    "success",
    "message",
    "binaryPath",
    "serverError",
    "smokeTestFinished",
    "passed",
    "output",
    "languageChanged",
    "harnessStatusChanged",
    "harnessInstallFinished",
    "adapter",
    "agentRunningChanged",
    "agentLogChanged",
    "startServer",
    "launchProfileId",
    "stopServer",
    "computeEffectiveProfile",
    "clearLog",
    "copyToClipboard",
    "text",
    "installOfficialBinary",
    "cancelOfficialBinaryInstall",
    "smokeTestServer",
    "smokeTestRunning",
    "resolveFlag",
    "binaryId",
    "flag",
    "version",
    "l",
    "key",
    "lf",
    "arg1",
    "readSetting",
    "QVariant",
    "defaultValue",
    "writeSetting",
    "value",
    "isHarnessInstalled",
    "installHarness",
    "startAgent",
    "stopAgent",
    "sendToAgent",
    "clearAgentLog",
    "agentNativeLogDir",
    "openAgentLogDir",
    "binaryRegistry",
    "BinaryRegistry*",
    "rootRegistry",
    "ModelRootRegistry*",
    "modelCatalog",
    "ModelCatalog*",
    "profileManager",
    "ProfileManager*",
    "serverRunning",
    "serverLog",
    "activeLaunchId",
    "effectiveProfile",
    "QVariantMap",
    "needsSetup",
    "serverBaseUrl",
    "installingOfficialBinary",
    "officialBinaryInstallStatus",
    "officialBinaryInstallLog",
    "language",
    "langV",
    "agentRunning",
    "agentLog",
    "activeAgentAdapter",
    "agentInTerminal",
    "installingHarness",
    "harnessInstallStatus",
    "harnessCheckV"
);
#else  // !QT_MOC_HAS_STRINGDATA
#error "qtmochelpers.h not found or too old."
#endif // !QT_MOC_HAS_STRINGDATA

Q_CONSTINIT static const uint qt_meta_data_ZN13AppControllerE[] = {

 // content:
      12,       // revision
       0,       // classname
       0,    0, // classinfo
      40,   14, // methods
      22,  352, // properties
       0,    0, // enums/sets
       0,    0, // constructors
       0,       // flags
      16,       // signalCount

 // signals: name, argc, parameters, tag, flags, initial metatype offsets
       1,    0,  254,    2, 0x06,   23 /* Public */,
       3,    0,  255,    2, 0x06,   24 /* Public */,
       4,    0,  256,    2, 0x06,   25 /* Public */,
       5,    0,  257,    2, 0x06,   26 /* Public */,
       6,    0,  258,    2, 0x06,   27 /* Public */,
       7,    0,  259,    2, 0x06,   28 /* Public */,
       8,    0,  260,    2, 0x06,   29 /* Public */,
       9,    0,  261,    2, 0x06,   30 /* Public */,
      10,    3,  262,    2, 0x06,   31 /* Public */,
      14,    1,  269,    2, 0x06,   35 /* Public */,
      15,    2,  272,    2, 0x06,   37 /* Public */,
      18,    0,  277,    2, 0x06,   40 /* Public */,
      19,    0,  278,    2, 0x06,   41 /* Public */,
      20,    3,  279,    2, 0x06,   42 /* Public */,
      22,    0,  286,    2, 0x06,   46 /* Public */,
      23,    0,  287,    2, 0x06,   47 /* Public */,

 // methods: name, argc, parameters, tag, flags, initial metatype offsets
      24,    1,  288,    2, 0x02,   48 /* Public */,
      26,    0,  291,    2, 0x02,   50 /* Public */,
      27,    1,  292,    2, 0x02,   51 /* Public */,
      28,    0,  295,    2, 0x02,   53 /* Public */,
      29,    1,  296,    2, 0x02,   54 /* Public */,
      31,    0,  299,    2, 0x02,   56 /* Public */,
      32,    0,  300,    2, 0x02,   57 /* Public */,
      33,    1,  301,    2, 0x02,   58 /* Public */,
      34,    0,  304,    2, 0x102,   60 /* Public | MethodIsConst  */,
      35,    2,  305,    2, 0x102,   61 /* Public | MethodIsConst  */,
      38,    0,  310,    2, 0x102,   64 /* Public | MethodIsConst  */,
      39,    1,  311,    2, 0x102,   65 /* Public | MethodIsConst  */,
      41,    2,  314,    2, 0x102,   67 /* Public | MethodIsConst  */,
      43,    2,  319,    2, 0x102,   70 /* Public | MethodIsConst  */,
      43,    1,  324,    2, 0x122,   73 /* Public | MethodCloned | MethodIsConst  */,
      46,    2,  327,    2, 0x02,   75 /* Public */,
      48,    1,  332,    2, 0x102,   78 /* Public | MethodIsConst  */,
      49,    1,  335,    2, 0x02,   80 /* Public */,
      50,    1,  338,    2, 0x02,   82 /* Public */,
      51,    0,  341,    2, 0x02,   84 /* Public */,
      52,    1,  342,    2, 0x02,   85 /* Public */,
      53,    0,  345,    2, 0x02,   87 /* Public */,
      54,    1,  346,    2, 0x102,   88 /* Public | MethodIsConst  */,
      55,    1,  349,    2, 0x102,   90 /* Public | MethodIsConst  */,

 // signals: parameters
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void, QMetaType::Bool, QMetaType::QString, QMetaType::QString,   11,   12,   13,
    QMetaType::Void, QMetaType::QString,   12,
    QMetaType::Void, QMetaType::Bool, QMetaType::QString,   16,   17,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void, QMetaType::Bool, QMetaType::QString, QMetaType::QString,   11,   21,   12,
    QMetaType::Void,
    QMetaType::Void,

 // methods: parameters
    QMetaType::Void, QMetaType::QString,   25,
    QMetaType::Void,
    QMetaType::Void, QMetaType::QString,   25,
    QMetaType::Void,
    QMetaType::Void, QMetaType::QString,   30,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void, QMetaType::QString,   25,
    QMetaType::Bool,
    QMetaType::QString, QMetaType::QString, QMetaType::QString,   36,   37,
    QMetaType::QString,
    QMetaType::QString, QMetaType::QString,   40,
    QMetaType::QString, QMetaType::QString, QMetaType::QString,   40,   42,
    0x80000000 | 44, QMetaType::QString, 0x80000000 | 44,   40,   45,
    0x80000000 | 44, QMetaType::QString,   40,
    QMetaType::Void, QMetaType::QString, 0x80000000 | 44,   40,   47,
    QMetaType::Bool, QMetaType::QString,   21,
    QMetaType::Void, QMetaType::QString,   21,
    QMetaType::Void, QMetaType::QString,   25,
    QMetaType::Void,
    QMetaType::Void, QMetaType::QString,   30,
    QMetaType::Void,
    QMetaType::QString, QMetaType::QString,   21,
    QMetaType::Void, QMetaType::QString,   21,

 // properties: name, type, flags, notifyId, revision
      56, 0x80000000 | 57, 0x00015409, uint(-1), 0,
      58, 0x80000000 | 59, 0x00015409, uint(-1), 0,
      60, 0x80000000 | 61, 0x00015409, uint(-1), 0,
      62, 0x80000000 | 63, 0x00015409, uint(-1), 0,
      64, QMetaType::Bool, 0x00015001, uint(0), 0,
      65, QMetaType::QString, 0x00015001, uint(1), 0,
      66, QMetaType::QString, 0x00015001, uint(2), 0,
      67, 0x80000000 | 68, 0x00015009, uint(3), 0,
      69, QMetaType::Bool, 0x00015001, uint(4), 0,
      70, QMetaType::QString, 0x00015001, uint(0), 0,
      71, QMetaType::Bool, 0x00015001, uint(5), 0,
      72, QMetaType::QString, 0x00015001, uint(6), 0,
      73, QMetaType::QString, 0x00015001, uint(7), 0,
      74, QMetaType::QString, 0x00015103, uint(11), 0,
      75, QMetaType::Int, 0x00015001, uint(11), 0,
      76, QMetaType::Bool, 0x00015001, uint(14), 0,
      77, QMetaType::QString, 0x00015001, uint(15), 0,
      78, QMetaType::QString, 0x00015001, uint(14), 0,
      79, QMetaType::Bool, 0x00015001, uint(14), 0,
      80, QMetaType::Bool, 0x00015001, uint(12), 0,
      81, QMetaType::QString, 0x00015001, uint(12), 0,
      82, QMetaType::Int, 0x00015001, uint(12), 0,

       0        // eod
};

Q_CONSTINIT const QMetaObject AppController::staticMetaObject = { {
    QMetaObject::SuperData::link<QObject::staticMetaObject>(),
    qt_meta_stringdata_ZN13AppControllerE.offsetsAndSizes,
    qt_meta_data_ZN13AppControllerE,
    qt_static_metacall,
    nullptr,
    qt_incomplete_metaTypeArray<qt_meta_tag_ZN13AppControllerE_t,
        // property 'binaryRegistry'
        QtPrivate::TypeAndForceComplete<BinaryRegistry*, std::true_type>,
        // property 'rootRegistry'
        QtPrivate::TypeAndForceComplete<ModelRootRegistry*, std::true_type>,
        // property 'modelCatalog'
        QtPrivate::TypeAndForceComplete<ModelCatalog*, std::true_type>,
        // property 'profileManager'
        QtPrivate::TypeAndForceComplete<ProfileManager*, std::true_type>,
        // property 'serverRunning'
        QtPrivate::TypeAndForceComplete<bool, std::true_type>,
        // property 'serverLog'
        QtPrivate::TypeAndForceComplete<QString, std::true_type>,
        // property 'activeLaunchId'
        QtPrivate::TypeAndForceComplete<QString, std::true_type>,
        // property 'effectiveProfile'
        QtPrivate::TypeAndForceComplete<QVariantMap, std::true_type>,
        // property 'needsSetup'
        QtPrivate::TypeAndForceComplete<bool, std::true_type>,
        // property 'serverBaseUrl'
        QtPrivate::TypeAndForceComplete<QString, std::true_type>,
        // property 'installingOfficialBinary'
        QtPrivate::TypeAndForceComplete<bool, std::true_type>,
        // property 'officialBinaryInstallStatus'
        QtPrivate::TypeAndForceComplete<QString, std::true_type>,
        // property 'officialBinaryInstallLog'
        QtPrivate::TypeAndForceComplete<QString, std::true_type>,
        // property 'language'
        QtPrivate::TypeAndForceComplete<QString, std::true_type>,
        // property 'langV'
        QtPrivate::TypeAndForceComplete<int, std::true_type>,
        // property 'agentRunning'
        QtPrivate::TypeAndForceComplete<bool, std::true_type>,
        // property 'agentLog'
        QtPrivate::TypeAndForceComplete<QString, std::true_type>,
        // property 'activeAgentAdapter'
        QtPrivate::TypeAndForceComplete<QString, std::true_type>,
        // property 'agentInTerminal'
        QtPrivate::TypeAndForceComplete<bool, std::true_type>,
        // property 'installingHarness'
        QtPrivate::TypeAndForceComplete<bool, std::true_type>,
        // property 'harnessInstallStatus'
        QtPrivate::TypeAndForceComplete<QString, std::true_type>,
        // property 'harnessCheckV'
        QtPrivate::TypeAndForceComplete<int, std::true_type>,
        // Q_OBJECT / Q_GADGET
        QtPrivate::TypeAndForceComplete<AppController, std::true_type>,
        // method 'serverRunningChanged'
        QtPrivate::TypeAndForceComplete<void, std::false_type>,
        // method 'serverLogChanged'
        QtPrivate::TypeAndForceComplete<void, std::false_type>,
        // method 'activeLaunchIdChanged'
        QtPrivate::TypeAndForceComplete<void, std::false_type>,
        // method 'effectiveProfileChanged'
        QtPrivate::TypeAndForceComplete<void, std::false_type>,
        // method 'setupStateChanged'
        QtPrivate::TypeAndForceComplete<void, std::false_type>,
        // method 'installingOfficialBinaryChanged'
        QtPrivate::TypeAndForceComplete<void, std::false_type>,
        // method 'officialBinaryInstallStatusChanged'
        QtPrivate::TypeAndForceComplete<void, std::false_type>,
        // method 'officialBinaryInstallLogChanged'
        QtPrivate::TypeAndForceComplete<void, std::false_type>,
        // method 'officialBinaryInstallFinished'
        QtPrivate::TypeAndForceComplete<void, std::false_type>,
        QtPrivate::TypeAndForceComplete<bool, std::false_type>,
        QtPrivate::TypeAndForceComplete<const QString &, std::false_type>,
        QtPrivate::TypeAndForceComplete<const QString &, std::false_type>,
        // method 'serverError'
        QtPrivate::TypeAndForceComplete<void, std::false_type>,
        QtPrivate::TypeAndForceComplete<const QString &, std::false_type>,
        // method 'smokeTestFinished'
        QtPrivate::TypeAndForceComplete<void, std::false_type>,
        QtPrivate::TypeAndForceComplete<bool, std::false_type>,
        QtPrivate::TypeAndForceComplete<const QString &, std::false_type>,
        // method 'languageChanged'
        QtPrivate::TypeAndForceComplete<void, std::false_type>,
        // method 'harnessStatusChanged'
        QtPrivate::TypeAndForceComplete<void, std::false_type>,
        // method 'harnessInstallFinished'
        QtPrivate::TypeAndForceComplete<void, std::false_type>,
        QtPrivate::TypeAndForceComplete<bool, std::false_type>,
        QtPrivate::TypeAndForceComplete<const QString &, std::false_type>,
        QtPrivate::TypeAndForceComplete<const QString &, std::false_type>,
        // method 'agentRunningChanged'
        QtPrivate::TypeAndForceComplete<void, std::false_type>,
        // method 'agentLogChanged'
        QtPrivate::TypeAndForceComplete<void, std::false_type>,
        // method 'startServer'
        QtPrivate::TypeAndForceComplete<void, std::false_type>,
        QtPrivate::TypeAndForceComplete<const QString &, std::false_type>,
        // method 'stopServer'
        QtPrivate::TypeAndForceComplete<void, std::false_type>,
        // method 'computeEffectiveProfile'
        QtPrivate::TypeAndForceComplete<void, std::false_type>,
        QtPrivate::TypeAndForceComplete<const QString &, std::false_type>,
        // method 'clearLog'
        QtPrivate::TypeAndForceComplete<void, std::false_type>,
        // method 'copyToClipboard'
        QtPrivate::TypeAndForceComplete<void, std::false_type>,
        QtPrivate::TypeAndForceComplete<const QString &, std::false_type>,
        // method 'installOfficialBinary'
        QtPrivate::TypeAndForceComplete<void, std::false_type>,
        // method 'cancelOfficialBinaryInstall'
        QtPrivate::TypeAndForceComplete<void, std::false_type>,
        // method 'smokeTestServer'
        QtPrivate::TypeAndForceComplete<void, std::false_type>,
        QtPrivate::TypeAndForceComplete<const QString &, std::false_type>,
        // method 'smokeTestRunning'
        QtPrivate::TypeAndForceComplete<bool, std::false_type>,
        // method 'resolveFlag'
        QtPrivate::TypeAndForceComplete<QString, std::false_type>,
        QtPrivate::TypeAndForceComplete<const QString &, std::false_type>,
        QtPrivate::TypeAndForceComplete<const QString &, std::false_type>,
        // method 'version'
        QtPrivate::TypeAndForceComplete<QString, std::false_type>,
        // method 'l'
        QtPrivate::TypeAndForceComplete<QString, std::false_type>,
        QtPrivate::TypeAndForceComplete<const QString &, std::false_type>,
        // method 'lf'
        QtPrivate::TypeAndForceComplete<QString, std::false_type>,
        QtPrivate::TypeAndForceComplete<const QString &, std::false_type>,
        QtPrivate::TypeAndForceComplete<const QString &, std::false_type>,
        // method 'readSetting'
        QtPrivate::TypeAndForceComplete<QVariant, std::false_type>,
        QtPrivate::TypeAndForceComplete<const QString &, std::false_type>,
        QtPrivate::TypeAndForceComplete<const QVariant &, std::false_type>,
        // method 'readSetting'
        QtPrivate::TypeAndForceComplete<QVariant, std::false_type>,
        QtPrivate::TypeAndForceComplete<const QString &, std::false_type>,
        // method 'writeSetting'
        QtPrivate::TypeAndForceComplete<void, std::false_type>,
        QtPrivate::TypeAndForceComplete<const QString &, std::false_type>,
        QtPrivate::TypeAndForceComplete<const QVariant &, std::false_type>,
        // method 'isHarnessInstalled'
        QtPrivate::TypeAndForceComplete<bool, std::false_type>,
        QtPrivate::TypeAndForceComplete<const QString &, std::false_type>,
        // method 'installHarness'
        QtPrivate::TypeAndForceComplete<void, std::false_type>,
        QtPrivate::TypeAndForceComplete<const QString &, std::false_type>,
        // method 'startAgent'
        QtPrivate::TypeAndForceComplete<void, std::false_type>,
        QtPrivate::TypeAndForceComplete<const QString &, std::false_type>,
        // method 'stopAgent'
        QtPrivate::TypeAndForceComplete<void, std::false_type>,
        // method 'sendToAgent'
        QtPrivate::TypeAndForceComplete<void, std::false_type>,
        QtPrivate::TypeAndForceComplete<const QString &, std::false_type>,
        // method 'clearAgentLog'
        QtPrivate::TypeAndForceComplete<void, std::false_type>,
        // method 'agentNativeLogDir'
        QtPrivate::TypeAndForceComplete<QString, std::false_type>,
        QtPrivate::TypeAndForceComplete<const QString &, std::false_type>,
        // method 'openAgentLogDir'
        QtPrivate::TypeAndForceComplete<void, std::false_type>,
        QtPrivate::TypeAndForceComplete<const QString &, std::false_type>
    >,
    nullptr
} };

void AppController::qt_static_metacall(QObject *_o, QMetaObject::Call _c, int _id, void **_a)
{
    auto *_t = static_cast<AppController *>(_o);
    if (_c == QMetaObject::InvokeMetaMethod) {
        switch (_id) {
        case 0: _t->serverRunningChanged(); break;
        case 1: _t->serverLogChanged(); break;
        case 2: _t->activeLaunchIdChanged(); break;
        case 3: _t->effectiveProfileChanged(); break;
        case 4: _t->setupStateChanged(); break;
        case 5: _t->installingOfficialBinaryChanged(); break;
        case 6: _t->officialBinaryInstallStatusChanged(); break;
        case 7: _t->officialBinaryInstallLogChanged(); break;
        case 8: _t->officialBinaryInstallFinished((*reinterpret_cast< std::add_pointer_t<bool>>(_a[1])),(*reinterpret_cast< std::add_pointer_t<QString>>(_a[2])),(*reinterpret_cast< std::add_pointer_t<QString>>(_a[3]))); break;
        case 9: _t->serverError((*reinterpret_cast< std::add_pointer_t<QString>>(_a[1]))); break;
        case 10: _t->smokeTestFinished((*reinterpret_cast< std::add_pointer_t<bool>>(_a[1])),(*reinterpret_cast< std::add_pointer_t<QString>>(_a[2]))); break;
        case 11: _t->languageChanged(); break;
        case 12: _t->harnessStatusChanged(); break;
        case 13: _t->harnessInstallFinished((*reinterpret_cast< std::add_pointer_t<bool>>(_a[1])),(*reinterpret_cast< std::add_pointer_t<QString>>(_a[2])),(*reinterpret_cast< std::add_pointer_t<QString>>(_a[3]))); break;
        case 14: _t->agentRunningChanged(); break;
        case 15: _t->agentLogChanged(); break;
        case 16: _t->startServer((*reinterpret_cast< std::add_pointer_t<QString>>(_a[1]))); break;
        case 17: _t->stopServer(); break;
        case 18: _t->computeEffectiveProfile((*reinterpret_cast< std::add_pointer_t<QString>>(_a[1]))); break;
        case 19: _t->clearLog(); break;
        case 20: _t->copyToClipboard((*reinterpret_cast< std::add_pointer_t<QString>>(_a[1]))); break;
        case 21: _t->installOfficialBinary(); break;
        case 22: _t->cancelOfficialBinaryInstall(); break;
        case 23: _t->smokeTestServer((*reinterpret_cast< std::add_pointer_t<QString>>(_a[1]))); break;
        case 24: { bool _r = _t->smokeTestRunning();
            if (_a[0]) *reinterpret_cast< bool*>(_a[0]) = std::move(_r); }  break;
        case 25: { QString _r = _t->resolveFlag((*reinterpret_cast< std::add_pointer_t<QString>>(_a[1])),(*reinterpret_cast< std::add_pointer_t<QString>>(_a[2])));
            if (_a[0]) *reinterpret_cast< QString*>(_a[0]) = std::move(_r); }  break;
        case 26: { QString _r = _t->version();
            if (_a[0]) *reinterpret_cast< QString*>(_a[0]) = std::move(_r); }  break;
        case 27: { QString _r = _t->l((*reinterpret_cast< std::add_pointer_t<QString>>(_a[1])));
            if (_a[0]) *reinterpret_cast< QString*>(_a[0]) = std::move(_r); }  break;
        case 28: { QString _r = _t->lf((*reinterpret_cast< std::add_pointer_t<QString>>(_a[1])),(*reinterpret_cast< std::add_pointer_t<QString>>(_a[2])));
            if (_a[0]) *reinterpret_cast< QString*>(_a[0]) = std::move(_r); }  break;
        case 29: { QVariant _r = _t->readSetting((*reinterpret_cast< std::add_pointer_t<QString>>(_a[1])),(*reinterpret_cast< std::add_pointer_t<QVariant>>(_a[2])));
            if (_a[0]) *reinterpret_cast< QVariant*>(_a[0]) = std::move(_r); }  break;
        case 30: { QVariant _r = _t->readSetting((*reinterpret_cast< std::add_pointer_t<QString>>(_a[1])));
            if (_a[0]) *reinterpret_cast< QVariant*>(_a[0]) = std::move(_r); }  break;
        case 31: _t->writeSetting((*reinterpret_cast< std::add_pointer_t<QString>>(_a[1])),(*reinterpret_cast< std::add_pointer_t<QVariant>>(_a[2]))); break;
        case 32: { bool _r = _t->isHarnessInstalled((*reinterpret_cast< std::add_pointer_t<QString>>(_a[1])));
            if (_a[0]) *reinterpret_cast< bool*>(_a[0]) = std::move(_r); }  break;
        case 33: _t->installHarness((*reinterpret_cast< std::add_pointer_t<QString>>(_a[1]))); break;
        case 34: _t->startAgent((*reinterpret_cast< std::add_pointer_t<QString>>(_a[1]))); break;
        case 35: _t->stopAgent(); break;
        case 36: _t->sendToAgent((*reinterpret_cast< std::add_pointer_t<QString>>(_a[1]))); break;
        case 37: _t->clearAgentLog(); break;
        case 38: { QString _r = _t->agentNativeLogDir((*reinterpret_cast< std::add_pointer_t<QString>>(_a[1])));
            if (_a[0]) *reinterpret_cast< QString*>(_a[0]) = std::move(_r); }  break;
        case 39: _t->openAgentLogDir((*reinterpret_cast< std::add_pointer_t<QString>>(_a[1]))); break;
        default: ;
        }
    }
    if (_c == QMetaObject::IndexOfMethod) {
        int *result = reinterpret_cast<int *>(_a[0]);
        {
            using _q_method_type = void (AppController::*)();
            if (_q_method_type _q_method = &AppController::serverRunningChanged; *reinterpret_cast<_q_method_type *>(_a[1]) == _q_method) {
                *result = 0;
                return;
            }
        }
        {
            using _q_method_type = void (AppController::*)();
            if (_q_method_type _q_method = &AppController::serverLogChanged; *reinterpret_cast<_q_method_type *>(_a[1]) == _q_method) {
                *result = 1;
                return;
            }
        }
        {
            using _q_method_type = void (AppController::*)();
            if (_q_method_type _q_method = &AppController::activeLaunchIdChanged; *reinterpret_cast<_q_method_type *>(_a[1]) == _q_method) {
                *result = 2;
                return;
            }
        }
        {
            using _q_method_type = void (AppController::*)();
            if (_q_method_type _q_method = &AppController::effectiveProfileChanged; *reinterpret_cast<_q_method_type *>(_a[1]) == _q_method) {
                *result = 3;
                return;
            }
        }
        {
            using _q_method_type = void (AppController::*)();
            if (_q_method_type _q_method = &AppController::setupStateChanged; *reinterpret_cast<_q_method_type *>(_a[1]) == _q_method) {
                *result = 4;
                return;
            }
        }
        {
            using _q_method_type = void (AppController::*)();
            if (_q_method_type _q_method = &AppController::installingOfficialBinaryChanged; *reinterpret_cast<_q_method_type *>(_a[1]) == _q_method) {
                *result = 5;
                return;
            }
        }
        {
            using _q_method_type = void (AppController::*)();
            if (_q_method_type _q_method = &AppController::officialBinaryInstallStatusChanged; *reinterpret_cast<_q_method_type *>(_a[1]) == _q_method) {
                *result = 6;
                return;
            }
        }
        {
            using _q_method_type = void (AppController::*)();
            if (_q_method_type _q_method = &AppController::officialBinaryInstallLogChanged; *reinterpret_cast<_q_method_type *>(_a[1]) == _q_method) {
                *result = 7;
                return;
            }
        }
        {
            using _q_method_type = void (AppController::*)(bool , const QString & , const QString & );
            if (_q_method_type _q_method = &AppController::officialBinaryInstallFinished; *reinterpret_cast<_q_method_type *>(_a[1]) == _q_method) {
                *result = 8;
                return;
            }
        }
        {
            using _q_method_type = void (AppController::*)(const QString & );
            if (_q_method_type _q_method = &AppController::serverError; *reinterpret_cast<_q_method_type *>(_a[1]) == _q_method) {
                *result = 9;
                return;
            }
        }
        {
            using _q_method_type = void (AppController::*)(bool , const QString & );
            if (_q_method_type _q_method = &AppController::smokeTestFinished; *reinterpret_cast<_q_method_type *>(_a[1]) == _q_method) {
                *result = 10;
                return;
            }
        }
        {
            using _q_method_type = void (AppController::*)();
            if (_q_method_type _q_method = &AppController::languageChanged; *reinterpret_cast<_q_method_type *>(_a[1]) == _q_method) {
                *result = 11;
                return;
            }
        }
        {
            using _q_method_type = void (AppController::*)();
            if (_q_method_type _q_method = &AppController::harnessStatusChanged; *reinterpret_cast<_q_method_type *>(_a[1]) == _q_method) {
                *result = 12;
                return;
            }
        }
        {
            using _q_method_type = void (AppController::*)(bool , const QString & , const QString & );
            if (_q_method_type _q_method = &AppController::harnessInstallFinished; *reinterpret_cast<_q_method_type *>(_a[1]) == _q_method) {
                *result = 13;
                return;
            }
        }
        {
            using _q_method_type = void (AppController::*)();
            if (_q_method_type _q_method = &AppController::agentRunningChanged; *reinterpret_cast<_q_method_type *>(_a[1]) == _q_method) {
                *result = 14;
                return;
            }
        }
        {
            using _q_method_type = void (AppController::*)();
            if (_q_method_type _q_method = &AppController::agentLogChanged; *reinterpret_cast<_q_method_type *>(_a[1]) == _q_method) {
                *result = 15;
                return;
            }
        }
    }
    if (_c == QMetaObject::RegisterPropertyMetaType) {
        switch (_id) {
        default: *reinterpret_cast<int*>(_a[0]) = -1; break;
        case 0:
            *reinterpret_cast<int*>(_a[0]) = qRegisterMetaType< BinaryRegistry* >(); break;
        case 2:
            *reinterpret_cast<int*>(_a[0]) = qRegisterMetaType< ModelCatalog* >(); break;
        case 1:
            *reinterpret_cast<int*>(_a[0]) = qRegisterMetaType< ModelRootRegistry* >(); break;
        case 3:
            *reinterpret_cast<int*>(_a[0]) = qRegisterMetaType< ProfileManager* >(); break;
        }
    }
    if (_c == QMetaObject::ReadProperty) {
        void *_v = _a[0];
        switch (_id) {
        case 0: *reinterpret_cast< BinaryRegistry**>(_v) = _t->binaryRegistry(); break;
        case 1: *reinterpret_cast< ModelRootRegistry**>(_v) = _t->rootRegistry(); break;
        case 2: *reinterpret_cast< ModelCatalog**>(_v) = _t->modelCatalog(); break;
        case 3: *reinterpret_cast< ProfileManager**>(_v) = _t->profileManager(); break;
        case 4: *reinterpret_cast< bool*>(_v) = _t->serverRunning(); break;
        case 5: *reinterpret_cast< QString*>(_v) = _t->serverLog(); break;
        case 6: *reinterpret_cast< QString*>(_v) = _t->activeLaunchId(); break;
        case 7: *reinterpret_cast< QVariantMap*>(_v) = _t->effectiveProfile(); break;
        case 8: *reinterpret_cast< bool*>(_v) = _t->needsSetup(); break;
        case 9: *reinterpret_cast< QString*>(_v) = _t->serverBaseUrl(); break;
        case 10: *reinterpret_cast< bool*>(_v) = _t->installingOfficialBinary(); break;
        case 11: *reinterpret_cast< QString*>(_v) = _t->officialBinaryInstallStatus(); break;
        case 12: *reinterpret_cast< QString*>(_v) = _t->officialBinaryInstallLog(); break;
        case 13: *reinterpret_cast< QString*>(_v) = _t->language(); break;
        case 14: *reinterpret_cast< int*>(_v) = _t->langV(); break;
        case 15: *reinterpret_cast< bool*>(_v) = _t->agentRunning(); break;
        case 16: *reinterpret_cast< QString*>(_v) = _t->agentLog(); break;
        case 17: *reinterpret_cast< QString*>(_v) = _t->activeAgentAdapter(); break;
        case 18: *reinterpret_cast< bool*>(_v) = _t->agentInTerminal(); break;
        case 19: *reinterpret_cast< bool*>(_v) = _t->installingHarness(); break;
        case 20: *reinterpret_cast< QString*>(_v) = _t->harnessInstallStatus(); break;
        case 21: *reinterpret_cast< int*>(_v) = _t->harnessCheckV(); break;
        default: break;
        }
    }
    if (_c == QMetaObject::WriteProperty) {
        void *_v = _a[0];
        switch (_id) {
        case 13: _t->setLanguage(*reinterpret_cast< QString*>(_v)); break;
        default: break;
        }
    }
}

const QMetaObject *AppController::metaObject() const
{
    return QObject::d_ptr->metaObject ? QObject::d_ptr->dynamicMetaObject() : &staticMetaObject;
}

void *AppController::qt_metacast(const char *_clname)
{
    if (!_clname) return nullptr;
    if (!strcmp(_clname, qt_meta_stringdata_ZN13AppControllerE.stringdata0))
        return static_cast<void*>(this);
    return QObject::qt_metacast(_clname);
}

int AppController::qt_metacall(QMetaObject::Call _c, int _id, void **_a)
{
    _id = QObject::qt_metacall(_c, _id, _a);
    if (_id < 0)
        return _id;
    if (_c == QMetaObject::InvokeMetaMethod) {
        if (_id < 40)
            qt_static_metacall(this, _c, _id, _a);
        _id -= 40;
    }
    if (_c == QMetaObject::RegisterMethodArgumentMetaType) {
        if (_id < 40)
            *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType();
        _id -= 40;
    }
    if (_c == QMetaObject::ReadProperty || _c == QMetaObject::WriteProperty
            || _c == QMetaObject::ResetProperty || _c == QMetaObject::BindableProperty
            || _c == QMetaObject::RegisterPropertyMetaType) {
        qt_static_metacall(this, _c, _id, _a);
        _id -= 22;
    }
    return _id;
}

// SIGNAL 0
void AppController::serverRunningChanged()
{
    QMetaObject::activate(this, &staticMetaObject, 0, nullptr);
}

// SIGNAL 1
void AppController::serverLogChanged()
{
    QMetaObject::activate(this, &staticMetaObject, 1, nullptr);
}

// SIGNAL 2
void AppController::activeLaunchIdChanged()
{
    QMetaObject::activate(this, &staticMetaObject, 2, nullptr);
}

// SIGNAL 3
void AppController::effectiveProfileChanged()
{
    QMetaObject::activate(this, &staticMetaObject, 3, nullptr);
}

// SIGNAL 4
void AppController::setupStateChanged()
{
    QMetaObject::activate(this, &staticMetaObject, 4, nullptr);
}

// SIGNAL 5
void AppController::installingOfficialBinaryChanged()
{
    QMetaObject::activate(this, &staticMetaObject, 5, nullptr);
}

// SIGNAL 6
void AppController::officialBinaryInstallStatusChanged()
{
    QMetaObject::activate(this, &staticMetaObject, 6, nullptr);
}

// SIGNAL 7
void AppController::officialBinaryInstallLogChanged()
{
    QMetaObject::activate(this, &staticMetaObject, 7, nullptr);
}

// SIGNAL 8
void AppController::officialBinaryInstallFinished(bool _t1, const QString & _t2, const QString & _t3)
{
    void *_a[] = { nullptr, const_cast<void*>(reinterpret_cast<const void*>(std::addressof(_t1))), const_cast<void*>(reinterpret_cast<const void*>(std::addressof(_t2))), const_cast<void*>(reinterpret_cast<const void*>(std::addressof(_t3))) };
    QMetaObject::activate(this, &staticMetaObject, 8, _a);
}

// SIGNAL 9
void AppController::serverError(const QString & _t1)
{
    void *_a[] = { nullptr, const_cast<void*>(reinterpret_cast<const void*>(std::addressof(_t1))) };
    QMetaObject::activate(this, &staticMetaObject, 9, _a);
}

// SIGNAL 10
void AppController::smokeTestFinished(bool _t1, const QString & _t2)
{
    void *_a[] = { nullptr, const_cast<void*>(reinterpret_cast<const void*>(std::addressof(_t1))), const_cast<void*>(reinterpret_cast<const void*>(std::addressof(_t2))) };
    QMetaObject::activate(this, &staticMetaObject, 10, _a);
}

// SIGNAL 11
void AppController::languageChanged()
{
    QMetaObject::activate(this, &staticMetaObject, 11, nullptr);
}

// SIGNAL 12
void AppController::harnessStatusChanged()
{
    QMetaObject::activate(this, &staticMetaObject, 12, nullptr);
}

// SIGNAL 13
void AppController::harnessInstallFinished(bool _t1, const QString & _t2, const QString & _t3)
{
    void *_a[] = { nullptr, const_cast<void*>(reinterpret_cast<const void*>(std::addressof(_t1))), const_cast<void*>(reinterpret_cast<const void*>(std::addressof(_t2))), const_cast<void*>(reinterpret_cast<const void*>(std::addressof(_t3))) };
    QMetaObject::activate(this, &staticMetaObject, 13, _a);
}

// SIGNAL 14
void AppController::agentRunningChanged()
{
    QMetaObject::activate(this, &staticMetaObject, 14, nullptr);
}

// SIGNAL 15
void AppController::agentLogChanged()
{
    QMetaObject::activate(this, &staticMetaObject, 15, nullptr);
}
QT_WARNING_POP

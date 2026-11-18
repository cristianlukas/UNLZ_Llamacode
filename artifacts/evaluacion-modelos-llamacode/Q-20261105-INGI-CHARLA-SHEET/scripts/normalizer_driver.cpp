#include "SpeechTextNormalizer.h"
#include <QFile>
#include <QTextStream>
#include <cstdio>
int main(int argc, char **argv) {
    QFile f(argv[1]); f.open(QIODevice::ReadOnly);
    QTextStream in(&f);
    while (!in.atEnd()) {
        const QString line = in.readLine().section(QLatin1Char('\t'), 0, 0);
        std::printf("%s\n", SpeechTextNormalizer::normalize(line).toUtf8().constData());
    }
}

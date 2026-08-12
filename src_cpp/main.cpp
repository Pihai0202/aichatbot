#include <QApplication>
#include <QFont>
#include <QIcon>
#include "MainWindow.h"

int main(int argc, char *argv[]) {
    QApplication app(argc, argv);

    // Set Source Han Sans TC / Noto Sans TC font family globally
    QFont font("Source Han Sans TC");
    font.setFamilies({"Source Han Sans TC", "Source Han Sans TW", "Noto Sans TC", "Microsoft JhengHei", "Segoe UI", "sans-serif"});
    font.setPixelSize(14);
    app.setFont(font);

    // Set App Window Icon from SVG
    app.setWindowIcon(QIcon("assets/icons/logo.svg"));

    MainWindow window;
    window.show();

    return app.exec();
}

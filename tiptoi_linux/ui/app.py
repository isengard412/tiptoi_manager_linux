"""Application entry point for the tiptoi-Manager look-alike desktop app."""

from __future__ import annotations

import sys

from tiptoi_linux.i18n import _
from tiptoi_linux.ui import theme


def main(argv: list[str] | None = None) -> int:
    try:
        from PySide6.QtCore import QLibraryInfo, QLocale, QTimer, QTranslator
        from PySide6.QtGui import QIcon
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print(
            _("error: the GUI requires PySide6 - install with: pip install '.[gui]'"),
            file=sys.stderr,
        )
        return 1

    from tiptoi_linux.gui import ICON_PATH, _PYSIDE6_IMPORT_ERROR

    if _PYSIDE6_IMPORT_ERROR is not None:  # pragma: no cover - same import above already succeeded
        print(str(_PYSIDE6_IMPORT_ERROR), file=sys.stderr)
        return 1

    app = QApplication(sys.argv if argv is None else [sys.argv[0], *argv])
    app.setApplicationName("tiptoi-manager-linux")
    app.setDesktopFileName("tiptoi")
    app.setWindowIcon(QIcon(str(ICON_PATH)))
    app.setStyleSheet(theme.build_style_sheet())

    translator = QTranslator(app)
    if translator.load(
        QLocale.system(), "qtbase", "_", QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    ):
        app.installTranslator(translator)

    from tiptoi_linux.ui.main_window import TiptoiWindow

    window = TiptoiWindow()
    window.show()
    window.start_initial_load()
    QTimer.singleShot(0, window._poll_pen)
    exit_code = app.exec()
    from PySide6.QtCore import QEvent

    app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())

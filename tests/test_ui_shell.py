"""Tests for the tiptoi-Manager look-alike shell (tiptoi_linux.ui)."""

from __future__ import annotations

import os
import time
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtCore import QEvent

    _PYSIDE6_AVAILABLE = True
except ImportError:
    _PYSIDE6_AVAILABLE = False

from tiptoi_linux.catalog import LoadedCatalog, parse_catalog
from tiptoi_linux.pen import Pen, PenSummary

from tests.test_gui import FIXTURE_CSV


def _pump_until_idle(app, job, timeout_s: float = 5.0) -> None:
    deadline = time.monotonic() + timeout_s
    while job.is_running and time.monotonic() < deadline:
        app.processEvents()
    for _ in range(20):
        app.processEvents()
    app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()


@unittest.skipUnless(_PYSIDE6_AVAILABLE, "PySide6 is not installed")
class ShellTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from PySide6.QtWidgets import QApplication

        cls.app = QApplication.instance() or QApplication([])

        from tiptoi_linux.ui import theme

        cls.app.setStyleSheet(theme.build_style_sheet())

    def setUp(self) -> None:
        from tiptoi_linux.gui import Services
        from tiptoi_linux.ui.main_window import TiptoiWindow

        self.catalog = parse_catalog(FIXTURE_CSV)
        self.services = Services(
            load_catalog=lambda **kw: LoadedCatalog(self.catalog),
            find_pen=lambda **kw: Pen(mountpoint=Path("/media/tiptoi"), source="/dev/sdb1"),
            pen_summary=lambda pen, catalog: PenSummary(
                pen=pen,
                free=2 * 1024**3,
                total=8 * 1024**3,
                installed=("Die Eiskoenigin.gme",),
                outdated=[],
            ),
            device_plugged_in=lambda: False,
            device_mounted=lambda: False,
            pen_mount_alive=lambda pen: True,
        )
        self.window = TiptoiWindow(services=self.services)
        self.window._poll_timer.stop()  # keep tests deterministic

    def tearDown(self) -> None:
        self.window.close()

    def test_nav_has_five_entries_in_original_order(self) -> None:
        self.assertEqual(len(self.window._nav._buttons), 5)
        self.assertEqual(self.window._stack.currentIndex(), 0)

    def test_nav_switching_changes_screen(self) -> None:
        self.window._nav.set_current(3)
        self.assertEqual(self.window._stack.currentIndex(), 3)
        self.window._nav.set_current(4)
        self.assertEqual(self.window._stack.currentIndex(), 4)

    def test_initial_load_populates_table_and_count(self) -> None:
        self.window.start_initial_load()
        _pump_until_idle(self.app, self.window._catalog_job)
        self.assertEqual(self.window._model.rowCount(), len(self.catalog.products))
        self.assertIn("product", self.window.download_screen.result_count.text().lower())

    def test_search_filters_table(self) -> None:
        self.window.start_initial_load()
        _pump_until_idle(self.app, self.window._catalog_job)
        self.window.download_screen.search.edit.setText("Eiskoenigin")
        self.assertEqual(self.window._proxy.rowCount(), 1)

    def test_detect_pen_updates_pen_card_and_installed(self) -> None:
        self.window._detect()
        _pump_until_idle(self.app, self.window._pen_job)
        card = self.window._header.pen_card
        self.assertTrue(card.status_pill.text())
        self.assertFalse(card.free_pill.isHidden())
        self.assertEqual(self.window._model._installed, frozenset({"die eiskoenigin.gme"}))

    def test_install_button_requires_pen_and_selection(self) -> None:
        self.window.start_initial_load()
        _pump_until_idle(self.app, self.window._catalog_job)
        self.assertFalse(self.window.download_screen.install_button.isEnabled())
        self.window._detect()
        _pump_until_idle(self.app, self.window._pen_job)
        index = self.window._proxy.index(0, 0)
        self.window.download_screen.grid.setCurrentIndex(index)
        self.assertTrue(self.window.download_screen.install_button.isEnabled())

    def test_pen_card_disconnected_text(self) -> None:
        card = self.window._header.pen_card
        self.assertTrue(card.status_pill.text())  # localized; must not be empty
        self.assertTrue(card.free_pill.isHidden())


if __name__ == "__main__":
    unittest.main()

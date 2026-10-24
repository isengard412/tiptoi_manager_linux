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


@unittest.skipUnless(_PYSIDE6_AVAILABLE, "PySide6 is not installed")
class FirmwareShellTests(unittest.TestCase):
    """The firmware panel/footer react to the pen's .tiptoi.log and the catalog header."""

    @classmethod
    def setUpClass(cls) -> None:
        from PySide6.QtWidgets import QApplication

        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        import tempfile
        from pathlib import Path

        from tiptoi_linux.gui import Services
        from tiptoi_linux.pen import FirmwareInfo
        from tiptoi_linux.ui.main_window import TiptoiWindow

        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.pen_dir = Path(self.tmp.name)
        (self.pen_dir / ".tiptoi.log").write_text(
            "serialNumber=987654321\nfirmwareversion=6GE020\n", encoding="utf-8"
        )
        pen = Pen(mountpoint=self.pen_dir, source=None)
        services = Services(
            load_catalog=lambda **kw: LoadedCatalog(parse_catalog(FIXTURE_CSV)),
            find_pen=lambda **kw: pen,
            pen_summary=lambda p, catalog: PenSummary(
                pen=p, free=0, total=0, installed=(), outdated=[]
            ),
            device_plugged_in=lambda: False,
            device_mounted=lambda: False,
            pen_mount_alive=lambda p: True,
        )
        self.window = TiptoiWindow(services=services)
        self.window._poll_timer.stop()
        self.window._firmware_info = FirmwareInfo(
            version="6GE027", checksum=1, url="https://example.invalid/x.upd"
        )

    def _connect(self) -> None:
        from tests.test_gui import _pump_until_idle

        self.window._detect()
        _pump_until_idle(self.app, self.window._pen_job)

    def test_update_button_offered_when_versions_differ(self) -> None:
        self._connect()
        button = self.window.firmware_panel.update_button
        self.assertTrue(button.isEnabled())
        self.assertIn("6GE027", button.text())

    def test_footer_shows_serial_and_firmware(self) -> None:
        self._connect()
        info = self.window._footer.info.text()
        self.assertIn("987654321", info)
        self.assertIn("6GE020", info)

    def test_pending_update_file_disables_button(self) -> None:
        (self.pen_dir / "update.upd").write_bytes(b"x")
        self._connect()
        self.assertFalse(self.window.firmware_panel.update_button.isEnabled())

    def test_same_version_disables_button(self) -> None:
        from tiptoi_linux.pen import FirmwareInfo

        self.window._firmware_info = FirmwareInfo(
            version="6GE020", checksum=1, url="https://example.invalid/x.upd"
        )
        self._connect()
        self.assertFalse(self.window.firmware_panel.update_button.isEnabled())


@unittest.skipUnless(_PYSIDE6_AVAILABLE, "PySide6 is not installed")
class UpdateChainTests(unittest.TestCase):
    """'Update all outdated titles' installs each outdated product in sequence."""

    @classmethod
    def setUpClass(cls) -> None:
        from PySide6.QtWidgets import QApplication

        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        import tempfile
        from pathlib import Path

        from tiptoi_linux.gui import Services
        from tiptoi_linux.pen import Pen
        from tiptoi_linux.ui.main_window import TiptoiWindow

        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.pen_dir = Path(self.tmp.name)
        # a .gme whose embedded version date (20190101) is older than the catalog (20190929)
        header = b"\0" * 0x20 + b"WissenQuizzenTiere 20190101\0"
        (self.pen_dir / "WissenQuizzenTiere.gme").write_bytes(header)
        pen = Pen(mountpoint=self.pen_dir, source=None)
        self.installed: list[str] = []
        services = Services(
            load_catalog=lambda **kw: LoadedCatalog(parse_catalog(FIXTURE_CSV)),
            find_pen=lambda **kw: pen,
            install_title=lambda p, product, progress=None: self.installed.append(product.name),
            device_plugged_in=lambda: False,
            device_mounted=lambda: False,
            pen_mount_alive=lambda p: True,
        )
        self.window = TiptoiWindow(services=services)
        self.window._poll_timer.stop()

    def test_chain_installs_outdated_product(self) -> None:
        from tests.test_gui import _pump_until_idle

        self.window.start_initial_load()
        _pump_until_idle(self.app, self.window._catalog_job)
        self.window._detect()
        _pump_until_idle(self.app, self.window._pen_job)
        self.assertTrue(self.window.update_outdated_button.isEnabled())

        self.window._start_update_outdated()
        _pump_until_idle(self.app, self.window._pen_job)
        self.assertEqual(self.installed, ["WissenQuizzenTiere"])
        self.assertEqual(self.window._update_queue, [])
        self.assertFalse(self.window._update_chain_active)


if __name__ == "__main__":
    unittest.main()

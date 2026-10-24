"""The tiptoi-Manager look-alike main window.

Reuses the proven machinery from tiptoi_linux.gui (Services, BackgroundJob,
ProductTableModel, PenPanel, connection state machine) inside the new shell:
orange header with pen card, left nav rail, stacked screens, footer.
"""

from __future__ import annotations

import webbrowser
from pathlib import Path
from typing import TypeVar

from PySide6.QtCore import QModelIndex, QSortFilterProxyModel, Qt, QTimer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QListView,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from tiptoi_linux import __version__
from tiptoi_linux.catalog import LoadedCatalog, Product, cache_path
from tiptoi_linux.gui import (
    POLL_INTERVAL_MS,
    Column,
    Connected,
    ConnectionState,
    BackgroundJob,
    PenPanel,
    Services,
    _PHASE_STATUS_TEXT,
    next_poll_action,
    PollAction,
)
from tiptoi_linux.i18n import _, ngettext
from tiptoi_linux.pen import FIRMWARE_FILE_NAME, Pen, PenSummary, Phase, read_pen_log
from tiptoi_linux.streams import percent
from tiptoi_linux.ui import catalog as catalog_screen_module
from tiptoi_linux.ui import theme, tiles, widgets

T = TypeVar("T")

PRIVACY_URL = "https://assets.ravensburger.com/legal/privacy/tiptoi_desktop/privacy_german.html"
TERMS_URL = "https://assets.ravensburger.com/legal/terms/tiptoi_desktop/terms_german.html"
FAQ_URL = "https://service.ravensburger.de/tiptoi%C2%AE/Produkte_FAQs"
SUPPORT_URL = "https://service.ravensburger.de/tiptoi%C2%AE/tiptoi%C2%AE_Audiodateien"
STATION_URL = "https://tiptoi.de/ladestation"
WLAN_URL = "https://tiptoi.de/wlan"

NAV_DOWNLOAD, NAV_CATALOG, NAV_AUDIOBOOKS, NAV_PEN, NAV_HELP = range(5)


def version_text() -> str:
    return _("unofficial tiptoi Manager for Linux {version}").format(version=__version__)


class DownloadScreen(QWidget):
    """Search + product tile grid + install action, like the original download screen."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.search = widgets.SearchBar(_("Search for a product name…"))
        self.search.edit.setAccessibleName(_("Search products"))

        self.result_count = QLabel("")
        self.result_count.setObjectName("ResultCount")

        self.grid = QListView()
        self.grid.setObjectName("productGrid")
        self.grid.setViewMode(QListView.ViewMode.IconMode)
        self.grid.setResizeMode(QListView.ResizeMode.Adjust)
        self.grid.setWrapping(True)
        self.grid.setUniformItemSizes(True)
        self.grid.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.grid.setSpacing(0)
        self.grid.setFrameShape(QListView.Shape.NoFrame)
        self.grid.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.grid.setAccessibleName(_("Products"))
        self.grid.setItemDelegate(tiles.TileDelegate(self.grid))

        self.install_button = widgets.pill_button(_("Install on pen"), primary=True)
        self.install_button.setAccessibleName(_("Install selected"))
        self.install_button.setEnabled(False)

        row = QHBoxLayout()
        row.setSpacing(10)
        row.addWidget(self.search, stretch=1)
        row.addWidget(self.install_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 12)
        layout.addLayout(row)
        layout.addWidget(self.result_count)
        layout.addWidget(self.grid, stretch=1)


class PlaceholderScreen(QWidget):
    """A screen that is announced but not implemented yet."""

    def __init__(self, headline: str, note: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        title = QLabel(headline)
        title.setObjectName("ResultCount")
        body = QLabel(note)
        body.setObjectName("Placeholder")
        body.setWordWrap(True)
        body.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        layout = QVBoxLayout(self)
        layout.addStretch()
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(body, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch()


class HelpScreen(QWidget):
    """Link list mirroring the original help screen (opens the browser)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 22, 28, 22)
        layout.setSpacing(12)

        title = QLabel(_("Help and information"))
        title.setObjectName("ResultCount")
        layout.addWidget(title)

        entries = (
            (_("tiptoi FAQ"), FAQ_URL),
            (_("Manual audio file download"), SUPPORT_URL),
            (_("tiptoi charging station"), STATION_URL),
            (_("tiptoi Wi-Fi pen"), WLAN_URL),
            (_("Privacy"), PRIVACY_URL),
            (_("Legal notice"), TERMS_URL),
        )
        for text, url in entries:
            button = QPushButton(f"• {text}")
            button.setObjectName("FooterLink")
            button.setStyleSheet("font-size: 14px; text-decoration: none; padding: 4px;")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _checked=False, link=url: webbrowser.open(link))
            layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addStretch()
        note = QLabel(
            _(
                "This is an unofficial, community-managed tool. It is not affiliated with "
                "or endorsed by Ravensburger. \"tiptoi\" is a trademark of Ravensburger AG."
            )
        )
        note.setObjectName("Placeholder")
        note.setWordWrap(True)
        layout.addWidget(note)


class TiptoiWindow(QMainWindow):
    def __init__(
        self,
        services: Services | None = None,
        *,
        portal_loader=None,
        cover_fetcher=None,
        firmware_downloader=None,
        firmware_installer=None,
    ) -> None:
        super().__init__()
        self._services = services if services is not None else Services()
        if portal_loader is None:
            from tiptoi_linux.enrich import fetch_portal_index

            portal_loader = fetch_portal_index
        if cover_fetcher is None:
            from tiptoi_linux.enrich import download_cover

            cover_fetcher = download_cover
        if firmware_downloader is None:
            from tiptoi_linux.pen import download_firmware

            def firmware_downloader(info, *, progress):
                return download_firmware(info, progress=progress)

        if firmware_installer is None:
            from tiptoi_linux.pen import install_firmware as _install_firmware

            def firmware_installer(pen, path, *, info):
                _install_firmware(pen, path, info=info)

        self._portal_loader = portal_loader
        self._cover_fetcher = cover_fetcher
        self._firmware_downloader = firmware_downloader
        self._firmware_installer = firmware_installer
        self.setWindowTitle(_("unofficial tiptoi Manager"))
        self.resize(1100, 700)

        self._model = tiles.CoverTableModel()
        self._proxy = QSortFilterProxyModel(self)
        self._proxy.setSourceModel(self._model)
        self._proxy.setFilterKeyColumn(Column.NAME)
        self._proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

        # --- shell -------------------------------------------------------
        self._header = widgets.HeaderBar()
        self._nav = widgets.NavRail()
        self._footer = widgets.FooterBar(version_text())
        self._footer.privacy_link.clicked.connect(lambda: webbrowser.open(PRIVACY_URL))
        self._footer.imprint_link.clicked.connect(lambda: webbrowser.open(TERMS_URL))

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setFixedWidth(180)
        self._progress_bar.setVisible(False)
        self._footer.layout().insertWidget(5, self._progress_bar)

        self.download_screen = DownloadScreen()
        self.download_screen.grid.setModel(self._proxy)
        self.download_screen.search.textChanged.connect(self._proxy.setFilterFixedString)
        self.download_screen.install_button.clicked.connect(self._start_install_selected)
        self.download_screen.grid.selectionModel().selectionChanged.connect(
            self._update_install_button_enabled
        )
        self.download_screen.grid.doubleClicked.connect(self._on_grid_double_clicked)

        self.catalog_screen = catalog_screen_module.CatalogScreen()
        self._catalog_proxy = catalog_screen_module.CatalogProxy(self)
        self.catalog_screen.use_model(self._model, self._catalog_proxy)
        self.catalog_screen.install_button.clicked.connect(self._start_install_catalog_selected)
        self.catalog_screen.on_selection_changed = self._update_install_button_enabled
        self.catalog_screen.grid.doubleClicked.connect(
            lambda _index: self._start_install_catalog_selected()
            if self.catalog_screen.install_button.isEnabled()
            else None
        )

        self.pen_panel = PenPanel()
        self.pen_panel.detect_button.clicked.connect(lambda: self._detect())
        self.pen_panel.choose_button.clicked.connect(self._choose_pen_folder)
        self.pen_panel.delete_button.clicked.connect(self._start_delete_selected)
        self.pen_panel.installed_list.itemSelectionChanged.connect(self._update_delete_button_enabled)
        self.firmware_panel = widgets.FirmwarePanel()
        self.firmware_panel.update_requested.connect(self._start_firmware_update)
        pen_screen_host = QWidget()
        pen_layout = QVBoxLayout(pen_screen_host)
        pen_layout.setContentsMargins(18, 16, 18, 12)
        pen_layout.addWidget(self.firmware_panel)
        pen_layout.addWidget(self.pen_panel)

        self._stack = QStackedWidget()
        self._stack.addWidget(self.download_screen)
        self._stack.addWidget(self.catalog_screen)
        self._stack.addWidget(
            PlaceholderScreen(
                _("Audiobooks and songs"),
                _("Buying and licensing audiobooks requires a Ravensburger account and is not "
                  "supported by this unofficial manager."),
            )
        )
        self._stack.addWidget(pen_screen_host)
        self._stack.addWidget(HelpScreen())
        self._nav.currentChanged.connect(self._stack.setCurrentIndex)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self._nav)
        body.addWidget(self._stack, stretch=1)

        central = QWidget()
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)
        central_layout.addWidget(self._header)
        central_layout.addLayout(body, stretch=1)
        central_layout.addWidget(self._footer)
        self.setCentralWidget(central)

        # --- options menu --------------------------------------------------
        self._header.options_menu.addAction(_("Refresh catalog"), self._start_refresh)
        self._header.options_menu.addAction(_("Detect pen"), lambda: self._detect())

        # --- state machine (ported from the legacy MainWindow) ---------------
        self._catalog_job = BackgroundJob(self)
        self._catalog_job.finished.connect(self._on_catalog_job_finished)
        self._close_when_idle = False

        self._cover_job = BackgroundJob(self)
        self._cover_job.finished.connect(self._on_cover_job_finished)

        self._pen_job = BackgroundJob(self)
        self._pen_job.finished.connect(self._on_pen_job_finished)
        self._progress_phase: Phase | None = None
        self._summary_refresh_pending = False

        self._catalog: LoadedCatalog | None = None
        self._connection: ConnectionState | Connected = ConnectionState.DISCONNECTED
        self._firmware_info = None  # FirmwareInfo | None
        self._pen_fields: dict[str, str] = {}

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(POLL_INTERVAL_MS)
        self._poll_timer.timeout.connect(self._poll_pen)
        self._poll_timer.start()

        self._update_pen_card()

    # --- status ------------------------------------------------------------

    def _show_status(self, message: str) -> None:
        self._footer.progress.setText(message)

    # --- catalog -------------------------------------------------------------

    def _start_load(self, *, force: bool) -> None:
        services = self._services
        if not self._catalog_job.start(
            lambda progress: services.load_catalog(force=force, allow_stale=not force),
            self._on_loaded,
            self._show_error,
        ):
            return
        self._show_status(_("Loading…"))

    def _start_refresh(self) -> None:
        self._start_load(force=True)

    def start_initial_load(self) -> None:
        self._start_load(force=False)

    def _on_catalog_job_finished(self) -> None:
        if self._close_when_idle and not self._catalog_job.is_running and not self._cover_job.is_running:
            self._close_when_idle = False
            self.close()
            from PySide6.QtWidgets import QApplication

            QApplication.quit()

    def _on_cover_job_finished(self) -> None:
        if self._close_when_idle and not self._catalog_job.is_running and not self._cover_job.is_running:
            self._close_when_idle = False
            self.close()
            from PySide6.QtWidgets import QApplication

            QApplication.quit()

    def _on_loaded(self, loaded: LoadedCatalog) -> None:
        self._catalog = loaded
        self._model.set_products(loaded.catalog.products)
        n = len(loaded.catalog.products)
        if loaded.stale_reason is not None:
            text = ngettext(
                "{n} product (offline — cached copy)",
                "{n} products (offline — cached copy)",
                n,
            ).format(n=n)
        else:
            text = ngettext("{n} product", "{n} products", n).format(n=n)
        self.download_screen.result_count.setText(text)
        self._show_status(_("Catalog cached at {path}").format(path=cache_path()))
        self._load_firmware_info()
        self._start_cover_refresh()
        if self._pen_job.is_running:
            self._summary_refresh_pending = True
        elif isinstance(self._connection, Connected):
            self._refresh_pen_summary(self._connection.pen)

    def _show_error(self, message: str) -> None:
        self._show_status(_("error: {message}").format(message=message))
        QMessageBox.warning(self, _("unofficial tiptoi Manager"), message)

    # --- covers --------------------------------------------------------------

    def _start_cover_refresh(self) -> None:
        """Map products to article numbers and download covers into the cache.

        Covers are cosmetic: any failure here is quiet (status line only).
        """
        if self._catalog is None or self._cover_job.is_running:
            return
        products = self._catalog.catalog.products
        portal_loader = self._portal_loader
        cover_fetcher = self._cover_fetcher

        def task(progress):
            from tiptoi_linux.enrich import EnrichError

            try:
                index = portal_loader()
            except EnrichError:
                return None
            mapping: dict[str, str] = {}
            for product in products:
                item = index.item_for(product.name)
                if item:
                    mapping[product.name] = item
            done = 0
            for name, item in mapping.items():
                try:
                    cover_fetcher(item)
                except EnrichError:
                    pass
                done += 1
                progress(Phase.DOWNLOAD, done, len(mapping))
            return mapping, index

        def succeeded(outcome) -> None:
            self._progress_bar.setVisible(False)
            if not outcome:
                return
            mapping, index = outcome
            if mapping:
                self._model.set_items(mapping)
                categories = sorted(set(index.categories.values()))
                self.catalog_screen.set_categories(categories)
                self._catalog_proxy.set_mapping(mapping, index.categories)

        def failed(message: str) -> None:
            self._progress_bar.setVisible(False)
            self._show_status(_("error: {message}").format(message=message))

        if not self._cover_job.start(
            task, succeeded, failed, on_progress=self._on_cover_progress
        ):
            return
        self._progress_bar.setRange(0, 0)
        self._progress_bar.setVisible(True)
        self._show_status(_("Loading product covers…"))

    def _on_cover_progress(self, phase: Phase, done: int, total: int | None) -> None:
        if total:
            if self._progress_bar.maximum() != 100:
                self._progress_bar.setRange(0, 100)
            self._progress_bar.setValue(percent(done, total))

    # --- selection -----------------------------------------------------------

    def _selected_product(self) -> Product | None:
        indexes = self.download_screen.grid.selectionModel().selectedIndexes()
        if not indexes:
            return None
        source_index = self._proxy.mapToSource(indexes[0])
        return self._model.product_at(source_index.row())

    def _on_grid_double_clicked(self, index: QModelIndex) -> None:
        if not index.isValid():
            return
        if self.download_screen.install_button.isEnabled():
            self._start_install_selected()

    def _pen(self) -> Pen | None:
        return self._connection.pen if isinstance(self._connection, Connected) else None

    def _pen_idle(self) -> bool:
        return self._pen() is not None and not self._pen_job.is_running

    def _update_install_button_enabled(self) -> None:
        has_selection = bool(self.download_screen.grid.selectionModel().selectedIndexes())
        self.download_screen.install_button.setEnabled(self._pen_idle() and has_selection)
        catalog_selection = bool(self.catalog_screen.grid.selectionModel().selectedIndexes())
        self.catalog_screen.install_button.setEnabled(self._pen_idle() and catalog_selection)

    def _update_delete_button_enabled(self) -> None:
        has_selection = bool(self.pen_panel.installed_list.selectedItems())
        self.pen_panel.delete_button.setEnabled(self._pen_idle() and has_selection)

    def _update_action_buttons_enabled(self) -> None:
        running = self._pen_job.is_running
        self.pen_panel.detect_button.setEnabled(not running)
        self.pen_panel.choose_button.setEnabled(not running)
        self._update_install_button_enabled()
        self._update_delete_button_enabled()

    # --- pen operations --------------------------------------------------------

    def _run_task(
        self,
        task,
        on_success,
        busy_message: str | None,
        *,
        on_failure=None,
    ) -> None:
        if not self._pen_job.start(
            task,
            on_success,
            on_failure if on_failure is not None else self._show_error,
            on_progress=self._on_task_progress,
        ):
            return
        self._progress_phase = None
        if busy_message is not None:
            self._show_status(busy_message)
        self._update_action_buttons_enabled()

    def _run_pen_op(
        self,
        op,
        busy_message: str | None,
        *,
        describe=None,
        then=None,
        on_failure=None,
        changes_pen: bool = False,
        announce: bool = True,
    ) -> None:
        catalog = self._catalog.catalog if self._catalog is not None else None
        services = self._services

        def task(progress):
            pen, result = op(progress)
            return result, services.pen_summary(pen, catalog)

        def succeeded(outcome):
            result, summary = outcome
            self._on_pen_refreshed(
                summary, message=describe(result) if describe else None, announce=announce
            )
            if then is not None:
                then(result)

        def failed(message: str) -> None:
            if changes_pen and isinstance(self._connection, Connected):
                self._summary_refresh_pending = True
            (on_failure if on_failure is not None else self._show_error)(message)

        self._run_task(task, succeeded, busy_message, on_failure=failed)

    def _detect(self, override: Path | None = None, *, quiet: bool = False) -> None:
        services = self._services
        self._run_pen_op(
            lambda progress: (services.find_pen(override=override), None),
            _("Detecting pen…"),
            on_failure=lambda message: self._on_detect_failed(message, quiet=quiet),
        )

    def _choose_pen_folder(self) -> None:
        from PySide6.QtWidgets import QFileDialog

        result = QFileDialog.getExistingDirectory(self, _("Choose pen folder"))
        if not result:
            return
        self._detect(Path(result))

    def _on_detect_failed(self, message: str, *, quiet: bool = False) -> None:
        self._clear_pen(self._state_without_pen())
        if quiet:
            self._show_status(message)
        else:
            self._show_error(message)

    def _start_install_selected(self) -> None:
        self._install_product(self._selected_product())

    def _start_install_catalog_selected(self) -> None:
        self._install_product(self.catalog_screen.selected_product())

    def _install_product(self, product: Product | None) -> None:
        pen = self._pen()
        if pen is None or product is None:
            return
        services = self._services

        def install(progress):
            services.install_title(pen, product, progress=progress)
            return pen, None

        self._run_pen_op(
            install,
            _("Installing {name}…").format(name=product.name),
            describe=lambda _result: _("Installed {name} — verified on the pen").format(
                name=product.name
            ),
            changes_pen=True,
        )

    def _start_delete_selected(self) -> None:
        pen = self._pen()
        names = self.pen_panel.selected_names()
        if pen is None or not names:
            return
        reply = QMessageBox.question(
            self,
            _("unofficial tiptoi Manager"),
            _("Delete these titles from the pen?\n\n{names}").format(names="\n".join(names)),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        services = self._services

        def delete(progress):
            return pen, sum(services.delete_title(pen, name) for name in names)

        n = len(names)
        self._run_pen_op(
            delete,
            ngettext("Deleting {n} title…", "Deleting {n} titles…", n).format(n=n),
            describe=lambda freed: ngettext(
                "Deleted {n} title, freed {size}", "Deleted {n} titles, freed {size}", n
            ).format(n=n, size=format_data_size(freed)),
            changes_pen=True,
        )

    def _refresh_pen_summary(self, pen: Pen, *, quiet: bool = False) -> None:
        if self._pen_job.is_running:
            self._summary_refresh_pending = True
            return
        self._run_pen_op(
            lambda progress: (pen, None),
            None if quiet else _("Pen ready"),
            announce=not quiet,
        )

    def _on_pen_job_finished(self) -> None:
        self._progress_bar.setVisible(False)
        self._update_action_buttons_enabled()
        self._update_firmware_panel()
        if self._summary_refresh_pending:
            self._summary_refresh_pending = False
            if isinstance(self._connection, Connected):
                self._refresh_pen_summary(self._connection.pen, quiet=True)

    def _on_task_progress(self, phase: Phase, done: int, total: int | None) -> None:
        if not self._progress_bar.isVisible():
            self._progress_bar.setVisible(True)
        if phase != self._progress_phase:
            self._progress_phase = phase
            status_text = _PHASE_STATUS_TEXT[phase]
            self._progress_bar.setFormat(f"{status_text} %p%")
            self._show_status(status_text)
        if total:
            if self._progress_bar.maximum() != 100:
                self._progress_bar.setRange(0, 100)
            self._progress_bar.setValue(percent(done, total))
        elif self._progress_bar.maximum() != 0:
            self._progress_bar.setRange(0, 0)

    # --- connection state -------------------------------------------------------

    def _on_pen_refreshed(
        self, summary: PenSummary, *, message: str | None = None, announce: bool = True
    ) -> None:
        self._connection = Connected(summary.pen)
        self.pen_panel.show_summary(summary)
        self._model.set_installed(summary.installed)
        self._pen_fields = read_pen_log(summary.pen)
        self._update_action_buttons_enabled()
        self._update_pen_card()
        self._update_firmware_panel()
        self._update_footer_info()
        if announce:
            self._show_status(message if message is not None else _("Pen ready"))

    def _update_pen_card(self) -> None:
        from PySide6.QtCore import QLocale

        card = self._header.pen_card
        if isinstance(self._connection, Connected):
            summary_free = self.pen_panel.space_bar.format()
            card.set_state(
                disconnected=False,
                free_text=None if summary_free == "—" else summary_free,
                connected_text=_("Connected"),
            )
        elif self._connection is ConnectionState.PLUGGED_IN_UNMOUNTED:
            card.set_state(
                disconnected=False,
                connected_text=_("Plugged in, not mounted"),
            )
            card.status_pill.setStyleSheet(
                f"background: {theme.ICON_ORANGE}; color: {theme.FRAME_TEAL};"
            )
        elif self._connection is ConnectionState.SAFELY_UNMOUNTED:
            card.set_state(disconnected=False, unplugged_text=_("Unmounted — safe to unplug"))
        else:
            card.set_state(disconnected=True)

    def _clear_pen(self, state: ConnectionState) -> None:
        self._connection = state
        self.pen_panel.reset()
        self._model.set_installed(())
        self._pen_fields = {}
        self._update_action_buttons_enabled()
        self._update_pen_card()
        self._update_firmware_panel()
        self._update_footer_info()

    def _state_without_pen(self) -> ConnectionState:
        if self._services.device_plugged_in():
            return ConnectionState.PLUGGED_IN_UNMOUNTED
        return ConnectionState.DISCONNECTED

    # --- firmware ------------------------------------------------------------

    _FIRMWARE_LOG_KEYS = ("firmwareversion", "firmware", "fw", "version")
    _SERIAL_LOG_KEYS = ("serialnumber", "serial", "sn")

    def _load_firmware_info(self) -> None:
        from tiptoi_linux.pen import parse_firmware_info

        try:
            text = cache_path().read_text(encoding="latin-1")
        except OSError:
            self._firmware_info = None
            return
        self._firmware_info = parse_firmware_info(text)

    def _log_field(self, keys: tuple[str, ...]) -> str | None:
        for key, value in self._pen_fields.items():
            if key.casefold() in keys and value:
                return value
        return None

    def _update_firmware_panel(self) -> None:
        connected = isinstance(self._connection, Connected)
        pending = False
        if connected:
            try:
                pending = (self._connection.pen.mountpoint / FIRMWARE_FILE_NAME).exists()
            except OSError:
                pending = False
        self.firmware_panel.show_state(
            pen_version=self._log_field(self._FIRMWARE_LOG_KEYS) if connected else None,
            latest_version=self._firmware_info.version if self._firmware_info else None,
            pending=pending,
            busy=self._pen_job.is_running,
        )

    def _update_footer_info(self) -> None:
        parts = [_("unofficial tiptoi Manager for Linux {version}").format(version=__version__)]
        if isinstance(self._connection, Connected):
            serial = self._log_field(self._SERIAL_LOG_KEYS)
            firmware = self._log_field(self._FIRMWARE_LOG_KEYS)
            if serial:
                parts.append(_("tiptoi® pen {serial}").format(serial=serial))
            if firmware:
                parts.append(_("Firmware-Version {version}").format(version=firmware))
        self._footer.info.setText(" · ".join(parts))

    def _start_firmware_update(self) -> None:
        pen = self._pen()
        info = self._firmware_info
        if pen is None or info is None or self._pen_job.is_running:
            return
        box = QMessageBox(
            QMessageBox.Icon.Question,
            _("A new firmware version is available"),
            _(
                "A new firmware version is available for your tiptoi pen.\n\n"
                "Do you want to update it now?"
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            self,
        )
        box.button(QMessageBox.StandardButton.Yes).setText(_("Update"))
        box.button(QMessageBox.StandardButton.No).setText(_("Not now"))
        if box.exec() != QMessageBox.StandardButton.Yes:
            return

        downloader = self._firmware_downloader
        installer = self._firmware_installer

        def task(progress):
            path = downloader(info, progress=progress)
            installer(pen, path, info=info)
            return path

        self._run_task(
            task,
            self._on_firmware_installed,
            _("Downloading firmware update…"),
        )

    def _on_firmware_installed(self, result: object) -> None:
        QMessageBox.information(
            self,
            _("Finish the firmware update"),
            _(
                "Please disconnect the pen from the computer and switch it on to complete "
                "the update. Only do this with sufficiently charged batteries, otherwise "
                "the update cannot run.\n\nWatch for the spoken instructions after "
                "switching the pen on; never remove the batteries while the update runs. "
                "Once the update is complete the pen announces it by voice."
            ),
        )
        if isinstance(self._connection, Connected):
            self._refresh_pen_summary(self._connection.pen, quiet=True)

    def _poll_pen(self) -> None:
        action = next_poll_action(
            self._connection,
            job_running=self._pen_job.is_running,
            device_plugged_in=self._services.device_plugged_in,
            device_mounted=self._services.device_mounted,
            pen_mount_alive=self._services.pen_mount_alive,
        )
        if action is PollAction.PEN_LOST:
            self._clear_pen(ConnectionState.DISCONNECTED)
            self._show_status(_("Pen disconnected"))
        elif action is PollAction.DEVICE_GONE:
            self._clear_pen(ConnectionState.DISCONNECTED)
        elif action is PollAction.DETECT:
            self._detect(quiet=True)

    def closeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if self._pen_job.is_running:
            event.ignore()
            QMessageBox.information(
                self, _("unofficial tiptoi Manager"), _("Please wait until the pen operation finishes.")
            )
            return
        self._poll_timer.stop()
        self._catalog_job.stop(0)
        self._cover_job.stop(0)
        if self._catalog_job.is_running or self._cover_job.is_running:
            self._close_when_idle = True
            self.hide()
            event.ignore()
            return
        super().closeEvent(event)


def format_data_size(freed: int) -> str:
    from PySide6.QtCore import QLocale

    return QLocale().formattedDataSize(freed)

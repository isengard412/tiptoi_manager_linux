"""Product detail overlay, mirroring the original's product_detail_overlay.

A dimmed scrim with a centered white card: large cover, name, version,
category, install action and a link to the service portal.
"""

from __future__ import annotations

import webbrowser

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from tiptoi_linux.catalog import Product
from tiptoi_linux.i18n import _
from tiptoi_linux.ui import theme, widgets

PORTAL_PRODUCT_URL = "https://service.ravensburger.de/Special:Search?tags={item}"


class DetailOverlay(QWidget):
    """Covers its parent widget with a scrim; click outside the card or press Esc to close."""

    closed = Signal()
    install_requested = Signal(object)  # Product

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("DetailOverlay")
        self.hide()
        self._product: Product | None = None
        self._item: str | None = None

        self._card = QWidget()
        self._card.setObjectName("DetailCard")
        self._card.setFixedWidth(760)

        self.cover = QLabel()
        self.cover.setFixedSize(260, 300)
        self.cover.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.title = QLabel()
        self.title.setObjectName("DetailTitle")
        self.title.setWordWrap(True)

        self.category_label = QLabel()
        self.category_label.setObjectName("DetailCategory")

        self.version_label = QLabel()
        self.version_label.setObjectName("FooterInfo")

        self.state_label = QLabel("")
        self.state_label.setObjectName("FooterInfo")

        self.install_button = widgets.pill_button(_("Install on pen"), primary=True)
        self.install_button.clicked.connect(self._install_clicked)

        self.portal_link = widgets.pill_button(_("More information"))
        self.portal_link.clicked.connect(self._open_portal)

        close_button = QPushButton("×")
        close_button.setObjectName("DetailClose")
        close_button.setFixedSize(30, 30)
        close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        close_button.clicked.connect(self.hide_overlay)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        buttons.addWidget(self.install_button)
        buttons.addWidget(self.portal_link)
        buttons.addStretch()

        info = QVBoxLayout()
        info.setSpacing(8)
        info.addWidget(self.title)
        info.addWidget(self.category_label)
        info.addWidget(self.version_label)
        info.addWidget(self.state_label)
        info.addSpacing(10)
        info.addLayout(buttons)
        info.addStretch()

        header = QHBoxLayout()
        header.addLayout(info, stretch=1)
        header.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignTop)

        card_layout = QHBoxLayout(self._card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(18)
        card_layout.addWidget(self.cover)
        card_layout.addLayout(header, stretch=1)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addStretch()
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(self._card)
        row.addStretch()
        outer.addLayout(row)
        outer.addStretch()

    # --- public API ------------------------------------------------------------

    def show_product(
        self,
        product: Product,
        *,
        item: str | None,
        category: str | None,
        pixmap,
        installed: bool,
        can_install: bool,
    ) -> None:
        self._product = product
        self._item = item
        self.title.setText(product.name.replace("_", " "))
        self.version_label.setText(_("Version: {version}").format(version=product.version))
        self.category_label.setText(category or _("Uncategorized"))
        if pixmap is not None and not pixmap.isNull():
            self.cover.setPixmap(
                pixmap.scaled(
                    self.cover.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        else:
            self.cover.setText("")
        self.state_label.setText(_("Installed on the pen") if installed else "")
        self.install_button.setText(_("Installed") if installed else _("Install on pen"))
        self.install_button.setEnabled(can_install and not installed)
        self.setGeometry(self.parentWidget().rect())
        self.show()
        self.raise_()

    def hide_overlay(self) -> None:
        was_visible = not self.isHidden()
        self.hide()
        if was_visible:
            self.closed.emit()

    # --- events ------------------------------------------------------------

    def paintEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(30, 40, 50, 130))
        painter.end()

    def resizeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if self.parentWidget() is not None:
            self.setGeometry(self.parentWidget().rect())
        super().resizeEvent(event)

    def mousePressEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if event.button() == Qt.MouseButton.LeftButton and not self._card.geometry().contains(event.pos()):
            self.hide_overlay()
            return
        super().mousePressEvent(event)

    def keyPressEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if event.key() == Qt.Key.Key_Escape:
            self.hide_overlay()
            return
        super().keyPressEvent(event)

    # --- actions ------------------------------------------------------------

    def _install_clicked(self) -> None:
        if self._product is not None:
            self.install_requested.emit(self._product)

    def _open_portal(self) -> None:
        if self._item:
            webbrowser.open(PORTAL_PRODUCT_URL.format(item=self._item))

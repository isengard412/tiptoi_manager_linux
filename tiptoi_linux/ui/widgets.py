"""Reusable shell widgets: header with pen card, nav rail, search bar, footer."""

from __future__ import annotations

import webbrowser

from PySide6.QtCore import QSize, QRectF, Signal, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from tiptoi_linux.i18n import _
from tiptoi_linux.ui import icons, theme

NAV_ENTRIES: tuple[tuple[str, str, str], ...] = (
    # (icon key, label, accessible name) - order mirrors the original navigation bar.
    # "\n" splits the label into two lines like the original nav rail.
    ("download", _("Load audio\nfiles"), "download"),
    ("catalog", _("Browse product\ncatalog"), "catalog"),
    ("audiobooks", _("Buy audiobooks\nand songs"), "audiobooks"),
    ("pen", _("Manage pen\nand content"), "pen"),
    ("help", _("Help and\ninformation"), "help"),
)


def pill_button(text: str, *, primary: bool = False) -> QPushButton:
    button = QPushButton(text)
    button.setProperty("buttonRole", "primary" if primary else "secondary")
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    return button


class PenCard(QFrame):
    """Header card showing pen name, connection state and free space."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("PenCard")

        self.title = QLabel(_("Your pen"))
        self.title.setObjectName("PenCardTitle")

        self.status_pill = QLabel(_("Not connected"))
        self.status_pill.setObjectName("PenStatusPill")
        self.status_pill.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.free_pill = QLabel("—")
        self.free_pill.setObjectName("PenFreePill")
        self.free_pill.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.free_pill.hide()

        self.pen_icon = QLabel()
        self.pen_icon.setPixmap(icons.pen_device_icon().pixmap(34, 34))

        text_col = QVBoxLayout()
        text_col.setSpacing(3)
        text_col.addWidget(self.title)
        text_col.addWidget(self.status_pill)
        text_col.addWidget(self.free_pill)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.addLayout(text_col)
        layout.addWidget(self.pen_icon)

        self.set_state(disconnected=True)

    def set_state(
        self,
        *,
        disconnected: bool,
        free_text: str | None = None,
        connected_text: str | None = None,
        unplugged_text: str | None = None,
    ) -> None:
        """Update the pills. Green when connected, orange when plugged-but-unmounted,
        gray when nothing is connected."""
        if unplugged_text is not None:
            self.status_pill.setText(unplugged_text)
            self.status_pill.setStyleSheet(f"background: {theme.ICON_ORANGE}; color: {theme.FRAME_TEAL};")
            self.free_pill.hide()
        elif disconnected:
            self.status_pill.setText(_("Not connected"))
            self.status_pill.setStyleSheet(f"background: #C9CDD3; color: {theme.BG_WHITE};")
            self.free_pill.hide()
        else:
            self.status_pill.setText(connected_text or _("Connected"))
            self.status_pill.setStyleSheet(f"background: {theme.ICON_GREEN}; color: {theme.FRAME_TEAL};")
            if free_text:
                self.free_pill.setText(free_text)
                self.free_pill.show()
            else:
                self.free_pill.hide()


class HeaderBar(QWidget):
    """Orange header: wordmark, pen card, options menu."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("HeaderBar")
        self.setFixedHeight(86)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # Own identity mark: the app icon + its name, no trademark wordmark.
        icon_label = QLabel()
        icon_label.setPixmap(icons.app_icon().pixmap(48, 48))
        icon_label.setAccessibleName("tiptoi")
        name = QLabel(_("tiptoi Manager"))
        name.setObjectName("AppName")
        sub = QLabel(_("unofficial · for Linux"))
        sub.setObjectName("LogoSub")

        text_col = QVBoxLayout()
        text_col.setSpacing(0)
        text_col.addWidget(name)
        text_col.addWidget(sub)

        logo_block = QHBoxLayout()
        logo_block.setSpacing(10)
        logo_block.addWidget(icon_label)
        logo_block.addLayout(text_col)
        logo_block.addStretch()

        self.pen_card = PenCard()

        self.options_button = QPushButton(_("Options"))
        self.options_button.setObjectName("OptionsButton")
        self.options_menu = QMenu(self.options_button)
        self.options_button.setMenu(self.options_menu)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 0, 18, 0)
        layout.addLayout(logo_block)
        layout.addStretch()
        layout.addWidget(self.pen_card)
        layout.addSpacing(10)
        layout.addWidget(self.options_button)

    def paintEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(self.rect())

        gradient = QLinearGradient(rect.topLeft(), rect.topRight())
        gradient.setColorAt(0, QColor(theme.HEADER_ORANGE))
        gradient.setColorAt(1, QColor(theme.HEADER_ORANGE_SOFT))
        painter.fillRect(rect, QBrush(gradient))

        # white swoosh sweeping across the header, like the original
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(theme.BG_WHITE))
        swoosh = QPainterPath()
        swoosh.moveTo(0, rect.height())
        swoosh.cubicTo(
            rect.width() * 0.35,
            rect.height() * 0.55,
            rect.width() * 0.65,
            rect.height() * 1.05,
            rect.width(),
            rect.height() * 0.42,
        )
        swoosh.lineTo(rect.width(), rect.height())
        swoosh.closeSubpath()
        painter.drawPath(swoosh)

        # thin brand-orange arc above the swoosh
        pen = QPen(QColor(theme.BRAND_ORANGE))
        pen.setWidthF(3.0)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        arc = QPainterPath()
        arc.moveTo(0, rect.height() - 6)
        arc.cubicTo(
            rect.width() * 0.35,
            rect.height() * 0.42,
            rect.width() * 0.65,
            rect.height() * 0.92,
            rect.width(),
            rect.height() * 0.32,
        )
        painter.drawPath(arc)
        painter.end()


class NavRail(QWidget):
    """Left navigation with the five round-icon entries of the original."""

    currentChanged = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("NavRail")
        self.setFixedWidth(210)

        self._buttons: list[QToolButton] = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 16, 12, 16)
        layout.setSpacing(10)

        for index, (icon_key, label, accessible) in enumerate(NAV_ENTRIES):
            button = QToolButton()
            button.setObjectName("NavItem")
            button.setText(label)
            button.setIcon(icons.nav_icon(icon_key))
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            button.setAccessibleName(accessible)
            button.setCheckable(True)
            button.setIconSize(QSize(40, 40))
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setProperty("active", False)
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            button.clicked.connect(lambda _checked=False, i=index: self.set_current(i))
            layout.addWidget(button)
            self._buttons.append(button)

        layout.addStretch()
        self.set_current(0)

    def set_current(self, index: int) -> None:
        if not 0 <= index < len(self._buttons):
            return
        for i, button in enumerate(self._buttons):
            active = i == index
            button.setChecked(active)
            button.setProperty("active", active)
            button.style().unpolish(button)
            button.style().polish(button)
        self.currentChanged.emit(index)

    def paintEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        # orange curve in the lower corner, like the original nav rail
        rect = QRectF(self.rect())
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(theme.HEADER_ORANGE))
        curve = QPainterPath()
        radius = rect.width() * 1.15
        curve.moveTo(0, rect.bottom())
        curve.arcTo(
            QRectF(-radius * 0.55, rect.bottom() - radius, radius * 2, radius * 2),
            0,
            -90,
        )
        curve.lineTo(0, rect.bottom())
        curve.closeSubpath()
        painter.drawPath(curve)
        painter.end()


class SearchBar(QWidget):
    """Rounded orange search field with the circular search button."""

    textChanged = Signal(str)

    def __init__(self, placeholder: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.edit = QLineEdit()
        self.edit.setObjectName("SearchInput")
        self.edit.setPlaceholderText(placeholder)
        self.edit.setClearButtonEnabled(True)
        self.edit.textChanged.connect(self.textChanged)

        self.button = QPushButton()
        self.button.setObjectName("SearchButton")
        self.button.setIcon(icons.search_icon())
        self.button.setIconSize(QSize(26, 26))
        self.button.setFixedSize(38, 38)
        self.button.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self.edit, stretch=1)
        layout.addWidget(self.button)


class FirmwarePanel(QFrame):
    """Pen-screen section: current vs available firmware and the update action."""

    update_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("PenCard")

        title = QLabel(_("Firmware"))
        title.setObjectName("PenCardTitle")
        self.current_label = QLabel(_("No pen connected"))
        self.current_label.setObjectName("FooterInfo")
        self.update_button = pill_button(_("Update firmware"), primary=True)
        self.update_button.setEnabled(False)
        self.update_button.clicked.connect(lambda: self.update_requested.emit())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)
        layout.addWidget(title)
        layout.addWidget(self.current_label)
        layout.addWidget(self.update_button, alignment=Qt.AlignmentFlag.AlignLeft)

    def show_state(self, *, pen_version: str | None, latest_version: str | None, pending: bool, busy: bool) -> None:
        if pen_version is None:
            self.current_label.setText(_("Firmware-Version {version}").format(version="—"))
        else:
            self.current_label.setText(_("Firmware-Version {version}").format(version=pen_version))
        if pending:
            self.current_label.setText(_("A firmware update is pending on the pen"))
            self.update_button.setEnabled(False)
        elif latest_version and pen_version and latest_version != pen_version:
            self.update_button.setText(_("Update firmware to {version}").format(version=latest_version))
            self.update_button.setEnabled(not busy)
        elif latest_version:
            self.update_button.setText(_("Up to date"))
            self.update_button.setEnabled(False)
        else:
            self.update_button.setEnabled(False)


class FooterBar(QWidget):
    """Footer: legal links left, version/firmware/serial right, progress in the middle."""

    def __init__(self, version_text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("FooterBar")
        self.setFixedHeight(30)

        self.privacy_link = QPushButton(_("Privacy"))
        self.imprint_link = QPushButton(_("Legal notice"))
        for link in (self.privacy_link, self.imprint_link):
            link.setObjectName("FooterLink")
            link.setCursor(Qt.CursorShape.PointingHandCursor)

        self.progress = QLabel("")
        self.progress.setObjectName("FooterInfo")

        self.info = QLabel(version_text)
        self.info.setObjectName("FooterInfo")
        self.info.setAlignment(Qt.AlignmentFlag.AlignRight)

        self.update_link = QPushButton("")
        self.update_link.setObjectName("FooterLink")
        self.update_link.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_link.hide()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 14, 0)
        layout.setSpacing(6)
        layout.addWidget(self.privacy_link)
        layout.addWidget(QLabel("·"))
        layout.addWidget(self.imprint_link)
        layout.addStretch()
        layout.addWidget(self.progress)
        layout.addStretch()
        layout.addWidget(self.update_link)
        layout.addWidget(self.info)

    def show_update(self, url: str, version: str) -> None:
        self.update_link.setText(_("New version {version}").format(version=version))
        self.update_link.clicked.connect(lambda _checked=False: webbrowser.open(url))
        self.update_link.show()

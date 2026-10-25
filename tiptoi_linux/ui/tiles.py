"""Product tile grid, mirroring the original download screen.

Covers are drawn as placeholders for now; the enrichment step (Phase 2) will
feed real cover pixmaps into CoverTableModel.set_cover() without touching
this rendering code.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QModelIndex, QPersistentModelIndex, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QScrollArea, QStyledItemDelegate, QToolButton, QVBoxLayout, QWidget

from tiptoi_linux.catalog import Product, gme_file_name
from tiptoi_linux.gui import Column, ProductTableModel
from tiptoi_linux.ui import theme

TILE_WIDTH = 176
COVER_HEIGHT = 208
LABEL_HEIGHT = 44


class CoverTableModel(ProductTableModel):
    """ProductTableModel + covers from the local cache (DecorationRole).

    The portal mapping (product name -> article number) is set once the index is
    loaded; pixmaps are read lazily from the cover cache when a tile paints, so
    memory stays bounded regardless of catalog size.
    """

    _MAX_CACHED_PIXMAPS = 160

    def __init__(self, products=(), parent=None) -> None:
        super().__init__(products, parent)
        self._items: dict[str, str] = {}
        self._loaded: dict[str, QPixmap] = {}
        self._covers_dir = None

    def set_items(self, items: dict[str, str]) -> None:
        """product name -> article number; triggers a repaint of the grid."""
        if items == self._items:
            return
        self._items = dict(items)
        self._loaded.clear()
        top_left = self.index(0, Column.NAME)
        bottom_right = self.index(self.rowCount() - 1, Column.NAME)
        if self.rowCount():
            self.dataChanged.emit(top_left, bottom_right, [Qt.ItemDataRole.DecorationRole])

    def item_for(self, product_name: str) -> str | None:
        return self._items.get(product_name)

    def is_installed(self, product: Product) -> bool:
        return self._is_installed(product)

    def cover_for(self, product: Product) -> QPixmap | None:
        item = self._items.get(product.name)
        if not item:
            return None
        cached = self._loaded.get(product.name)
        if cached is not None:
            return cached
        from tiptoi_linux.enrich import cache_dir

        path = (self._covers_dir or cache_dir()) / f"{item}.webp"
        if not path.is_file():
            return None
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            return None
        if len(self._loaded) >= self._MAX_CACHED_PIXMAPS:
            self._loaded.clear()
        self._loaded[product.name] = pixmap
        return pixmap

    def data(self, index: QModelIndex | QPersistentModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if index.isValid() and index.column() == Column.NAME and role == Qt.ItemDataRole.DecorationRole:
            product = self.product_at(index.row())
            if product is not None:
                return self.cover_for(product)
        return super().data(index, role)


def _placeholder_cover(name: str, size: QSize) -> QPixmap:
    """A light card with the product initials, used until covers are fetched."""
    pixmap = QPixmap(size)
    pixmap.fill(QColor(theme.BG_LIGHT))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    letters = "".join(word[0] for word in name.replace("_", " ").split()[:3]).upper()[:3]
    font = QFont(painter.font())
    font.setPixelSize(int(size.height() * 0.28))
    font.setBold(True)
    painter.setFont(font)
    painter.setPen(QColor("#C4CFD6"))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, letters)
    painter.end()
    return pixmap


class TileDelegate(QStyledItemDelegate):
    """One product: cover card, state badge, two-line name."""

    def sizeHint(self, option, index: QModelIndex | QPersistentModelIndex) -> QSize:
        return QSize(TILE_WIDTH, COVER_HEIGHT + LABEL_HEIGHT)

    def paint(self, painter: QPainter, option, index: QModelIndex | QPersistentModelIndex) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        cell = option.rect.adjusted(8, 8, -8, -8)
        cover = cell.adjusted(0, 0, 0, -(LABEL_HEIGHT - 8))

        source = self._source(index)
        product = self._product_for(index)

        # cover card
        path = QPainterPath()
        path.addRoundedRect(QRectF(cover), 8, 8)
        painter.setClipPath(path)
        pixmap = None
        if product is not None and source is not None:
            pixmap = source.cover_for(product)
        if pixmap is None and product is not None:
            pixmap = _placeholder_cover(product.name, cover.size())
        if pixmap is not None:
            # aspect-fill: scale to cover the rect, then center-crop (no stretching)
            scaled = pixmap.scaled(cover.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            x = cover.x() + (cover.width() - scaled.width()) / 2
            y = cover.y() + (cover.height() - scaled.height()) / 2
            painter.drawPixmap(int(x), int(y), scaled)
        painter.setClipping(False)
        painter.setPen(QPen(QColor(theme.ICON_PINK), 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)

        # badge: green check when installed, else orange download circle
        installed = index.siblingAtColumn(Column.ON_PEN).data(Qt.ItemDataRole.DisplayRole) == "✓"
        badge_d = 30
        bx = cover.right() - badge_d - 6
        by = cover.top() + 6
        painter.setPen(Qt.PenStyle.NoPen)
        if installed:
            painter.setBrush(QColor("#4CAF87"))
            painter.drawEllipse(bx, by, badge_d, badge_d)
            pen = QPen(QColor(theme.BG_WHITE))
            pen.setWidthF(2.6)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawLine(bx + 8, by + 15, bx + 13, by + 21)
            painter.drawLine(bx + 13, by + 21, bx + 23, by + 9)
        else:
            painter.setBrush(QColor(theme.BRAND_ORANGE))
            painter.drawEllipse(bx, by, badge_d, badge_d)
            pen = QPen(QColor(theme.BG_WHITE))
            pen.setWidthF(2.4)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            cx = bx + badge_d / 2
            painter.drawLine(int(cx), by + 7, int(cx), by + 18)
            painter.drawLine(int(cx - 5), by + 14, int(cx), by + 19)
            painter.drawLine(int(cx + 5), by + 14, int(cx), by + 19)
            painter.drawLine(bx + 8, by + 23, bx + badge_d - 8, by + 23)

        # name, up to two elided lines
        name = index.siblingAtColumn(Column.NAME).data(Qt.ItemDataRole.DisplayRole) or ""
        font = QFont(painter.font())
        font.setPointSizeF(9.5)
        painter.setFont(font)
        painter.setPen(QColor(theme.FRAME_TEAL))
        metrics = QFontMetrics(font)
        label_rect = cell.adjusted(0, cover.height() + 4, 0, 0)
        text = metrics.elidedText(name.replace("_", " "), Qt.TextElideMode.ElideRight, label_rect.width())
        painter.drawText(label_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, text)

    def _product_for(self, index: QModelIndex | QPersistentModelIndex) -> Product | None:
        """The product a (possibly filtered/sorted) view index refers to."""
        source = self._source(index)
        if source is None:
            return None
        # WHY: index is a PROXY index; product_at expects a SOURCE row. Without mapping,
        # any active filter shifts every cover onto the wrong tile.
        model = index.model()
        map_to_source = getattr(model, "mapToSource", None)
        source_row = map_to_source(index).row() if map_to_source is not None else index.row()
        return source.product_at(source_row)

    def _source(self, index: QModelIndex | QPersistentModelIndex) -> CoverTableModel | None:
        model = index.model()
        source = getattr(model, "sourceModel", lambda: None)()
        return source if isinstance(source, CoverTableModel) else None


class NewestStrip(QWidget):
    """Horizontal row of the newest catalog products (by version date), like the
    original download screen's news section."""

    clicked = Signal(object)  # Product

    COUNT = 8

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._holder = QWidget()
        self._row = QHBoxLayout(self._holder)
        self._row.setContentsMargins(0, 0, 0, 0)
        self._row.setSpacing(10)

        scroller = QScrollArea()
        scroller.setWidget(self._holder)
        scroller.setWidgetResizable(True)
        scroller.setFrameShape(QScrollArea.Shape.NoFrame)
        scroller.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroller.setFixedHeight(170)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroller)

    def set_products(self, products: list[Product], cover_provider) -> None:
        while self._row.count():
            item = self._row.takeAt(0)
            if item.widget():
                # WHY: setParent(None) destroys deterministically; deleteLater would queue
                # events that Qt may process against a half-torn-down Python at exit
                item.widget().setParent(None)

        newest = sorted(products, key=lambda p: p.version, reverse=True)[: self.COUNT]
        for product in newest:
            button = QToolButton()
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            button.setFixedSize(120, 160)
            pixmap = cover_provider(product)
            if pixmap is not None and pixmap.isNull():
                pixmap = None
            if pixmap is None:
                # blank white tiles look broken; use the same initials placeholder as the grid
                pixmap = _placeholder_cover(product.name, QSize(110, 120))
            button.setIcon(QIcon(pixmap))
            button.setIconSize(QSize(110, 120))
            name = product.name.replace("_", " ")
            button.setText(name if len(name) <= 18 else name[:17] + "…")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _checked=False, p=product: self.clicked.emit(p))
            self._row.addWidget(button)
        self._row.addStretch()

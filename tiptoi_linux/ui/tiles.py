"""Product tile grid, mirroring the original download screen.

Covers are drawn as placeholders for now; the enrichment step (Phase 2) will
feed real cover pixmaps into CoverTableModel.set_cover() without touching
this rendering code.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QModelIndex, QPersistentModelIndex, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QStyledItemDelegate

from tiptoi_linux.catalog import Product, gme_file_name
from tiptoi_linux.gui import Column, ProductTableModel
from tiptoi_linux.ui import theme

TILE_WIDTH = 176
COVER_HEIGHT = 208
LABEL_HEIGHT = 44


class CoverTableModel(ProductTableModel):
    """ProductTableModel + per-product cover pixmaps (DecorationRole)."""

    def __init__(self, products=(), parent=None) -> None:
        super().__init__(products, parent)
        self._covers: dict[str, QPixmap] = {}

    def set_cover(self, product_name: str, pixmap: QPixmap) -> None:
        self._covers[product_name] = pixmap
        self.dataChanged.emit(self.index(0, 0), self.index(self.rowCount() - 1, 0))

    def cover_for(self, product: Product) -> QPixmap | None:
        return self._covers.get(product.name)

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
        product = source.product_at(index.row()) if source is not None else None

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
            painter.drawPixmap(cover, pixmap)
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

    def _source(self, index: QModelIndex | QPersistentModelIndex) -> CoverTableModel | None:
        model = index.model()
        source = getattr(model, "sourceModel", lambda: None)()
        return source if isinstance(source, CoverTableModel) else None

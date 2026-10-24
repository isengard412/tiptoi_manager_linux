"""Catalog screen: category filter chips + the shared product tile grid."""

from __future__ import annotations

from PySide6.QtCore import QSortFilterProxyModel, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QListView,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from tiptoi_linux.catalog import Product
from tiptoi_linux.gui import Column
from tiptoi_linux.i18n import _, ngettext
from tiptoi_linux.ui import tiles, widgets


class CatalogProxy(QSortFilterProxyModel):
    """Search + category filtering over the product model.

    The category of a product is resolved through the portal mapping
    (product name -> article number -> category). Products without a known
    category pass only the "Alle" filter.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._search = ""
        self._category: str | None = None
        self._items: dict[str, str] = {}  # product name -> article number
        self._categories: dict[str, str] = {}  # article number -> category
        self.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

    def set_search(self, text: str) -> None:
        self._search = text.strip().casefold()
        self.invalidateRowsFilter()

    def set_category(self, category: str | None) -> None:
        self._category = category
        self.invalidateRowsFilter()

    def set_mapping(self, items: dict[str, str], categories: dict[str, str]) -> None:
        self._items = dict(items)
        self._categories = dict(categories)
        self.invalidateRowsFilter()

    def category_of(self, product_name: str) -> str | None:
        item = self._items.get(product_name)
        return self._categories.get(item) if item else None

    def filterAcceptsRow(self, source_row: int, source_parent) -> bool:
        model = self.sourceModel()
        name_index = model.index(source_row, Column.NAME, source_parent)
        name = model.data(name_index, Qt.ItemDataRole.DisplayRole) or ""
        if self._search and self._search not in name.casefold().replace("_", " "):
            return False
        if self._category is not None:
            product = model.product_at(source_row) if hasattr(model, "product_at") else None
            if product is None or self.category_of(product.name) != self._category:
                return False
        return True


class CategoryChipBar(QWidget):
    """Horizontally scrollable row of filter chips, "Alle" first."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._buttons: dict[str | None, QPushButton] = {}
        self.selected_changed = None  # callable(str | None), set by the screen

        self._row = QHBoxLayout()
        self._row.setContentsMargins(0, 0, 0, 0)
        self._row.setSpacing(8)
        holder = QWidget()
        holder.setLayout(self._row)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroller = QScrollArea()
        scroller.setWidget(holder)
        scroller.setWidgetResizable(True)
        scroller.setFrameShape(QScrollArea.Shape.NoFrame)
        scroller.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroller.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroller.setFixedHeight(38)
        outer.addWidget(scroller)

    def set_categories(self, categories: list[str]) -> None:
        if [b.text() for b in self._buttons.values()] == [_("All"), *categories]:
            return
        for button in self._buttons.values():
            self._row.removeWidget(button)
            button.setParent(None)  # immediate removal; deleteLater would need a running event loop
        self._buttons.clear()
        self._add_chip(None, _("All"))
        for category in categories:
            self._add_chip(category, category)
        self._select(None)
        self._row.addStretch()

    def _add_chip(self, category: str | None, label: str) -> None:
        button = QPushButton(label)
        button.setObjectName("CategoryChip")
        button.setCheckable(True)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.clicked.connect(lambda _checked=False, c=category: self._select(c))
        self._buttons[category] = button
        self._row.addWidget(button)

    def _select(self, category: str | None) -> None:
        for key, button in self._buttons.items():
            button.setChecked(key == category)
        if self.selected_changed is not None:
            self.selected_changed(category)


class CatalogScreen(QWidget):
    """Browse-by-category screen sharing the product model with the download screen."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.on_selection_changed: callable | None = None
        self.search = widgets.SearchBar(_("Search the catalog…"))
        self.chips = CategoryChipBar()
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
        self.install_button.setEnabled(False)

        top = QHBoxLayout()
        top.setSpacing(10)
        top.addWidget(self.search, stretch=1)
        top.addWidget(self.install_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 12)
        layout.addLayout(top)
        layout.addWidget(self.chips)
        layout.addWidget(self.result_count)
        layout.addWidget(self.grid, stretch=1)

        self.chips.selected_changed = self._category_changed

    def use_model(self, model: tiles.CoverTableModel, proxy: CatalogProxy) -> None:
        if proxy.parent() is None:
            # WHY: the screen connects its search bar to the proxy - without shared ownership a
            # parentless proxy can be collected before the screen, firing slots on deleted objects
            proxy.setParent(self)
        self._proxy = proxy
        proxy.setSourceModel(model)
        self.grid.setModel(proxy)
        self.search.textChanged.connect(proxy.set_search)
        self.search.textChanged.connect(self._refresh_count)
        self.grid.selectionModel().selectionChanged.connect(self._on_selection)
        self._proxy.layoutChanged.connect(self._refresh_count)
        self._proxy.modelReset.connect(self._refresh_count)

    def set_categories(self, categories: list[str]) -> None:
        self.chips.set_categories(categories)

    def _category_changed(self, category: str | None) -> None:
        self._proxy.set_category(category)
        self._refresh_count()

    def _on_selection(self) -> None:
        if self.on_selection_changed is not None:
            self.on_selection_changed()

    def selected_product(self) -> Product | None:
        indexes = self.grid.selectionModel().selectedIndexes()
        if not indexes:
            return None
        source_index = self._proxy.mapToSource(indexes[0])
        model = self._proxy.sourceModel()
        return model.product_at(source_index.row()) if hasattr(model, "product_at") else None

    def _refresh_count(self) -> None:
        n = self._proxy.rowCount()
        self.result_count.setText(ngettext("{n} product", "{n} products", n).format(n=n))

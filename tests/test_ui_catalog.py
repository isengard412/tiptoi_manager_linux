"""Tests for the catalog screen: category chips + search over the shared model."""

from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication

    _PYSIDE6_AVAILABLE = True
except ImportError:
    _PYSIDE6_AVAILABLE = False

from tiptoi_linux.catalog import parse_catalog
from tiptoi_linux.enrich import PortalIndex

from tests.test_gui import FIXTURE_CSV


@unittest.skipUnless(_PYSIDE6_AVAILABLE, "PySide6 is not installed")
class CatalogScreenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        from tiptoi_linux.ui import theme
        from tiptoi_linux.ui.catalog import CatalogProxy, CatalogScreen
        from tiptoi_linux.ui.tiles import CoverTableModel

        self.catalog = parse_catalog(FIXTURE_CSV)
        self.model = CoverTableModel(self.catalog.products)
        self.screen = CatalogScreen()
        self.proxy = CatalogProxy()
        self.screen.use_model(self.model, self.proxy)
        self.index = PortalIndex(
            items={"create kreative bildergeschichten": "00001", "wissen quizzen tiere": "00002"},
            compact={"createkreativebildergeschichten": "00001", "wissenquizzentiere": "00002"},
            categories={"00001": "CREATE", "00002": "Spiele"},
        )

    def tearDown(self) -> None:
        # WHY: delete the parentless screen while Qt is still alive; GC'ing it during
        # interpreter shutdown corrupts the heap (crash seen with LANGUAGE=C)
        self.screen.deleteLater()
        self.app.processEvents()
        self.screen = None

    def test_all_products_visible_initially(self) -> None:
        self.assertEqual(self.proxy.rowCount(), len(self.catalog.products))

    def test_category_filter(self) -> None:
        self.proxy.set_mapping(
            {"CREATE_Kreative_Bildergeschichten": "00001", "WissenQuizzenTiere": "00002"},
            self.index.categories,
        )
        self.proxy.set_category("Spiele")
        names = [self.model.product_at(self.proxy.mapToSource(self.proxy.index(r, 0)).row()).name for r in range(self.proxy.rowCount())]
        self.assertEqual(names, ["WissenQuizzenTiere"])
        self.proxy.set_category(None)
        self.assertEqual(self.proxy.rowCount(), len(self.catalog.products))

    def test_products_without_category_hidden_when_filtered(self) -> None:
        self.proxy.set_mapping({"CREATE_Kreative_Bildergeschichten": "00001"}, self.index.categories)
        self.proxy.set_category("CREATE")
        self.assertEqual(self.proxy.rowCount(), 1)

    def test_search_combines_with_category(self) -> None:
        self.proxy.set_mapping(
            {"CREATE_Kreative_Bildergeschichten": "00001", "WissenQuizzenTiere": "00002"},
            self.index.categories,
        )
        self.proxy.set_search("tiere")
        self.assertEqual(self.proxy.rowCount(), 1)
        self.proxy.set_category("CREATE")
        self.assertEqual(self.proxy.rowCount(), 0)

    def test_chips_built_from_categories(self) -> None:
        from tiptoi_linux.i18n import _

        self.screen.set_categories(["Bücher", "Spiele"])
        labels = [b.text() for b in self.screen.chips._buttons.values()]
        self.assertEqual(labels[0], _("All"))
        self.assertIn("Bücher", labels)

    def test_selected_product_maps_through_proxy(self) -> None:
        self.proxy.set_search("Eiskoenigin")
        self.assertEqual(self.proxy.rowCount(), 1)
        self.screen.grid.setCurrentIndex(self.proxy.index(0, 0))
        product = self.screen.selected_product()
        self.assertIsNotNone(product)
        self.assertEqual(product.name, "Die Eiskoenigin")

    def test_delegate_maps_filtered_proxy_rows_to_source_products(self) -> None:
        """WHY: a regression where the tile delegate used proxy rows as source rows,
        so any active filter shifted every cover onto the wrong product."""
        from tiptoi_linux.ui import tiles

        mapping = {p.name: f"0{i}" for i, p in enumerate(self.catalog.products)}
        self.model.set_items(mapping)
        delegate = tiles.TileDelegate(self.screen.grid)

        self.proxy.set_search("Eiskoenigin")
        self.assertEqual(self.proxy.rowCount(), 1)
        view_index = self.proxy.index(0, 0)
        product = delegate._product_for(view_index)
        self.assertIsNotNone(product)
        self.assertEqual(product.name, "Die Eiskoenigin")

        self.proxy.set_search("")
        # with sorting on the download proxy the rows can differ; check every row maps right
        for row in range(self.proxy.rowCount()):
            idx = self.proxy.index(row, 0)
            p = delegate._product_for(idx)
            src = self.proxy.mapToSource(idx)
            self.assertEqual(p, self.model.product_at(src.row()))


if __name__ == "__main__":
    unittest.main()

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


if __name__ == "__main__":
    unittest.main()

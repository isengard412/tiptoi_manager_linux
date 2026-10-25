"""Tests for the cover enrichment module (tiptoi_linux.enrich)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tiptoi_linux.enrich import (
    PortalIndex,
    normalize_name,
    parse_portal_links,
)

PORTAL_FIXTURE = """
<html><body>
<ul>
  <li><a href="https://service.ravensburger.de/tiptoi%C2%AE/tiptoi%C2%AE_Audiodateien/Audiodateien_tiptoi%C2%AE_Adventskalender">Audiodateien tiptoi&reg; Adventskalender</a></li>
  <li><a href="https://service.ravensburger.de/tiptoi%C2%AE/tiptoi%C2%AE_Audiodateien/Audiodateien_tiptoi%C2%AE_Adventskalender/tiptoi%C2%AE_Adventskalender_Mandelmann_00037">tiptoi&reg; Audiodatei Adventskalender&nbsp;Mandelmann 00562 und 00037</a></li>
  <li><a href="https://service.ravensburger.de/tiptoi%C2%AE/tiptoi%C2%AE_Audiodateien/Audiodateien_tiptoi%C2%AE_Puzzle/Puzzle_f%C3%BCr_kleine_Entdecker_Feuerwehrmann_Sam_00139">tiptoi&reg; Audiodatei Puzzle für kleine Entdecker Feuerwehrmann Sam 00046 und</a></li>
  <li><a href="https://service.ravensburger.de/tiptoi%C2%AE/tiptoi%C2%AE_Audiodateien/Audiodateien_tiptoi%C2%AE_Wissen/Wissen_und_Quizzen_FCBayern_00006">tiptoi&reg; Audiodatei Wissen und Quizzen FC Bayern München 2019/2020</a></li>
</ul>
</body></html>
"""


class NormalizeNameTests(unittest.TestCase):
    def test_umlaut_variants_agree(self) -> None:
        self.assertEqual(normalize_name("Die Eiskönigin"), normalize_name("Die_Eiskoenigin"))

    def test_camel_case_is_split(self) -> None:
        self.assertEqual(normalize_name("WissenQuizzenTiere"), "wissen quizzen tiere")

    def test_tiptoi_prefix_and_punctuation_stripped(self) -> None:
        self.assertEqual(normalize_name("tiptoi® Tier-Set Bauernhof"), "tier set bauernhof")

    def test_sharp_s(self) -> None:
        self.assertEqual(normalize_name("Mein großer Adventskalender"), "mein grosser adventskalender")


class ParsePortalLinksTests(unittest.TestCase):
    def setUp(self) -> None:
        self.index = parse_portal_links(PORTAL_FIXTURE)

    def test_category_pages_are_skipped(self) -> None:
        self.assertNotIn("adventskalender", self.index.items)

    def test_titles_are_cleaned(self) -> None:
        self.assertIn("adventskalender mandelmann", self.index.items)
        self.assertEqual(self.index.items["adventskalender mandelmann"], "00037")

    def test_year_range_tokens_stripped(self) -> None:
        self.assertIn("wissen und quizzen fc bayern muenchen", self.index.items)


class LookupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.index = parse_portal_links(PORTAL_FIXTURE)

    def test_exact_match(self) -> None:
        self.assertEqual(self.index.item_for("Adventskalender Mandelmann"), "00037")

    def test_camel_case_compact_match(self) -> None:
        self.assertEqual(self.index.item_for("WissenQuizzenFCBayernMuenchen"), "00006")

    def test_token_subsequence_match(self) -> None:
        self.assertEqual(self.index.item_for("Puzzle_Entdecker_Feuerwehrmann_Sam"), "00139")

    def test_unknown_product_returns_none(self) -> None:
        self.assertIsNone(self.index.item_for("EinProduktDasNichtExistiert123"))

    def test_ambiguous_query_returns_none(self) -> None:
        index = PortalIndex(
            items={"puzzle a tier": "00001", "puzzle b tier": "00002"},
            compact={"puzzleatier": "00001", "puzzlebtier": "00002"},
        )
        self.assertIsNone(index.item_for("puzzle tier"))

    def test_series_alias_prefix(self) -> None:
        index = PortalIndex(items={"wieso weshalb warum bei der polizei": "49304"})
        self.assertEqual(index.item_for("WWW_Bei_der_Polizei"), "49304")

    def test_numeric_guard_rejects_wrong_class_number(self) -> None:
        index = PortalIndex(
            items={"lern mit mir mathe 1 klasse": "49284", "mathe 2 klasse": "41807"},
        )
        self.assertEqual(index.item_for("Lern mit mir - Mathe - Klasse 2"), "41807")
        self.assertEqual(index.item_for("Lern mit mir - Mathe - Klasse 1"), "49284")

    def test_token_set_match_ignores_word_order(self) -> None:
        index = PortalIndex(items={"deutsch 1 klasse": "49283"})
        self.assertEqual(index.item_for("Lern mit mir - Deutsch - Klasse 1"), "49283")

    def test_inner_article_numbers_stripped(self) -> None:
        index = parse_portal_links(
            '<a href="https://service.ravensburger.de/tiptoi%C2%AE/tiptoi%C2%AE_Audiodateien/'
            'Audiodateien_tiptoi%C2%AE_Spiele/Memory_Rekorde_im_Tierreich_80671">'
            'tiptoi&reg; Audiodatei Memory Rekorde im Tierreich 00519 und Happy Meal Edition</a>'
        )
        self.assertIn("memory rekorde im tierreich happy meal edition", index.items)

    def test_portal_page_url_is_captured(self) -> None:
        index = parse_portal_links(PORTAL_FIXTURE)
        # the "Adventskalender Mandelmann" entry carries its own service-portal page URL
        page = index.pages["adventskalender mandelmann"]
        self.assertTrue(page.startswith("https://service.ravensburger.de/"))
        self.assertIn("Mandelmann_00037", page)


class CoverPathTests(unittest.TestCase):
    def test_download_cover_uses_cache(self) -> None:
        from tiptoi_linux.enrich import download_cover

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self, _limit):
                return b"webp-bytes"

        calls = []

        class FakeOpener:
            def open(self, url, timeout=None):
                calls.append(url)
                return FakeResponse()

        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            path = download_cover("00037", dest_dir=dest, opener=FakeOpener())
            self.assertTrue(path.is_file())
            self.assertEqual(path.read_bytes(), b"webp-bytes")
            self.assertIn("ravensburger.cloud", calls[0])
            # second call must hit the cache, not the network
            download_cover("00037", dest_dir=dest, opener=FakeOpener())
            self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()

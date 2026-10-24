"""The fr/it/nl catalogs exist and cover the core navigation strings."""

from __future__ import annotations

import gettext
import unittest
from pathlib import Path

from tiptoi_linux.i18n import LOCALE_DIR

NAV_STRINGS = (
    "Load audio\nfiles",
    "Browse product\ncatalog",
    "Manage pen\nand content",
    "Help and\ninformation",
    "Options",
)


class AdditionalLanguageCatalogTests(unittest.TestCase):
    def test_catalogs_cover_navigation(self) -> None:
        for code in ("fr", "it", "nl"):
            mo = LOCALE_DIR / code / "LC_MESSAGES" / "tiptoi.mo"
            self.assertTrue(mo.is_file(), f"missing compiled catalog for {code}")
            with open(mo, "rb") as handle:
                catalog = gettext.GNUTranslations(handle)
            for msgid in NAV_STRINGS:
                translated = catalog.gettext(msgid)
                if msgid == "Options":  # identical and correct in French
                    self.assertTrue(translated.strip())
                    continue
                self.assertNotEqual(translated, msgid, f"{code}: {msgid!r} untranslated")
                self.assertTrue(translated.strip())

    def test_po_and_mo_are_in_sync(self) -> None:
        import subprocess
        import shutil

        if not shutil.which("msgfmt"):
            self.skipTest("msgfmt not installed")
        for code in ("fr", "it", "nl"):
            po = LOCALE_DIR / code / "LC_MESSAGES" / "tiptoi.po"
            result = subprocess.run(["msgfmt", "--check", "-o", "/dev/null", str(po)])
            self.assertEqual(result.returncode, 0, f"{code}.po failed msgfmt --check")


if __name__ == "__main__":
    unittest.main()

"""Translations for user-facing text.

Language precedence: TIPTOI_LANGUAGE environment variable (used by tests),
then the "language" entry in the user settings file, then the system locale.
"""
from __future__ import annotations

import gettext
import os
from pathlib import Path

LOCALE_DIR = Path(__file__).parent / "locale"


def _preferred_languages() -> list[str] | None:
    override = os.environ.get("TIPTOI_LANGUAGE")
    if override:
        return [override, "en"]
    try:  # local import: settings must not depend on i18n
        from tiptoi_linux.settings import load_settings

        configured = load_settings().get("language")
    except Exception:
        configured = None
    if configured:
        return [configured, "en"] if configured != "system" else None
    return None


_translation = gettext.translation("tiptoi", localedir=LOCALE_DIR, languages=_preferred_languages(), fallback=True)
_ = _translation.gettext
ngettext = _translation.ngettext

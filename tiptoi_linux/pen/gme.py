"""Read the version date out of a .gme file's header."""

from __future__ import annotations

import re
from pathlib import Path

from tiptoi_linux.i18n import _
from tiptoi_linux.pen._base import PenError

GME_HEADER_OFFSET = 0x20
GME_HEADER_READ_BYTES = 0x100

# the yyyymmdd date that ends recent headers, e.g. "...Ver2.10.090120210112" -> "20210112"
_TRAILING_DATE_RE = re.compile(r"(\d{8})$")
# older headers embed the version date before a language token, e.g.
# "...Ver2.10.090120150819GERMAN..." - a plausible date followed by a non-digit.
# No lookbehind: the date directly abuts the "0901" version digits, so the engine
# must slide through the digit run; earlier windows fail the (?=\D) lookahead and
# _is_plausible_date rejects nonsense splits like "09012015".
_PLAUSIBLE_DATE_RE = re.compile(r"(\d{8})(?=\D)")


def _is_plausible_date(value: str) -> bool:
    year, month, day = int(value[0:4]), int(value[4:6]), int(value[6:8])
    return 2000 <= year <= 2100 and 1 <= month <= 12 and 1 <= day <= 31


def read_gme_version(path: Path) -> str | None:
    try:
        with open(path, "rb") as handle:
            data = handle.read(GME_HEADER_READ_BYTES)
    except OSError as exc:
        raise PenError(_("cannot read {path}: {error}").format(path=path, error=exc)) from exc

    # WHY: verified on a real pen (2026-11-01): every .gme's header starts at this offset and its
    # NUL-terminated ASCII text ends in the installed yyyymmdd date. Older files append a language
    # token (and later some junk) after the date instead, so a plausible date followed by a
    # non-digit anywhere in the header is accepted as a fallback.
    text_bytes = data[GME_HEADER_OFFSET:].split(b"\0", 1)[0]
    try:
        text = text_bytes.decode("ascii")
    except UnicodeDecodeError:
        text = None
    if text is not None:
        match = _TRAILING_DATE_RE.search(text)
        if match:
            return match.group(1)
    loose = text_bytes.decode("ascii", errors="replace")
    for candidate in _PLAUSIBLE_DATE_RE.findall(loose):
        if _is_plausible_date(candidate):
            return candidate
    return None

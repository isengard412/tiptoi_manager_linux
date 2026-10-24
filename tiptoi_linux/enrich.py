"""Enrich the CSV catalog with product covers from Ravensburger's public shop CDN.

The service portal page "tiptoi® Audiodateien" lists one link per product with the
five-digit article number in the page slug (e.g. "..._Mandelmann_00037"). The shop
CDN then serves a cover image per article number. Everything is fetched at runtime
and cached; no images are shipped with this package (see docs/reference/style-guide.md).
"""

from __future__ import annotations

import os
import re
import tempfile
import unicodedata
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path

from tiptoi_linux.errors import TiptoiError
from tiptoi_linux.i18n import _
from tiptoi_linux.net import https_opener

PORTAL_URL = "https://service.ravensburger.de/tiptoi%C2%AE/tiptoi%C2%AE_Audiodateien"
COVER_URL_TEMPLATE = "https://ravensburger.cloud/images/produktseiten/520x445/{item}.webp"
MAX_PORTAL_BYTES = 8 * 1024 * 1024
MAX_COVER_BYTES = 2 * 1024 * 1024

_ITEM_SUFFIX_RE = re.compile(r"^(?P<name>.+?)_(?P<item>\d{5})$")
_LINK_RE = re.compile(
    r'<a[^>]*href="[^"]*tiptoi%C2%AE_Audiodateien/(([^"#?]*)/)?[^"#?]*?/([^"#?]+)"[^>]*>(.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)
_TAG_RE = re.compile(r"<[^>]+>")
_TITLE_PREFIX_RE = re.compile(
    r"^(?:tiptoi\s*(?:®|&reg;)?\s*)?(?:audiodatei(?:en)?|audioatei(?:en)?)\s+", re.IGNORECASE
)
_NUMBER_TOKEN_RE = re.compile(r"^(?:\d{2,5}(?:[./-]\d{2,5})*|\d{4,5})$")
_CONNECTOR_TOKENS = frozenset({"und", "u.", "u"})


class EnrichError(TiptoiError):
    """Raised for portal or cover download failures."""


def normalize_name(name: str) -> str:
    """Fold a product name for matching: caseless, umlaut-expanded, punctuation-free.

    "Die Eiskönigin" and "Die Eiskoenigin" normalize identically, as do
    "tiptoi® Tier-Set Bauernhof" and "tier_set_bauernhof".
    """
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", name)  # split CamelCase: WissenQuizzenTiere -> Wissen QuizzenTiere
    text = text.casefold()
    fold = {
        "ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss",
        "à": "a", "è": "e", "é": "e", "ì": "i", "ò": "o", "ù": "u",
    }
    for src, dst in fold.items():
        text = text.replace(src, dst)
    # drop any remaining accents (NFKD + combining-mark filter), e.g. ç -> c
    text = "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))
    text = text.replace("&amp;", "und")
    kept = [c if (c.isalnum() or c == " ") else " " for c in text]
    collapsed = re.sub(r"\s+", " ", "".join(kept)).strip()
    for prefix in ("tiptoi ", "tiptoi"):
        if collapsed.startswith(prefix):
            collapsed = collapsed[len(prefix) :].strip()
            break
    return collapsed


@dataclass(frozen=True)
class PortalIndex:
    """Article numbers by product name, with staged fuzzy lookup.

    Matching order: exact normalized name -> exact space-free (compact) name ->
    unique containment -> best fuzzy match >= 0.85. The compact stage is what
    bridges CSV CamelCase ("WissenQuizzenTiere") to portal titles ("Wissen Quizzen
    Tiere"); containment catches "Puzzle Entdecker X" vs "puzzle für kleine
    entdecker X". Ambiguous candidates are rejected rather than guessed.
    """

    items: dict[str, str]
    compact: dict[str, str] = field(default_factory=dict)

    @property
    def size(self) -> int:
        return len(self.items)

    def item_for(self, product_name: str) -> str | None:
        name = normalize_name(product_name)
        if not name:
            return None
        if name in self.items:
            return self.items[name]
        key = name.replace(" ", "")
        if key in self.compact:
            return self.compact[key]
        query = name.split()
        if len(query) >= 2:
            hits = set()
            for candidate, item in self.items.items():
                tokens = candidate.split()
                if len(tokens) < 2:
                    continue
                shorter, longer = (query, tokens) if len(query) <= len(tokens) else (tokens, query)
                if len(shorter) / len(longer) < 0.6:
                    continue
                if _is_subsequence(shorter, longer):
                    hits.add(item)
            if len(hits) == 1:
                return hits.pop()
            if hits:
                # several portal entries could be this product - refuse to guess
                return None
        best_item: str | None = None
        best_ratio = 0.0
        for candidate, item in self.items.items():
            ratio = SequenceMatcher(None, key, candidate.replace(" ", "")).ratio()
            if ratio > best_ratio:
                best_item, best_ratio = item, ratio
        if best_ratio >= 0.85:
            return best_item
        return None


def _is_subsequence(needles: list[str], haystack: list[str]) -> bool:
    it = iter(haystack)
    return all(any(n == h for h in it) for n in needles)


def _clean_anchor_text(text: str) -> str:
    """Strip tags/entities, the "tiptoi® Audiodatei" prefix and trailing article numbers.

    Titles end in the covered article numbers, e.g. "... Mandelmann 00562 und 00037"
    or "... Paw Patrol 00069 und" - drop those trailing number/connector tokens.
    """
    import html as html_module

    plain = html_module.unescape(_TAG_RE.sub(" ", text)).replace("\xa0", " ")
    plain = _TITLE_PREFIX_RE.sub("", plain.strip())
    tokens = plain.split()
    while tokens and (
        _NUMBER_TOKEN_RE.match(tokens[-1]) or tokens[-1].lower() in _CONNECTOR_TOKENS
    ):
        tokens.pop()
    return " ".join(tokens).strip()


def parse_portal_links(html: str) -> PortalIndex:
    """Extract {normalized product name: article number} from the portal page HTML.

    Uses the anchor text (a clean "tiptoi® Audiodatei <Name> <nummern>" title) for the
    name and the page slug's trailing five-digit number for the article number.
    """
    items: dict[str, str] = {}
    for raw_slug, raw_text in _LINK_RE.findall(html):
        slug = urllib.parse.unquote(raw_slug.rsplit("/", 1)[-1])
        match = _ITEM_SUFFIX_RE.match(slug)
        if not match:
            continue
        name = normalize_name(_clean_anchor_text(raw_text))
        if name:
            items.setdefault(name, match.group("item"))
    compact = {name.replace(" ", ""): item for name, item in items.items()}
    return PortalIndex(items, compact)


def cover_url(item: str) -> str:
    return COVER_URL_TEMPLATE.format(item=item)


def cache_dir() -> Path:
    xdg_cache = os.environ.get("XDG_CACHE_HOME")
    base = Path(xdg_cache) if xdg_cache else Path.home() / ".cache"
    return base / "tiptoi-linux" / "covers"


def portal_cache_path() -> Path:
    xdg_cache = os.environ.get("XDG_CACHE_HOME")
    base = Path(xdg_cache) if xdg_cache else Path.home() / ".cache"
    return base / "tiptoi-linux" / "portal_audiodateien.html"


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, prefix=".cover-", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    except BaseException:
        Path(tmp_path).unlink(missing_ok=True)
        raise


def fetch_portal_index(
    url: str = PORTAL_URL,
    *,
    cache: Path | None = None,
    opener: urllib.request.OpenerDirector = https_opener,
    force: bool = False,
    max_age: int = 86400,
) -> PortalIndex:
    """Load the portal page (cached once a day) and parse the article numbers."""
    import time

    target = portal_cache_path() if cache is None else cache
    if not force:
        try:
            age = time.time() - target.stat().st_mtime
        except OSError:
            age = None
        if age is not None and 0 <= age < max_age:
            try:
                return parse_portal_links(target.read_text(encoding="utf-8", errors="replace"))
            except OSError:
                pass

    try:
        with opener.open(url, timeout=30) as response:
            raw = response.read(MAX_PORTAL_BYTES + 1)
    except OSError as exc:
        raise EnrichError(_("failed to download the product portal page: {error}").format(error=exc)) from exc
    if len(raw) > MAX_PORTAL_BYTES:
        raise EnrichError(_("the portal page response exceeds {max_bytes} bytes").format(max_bytes=MAX_PORTAL_BYTES))
    text = raw.decode("utf-8", errors="replace")
    index = parse_portal_links(text)
    if not index.items:
        raise EnrichError(_("the portal page listed no products; refusing to cache it"))
    try:
        _atomic_write_bytes(target, text.encode("utf-8"))
    except OSError:
        pass  # a broken cache is not fatal - the parsed index is already in hand
    return index


def download_cover(
    item: str,
    *,
    dest_dir: Path | None = None,
    opener: urllib.request.OpenerDirector = https_opener,
) -> Path:
    """Fetch one cover image into the cache; return its path (cached copy reused)."""
    target_dir = cache_dir() if dest_dir is None else dest_dir
    target = target_dir / f"{item}.webp"
    if target.is_file() and target.stat().st_size > 0:
        return target
    try:
        with opener.open(cover_url(item), timeout=30) as response:
            data = response.read(MAX_COVER_BYTES + 1)
    except OSError as exc:
        raise EnrichError(_("failed to download cover {item}: {error}").format(item=item, error=exc)) from exc
    if not data or len(data) > MAX_COVER_BYTES:
        raise EnrichError(_("cover {item} has an unexpected size").format(item=item))
    _atomic_write_bytes(target, data)
    return target

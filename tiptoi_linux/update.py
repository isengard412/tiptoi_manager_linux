"""Self-update check against the project's GitHub releases."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass

from tiptoi_linux import __version__
from tiptoi_linux.errors import TiptoiError
from tiptoi_linux.i18n import _
from tiptoi_linux.net import https_opener

RELEASES_API = "https://api.github.com/repos/isengard412/tiptoi_manager_linux/releases/latest"


class UpdateCheckError(TiptoiError):
    """Raised when the release feed cannot be read or parsed."""


@dataclass(frozen=True)
class ReleaseInfo:
    version: str  # tag without the leading "v"
    url: str


def parse_version(text: str) -> tuple[int, ...]:
    """Numeric compare key for a version string; dev/prerelease sorts lowest."""
    core = text.lstrip("v").split("+")[0]
    main, _, pre = core.partition("-")
    parts: list[int] = []
    for chunk in main.split("."):
        digits = "".join(c for c in chunk if c.isdigit())
        parts.append(int(digits) if digits else 0)
    return (0 if pre else 1, *parts)


def is_newer(latest: str, current: str) -> bool:
    try:
        return parse_version(latest) > parse_version(current)
    except ValueError:
        return False


def fetch_latest_release(
    url: str = RELEASES_API,
    *,
    opener: urllib.request.OpenerDirector = https_opener,
) -> ReleaseInfo | None:
    """Return the newest published release, or None when the repository has none yet."""
    try:
        with opener.open(url, timeout=15) as response:
            payload = json.loads(response.read(256 * 1024).decode("utf-8", errors="replace"))
    except (OSError, ValueError) as exc:
        raise UpdateCheckError(_("failed to check for a new version: {error}").format(error=exc)) from exc
    if not isinstance(payload, dict):
        raise UpdateCheckError(_("unexpected release feed response"))
    tag = payload.get("tag_name")
    if not tag:  # GitHub answers 404 as JSON without tag_name when no release exists
        return None
    page = payload.get("html_url") or "https://github.com/isengard412/tiptoi_manager_linux/releases"
    return ReleaseInfo(version=str(tag), url=str(page))

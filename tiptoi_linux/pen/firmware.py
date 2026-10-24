"""tiptoi pen firmware: catalog header, download, checksum, and install on the pen.

The public tiptoi.csv carries the current firmware in its first two lines:

    CSV file version,Firmware version,Firmware checksum,Firmware download address
    26092403,6GE027,1872396468,https://cdn.ravensburger.de/db/Firmware-Files/.../Update6E.upd

The checksum is the plain sum of all bytes of the .upd file (verified against the
live file for 6GE027). The pen applies an update by reading a file named
"update.upd" from its root on the next power-on.
"""

from __future__ import annotations

import os
import re
import tempfile
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from tiptoi_linux.errors import TiptoiError
from tiptoi_linux.i18n import _
from tiptoi_linux.net import https_opener
from tiptoi_linux.pen._base import Pen, fsync_directory, require_mounted
from tiptoi_linux.pen.install import Phase

FIRMWARE_FILE_NAME = "update.upd"
MAX_FIRMWARE_BYTES = 64 * 1024 * 1024


class FirmwareError(TiptoiError):
    """Raised for firmware download, verification or install failures."""


@dataclass(frozen=True)
class FirmwareInfo:
    version: str
    checksum: int
    url: str

    @property
    def generation(self) -> str | None:
        """Hardware revision tag from the download URL (e.g. "REV12"), if present."""
        match = re.search(r"(REV[-\w]+)", urllib.parse.unquote(self.url))
        return match.group(1) if match else None


def parse_firmware_info(csv_text: str) -> FirmwareInfo | None:
    """Extract the firmware header from the raw catalog text; None when absent."""
    header_seen = False
    for line in csv_text.splitlines():
        fields = [field.strip() for field in line.split(",")]
        if not header_seen:
            if fields and fields[0] == "CSV file version":
                header_seen = True
            continue
        # the row right after the header holds: csvVersion, firmwareVersion, checksum, url
        if len(fields) >= 4 and fields[1] and fields[3].startswith("https://"):
            try:
                return FirmwareInfo(version=fields[1], checksum=int(fields[2]), url=fields[3])
            except ValueError:
                return None
        return None
    return None


def checksum_of(data: bytes) -> int:
    return sum(data)


def verify_checksum(data: bytes, expected: int) -> bool:
    return checksum_of(data) & 0xFFFFFFFF == expected & 0xFFFFFFFF


def firmware_cache_path(info: FirmwareInfo) -> Path:
    xdg_cache = os.environ.get("XDG_CACHE_HOME")
    base = Path(xdg_cache) if xdg_cache else Path.home() / ".cache"
    return base / "tiptoi-linux" / "firmware" / f"{info.version}.upd"


def download_firmware(
    info: FirmwareInfo,
    *,
    opener: urllib.request.OpenerDirector = https_opener,
    progress=None,
) -> Path:
    """Download the .upd file (verified against the catalog checksum), cached by version."""
    target = firmware_cache_path(info)
    if target.is_file() and target.stat().st_size > 0:
        try:
            if verify_checksum(target.read_bytes(), info.checksum):
                return target
        except OSError:
            pass

    scheme = urllib.parse.urlparse(info.url).scheme
    if scheme != "https":
        raise FirmwareError(_("refusing to download firmware over non-https URL: {url}").format(url=info.url))
    total_hint: int | None = None
    try:
        with opener.open(info.url, timeout=60) as response:
            length_header = response.headers.get("Content-Length")
            if length_header and length_header.isdigit():
                total_hint = int(length_header)
            chunks = []
            done = 0
            while True:
                block = response.read(64 * 1024)
                if not block:
                    break
                chunks.append(block)
                done += len(block)
                if progress is not None:
                    progress(Phase.DOWNLOAD, done, total_hint if total_hint and total_hint >= done else done + 1)
            data = b"".join(chunks)
    except OSError as exc:
        raise FirmwareError(_("failed to download firmware {version}: {error}").format(version=info.version, error=exc)) from exc
    if not data or len(data) > MAX_FIRMWARE_BYTES:
        raise FirmwareError(_("firmware {version} has an unexpected size").format(version=info.version))
    if not verify_checksum(data, info.checksum):
        raise FirmwareError(
            _("firmware checksum mismatch for {version} - refusing to install").format(version=info.version)
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write(target, data)
    return target


def install_firmware(pen: Pen, source: Path, *, info: FirmwareInfo) -> None:
    """Copy the verified .upd onto the pen as update.upd (atomic via temp + rename)."""
    require_mounted(pen)
    destination = pen.mountpoint / FIRMWARE_FILE_NAME
    if destination.exists():
        raise FirmwareError(_("the pen already has a pending firmware update"))
    fd, tmp_path = tempfile.mkstemp(dir=pen.mountpoint, prefix=".update-", suffix=".upd.tmp")
    try:
        data = source.read_bytes()
    except OSError as exc:
        os.close(fd)
        Path(tmp_path).unlink(missing_ok=True)
        raise FirmwareError(_("cannot read firmware file {path}: {error}").format(path=source, error=exc)) from exc
    if not verify_checksum(data, info.checksum):
        os.close(fd)
        Path(tmp_path).unlink(missing_ok=True)
        raise FirmwareError(_("firmware checksum mismatch for {version} - refusing to install").format(version=info.version))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, destination)
        fsync_directory(pen.mountpoint)
    except OSError as exc:
        Path(tmp_path).unlink(missing_ok=True)
        raise FirmwareError(_("cannot write firmware update to the pen: {error}").format(error=exc)) from exc


def read_pen_log(pen: Pen) -> dict[str, str]:
    """Parse the pen's .tiptoi.log key=value metadata (serialNumber, mcu, language, ...).

    A missing or unreadable log yields an empty dict - the pen simply shows fewer details.
    """
    log_path = pen.mountpoint / ".tiptoi.log"
    try:
        text = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    fields: dict[str, str] = {}
    for line in text.splitlines():
        key, sep, value = line.partition("=")
        if sep and key.strip():
            fields.setdefault(key.strip(), value.strip())
    return fields


def _atomic_write(path: Path, data: bytes) -> None:
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, prefix=".firmware-", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    except BaseException:
        Path(tmp_path).unlink(missing_ok=True)
        raise

"""Tests for the pen firmware module (tiptoi_linux.pen.firmware)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tiptoi_linux.pen import Pen
from tiptoi_linux.pen._base import require_mounted
from tiptoi_linux.pen.firmware import (
    FIRMWARE_FILE_NAME,
    FirmwareError,
    FirmwareInfo,
    checksum_of,
    install_firmware,
    parse_firmware_info,
    read_pen_log,
    verify_checksum,
)

CSV_WITH_FIRMWARE = (
    "CSV file version,Firmware version,Firmware checksum,Firmware download address\n"
    "26092403,6GE027,1872396468,"
    "https://cdn.ravensburger.de/db/Firmware-Files/de/27/REV12/Update6E.upd\n"
    "Items._id,Items._version,Items._url,Items._fileName\n"
    "150,20190529,https://cdn.ravensburger.de/db/applications/X.gme,X\n"
)

CSV_WITHOUT_FIRMWARE = (
    "CSV file version,Firmware version,Firmware checksum,Firmware download address\n"
    "Items._id,Items._version,Items._url,Items._fileName\n"
)


class ParseFirmwareInfoTests(unittest.TestCase):
    def test_parses_header_row(self) -> None:
        info = parse_firmware_info(CSV_WITH_FIRMWARE)
        self.assertIsNotNone(info)
        self.assertEqual(info.version, "6GE027")
        self.assertEqual(info.checksum, 1872396468)
        self.assertEqual(info.generation, "REV12")

    def test_missing_firmware_returns_none(self) -> None:
        self.assertIsNone(parse_firmware_info(CSV_WITHOUT_FIRMWARE))

    def test_empty_text_returns_none(self) -> None:
        self.assertIsNone(parse_firmware_info(""))


class ChecksumTests(unittest.TestCase):
    def test_sum_of_bytes(self) -> None:
        self.assertEqual(checksum_of(b"\x01\x02\x03"), 6)

    def test_verify_roundtrip(self) -> None:
        data = bytes(range(256)) * 100
        self.assertTrue(verify_checksum(data, checksum_of(data)))
        self.assertFalse(verify_checksum(data, checksum_of(data) + 1))


class InstallFirmwareTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.pen = Pen(mountpoint=self.root, source=None)
        self.payload = b"ANYKA106" + bytes(range(200))
        self.info = FirmwareInfo(version="TEST01", checksum=checksum_of(self.payload), url="https://example.invalid/x.upd")
        self.source = self.root / "download" / "firmware.upd"
        self.source.parent.mkdir()
        self.source.write_bytes(self.payload)

    def test_writes_update_upd_atomically(self) -> None:
        install_firmware(self.pen, self.source, info=self.info)
        destination = self.root / FIRMWARE_FILE_NAME
        self.assertTrue(destination.is_file())
        self.assertEqual(destination.read_bytes(), self.payload)
        self.assertFalse(any(p.name.startswith(".update-") for p in self.root.iterdir()))

    def test_refuses_when_update_already_pending(self) -> None:
        (self.root / FIRMWARE_FILE_NAME).write_bytes(b"other")
        with self.assertRaises(FirmwareError):
            install_firmware(self.pen, self.source, info=self.info)

    def test_refuses_checksum_mismatch(self) -> None:
        bad = FirmwareInfo(version="TEST01", checksum=self.info.checksum + 1, url=self.info.url)
        with self.assertRaises(FirmwareError):
            install_firmware(self.pen, self.source, info=bad)


class PenLogTests(unittest.TestCase):
    def test_parses_key_value_lines(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        pen = Pen(mountpoint=root, source=None)
        (root / ".tiptoi.log").write_text(
            "serialNumber=123456789\nmcu=ANYKA\nlanguage=GERMAN\nfirmwareversion=6GE027\n",
            encoding="utf-8",
        )
        fields = read_pen_log(pen)
        self.assertEqual(fields["serialNumber"], "123456789")
        self.assertEqual(fields["firmwareversion"], "6GE027")

    def test_missing_log_is_empty(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        pen = Pen(mountpoint=Path(tmp.name), source=None)
        self.assertEqual(read_pen_log(pen), {})


if __name__ == "__main__":
    unittest.main()

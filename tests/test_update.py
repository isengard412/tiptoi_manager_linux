"""Tests for the GitHub self-update check."""

from __future__ import annotations

import json
import unittest

from tiptoi_linux.update import ReleaseInfo, fetch_latest_release, is_newer, parse_version


class VersionCompareTests(unittest.TestCase):
    def test_newer_release(self) -> None:
        self.assertTrue(is_newer("v0.2.0", "v0.1.0"))
        self.assertFalse(is_newer("v0.1.0", "v0.2.0"))

    def test_equal_versions_are_not_newer(self) -> None:
        self.assertFalse(is_newer("1.2.3", "1.2.3"))

    def test_dev_build_is_older_than_any_release(self) -> None:
        self.assertTrue(is_newer("0.0.1", "0.0.0.dev0"))
        self.assertFalse(is_newer("0.0.0", "0.0.0.dev0"))

    def test_multi_digit_components(self) -> None:
        self.assertGreater(parse_version("1.10.0"), parse_version("1.9.0"))


class _FakeResponse:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, _limit=-1):
        return self._payload


class _FakeOpener:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def open(self, url, timeout=None):
        return _FakeResponse(self._payload)


class FetchLatestReleaseTests(unittest.TestCase):
    def test_parses_tag_and_url(self) -> None:
        payload = json.dumps({"tag_name": "v0.3.1", "html_url": "https://gh/x"}).encode()
        info = fetch_latest_release(opener=_FakeOpener(payload))  # type: ignore[arg-type]
        self.assertEqual(info, ReleaseInfo(version="v0.3.1", url="https://gh/x"))

    def test_no_release_returns_none(self) -> None:
        payload = json.dumps({"message": "Not Found"}).encode()
        self.assertIsNone(fetch_latest_release(opener=_FakeOpener(payload)))  # type: ignore[arg-type]

    def test_garbage_raises(self) -> None:
        from tiptoi_linux.update import UpdateCheckError

        with self.assertRaises(UpdateCheckError):
            fetch_latest_release(url="not-a-url", opener=_FakeOpener(b""))  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()

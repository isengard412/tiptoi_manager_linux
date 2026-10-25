"""Test runner for the whole suite.

Usage: python -m tests.run

WHY not plain `python -m unittest discover`: unittest keeps every TestCase
instance (and through them every Qt widget) alive until interpreter
finalization, where shiboken's teardown races Qt's own and can abort the
process ("corrupted double-linked list" / SIGSEGV *after* "OK"). This runner
reports results normally, flushes, and then exits the process before that
teardown begins - failures still produce a non-zero exit code.
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def main(argv: list[str] | None = None) -> int:
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    argv = sys.argv[1:] if argv is None else argv
    verbosity = 2 if "-v" in argv else 1

    # Pin the test language to English before any tiptoi module is imported (i18n binds
    # gettext at import time); tests/__init__.py does the same for `unittest discover`.
    os.environ["LANGUAGE"] = "C"

    loader = unittest.TestLoader()
    suite = loader.discover(str(REPO_ROOT / "tests"), top_level_dir=str(REPO_ROOT))
    result = unittest.TextTestRunner(verbosity=verbosity).run(suite)
    ok = result.wasSuccessful()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0 if ok else 1)


if __name__ == "__main__":
    main()

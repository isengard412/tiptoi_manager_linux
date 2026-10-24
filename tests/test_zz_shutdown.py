"""Last test module (alphabetically): drain Qt's deferred deletes while the
interpreter is still fully alive.

The suite creates many top-level widgets across modules; letting them be
collected during interpreter shutdown races Qt's own teardown and can abort
the process ("corrupted double-linked list" / SIGSEGV after "OK"). Running
the same drain that gui.main() performs at exit makes the suite terminate
cleanly.
"""

from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtCore import QEvent

    _PYSIDE6_AVAILABLE = True
except ImportError:
    _PYSIDE6_AVAILABLE = False


@unittest.skipUnless(_PYSIDE6_AVAILABLE, "PySide6 is not installed")
class ShutdownDrainTests(unittest.TestCase):
    def test_drain_deferred_events(self) -> None:
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            return
        import gc

        gc.collect()
        app.processEvents()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        app.processEvents()

"""Node-Mate entry: single-instance guard + Qt WebEngine bootstrap."""

from __future__ import annotations

import sys
import os

# Silence noisy Qt DPI warnings on Windows 11
os.environ["QT_LOGGING_RULES"] = "qt.qpa.window=false"

# Path injection for PyQt6-WebEngine DLL issues on Windows
if sys.platform == "win32":
    try:
        from pathlib import Path
        # Try finding binaries relative to common site-packages locations
        _me = Path(__file__).resolve()
        _sp = _me.parent.parent / ".venv" / "Lib" / "site-packages"
        for candidate in [
            _sp / "PyQt6" / "Qt6" / "bin",
            _sp / "PyQt6_WebEngine_Qt6" / "Qt6" / "bin",
            Path(sys.prefix) / "Lib" / "site-packages" / "PyQt6" / "Qt6" / "bin",
        ]:
            if candidate.exists():
                os.add_dll_directory(str(candidate))
                os.environ["PATH"] = str(candidate) + os.pathsep + os.environ.get("PATH", "")
    except Exception:
        pass

from pathlib import Path


def _win32_dpi_awareness_early() -> None:
    """
    Align physical pixels with automation (PrintWindow / client coords) before Qt touches DPI.
    shcore.SetProcessDpiAwareness may fail if another loader set context first — try fallbacks.
    """
    if sys.platform != "win32":
        return
    import ctypes

    try:
        # 2 = PROCESS_PER_MONITOR_DPI_AWARE
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            # 1 = PROCESS_SYSTEM_DPI_AWARE (Gemini suggestion path)
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass


from PyQt6.QtCore import QDir, QLockFile, Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication

from nodemate.lightweight_main import LightweightMainWindow


def _single_instance_lock() -> QLockFile | None:
    lock_path = QDir.tempPath() + "/NodeMateSingleInstance.lock"
    lock = QLockFile(lock_path)
    lock.setStaleLockTime(10_000)
    if not lock.tryLock(200):
        return None
    return lock


def main() -> int:
    _win32_dpi_awareness_early()
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts, True)

    lock = _single_instance_lock()
    if lock is None:
        if sys.platform == "win32":
            import ctypes

            ctypes.windll.user32.MessageBoxW(
                0,
                "Node-Mate is already running.",
                "Node-Mate",
                0x40,
            )
        return 0

    app = QApplication(sys.argv)
    _f = app.font()
    if _f.pointSize() <= 0:
        _f.setPointSize(10)
        app.setFont(_f)
    app.setApplicationName("Node-Mate")
    app.setOrganizationName("NodeMate")
    w = LightweightMainWindow()
    w.show()
    rc = app.exec()
    lock.unlock()
    return int(rc)


if __name__ == "__main__":
    raise SystemExit(main())

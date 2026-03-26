"""Windows-only: IsHungAppWindow and HWND lookup by PID (lightweight ctypes)."""

from __future__ import annotations

import sys

if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)

    IsHungAppWindow = user32.IsHungAppWindow
    IsHungAppWindow.argtypes = (wintypes.HWND,)
    IsHungAppWindow.restype = wintypes.BOOL

    GetWindowThreadProcessId = user32.GetWindowThreadProcessId
    GetWindowThreadProcessId.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.DWORD))
    GetWindowThreadProcessId.restype = wintypes.DWORD

    IsWindowVisible = user32.IsWindowVisible
    IsWindowVisible.argtypes = (wintypes.HWND,)
    IsWindowVisible.restype = wintypes.BOOL

    EnumWindows = user32.EnumWindows
    EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def hwnds_for_pid(pid: int) -> list[int]:
        results: list[int] = []

        def cb(hwnd: int, _lp: int) -> bool:
            p = wintypes.DWORD()
            GetWindowThreadProcessId(hwnd, ctypes.byref(p))
            if int(p.value) == pid: # Include non-visible for hidden capture
                results.append(int(hwnd))
            return True

        EnumWindows(EnumWindowsProc(cb), 0)
        return results

    def capture_hidden_window(hwnd: int):
        """
        Captures a window even if it is obscured or minimized using PrintWindow.
        Returns a PIL Image or None.
        """
        import win32gui
        import win32ui
        import win32con
        from PIL import Image

        try:
            # Get window dimensions
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            width = max(right - left, 1)
            height = max(bottom - top, 1)

            # Create device contexts
            hwnd_dc = win32gui.GetWindowDC(hwnd)
            mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
            save_dc = mfc_dc.CreateCompatibleDC()

            # Create bitmap
            save_bit_map = win32ui.CreateBitmap()
            save_bit_map.CreateCompatibleBitmap(mfc_dc, width, height)
            save_dc.SelectObject(save_bit_map)

            # Use PrintWindow (PW_RENDERFULLCONTENT = 2)
            # This works for most modern apps (Electron, etc.)
            result = ctypes.windll.user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), 2)
            
            bmp_info = save_bit_map.GetInfo()
            bmp_str = save_bit_map.GetBitmapBits(True)
            
            img = Image.frombuffer(
                'RGB',
                (bmp_info['bmWidth'], bmp_info['bmHeight']),
                bmp_str, 'raw', 'BGRX', 0, 1
            )

            # Clean up
            win32gui.DeleteObject(save_bit_map.GetHandle())
            save_dc.DeleteDC()
            mfc_dc.DeleteDC()
            win32gui.ReleaseDC(hwnd, hwnd_dc)

            if result == 1:
                return img
            return None
        except Exception:
            return None

    def process_has_hung_window(pid: int) -> bool:
        for h in hwnds_for_pid(pid):
            if IsHungAppWindow(h) and IsWindowVisible(h):
                return True
        return False

    def preferred_click_hwnd(root_hwnd: int) -> int:
        """
        Electron/Chromium often ignores PostMessage on the top-level HWND; use the
        largest visible render child when present.
        """
        import win32gui

        best_h = int(root_hwnd)
        best_a = 0

        def visit(hwnd: int, _extra: object) -> bool:
            nonlocal best_h, best_a
            try:
                if not win32gui.IsWindowVisible(hwnd):
                    return True
                cls = win32gui.GetClassName(hwnd)
                if "Chrome_RenderWidgetHostHWND" not in cls and "Intermediate D3D" not in cls:
                    return True
                left, top, right, bottom = win32gui.GetWindowRect(hwnd)
                a = max(0, right - left) * max(0, bottom - top)
                if a > best_a and a > 8000:
                    best_a = a
                    best_h = int(hwnd)
            except Exception:
                pass
            return True

        try:
            win32gui.EnumChildWindows(int(root_hwnd), visit, None)
        except Exception:
            pass
        return best_h

    def map_client_point_to_hwnd(root_hwnd: int, click_hwnd: int, cx: int, cy: int) -> tuple[int, int]:
        """Map client coords on root to client coords on click_hwnd (same screen point)."""
        import win32gui

        if int(click_hwnd) == int(root_hwnd):
            return int(cx), int(cy)
        try:
            sx, sy = win32gui.ClientToScreen(int(root_hwnd), (int(cx), int(cy)))
            return win32gui.ScreenToClient(int(click_hwnd), (sx, sy))
        except Exception:
            return int(cx), int(cy)

    def _title_match_tokens(title_hint: str) -> list[str]:
        s = (title_hint or "").lower()
        for junk in ("(exe)", "(browser)", ".exe", "(user)", "(docker)"):
            s = s.replace(junk, " ")
        parts = [p for p in s.split() if len(p) >= 2]
        if not parts and s.strip():
            return [s.strip()]
        return parts

    def best_hwnd_for_pid_with_title_hint(
        pid: int,
        title_hint: str,
        *,
        min_w: int = 200,
        min_h: int = 200,
    ) -> int | None:
        """
        Prefer the largest visible window whose title contains a token from the node name
        (e.g. 'Grass' matches 'grass — dashboard'). Falls back to largest window if no title hit.
        """
        import win32gui

        tokens = _title_match_tokens(title_hint)
        matched: list[tuple[int, int]] = []
        all_sized: list[tuple[int, int]] = []

        for hwnd in hwnds_for_pid(pid):
            try:
                left, top, right, bottom = win32gui.GetWindowRect(hwnd)
                w, h = right - left, bottom - top
                if w < min_w or h < min_h:
                    continue
                area = w * h
                title = (win32gui.GetWindowText(hwnd) or "").lower()
                all_sized.append((area, int(hwnd)))
                if tokens and any(t in title for t in tokens):
                    matched.append((area, int(hwnd)))
            except Exception:
                continue

        if matched:
            matched.sort(key=lambda x: -x[0])
            return matched[0][1]
        if all_sized:
            all_sized.sort(key=lambda x: -x[0])
            return all_sized[0][1]
        return None
else:
    def hwnds_for_pid(pid: int) -> list[int]:
        return []

    def process_has_hung_window(pid: int) -> bool:
        return False

    def preferred_click_hwnd(root_hwnd: int) -> int:
        return root_hwnd

    def map_client_point_to_hwnd(root_hwnd: int, click_hwnd: int, cx: int, cy: int) -> tuple[int, int]:
        return cx, cy

    def best_hwnd_for_pid_with_title_hint(
        pid: int,
        title_hint: str,
        *,
        min_w: int = 200,
        min_h: int = 200,
    ) -> int | None:
        return None

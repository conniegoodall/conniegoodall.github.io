"""
Logout Detector: Multi-tier detection of whether a DePIN app is logged out.
Veto Fix: If any login indicator is found, it overrides dashboard signals.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Optional

import win32gui

logger = logging.getLogger(__name__)

# Keywords that suggest the app is on a login screen (Updated for Google OAuth flows)
_LOGOUT_KEYWORDS = re.compile(
    r"\b(sign.?in|log.?in|login|signin|sign.?up|signup|create.?account|"
    r"enter.?your|email.?address|forgot.?password|reset.?password|"
    r"welcome.?back|get.?started|google|choose.?an.?account|continue.?with)\b",
    re.I,
)

# Keywords that suggest the app is logged in / on a dashboard
_LOGGED_IN_KEYWORDS = re.compile(
    r"\b(dashboard|connected|sign.?out|log.?out|logout|my.?account|"
    r"earnings|rewards|profile|settings|node.?running|"
    r"uptime|points|balance|disconnect|stop.?node|active|completed|core.?node)\b",
    re.I,
)

# Wallet address pattern (common in DePIN apps)
_WALLET_PATTERN = re.compile(r"0x[a-fA-F0-9]{32,42}")

# Strong login indicators (VETO trigger)
_STRONG_LOGIN = re.compile(
    r"\b(sign.?in|log.?in|login|enter.?password|sign.?up|signup|google)\b",
    re.I,
)


def detect_logout_state(
    hwnd: int,
    use_vlm: bool = False, # Parameter kept for compatibility but ignored
    pil_image=None,
) -> str:
    if not win32gui.IsWindow(hwnd):
        return "unknown"

    # --- TIER 1: UIA scan (instant, 0% GPU) ---
    tier1 = _tier1_uia_scan(hwnd)
    if tier1 == "logged_out":
        logger.info(f"Logout detector tier 1 (UIA): {tier1}")
        return "logged_out"

    # --- TIER 2: OCR snapshot (fast, 0% GPU) ---
    tier2 = _tier2_ocr_scan(hwnd, pil_image)
    if tier2 == "logged_out":
        logger.info(f"Logout detector tier 2 (OCR): {tier2}")
        return "logged_out"

    # If either tier says logged_in, and NO tier said logged_out, return logged_in
    if tier1 == "logged_in" or tier2 == "logged_in":
        return "logged_in"

    logger.info("Logout detector: all tiers inconclusive → unknown")
    return "unknown"


def _tier1_uia_scan(hwnd: int) -> str:
    """Check UIA tree with a strict veto for login elements. Avoids deep scans to prevent freezing."""
    try:
        # Check window class to avoid freezing Chromium/Electron apps
        cls_name = win32gui.GetClassName(hwnd)
        if "Chrome" in cls_name or "Edge" in cls_name or "Mozilla" in cls_name:
            # Chromium UIA tree building freezes the browser and system mouse
            return "unknown"
            
        from pywinauto import Application

        app = Application(backend="uia").connect(handle=hwnd, timeout=1.5)
        win = app.window(handle=hwnd)

        login_signals = 0
        dashboard_signals = 0

        # Only get top-level children to prevent deep recursive freezing
        for el in win.children():
            try:
                if not el.is_visible():
                    continue
                txt = (el.window_text() or "").strip()
                
                info = getattr(el, "element_info", None)
                ctrl = str(getattr(info, "control_type", "")).lower() if info else ""
                auto_id = str(getattr(info, "automation_id", "")).lower() if info else ""

                blob = f"{txt} {auto_id}".lower()

                if _STRONG_LOGIN.search(blob) or _LOGOUT_KEYWORDS.search(blob):
                    login_signals += 1
                
                if "edit" in ctrl and any(k in blob for k in ("password", "email", "user", "username")):
                    login_signals += 1

                if _LOGGED_IN_KEYWORDS.search(blob):
                    dashboard_signals += 1
                
                if _WALLET_PATTERN.search(blob):
                    dashboard_signals += 1

            except Exception:
                continue

        if login_signals >= 1:
            return "logged_out"
        
        if dashboard_signals >= 2:
            return "logged_in"

    except Exception as e:
        logger.debug(f"Tier 1 UIA scan failed: {e}")

    return "unknown"


def _tier2_ocr_scan(hwnd: int, pil_image=None) -> str:
    """OCR the window with a strict veto for visible login buttons/text."""
    try:
        if pil_image is None:
            # We use a basic capture here to avoid 0% GPU requirement
            from nodemate.win32_util import capture_hidden_window # Assuming it's moved or accessible
            pil_image = capture_hidden_window(hwnd)

        if pil_image is None:
            return "unknown"

        # Use pytesseract directly if uia_composer is gone
        import pytesseract
        ocr_text = pytesseract.image_to_string(pil_image).lower()
        
        if not ocr_text or len(ocr_text.strip()) < 5:
            return "unknown"

        # STRICT VETO: If "Sign In", "Login", or "Google" text is detected, the state is logged_out.
        if _STRONG_LOGIN.search(ocr_text) or _LOGOUT_KEYWORDS.search(ocr_text):
            return "logged_out"

        # Only check dashboard hits if the screen is clean of login text
        if _LOGGED_IN_KEYWORDS.search(ocr_text) or _WALLET_PATTERN.search(ocr_text):
            return "logged_in"

    except Exception as e:
        logger.debug(f"Tier 2 OCR scan failed: {e}")

    return "unknown"
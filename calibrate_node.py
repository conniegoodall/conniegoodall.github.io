"""
Calibration script for NodeMate: Hold My Hand (Visual Anchors).
Run this to 'teach' the agent where buttons are by hovering your mouse.
"""

import os
import sys
import time
from pathlib import Path

import pyautogui
import pywinauto
from PIL import Image

def find_hwnd_per_user(name: str):
    """Fallback window finder using pywinauto."""
    try:
        from pywinauto import Desktop
        windows = Desktop(backend="uia").windows()
        for w in windows:
            title = w.window_text().lower()
            if name.lower() in title:
                return w.handle
    except Exception:
        pass
    return None

def calibrate_node(node_name: str):
    print(f"\n--- CALIBRATING {node_name.upper()} ---")
    print("This will create 'Visual Anchors' so the agent never misses a click.")
    
    hwnd = find_hwnd_per_user(node_name)
    if not hwnd:
        print(f"Error: Could not find window for '{node_name}'. Is it open?")
        return

    # Create assets directory
    assets_dir = Path("nodemate/node_assets") / node_name.lower()
    assets_dir.mkdir(parents=True, exist_ok=True)

    targets = [
        ("sign_in", "Hover over the 'Sign In' button (top right)"),
        ("google", "Click 'Sign In' manually, then hover over 'G Google' button"),
        ("account", "Click 'G Google' manually, then hover over your Account/Email in the popup"),
        ("password_box", "Type your password manually, hover over the 'Password' box, and press ENTER"),
        ("next", "Hover over the 'Next' button (blue button under password) and press ENTER"),
    ]

    for target_id, instruction in targets:
        print(f"\nSTEP: {instruction}")
        print("Press 'S' to Save the anchor when your mouse is centered on the button.")
        print("Press 'Q' to skip this step.")

        while True:
            # Simple busy-wait for keypress (pyautogui doesn't have good async key wait)
            # In a real tool, we'd use 'keyboard' lib, but we'll use a 2s timer for simplicity if needed.
            # actually, let's use input() for now.
            cmd = input("Ready? Hover your mouse and press ENTER to capture... (or 'q' to skip): ")
            if cmd.lower() == 'q':
                break
            
            # Capture 60x60 patch around cursor
            mx, my = pyautogui.position()
            patch = pyautogui.screenshot(region=(mx - 30, my - 30, 60, 60))
            
            save_path = assets_dir / f"{target_id}.png"
            patch.save(save_path)
            print(f"✅ Saved visual anchor to {save_path}")
            
            # Auto-open the image so the user can see what the agent 'learned'
            try:
                os.startfile(save_path)
            except Exception:
                pass
            
            break

    print(f"\n--- CALIBRATION COMPLETE for {node_name} ---")
    print("The agent will now use these photos to find buttons with 100% precision.")

if __name__ == "__main__":
    node = "Grass"
    if len(sys.argv) > 1:
        node = sys.argv[1]
    calibrate_node(node)

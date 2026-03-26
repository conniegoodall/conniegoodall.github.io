import pywinauto
import win32gui
import sys

def main():
    hwnds = []
    def callback(w, _):
        if win32gui.IsWindowVisible(w) and "Grass" in win32gui.GetWindowText(w):
            hwnds.append(w)
    win32gui.EnumWindows(callback, None)
    
    if not hwnds:
        print("Grass not found")
        return

    hwnd = hwnds[0]
    print(f"Dumping UIA for HWND {hwnd} ({win32gui.GetWindowText(hwnd)})")
    
    try:
        app = pywinauto.Application(backend="uia").connect(handle=hwnd, timeout=5)
        dlg = app.top_window()
        dlg.print_control_identifiers()
    except Exception as e:
        print(f"UIA Dump failed: {e}")

if __name__ == "__main__":
    main()

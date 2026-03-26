import win32gui

def main():
    def callback(w, _):
        title = win32gui.GetWindowText(w)
        if title:
            print(f"HWND: {w} | Title: '{title}'")
            
    win32gui.EnumWindows(callback, None)

if __name__ == "__main__":
    main()

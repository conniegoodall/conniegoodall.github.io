import psutil
import win32gui
import win32process

def main():
    print("Listing all processes with 'grass' in them...")
    found = False
    for proc in psutil.process_iter(['pid', 'name', 'exe']):
        try:
            pname = proc.info['name'].lower()
            if 'grass' in pname:
                print(f"PID: {proc.info['pid']} | Name: {proc.info['name']} | Exe: {proc.info['exe']}")
                found = True
                
                # Try to find all windows for this PID
                def callback(hwnd, windows):
                    if win32gui.IsWindowVisible(hwnd):
                        _, pid = win32process.GetWindowThreadProcessId(hwnd)
                        if pid == proc.info['pid']:
                            windows.append((hwnd, win32gui.GetWindowText(hwnd)))
                
                windows = []
                win32gui.EnumWindows(callback, windows)
                for h, t in windows:
                    print(f"  -> HWND: {h} | Title: '{t}'")
                    
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
            
    if not found:
        print("No process found with 'grass' in the name.")

if __name__ == "__main__":
    main()

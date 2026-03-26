"""Test PID-based pywinauto connection to optimai-corenode."""
import psutil
from pywinauto import Application

# Find all optimai-corenode PIDs
pids = []
for proc in psutil.process_iter(['pid', 'name']):
    try:
        if 'optimai' in (proc.info['name'] or '').lower():
            pids.append(proc.info['pid'])
    except (psutil.AccessDenied, psutil.NoSuchProcess):
        pass

print(f"Found PIDs: {pids}")

for pid in pids:
    try:
        app = Application(backend="uia").connect(process=pid, timeout=3)
        wins = app.windows()
        for w in wins:
            try:
                if w.is_visible():
                    title = w.window_text()
                    print(f"PID {pid}: visible window = {repr(title)}")
                    
                    edits = w.descendants(control_type="Edit")
                    for e in edits:
                        try:
                            if e.is_visible():
                                r = e.rectangle()
                                print(f"  EDIT: text={repr(e.window_text())} at ({r.left},{r.top})-({r.right},{r.bottom})")
                        except Exception:
                            pass
                    
                    buttons = w.descendants(control_type="Button")
                    for b in buttons:
                        try:
                            txt = b.window_text()
                            if txt.strip():
                                print(f"  BUTTON: {repr(txt)}")
                        except Exception:
                            pass
            except Exception:
                pass
    except Exception as e:
        print(f"PID {pid}: connect failed - {e}")

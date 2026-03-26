import sys
import win32gui
import json
import os
import tkinter as tk
from pathlib import Path

NODE_MEMORY_PATH = Path(os.environ.get("LOCALAPPDATA", "")) / "NodeMate" / "node_memory.json"

def main():
    hwnds = []
    def callback(w, _):
        if win32gui.IsWindowVisible(w) and "Grass" in win32gui.GetWindowText(w):
            hwnds.append(w)
    win32gui.EnumWindows(callback, None)
    
    if not hwnds:
        print("ERROR: Grass window not found. Please open Grass first.")
        return
        
    hwnd = hwnds[0]
    win32gui.SetForegroundWindow(hwnd)
    rect = win32gui.GetWindowRect(hwnd)
    left, top, right, bottom = rect
    w = right - left
    h = bottom - top

    root = tk.Tk()
    root.title("MANUAL AI TRAINING")
    root.geometry(f"{w}x{h}+{left}+{top}")
    root.overrideredirect(True) # borderless
    root.attributes("-alpha", 0.4) # translucent
    root.attributes("-topmost", True)
    root.config(bg="red")
    
    lbl = tk.Label(root, text="CLICK EXACTLY ON 'SIGN IN' NOW...", bg="red", fg="white", font=("Arial", 14, "bold"))
    lbl.pack(pady=40)
    
    def on_click(event):
        x, y = event.x, event.y
        y_frac = y / h
        x_frac = x / w
        print(f"Clicked: {x_frac:.4f}, {y_frac:.4f}")
        
        cfg_path = Path(os.environ.get("LOCALAPPDATA", "")) / "NodeMate" / "config.json"
        
        # We find the Node ID to save the memory to
        node_id = "unknown"
        if cfg_path.exists():
            with open(cfg_path, 'r') as f:
                try:
                    cfg = json.load(f)
                    nodes = cfg.get("nodes", [])
                    # Find Grass node, or use the first one
                    for n in nodes:
                        if "grass" in n.get("name", "").lower():
                            node_id = n.get("id", "unknown")
                            break
                    if node_id == "unknown" and nodes:
                        node_id = nodes[0].get("id", "unknown")
                except Exception as e:
                    print(f"Error reading config: {e}")
        
        if NODE_MEMORY_PATH.exists():
            with open(NODE_MEMORY_PATH, 'r') as fid:
                try:
                    mem = json.load(fid)
                except:
                    mem = {"version": 1, "nodes": {}}
        else:
            NODE_MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
            mem = {"version": 1, "nodes": {}}
            
        if node_id not in mem.get("nodes", {}):
            mem.setdefault("nodes", {})[node_id] = {"coords": {}, "coord_space": "client", "updated_unix": 0}
            
        mem["nodes"][node_id].setdefault("coords", {})["Sign In"] = [y_frac, x_frac]
        
        with open(NODE_MEMORY_PATH, 'w') as fid:
            json.dump(mem, fid, indent=2)
            
        print("SUCCESS! 'Sign In' coordinates learned permanently.")
        root.destroy()

    root.bind("<Button-1>", on_click)
    root.mainloop()

if __name__ == "__main__":
    main()

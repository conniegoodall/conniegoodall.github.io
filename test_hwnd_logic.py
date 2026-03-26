import time
import win32gui
from nodemate.config_store import load_config, NodeEntry
from nodemate.launcher import find_pids_for_node
from nodemate.win32_util import hwnds_for_pid

# Create dummy node for OptimAI Core Node
node = NodeEntry.new("exe", "OptimAI Core Node")
node.exe_path = "OptimAI Core Node"

pids = find_pids_for_node(node)
print(f"Found PIDs: {pids}")

best_area = 0
target_hwnd = None
for pid in pids:
    for hwnd in hwnds_for_pid(pid):
        try:
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            w = right - left
            h = bottom - top
            area = w * h
            title = win32gui.GetWindowText(hwnd)
            print(f"PID {pid} -> HWND {hwnd} | Rect: {w}x{h} | Area: {area} | Title: '{title}'")
            if w > 200 and h > 200 and area > best_area:
                best_area = area
                target_hwnd = hwnd
        except Exception as e:
            print(f"Error on hwnd {hwnd}: {e}")

print(f"Selected target_hwnd: {target_hwnd} with area {best_area}")

"""
Lightweight Watchdog - Zero GPU Usage
Process monitoring with psutil, zombie detection, and manual control.
"""

from __future__ import annotations

import psutil
import time
import threading
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal, QTimer

from nodemate.config_store import NodeEntry
from nodemate.logout_detector import detect_logout_state

logger = logging.getLogger(__name__)


class LightweightWatchdog(QObject):
    """Ultra-lightweight watchdog using psutil only - 0% GPU usage."""
    
    # Signals for UI updates
    node_status_changed = pyqtSignal(str, str, str)  # node_id, status, message
    alert_required = pyqtSignal(str, str)  # node_name, screenshot_path
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_active = False
        self.nodes: Dict[str, NodeEntry] = {}
        self.node_processes: Dict[str, int] = {}  # node_id -> pid
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self._monitor_nodes)
        
        # Zombie detection settings
        self.zombie_cpu_threshold = 0.2  # %
        self.zombie_ram_threshold = 50 * 1024 * 1024  # 50MB
        self.zombie_duration = 30  # seconds before considering zombie
        
        # Process state tracking
        self.node_states: Dict[str, Dict] = {}  # node_id -> state info
        self.last_global_launch_time = datetime.now() - timedelta(hours=1)
        self.current_stagger_delay = 0  # Holds the delay requirement of the previously launched app
        
        logger.info("LightweightWatchdog initialized")
    
    def start_monitoring(self, nodes: List[NodeEntry]) -> None:
        """Start monitoring the given nodes."""
        self.nodes = {node.id: node for node in nodes}
        self.is_active = True
        
        # Initialize node states
        for node in nodes:
            if node.id not in self.node_states:
                self.node_states[node.id] = {
                    'last_check': datetime.now(),
                    'last_restart': datetime.now() - timedelta(minutes=5),
                    'restart_count': 0,
                    'suspicious_count': 0,
                    'zombie_since': None
                }
        
        # Start monitoring every 60 seconds (lighter on resources)
        self.monitor_timer.start(10000) # Check every 10 seconds (was 60s)
        # Trigger first check immediately instead of waiting 60s
        QTimer.singleShot(100, self._monitor_nodes)
        logger.info(f"Lightweight watchdog started for {len(nodes)} nodes")
    
    def _monitor_nodes(self) -> None:
        """Monitor all nodes for issues."""
        if not self.is_active:
            return
            
        # Run in a background thread to prevent UI/mouse freezing
        threading.Thread(target=self._monitor_nodes_thread, daemon=True).start()
            
    def _monitor_nodes_thread(self) -> None:
        current_time = datetime.now()
        
        # Batch process discovery ONCE for all nodes to prevent CPU spikes and freezing
        from nodemate.launcher import map_nodes_to_pids
        nodes_list = list(self.nodes.values())
        if not nodes_list:
            return
            
        # We no longer sort alphabetically here.
        # By leaving nodes_list in its original order (which matches the 'ticked' order from the main UI),
        # the watchdog will launch apps strictly in the order they appear in the Blue Box.
            
        all_pids_map = map_nodes_to_pids(nodes_list)
        
        for node in nodes_list:
            if not node.enabled:
                continue
                
            logger.info(f"Checking node {node.name} ({node.id})")
            try:
                node_pids = all_pids_map.get(node.id, [])
                launched = self._check_node_health(node, current_time, node_pids)
                
                # STRICT QUEUE ENFORCEMENT:
                # If we just launched an app, we MUST immediately break the loop.
                # This ensures we don't accidentally launch the next app in the same cycle 
                # before the global clock has ticked forward.
                if launched:
                    break
                    
            except Exception as e:
                logger.error(f"CRITICAL Error monitoring {node.name}: {e}", exc_info=True)
    
    def _check_node_health(self, node: NodeEntry, current_time: datetime, pids: List[int]) -> bool:
        """Check individual node health. Returns True if a launch occurred."""
        state = self.node_states[node.id]
        
        if not pids:
            logger.info(f"Node {node.name} process missing. Calling relaunch.")
            # Process missing - relaunch
            return self._handle_missing_process(node, current_time)
        
        logger.info(f"Node {node.name} found with PIDs: {pids}")
        
        self.node_processes[node.id] = pids[0]
        
        # 2. Zombie Detection - check if process is frozen
        is_zombie = False
        zero_cpu = True # Assume true until proven otherwise, but only if we have PIDs
        
        for pid in pids:
            if self._is_zombie_process(pid):
                is_zombie = True
                break
            
            # Check CPU if enabled for this node
            if getattr(node, 'restart_on_zero_cpu', False):
                if 'process_cache' not in state:
                    state['process_cache'] = {}
                    
                if pid not in state['process_cache']:
                    try:
                        proc = psutil.Process(pid)
                        proc.cpu_percent() # Initialize the internal psutil counter
                        state['process_cache'][pid] = proc
                        zero_cpu = False # Just initialized, can't reliably say it's 0 yet
                    except Exception:
                        pass
                else:
                    try:
                        cpu_percent = state['process_cache'][pid].cpu_percent()
                        if cpu_percent > 0.0:
                            zero_cpu = False
                    except Exception:
                        # Process might have died, remove from cache
                        state['process_cache'].pop(pid, None)
                        
        # If the feature is disabled, force zero_cpu to False so it doesn't trigger
        if not getattr(node, 'restart_on_zero_cpu', False):
            zero_cpu = False
        
        if is_zombie:
            if state['zombie_since'] is None:
                state['zombie_since'] = current_time
            
            # If zombie for more than 30 seconds, kill and restart
            if (current_time - state['zombie_since']).total_seconds() > 30:
                logger.warning(f"Zombie process confirmed: {node.name} - killing")
                self._handle_zombie_process(node, pids[0])
                state['zombie_since'] = None
                return False
        else:
            state['zombie_since'] = None
            
        # 2.5 Zero CPU Heartbeat Detection
        if getattr(node, 'restart_on_zero_cpu', False):
            if zero_cpu:
                if state.get('zero_cpu_since') is None:
                    state['zero_cpu_since'] = current_time
                else:
                    zero_cpu_timeout = getattr(node, 'zero_cpu_minutes', 5) * 60
                    time_dead = (current_time - state['zero_cpu_since']).total_seconds()
                    
                    if time_dead > zero_cpu_timeout:
                        logger.warning(f"Node {node.name} has been at 0% CPU for {time_dead}s. Triggering recovery.")
                        state['zero_cpu_since'] = None
                        
                        # Step 1: Try Auto-Clicker first (if configured)
                        if getattr(node, 'auto_click_image_path', ""):
                            logger.info(f"Attempting to auto-click {node.name} to revive it.")
                            self.node_status_changed.emit(node.id, "waiting", "Auto-clicking to revive...")
                            # Run without delay, we assume UI is already loaded since it was running
                            threading.Thread(target=self._run_auto_clicker, args=(node, True), daemon=True).start()
                            # Give it 30 seconds to show CPU activity before next check
                            state['last_check'] = current_time + timedelta(seconds=30) 
                            return False
                        
                        # Step 2: Fallback to full restart if no auto-clicker
                        logger.warning(f"No auto-clicker configured for {node.name}, killing and restarting due to 0% CPU.")
                        self._handle_zombie_process(node, pids[0])
                        return False
            else:
                state['zero_cpu_since'] = None
                
        # 2.8 Docker Container Linked Check
        docker_name = getattr(node, 'docker_name', "")
        if docker_name:
            import subprocess
            try:
                # Silently check if the specific container is running
                result = subprocess.run(
                    ["docker", "inspect", "-f", "{{.State.Running}}", docker_name],
                    capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW
                )
                is_running = result.stdout.strip().lower() == "true"
                if not is_running:
                    logger.warning(f"Linked Docker container '{docker_name}' for {node.name} is down. Restarting container.")
                    self.node_status_changed.emit(node.id, "waiting", f"Starting container {docker_name}...")
                    subprocess.run(
                        ["docker", "start", docker_name],
                        capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW
                    )
                    # We do NOT return False here, because the main .exe is still running. 
                    # We just kicked the container back alive in the background!
            except Exception as e:
                logger.error(f"Failed to check linked Docker container {docker_name}: {e}")
        
        # 3. Logout Gate - check login status (0% GPU)
        # Browsers usually don't need UIA checks and it causes freezing, so skip for browsers
        if getattr(node, 'node_type', '') == 'browser':
            logger.info(f"Node {node.name} is running (PID: {pids[0]}).")
            self.node_status_changed.emit(node.id, "healthy", "Running")
        else:
            hwnd = self._find_window_for_pid(pids[0], node.name)
            if hwnd:
                logger.info(f"Node {node.name} window found: {hwnd}")
                logout_state = detect_logout_state(hwnd)
                self._handle_logout_detection(node, logout_state, hwnd)
            else:
                logger.info(f"Node {node.name} is running but has no visible window yet (PID: {pids[0]}).")
                self.node_status_changed.emit(node.id, "healthy", f"Running (PID: {pids[0]})")
        
        state['last_check'] = current_time
        return False
    
    def _find_node_pids(self, node: NodeEntry) -> List[int]:
        """Find PIDs for a node."""
        from nodemate.launcher import find_pids_for_node
        return find_pids_for_node(node)
    
    def _is_zombie_process(self, pid: int) -> bool:
        """Check if process is REAL system zombie or dead."""
        try:
            proc = psutil.Process(pid)
            # Only consider real OS-level zombies or dead processes
            return proc.status() in [psutil.STATUS_ZOMBIE, psutil.STATUS_DEAD]
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return True # If we can't access it/it's gone, it's effectively dead
    
    def _find_window_for_pid(self, pid: int, name: str) -> Optional[int]:
        """Find a visible window handle for a given PID."""
        import win32process
        import win32gui
        
        found_hwnds = []
        
        def enum_cb(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                _, found_pid = win32process.GetWindowThreadProcessId(hwnd)
                if found_pid == pid:
                    found_hwnds.append(hwnd)
        
        win32gui.EnumWindows(enum_cb, None)
        return found_hwnds[0] if found_hwnds else None

    def _handle_missing_process(self, node: NodeEntry, current_time: datetime) -> bool:
        """Handle missing process - relaunch it with staggered delay and RAM checks. Returns True if launched."""
        state = self.node_states[node.id]
        
        # 0. Check Auto-Start flag
        if not getattr(node, 'auto_start', True):
            self.node_status_changed.emit(node.id, "stopped", "Auto-start disabled")
            return False

        # 1. Global Stagger Check
        # Ensure we don't blast multiple launches too close together across ANY apps
        time_since_last_global = (current_time - self.last_global_launch_time).total_seconds()
        
        # Determine the delay we should be waiting for.
        # Use the delay set on THIS node, but default to 0s if none is set.
        delay_sec = getattr(node, 'start_delay_seconds', 0)
        if delay_sec == 0 and getattr(node, 'start_delay_minutes', 0) > 0:
            delay_sec = node.start_delay_minutes * 60
            
        if delay_sec > 0 and time_since_last_global < delay_sec:
            wait_remaining = int(delay_sec - time_since_last_global)
            self.node_status_changed.emit(node.id, "waiting", f"Staggered: {wait_remaining}s left")
            return False
        elif delay_sec == 0 and time_since_last_global < 2.0:
            # Even if delay is 0, enforce a tiny 2-second global gap so multiple "0 delay" apps don't launch simultaneously
            self.node_status_changed.emit(node.id, "waiting", "Queued...")
            return False

        # 2. RAM Headroom Check ("Heavy" mode)
        if getattr(node, 'wait_for_ram', False):
            # Check if we have at least 1GB free (arbitrary "Heavy" threshold)
            free_ram_gb = psutil.virtual_memory().available / (1024**3)
            if free_ram_gb < 1.0:
                self.node_status_changed.emit(node.id, "waiting", f"Low Memory ({free_ram_gb:.1f}GB free)")
                return False

        # 3. Per-Node Cooldown (avoid rapid restart loops)
        if (current_time - state['last_restart']).total_seconds() < 15:
            return False
        
        logger.info(f"Relaunching {node.name} (Global Stagger OK)")
        
        try:
            from nodemate.launcher import launch_node
            ok, err, pid = launch_node(node)
            
            if ok:
                state['last_restart'] = current_time
                self.last_global_launch_time = current_time
                
                state['restart_count'] += 1
                state['next_launch_allowed_at'] = None 
                self.node_status_changed.emit(node.id, "restarted", "Relaunched")
                return True
            else:
                logger.error(f"Failed to relaunch {node.name}: {err}")
                self.node_status_changed.emit(node.id, "failed", f"Launch Failure: {err}")
                return False
        except Exception as e:
            logger.error(f"Error during relaunch of {node.name}: {e}")
            self.node_status_changed.emit(node.id, "failed", f"Error: {e}")
            return False
    
    def _handle_zombie_process(self, node: NodeEntry, pid: int) -> None:
        """Handle zombie process - kill and restart."""
        try:
            proc = psutil.Process(pid)
            proc.kill() # Direct kill for zombies
            self._handle_missing_process(node, datetime.now())
        except Exception:
            pass
    
    def _handle_logout_detection(self, node: NodeEntry, logout_state: str, hwnd: int) -> None:
        """Handle logout detection - send alert to Telegram."""
        if logout_state == "logged_out":
            from nodemate.win32_util import capture_hidden_window
            img = capture_hidden_window(hwnd)
            
            # Save temporary alert image
            alert_dir = Path.home() / ".nodemate" / "alerts"
            alert_dir.mkdir(parents=True, exist_ok=True)
            path = str(alert_dir / f"{node.name}_logout.png")
            if img:
                img.save(path)
            
            logger.warning(f"⚠️ {node.name} needs login.")
            self.alert_required.emit(node.name, path)
            self.node_status_changed.emit(node.id, "logged_out", "Manual login required")
        elif logout_state == "logged_in":
            self.node_status_changed.emit(node.id, "healthy", "Running")
    
    def stop_monitoring(self) -> None:
        """Stop monitoring nodes."""
        self.is_active = False
        self.monitor_timer.stop()
        logger.info("Lightweight watchdog stopped")

    def get_node_status(self, node_id: str) -> Dict:
        """Get current status of a node."""
        state = self.node_states.get(node_id, {})
        return {
            'status': 'unknown',
            'last_check': state.get('last_check'),
            'restart_count': state.get('restart_count', 0),
            'suspicious_count': state.get('suspicious_count', 0)
        }

    def _run_auto_clicker(self, node: NodeEntry, immediate: bool = False) -> None:
        """Wait for the app to load, then search for the button image and click it."""
        import time
        import pyautogui
        import os
        
        delay = getattr(node, 'auto_click_delay', 15)
        image_path = getattr(node, 'auto_click_image_path', "")
        
        if not os.path.exists(image_path):
            logger.error(f"Auto-click failed: Image not found at {image_path}")
            return
            
        if not immediate:
            logger.info(f"Auto-clicker sleeping for {delay}s waiting for {node.name} UI...")
            time.sleep(delay)
        else:
            logger.info(f"Running auto-clicker immediately for {node.name} (Revive attempt)...")
            
        try:
            location = pyautogui.locateCenterOnScreen(image_path, confidence=0.8)
            if location:
                pyautogui.click(location)
                logger.info(f"Successfully auto-clicked for {node.name}")
            else:
                logger.warning(f"Auto-click failed: Image not found on screen for {node.name}")
        except Exception as e:
            logger.error(f"Error during auto-click for {node.name}: {e}")

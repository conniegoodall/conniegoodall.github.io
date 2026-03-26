"""Start exes, Docker containers, browser profiles, and scripts (bat/ps1/wsl)."""

from __future__ import annotations

import ctypes
import io
import logging
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Iterable, Any

from PIL import Image

import warnings
# Silence pywinauto's annoying STA COM warning
warnings.filterwarnings("ignore", category=UserWarning, module="pywinauto")

# --- DPI AWARENESS FIX ---
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1) # PROCESS_SYSTEM_DPI_AWARE
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

import psutil
import pyautogui
import pyperclip
import win32gui
import win32con

from nodemate.browser_profiles import default_browser_exe, BrowserProfileInfo
from nodemate.config_store import NodeEntry, SequenceEntry, load_node_memory
from nodemate.win32_util import preferred_click_hwnd
from nodemate.subprocess_util import popen_hidden, run_hidden

def safe_shlex_split(command: str) -> list[str]:
    import shlex
    if not command: return []
    try: return shlex.split(command.replace('\\', '\\\\'))
    except: return command.split()

logger = logging.getLogger(__name__)


def _split_args(s: str) -> list[str]:
    s = (s or "").strip()
    if not s:
        return []
    return safe_shlex_split(s)


def _parse_stored_exe_field(raw: str) -> tuple[str, str]:
    raw = (raw or "").strip()
    if not raw:
        return "", ""
    exe_path_only = raw
    extra = ""
    if raw.startswith('"'):
        end_quote = raw.find('"', 1)
        if end_quote != -1:
            exe_path_only = raw[1:end_quote]
            extra = raw[end_quote + 1 :].strip()
    elif " " in raw and not Path(raw).exists():
        parts = safe_shlex_split(raw)
        if parts:
            exe_path_only = parts[0]
            if len(parts) > 1:
                extra = " ".join(parts[1:])
    return exe_path_only, extra


def _login_log(msg: str) -> None:
    """Set NODE_MATE_LOGIN_DEBUG=1 for stderr + %LOCALAPPDATA%\\NodeMate\\login_debug.log."""
    if not (os.environ.get("NODE_MATE_LOGIN_DEBUG") or "").strip():
        return
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n"
    try:
        print(f"[Node-Mate login] {msg}", file=sys.stderr, flush=True)
    except Exception:
        pass
    try:
        base = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
        d = base / "NodeMate"
        d.mkdir(parents=True, exist_ok=True)
        with (d / "login_debug.log").open("a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass


def check_and_auto_login(node: NodeEntry, max_retries: int = 1, retry_delay: int = 30) -> bool:
    """
    Auto-login has been completely removed in favor of lightweight Telegram alerts.
    The watchdog will detect logouts and ping the user via Telegram to handle it remotely.
    """
    return False


def _attempt_login_strategies(node: NodeEntry, target_hwnd: int, login_email: str, login_pass: str, attempt: int, bypass_replay: bool = False) -> bool:
    """Legacy function - auto-login is removed."""
    return False



def launch_node(node: NodeEntry) -> tuple[bool, str, int | None]:
    prelaunch = getattr(node, "prelaunch_command", "").strip()
    if prelaunch:
        try:
            # 0x08000000 is CREATE_NO_WINDOW
            subprocess.run(["cmd.exe", "/c", prelaunch] if os.name == "nt" else ["/bin/sh", "-c", prelaunch], 
                           timeout=30, creationflags=0x08000000 if os.name == "nt" else 0)
        except Exception: pass

    if node.node_type == "exe":
        if not node.exe_path:
            return False, "No executable path", None
            
        raw_exe = os.path.expandvars(node.exe_path.strip())
        
        # 0. Check if this is Docker Desktop
        # Docker Desktop's main exe immediately exits after spawning background services.
        # We must explicitly handle it so we don't throw "Process exited immediately" errors.
        is_docker_desktop = "docker desktop.exe" in node.exe_path.lower()
        
        # 1. Shell Launch for Shortcuts (.lnk) or Scripts (.bat, .cmd, .ps1) or Docker Desktop
        if raw_exe.lower().endswith(('.lnk', '.bat', '.cmd', '.ps1')) or is_docker_desktop:
            logger.info(f"Using shell-launch for shortcut/script/docker: {raw_exe}")
            try:
                os.startfile(raw_exe)
                time.sleep(3.0) # Wait a bit longer for Docker to spawn its services
                
                # If it's docker, we can just assume it launched successfully even if we can't find a PID yet.
                # The watchdog will eventually catch the background service.
                pids = find_pids_for_node(node)
                if is_docker_desktop and not pids:
                    return True, "", 0
                    
                return True, "", pids[0] if pids else None
            except Exception as e:
                return False, f"Shortcut/Script launch failed: {e}", None

        # 2. Path Validation & Parsing
        exe_path_only, extra_from_field = _parse_stored_exe_field(raw_exe)
        exe_quoted = f'"{exe_path_only}"' if not exe_path_only.startswith('"') else exe_path_only
        
        cmd = f'{exe_quoted} {extra_from_field} {node.exe_args}'.strip()
        
        # Handle batch scripts specially to keep console open if requested
        # (Note: Scripts are mostly handled by startfile above now, this is a fallback)
        if raw_exe.lower().endswith(('.bat', '.cmd')) and not node.run_without_hidden_console:
            cmd = f'cmd.exe /c "{cmd}"'
        elif raw_exe.lower().endswith(('.ps1')) and not node.run_without_hidden_console:
            cmd = f'powershell.exe -ExecutionPolicy Bypass -File {cmd}'
            
        logger.info(f"Executing manual launch: {cmd}")
        
        try:
            cwd_path = Path(exe_path_only.strip('"')).parent
            
            if node.run_without_hidden_console and sys.platform == "win32":
                # Fallback visible console launch if startfile was bypassed
                flags = subprocess.CREATE_NEW_CONSOLE | 0x08000000
                p = subprocess.Popen(
                    cmd, 
                    shell=True,
                    cwd=str(cwd_path) if cwd_path.exists() else None,
                    creationflags=flags
                )
                time.sleep(1.5)
                return True, "", p.pid
            else:
                flags = 0x08000000 if sys.platform == "win32" else 0
                
                p = subprocess.Popen(
                    cmd, 
                    shell=True,
                    cwd=str(cwd_path) if cwd_path.exists() else None, 
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=flags
                )
                # Immediate health check for silent failures (except Docker)
                time.sleep(1.5)
                if not is_docker_desktop and p.poll() is not None and p.returncode != 0:
                    return False, f"Process exited immediately (code {p.returncode}). Try 'Don't hide console' in Props.", None
                    
                return True, "", p.pid
        except Exception as e:
            return False, f"Launch failed: {e}", None

    if node.node_type == "docker":
        if not node.docker_name:
            return False, "No container name", None
        r = run_hidden(["docker", "start", node.docker_name])
        if r.returncode != 0:
            return False, "Docker start failed", None
        _maybe_spawn_auto_login_thread(node)
        return True, "", None

    if node.node_type == "browser":
        # 1. Resolve Executable Path
        bexe = os.path.expandvars((node.exe_path or "").strip())
        
        if bexe.lower().endswith(".lnk"):
            logger.info(f"Using shell-launch for browser shortcut: {bexe}")
            try:
                os.startfile(bexe)
                time.sleep(2.0)
                pids = find_pids_for_node(node)
                return True, "", pids[0] if pids else None
            except Exception as e:
                return False, f"Shortcut launch failed: {e}", None

        if not bexe or not Path(bexe.strip('"')).is_file():
            bexe = node.browser_exe if (node.browser_exe and Path(os.path.expandvars(node.browser_exe)).is_file()) else None
            if not bexe:
                bexe = default_browser_exe_type(node)
            bexe = os.path.expandvars(bexe or "")
            
        if not bexe:
            return False, f"Browser executable not found: {bexe}", None

        # 2. Build Arguments
        stored_args = node.exe_args or ""
        bexe_quoted = f'"{bexe}"' if not bexe.startswith('"') else bexe
        args_list = [bexe_quoted]
        
        udd = node.browser_user_data_dir
        pd = node.browser_profile_dir
        
        has_udd = "--user-data-dir=" in stored_args.lower()
        has_pd = "--profile-directory=" in stored_args.lower() or "--side-profile=" in stored_args.lower()

        if not has_udd and udd:
            args_list.append(f'--user-data-dir="{udd}"')
        if not has_pd and pd and pd != ".":
            if "opera" in str(bexe).lower() or "launcher.exe" in str(bexe).lower():
                args_list.append(f'--side-profile="{pd}"')
            else:
                args_list.append(f'--profile-directory="{pd}"')
        
        args_list.extend(["--no-first-run", "--no-default-browser-check"])
        
        cmd = " ".join(args_list)
        if stored_args:
            cmd += f" {stored_args}"
            
        logger.info(f"Executing hidden launch for {node.name}: {cmd}")
        try:
            p = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=0x08000000 if sys.platform == "win32" else 0
            )
            
            # Immediate health check for silent failures
            time.sleep(1.0)
            if p.poll() is not None:
                 time.sleep(1.5)
                 if not find_pids_for_node(node):
                     return False, f"Browser process exited immediately (code {p.returncode})", None
            
            _maybe_spawn_auto_login_thread(node)
            return True, "", p.pid
        except Exception as e:
            return False, f"Browser launch failed: {e}", None
    
    return False, f"Unknown node type: {node.node_type}", None


def launch_sequence_entry(e: SequenceEntry, nodes_by_id: dict[str, NodeEntry]) -> tuple[bool, str]:
    try:
        if e.entry_type == "node":
            n = nodes_by_id.get(e.node_id)
            if not n:
                return False, f"Node {e.node_id} not found"
            ok, err, _pid = launch_node(n)
            return ok, err
        
        if not e.path or not Path(e.path).is_file():
            return False, f"Missing script file: {e.path}"
        
        if e.kind == "ps1":
            popen_hidden(["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", e.path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif e.kind == "wsl":
            popen_hidden(["wsl", "-d", e.wsl_distro or "Ubuntu", "--", "bash", e.path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else: # bat
            popen_hidden(["cmd.exe", "/c", e.path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
        return True, ""
    except Exception as ex:
        return False, str(ex)


def _maybe_spawn_auto_login_thread(node: NodeEntry) -> None:
    # Function kept for backwards compatibility but stripped out to save resources.
    # Auto-login is completely removed in favor of Telegram alerts.
    pass


_LNK_CACHE = {}

def _get_lnk_target_and_args(lnk_path: str) -> tuple[str, str]:
    try:
        lnk_path_abs = str(Path(lnk_path).absolute())
        if lnk_path_abs in _LNK_CACHE:
            return _LNK_CACHE[lnk_path_abs]
        
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(lnk_path_abs)
        target = shortcut.TargetPath.lower()
        args = shortcut.Arguments.lower()
        _LNK_CACHE[lnk_path_abs] = (target, args)
        return target, args
    except Exception:
        return "", ""

def find_pids_for_node(node: NodeEntry) -> list[int]:
    return map_nodes_to_pids([node]).get(node.id, [])


def map_nodes_to_pids(nodes: Iterable[NodeEntry]) -> dict[str, list[int]]:
    nodes_list = list(nodes)
    out = {n.id: [] for n in nodes_list}
    
    def norm_p(p): return str(Path(p)).lower().replace("/", "\\")
    
    try:
        for proc in psutil.process_iter(["pid", "name", "exe", "cmdline"]):
            try:
                info = proc.info
                exe_lower = norm_p(info.get("exe") or "")
                cmdline_parts = info.get("cmdline") or []
                cmd_lower = norm_p(" ".join(cmdline_parts))
                pid = info["pid"]
                
                for n in nodes_list:
                    # 1. Validation check for browser profile
                    if n.node_type == "browser":
                        if n.browser_profile_dir:
                            pd = n.browser_profile_dir.lower()
                            # If profile is defined, it MUST be in the cmdline
                            if pd not in cmd_lower:
                                continue
                        else:
                            # If it's a default profile (no profile dir), it MUST NOT match a side profile
                            if "--side-profile-name=" in cmd_lower or "--profile-directory=" in cmd_lower:
                                continue
                                
                        if n.browser_user_data_dir:
                            udd = norm_p(n.browser_user_data_dir)
                            if udd not in cmd_lower:
                                continue
                                
                    # 2. Match by executable filename
                    is_match = False
                    if n.exe_path:
                        exe_path_only, _ = _parse_stored_exe_field(n.exe_path)
                        target_filename = Path(exe_path_only).name.lower()
                        target_stem = Path(exe_path_only).stem.lower()
                        
                        # Special handling for Opera browsers
                        is_opera = "opera" in target_filename or "launcher.exe" in target_filename
                        
                        # For batch/shell scripts, the exe is usually cmd.exe or powershell.exe,
                        # and the script name is in the cmdline. Or it could be the actual miner exe if the batch file passed control.
                        if target_filename.endswith(('.bat', '.cmd', '.ps1', '.sh')):
                            if target_filename in cmd_lower:
                                is_match = True
                            elif target_stem in cmd_lower:
                                is_match = True
                        elif is_opera:
                            # Opera uses launcher.exe but the real process is opera.exe
                            if "opera.exe" in exe_lower or "launcher.exe" in exe_lower:
                                is_match = True
                                # If it's a shortcut or has manual args, enforce profile matching
                                req_args = ""
                                if exe_path_only.endswith(".lnk"):
                                    _, req_args = _get_lnk_target_and_args(exe_path_only)
                                elif n.exe_args:
                                    req_args = n.exe_args.lower()
                                
                                if req_args:
                                    # Ensure important profile args are present in the cmdline
                                    if "--side-profile-name=" in req_args:
                                        profile_part = [p for p in req_args.split() if "--side-profile-name=" in p]
                                        if profile_part and profile_part[0] not in cmd_lower:
                                            is_match = False
                                    elif "--profile-directory=" in req_args:
                                        profile_part = [p for p in req_args.split() if "--profile-directory=" in p]
                                        if profile_part and profile_part[0] not in cmd_lower:
                                            is_match = False
                                else:
                                    # Default manual Opera should NOT match side profiles
                                    if "--side-profile-name=" in cmd_lower or "--profile-directory=" in cmd_lower:
                                        is_match = False
                        elif target_filename == "docker desktop.exe":
                            # Docker Desktop's actual background GUI process is often named differently
                            # or just "Docker Desktop.exe". We need to be slightly more permissive here.
                            # Also check for "docker.exe" or "com.docker.backend.exe" as they are key services
                            if "docker desktop.exe" in exe_lower or "docker desktop.exe" in cmd_lower or "com.docker.backend.exe" in exe_lower:
                                is_match = True
                        else:
                            if target_filename in exe_lower or target_filename in cmd_lower:
                                is_match = True
                            elif target_filename.endswith(".lnk") and (target_stem in exe_lower or target_stem in cmd_lower):
                                is_match = True
                            
                    elif n.node_type == "browser":
                        bexe = default_browser_exe_type(n)
                        if bexe:
                            target_filename = Path(bexe).name.lower()
                            if target_filename in exe_lower or target_filename in cmd_lower:
                                is_match = True
                                
                    if is_match:
                        out[n.id].append(pid)
                        
            except (psutil.NoSuchProcess, psutil.AccessDenied): continue
            except Exception as e: 
                logger.error(f"Error in map_nodes_to_pids process loop: {e}")
                continue
    except Exception as e: 
        logger.error(f"Error in map_nodes_to_pids: {e}")
    
    # Log results for manual nodes (UUID-style IDs)
    for nid, pids in out.items():
        if len(nid) <= 8: # UUID-style
            logger.info(f"PID Map Result: {nid} -> {pids}")
    return out


def node_is_running(node: NodeEntry) -> bool:
    if node.node_type == "docker":
        return node.docker_name in docker_running_names() if node.docker_name else False
    return len(find_pids_for_node(node)) > 0


def docker_running_names() -> set[str]:
    try:
        r = run_hidden(["docker", "ps", "--format", "{{.Names}}"], timeout=4)
        return {x.strip() for x in (r.stdout or "").splitlines() if x.strip()}
    except Exception: return set()


def discover_docker_container_names() -> list[str]:
    try:
        r = run_hidden(["docker", "ps", "-a", "--format", "{{.Names}}"], timeout=8)
        return sorted({x.strip() for x in (r.stdout or "").splitlines() if x.strip()})
    except Exception: return []


def default_browser_exe_type(node: NodeEntry) -> str:
    # Use top-level import now
    be = (node.browser_exe or "").strip().lower()
    
    # 1. If it's already a full path, use it
    if be and Path(be).is_file(): return be
    
    # 2. If it's a browser type (like "opera"), but maybe mixed case or from name
    nm = (node.name or "").lower()
    if not be or be not in ["chrome", "edge", "brave", "opera", "vivaldi"]:
        if "edge" in nm: be = "edge"
        elif "brave" in nm: be = "brave"
        elif "opera" in nm: be = "opera"
        elif "vivaldi" in nm: be = "vivaldi"
        else: be = "chrome"

    info = BrowserProfileInfo(
        browser=be,
        display_name=node.name,
        user_data_dir=node.browser_user_data_dir,
        profile_directory=node.browser_profile_dir,
    )
    return default_browser_exe(info)


def run_update_command(cmd: str) -> tuple[int, str]:
    if not cmd: return -1, "Empty command"
    try:
        p = popen_hidden(["cmd.exe", "/c", cmd] if os.name == "nt" else ["/bin/sh", "-c", cmd])
        out, err = p.communicate(timeout=600)
        return p.returncode, ((out or "") + (err or ""))[:4000].strip()
    except Exception as e:
        return -1, str(e)
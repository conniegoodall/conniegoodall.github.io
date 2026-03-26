"""
Browser Profile Discovery - Lightweight
Finds Chrome, Edge, Brave, and Opera profiles.
"""

from __future__ import annotations

import os
import json
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional
from nodemate.config_store import NodeEntry

@dataclass
class BrowserProfileInfo:
    browser: str
    display_name: str
    user_data_dir: str
    profile_directory: str
    icon_path: str = ""

def scan_all_browser_profiles() -> List[NodeEntry]:
    """Scan for all supported browser profiles."""
    nodes = []
    
    # 1. User Data Roots Scan
    user_data_roots = {
        "Chrome": Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "User Data",
        "Edge": Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Edge" / "User Data",
        "Brave": Path(os.environ.get("LOCALAPPDATA", "")) / "BraveSoftware" / "Brave-Browser" / "User Data",
        "Opera": Path(os.environ.get("APPDATA", "")) / "Opera Software" / "Opera Stable",
        "Opera GX": Path(os.environ.get("APPDATA", "")) / "Opera Software" / "Opera GX Stable",
        "Vivaldi": Path(os.environ.get("LOCALAPPDATA", "")) / "Vivaldi" / "User Data",
    }
    
    for name, root in user_data_roots.items():
        if root.exists():
            nodes.extend(_scan_profiles_in_root(name, root))
            
    # 2. Desktop Shortcuts Scan (Very reliable for profile-specific launches)
    nodes.extend(scan_desktop_browser_shortcuts())
            
    return nodes

def _scan_profiles_in_root(browser_name: str, root: Path) -> List[NodeEntry]:
    """Scan for profiles given a User Data root."""
    nodes = []
    
    # Profiles are folders like "Default", "Profile 1", etc.
    # Opera GX uses "side_profiles" sometimes
    search_dirs = []
    if "Opera" in browser_name:
        search_dirs = [root]
        # Also check for side profiles
        side_profiles = root / "side_profiles"
        if side_profiles.exists():
            search_dirs.extend([d for d in side_profiles.iterdir() if d.is_dir()])
    else:
        search_dirs = [d for d in root.iterdir() if d.is_dir() if (d / "Preferences").exists()]
    
    for pdir in search_dirs:
        pref_file = pdir / "Preferences"
        if pref_file.exists():
            profile_name = pdir.name
            display_name = f"{browser_name} - {profile_name}"
            
            try:
                with open(pref_file, 'r', encoding='utf-8', errors='ignore') as f:
                    data = json.load(f)
                    acc_name = data.get("profile", {}).get("name")
                    if acc_name: display_name = f"{browser_name} - {acc_name}"
            except: pass
            
            nodes.append(NodeEntry(
                id=f"{browser_name.lower()}_{profile_name}",
                name=display_name,
                node_type="browser",
                browser_exe=browser_name.lower(),
                browser_user_data_dir=str(root),
                browser_profile_dir=profile_name,
                enabled=False
            ))
            
    return nodes

def scan_desktop_browser_shortcuts() -> List[NodeEntry]:
    """Scan the desktop, Public desktop, and Start Menu for browser shortcuts with profile arguments."""
    nodes = []
    try:
        import win32com.client
        import shlex
        
        shell = win32com.client.Dispatch("WScript.Shell")
        
        locations = [
            Path(os.environ.get("USERPROFILE", "")) / "Desktop",
            Path(os.environ.get("PUBLIC", r"C:\Users\Public")) / "Desktop",
            Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
            Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
        ]
        
        for base in locations:
            if not base.exists(): continue
            
            # Recursive scan (2 levels deep for Start Menu folders)
            shortcuts = list(base.glob("*.lnk")) + list(base.glob("*/*.lnk")) + list(base.glob("*/*/*.lnk"))
            for lnk in shortcuts:
                try:
                    shortcut = shell.CreateShortCut(str(lnk))
                    target = shortcut.TargetPath.lower()
                    args = shortcut.Arguments
                    
                    # Check if it's a browser (more flexible detection - check full path)
                    browser_name = None
                    if "chrome" in target: browser_name = "Chrome"
                    elif "msedge" in target or "edge" in target: browser_name = "Edge"
                    elif "brave" in target: browser_name = "Brave"
                    elif "opera" in target: browser_name = "Opera"
                    elif "vivaldi" in target: browser_name = "Vivaldi"
                    elif "epic" in target: browser_name = "Epic"
                    
                    # If we suspect it's a browser, or if it has --profile-directory
                    if browser_name or "--profile-directory" in args or "--user-data-dir" in args:
                        if not browser_name: browser_name = "Browser" # Fallback
                        
                        # Extract profile name
                        profile = "Default"
                        if "--profile-directory=" in args:
                            try:
                                # Simple split to avoid shlex issues with weird paths
                                for p in args.split():
                                    if "--profile-directory=" in p:
                                        profile = p.split("=")[1].strip('"')
                            except: pass
                        
                        print(f"Found Profile Shortcut: {lnk.stem} ({browser_name})")
                        
                        nodes.append(NodeEntry(
                            id=f"shortcut_{lnk.stem}_{profile}",
                            name=f"{lnk.stem}", # Use the shortcut name
                            node_type="browser",
                            browser_exe=browser_name.lower(),
                            browser_profile_dir=profile,
                            exe_args=args, # Full args!
                            enabled=False
                        ))
                except: continue
    except: pass
    return nodes

def default_browser_exe(info) -> str:
    """Find the full path to the browser executable on Windows."""
    browser = info.browser.lower()
    
    # Common paths for each browser
    paths = {
        "chrome": [
            Path(os.environ.get("ProgramFiles", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
            Path(os.environ.get("ProgramFiles(x86)", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
        ],
        "edge": [
            Path(os.environ.get("ProgramFiles(x86)", "")) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
        ],
        "brave": [
            Path(os.environ.get("ProgramFiles", "")) / "BraveSoftware" / "Brave-Browser" / "Application" / "brave.exe",
            Path(os.environ.get("LOCALAPPDATA", "")) / "BraveSoftware" / "Brave-Browser" / "Application" / "brave.exe",
        ],
        "opera": [
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Opera GX" / "launcher.exe",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Opera" / "launcher.exe",
            Path(os.environ.get("ProgramFiles", "")) / "Opera GX" / "launcher.exe",
        ],
        "vivaldi": [
            Path(os.environ.get("LOCALAPPDATA", "")) / "Vivaldi" / "Application" / "vivaldi.exe",
            Path(os.environ.get("ProgramFiles", "")) / "Vivaldi" / "Application" / "vivaldi.exe",
        ]
    }
    
    if browser in paths:
        for p in paths[browser]:
            if p.exists():
                return str(p)
                
    return browser # fallback

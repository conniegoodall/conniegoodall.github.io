"""
Discovery Module - Revo-Style System Scanning
Scans Registry, Local Programs, and Browser Profiles to find nodes.
"""

from __future__ import annotations

import os
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import winreg

from nodemate.config_store import NodeEntry
from nodemate.browser_profiles import scan_all_browser_profiles

logger = logging.getLogger(__name__)

DEFAULT_EXE_KEYWORDS = ["node", "depin", "gpu", "crypto", "grass", "optim", "compute", "proxy", "ai", "miner"]

def scan_system_safe(narrow: bool = False) -> List[NodeEntry]:
    """Perform a safe, comprehensive system scan (Registry + Local Programs + Browsers)."""
    nodes: List[NodeEntry] = []
    
    # 1. Registry Scan (HKCU then HKLM)
    nodes.extend(scan_registry_exes(narrow=narrow))
    
    # 2. Local Programs Scan
    nodes.extend(scan_localappdata_programs_exes())
    
    # 3. Browser Profiles
    nodes.extend(scan_all_browser_profiles())
    
    # Deduplicate by exe_path or (browser, profile)
    seen_exes = set()
    seen_browser_profiles = set()
    unique_nodes = []
    
    for node in nodes:
        if node.node_type == "exe" and node.exe_path:
            path_norm = str(Path(node.exe_path).resolve()).lower()
            if path_norm not in seen_exes:
                seen_exes.add(path_norm)
                unique_nodes.append(node)
        elif node.node_type == "browser":
            # For browser nodes, deduplicate by browser name and profile dir
            # Note: shortcuts might have different IDs but point to same profile
            key = (node.browser_exe, node.browser_profile_dir)
            if key not in seen_browser_profiles:
                seen_browser_profiles.add(key)
                unique_nodes.append(node)
        else:
            unique_nodes.append(node)
            
    return unique_nodes

def scan_registry_exes(narrow: bool = False, max_entries: int = 2500) -> List[NodeEntry]:
    """Scan Windows Uninstall registry hives for installed apps."""
    nodes = []
    # 1. Uninstall Registry
    hives = [
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall")
    ]
    
    for root, path in hives:
        try:
            with winreg.OpenKey(root, path) as key:
                for i in range(winreg.QueryInfoKey(key)[0]):
                    if len(nodes) >= max_entries: break
                    try:
                        name = winreg.EnumKey(key, i)
                        with winreg.OpenKey(key, name) as subkey:
                            dname, _ = winreg.QueryValueEx(subkey, "DisplayName")
                            if not dname: continue
                            
                            # Filtering (Per user request, make it broad)
                            if narrow:
                                combined = f"{dname} {name}".lower()
                                if not any(kw in combined for kw in DEFAULT_EXE_KEYWORDS):
                                    continue
                                    
                            exe_path = _find_best_exe_for_registry_entry(subkey)
                            if exe_path and Path(exe_path).exists():
                                nodes.append(NodeEntry(
                                    id=name,
                                    name=dname,
                                    node_type="exe",
                                    exe_path=exe_path,
                                    enabled=False
                                ))
                    except: continue
        except: continue
    
    # 2. App Paths Registry (Broader discovery)
    app_path_hives = [
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\App Paths"),
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\App Paths")
    ]
    for root, path in app_path_hives:
        try:
            with winreg.OpenKey(root, path) as key:
                for i in range(winreg.QueryInfoKey(key)[0]):
                    try:
                        name = winreg.EnumKey(key, i)
                        with winreg.OpenKey(key, name) as subkey:
                            # Default value is the exe path
                            exe_path, _ = winreg.QueryValueEx(subkey, "")
                            if exe_path and Path(exe_path).exists():
                                nodes.append(NodeEntry(
                                    id=f"apppath_{name}",
                                    name=name.replace(".exe", ""),
                                    node_type="exe",
                                    exe_path=exe_path,
                                    enabled=False
                                ))
                    except: continue
        except: continue
    
    return nodes

def _find_best_exe_for_registry_entry(subkey) -> Optional[str]:
    """Heuristic to find the main EXE instead of uninstaller."""
    try:
        # 1. Try DisplayIcon
        icon_path, _ = winreg.QueryValueEx(subkey, "DisplayIcon")
        if icon_path:
            path = icon_path.split(',')[0].strip('"')
            if path.lower().endswith(".exe"): return path
            
        # 2. Try InstallLocation + heuristic
        loc, _ = winreg.QueryValueEx(subkey, "InstallLocation")
        if loc and Path(loc).exists():
            exes = list(Path(loc).glob("*.exe"))
            # Filter out uninstallers
            exes = [e for e in exes if "unins" not in e.name.lower() and "setup" not in e.name.lower()]
            if exes:
                # Rank by name similarity to DisplayName (simple heuristic)
                dname, _ = winreg.QueryValueEx(subkey, "DisplayName")
                exes.sort(key=lambda x: _similarity(x.stem, dname), reverse=True)
                return str(exes[0])
                
        # 3. Fallback to UninstallString (last resort, often an uninstaller)
        uninst, _ = winreg.QueryValueEx(subkey, "UninstallString")
        if uninst:
            import shlex
            try:
                parts = shlex.split(uninst.replace('\\', '\\\\'))
                if parts and "unins" not in parts[0].lower():
                    return parts[0]
            except: pass
    except: pass
    return None

def _similarity(s1: str, s2: str) -> float:
    """Very simple string similarity."""
    s1, s2 = s1.lower(), s2.lower()
    if s1 in s2 or s2 in s1: return 1.0
    return 0.0

def scan_localappdata_programs_exes() -> List[NodeEntry]:
    """Scan %LOCALAPPDATA% and %APPDATA% recursively for any EXE that looks like a program."""
    nodes = []
    
    # 1. Standard "Programs" folder
    base = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs"
    if base.exists():
        for folder in base.iterdir():
            if folder.is_dir():
                exes = list(folder.glob("*.exe"))
                exes = [e for e in exes if "unins" not in e.name.lower() and "setup" not in e.name.lower()]
                if exes:
                    exes.sort(key=lambda x: _similarity(x.stem, folder.name), reverse=True)
                    nodes.append(NodeEntry(
                        id=f"prog_{folder.name}", name=folder.name, node_type="exe", exe_path=str(exes[0]),
                        enabled=False
                    ))

    # 2. Aggressive Scan of LocalAppData and Roaming (1 level deep)
    search_roots = [
        Path(os.environ.get("LOCALAPPDATA", "")),
        Path(os.environ.get("APPDATA", ""))
    ]
    for root in search_roots:
        try:
            for folder in root.iterdir():
                if folder.is_dir() and "temp" not in folder.name.lower() and "package" not in folder.name.lower():
                    # Look for EXEs directly in these folders (many portable apps/nodes live here)
                    for exe in folder.glob("*.exe"):
                        if "unins" not in exe.name.lower() and "setup" not in exe.name.lower():
                            nodes.append(NodeEntry(
                                id=f"appdata_{exe.stem}", name=exe.stem, node_type="exe", exe_path=str(exe),
                                enabled=False
                            ))
        except: continue
        
    return nodes

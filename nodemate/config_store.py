"""JSON persistence for Node-Mate (nodes, sequence, ad URL, window geometry)."""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


def _config_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    d = Path(base) / "NodeMate"
    d.mkdir(parents=True, exist_ok=True)
    return d


CONFIG_PATH = _config_dir() / "config.json"


@dataclass
class SequenceEntry:
    id: str
    entry_type: str  # script | node
    path: str
    kind: str  # bat | ps1 | wsl
    node_id: str
    start_order: int
    delay_sec: float
    ram_threshold: float  # 0 = use queue default; else wait until RAM % < this
    wsl_distro: str = "Ubuntu"
    heavy: bool = True

    @staticmethod
    def new_script(
        path: str,
        kind: str,
        start_order: int,
        delay_sec: float,
        wsl_distro: str = "Ubuntu",
        heavy: bool = True,
        ram_threshold: float = 0.0,
    ) -> "SequenceEntry":
        return SequenceEntry(
            id=str(uuid.uuid4()),
            entry_type="script",
            path=path,
            kind=kind,
            node_id="",
            start_order=start_order,
            delay_sec=delay_sec,
            ram_threshold=float(ram_threshold),
            wsl_distro=wsl_distro,
            heavy=heavy,
        )

    @staticmethod
    def new_node(
        node_id: str,
        start_order: int,
        delay_sec: float,
        ram_threshold: float,
        heavy: bool = True,
    ) -> "SequenceEntry":
        return SequenceEntry(
            id=str(uuid.uuid4()),
            entry_type="node",
            path="",
            kind="",
            node_id=node_id,
            start_order=start_order,
            delay_sec=delay_sec,
            ram_threshold=float(ram_threshold),
            wsl_distro="",
            heavy=heavy,
        )


@dataclass
class NodeEntry:
    id: str
    node_type: str  # exe | docker | browser
    name: str
    enabled: bool
    update_command: str = ""
    log_watch_path: str = ""
    stale_minutes: int = 10
    exe_path: str = ""
    exe_args: str = ""
    docker_name: str = ""
    browser_exe: str = ""
    browser_user_data_dir: str = ""
    browser_profile_dir: str = ""
    heavy: bool = True
    # When watchdog is on: launch this node if it is ticked but not running (cooldown applies).
    auto_start_if_stopped: bool = True
    # Windows: if True, launch without CREATE_NO_WINDOW (some CLI/node exes fail when fully detached).
    run_without_hidden_console: bool = False
    working_dir: str = ""
    prelaunch_command: str = ""
    login_email: str = ""
    login_password: str = ""
    ai_login_coords: dict[str, list[float]] = field(default_factory=dict)
    # "window" = legacy normalization vs GetWindowRect; "client" = Composer scan (PostMessage-safe).
    ai_login_coord_space: str = "window"
    start_delay_minutes: int = 0  # Legacy field (mapped from seconds)
    start_delay_seconds: int = 0  # Granular start delay
    wait_for_ram: bool = False     # "Heavy" mode - wait for system headroom
    auto_start: bool = True       # Auto-start when ticked
    auto_click_image_path: str = "" # Path to an image template to auto-click after launch
    auto_click_delay: int = 15      # Seconds to wait after launch before looking for the image
    restart_on_zero_cpu: bool = False # If true, watchdog checks if CPU is 0%
    zero_cpu_minutes: int = 5         # How many minutes of 0% CPU before taking action

    @staticmethod
    def new(
        node_type: str,
        name: str,
        enabled: bool = False,
        **kwargs: Any,
    ) -> "NodeEntry":
        return NodeEntry(
            id=str(uuid.uuid4()),
            node_type=node_type,
            name=name,
            enabled=enabled,
            update_command=str(kwargs.get("update_command", "")),
            log_watch_path=str(kwargs.get("log_watch_path", "")),
            stale_minutes=int(kwargs.get("stale_minutes", 10)),
            exe_path=str(kwargs.get("exe_path", "")),
            exe_args=str(kwargs.get("exe_args", "")),
            docker_name=str(kwargs.get("docker_name", "")),
            browser_exe=str(kwargs.get("browser_exe", "")),
            browser_user_data_dir=str(kwargs.get("browser_user_data_dir", "")),
            browser_profile_dir=str(kwargs.get("browser_profile_dir", "")),
            heavy=bool(kwargs.get("heavy", True)),
            auto_start_if_stopped=bool(kwargs.get("auto_start_if_stopped", True)),
            run_without_hidden_console=bool(kwargs.get("run_without_hidden_console", False)),
            prelaunch_command=str(kwargs.get("prelaunch_command", "")),
            login_email=str(kwargs.get("login_email", "")),
            login_password=str(kwargs.get("login_password", "")),
            ai_login_coords=dict(kwargs.get("ai_login_coords", {})),
            ai_login_coord_space=str(kwargs.get("ai_login_coord_space", "window")),
            start_delay_minutes=int(kwargs.get("start_delay_minutes", 0)),
            start_delay_seconds=int(kwargs.get("start_delay_seconds", 0)),
            wait_for_ram=bool(kwargs.get("wait_for_ram", False)),
            auto_start=bool(kwargs.get("auto_start", True)),
            auto_click_image_path=str(kwargs.get("auto_click_image_path", "")),
            auto_click_delay=int(kwargs.get("auto_click_delay", 15)),
            restart_on_zero_cpu=bool(kwargs.get("restart_on_zero_cpu", False)),
            zero_cpu_minutes=int(kwargs.get("zero_cpu_minutes", 5)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "node_type": self.node_type,
            "name": self.name,
            "enabled": self.enabled,
            "update_command": self.update_command,
            "log_watch_path": self.log_watch_path,
            "stale_minutes": self.stale_minutes,
            "exe_path": self.exe_path,
            "exe_args": self.exe_args,
            "docker_name": self.docker_name,
            "browser_exe": self.browser_exe,
            "browser_user_data_dir": self.browser_user_data_dir,
            "browser_profile_dir": self.browser_profile_dir,
            "heavy": self.heavy,
            "auto_start_if_stopped": self.auto_start_if_stopped,
            "run_without_hidden_console": self.run_without_hidden_console,
            "prelaunch_command": getattr(self, "prelaunch_command", ""),
            "login_email": getattr(self, "login_email", ""),
            "login_password": getattr(self, "login_password", ""),
            "ai_login_coords": getattr(self, "ai_login_coords", {}),
            "ai_login_coord_space": getattr(self, "ai_login_coord_space", "window"),
            "start_delay_minutes": getattr(self, "start_delay_minutes", 0),
            "start_delay_seconds": getattr(self, "start_delay_seconds", 0),
            "wait_for_ram": getattr(self, "wait_for_ram", False),
            "auto_start": getattr(self, "auto_start", True),
            "auto_click_image_path": getattr(self, "auto_click_image_path", ""),
            "auto_click_delay": getattr(self, "auto_click_delay", 15),
            "restart_on_zero_cpu": getattr(self, "restart_on_zero_cpu", False),
            "zero_cpu_minutes": getattr(self, "zero_cpu_minutes", 5),
        }


@dataclass
class AppConfig:
    ad_url: str = ""
    nodes: list[dict[str, Any]] = field(default_factory=list)
    sequence: list[dict[str, Any]] = field(default_factory=list)
    window_geometry: dict[str, Any] = field(default_factory=dict)
    pinned_geometry: dict[str, Any] = field(default_factory=dict)
    ram_idle_threshold: float = 95.0
    health_poll_sec: int = 8
    watchdog_poll_sec: int = 45
    # When False: no process table scan / Docker ps — only static list (Revo-style). User must start watchdog.
    watchdog_active: bool = False
    # Revo page: SCAN SYSTEM options (defaults favor full registry list).
    registry_scan_narrow: bool = False
    scan_include_docker: bool = False

    def to_json(self) -> dict[str, Any]:
        return {
            "ad_url": self.ad_url,
            "nodes": self.nodes,
            "sequence": self.sequence,
            "window_geometry": self.window_geometry,
            "pinned_geometry": self.pinned_geometry,
            "ram_idle_threshold": self.ram_idle_threshold,
            "health_poll_sec": self.health_poll_sec,
            "watchdog_poll_sec": self.watchdog_poll_sec,
            "watchdog_active": self.watchdog_active,
            "registry_scan_narrow": self.registry_scan_narrow,
            "scan_include_docker": self.scan_include_docker,
        }

    @classmethod
    def from_json(cls, d: dict[str, Any]) -> "AppConfig":
        return cls(
            ad_url=d.get("ad_url", cls.ad_url),
            nodes=list(d.get("nodes", [])),
            sequence=list(d.get("sequence", [])),
            window_geometry=dict(d.get("window_geometry", {})),
            pinned_geometry=dict(d.get("pinned_geometry", {})),
            ram_idle_threshold=float(d.get("ram_idle_threshold", 95.0)),
            health_poll_sec=int(d.get("health_poll_sec", 8)),
            watchdog_poll_sec=int(d.get("watchdog_poll_sec", 45)),
            watchdog_active=bool(d.get("watchdog_active", False)),
            registry_scan_narrow=bool(d.get("registry_scan_narrow", False)),
            scan_include_docker=bool(d.get("scan_include_docker", False)),
        )


def load_config() -> AppConfig:
    if not CONFIG_PATH.is_file():
        return AppConfig()
    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            return AppConfig.from_json(json.load(f))
    except (json.JSONDecodeError, OSError):
        return AppConfig()


def save_config(cfg: AppConfig) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG_PATH.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(cfg.to_json(), f, indent=2)
    tmp.replace(CONFIG_PATH)


def sequence_from_dicts(rows: list[dict[str, Any]]) -> list[SequenceEntry]:
    out: list[SequenceEntry] = []
    for r in rows:
        et = r.get("entry_type") or ("node" if r.get("node_id") else "script")
        out.append(
            SequenceEntry(
                id=r.get("id") or str(uuid.uuid4()),
                entry_type=str(et),
                path=r.get("path", ""),
                kind=r.get("kind", "bat"),
                node_id=str(r.get("node_id", "")),
                start_order=int(r.get("start_order", 0)),
                delay_sec=float(r.get("delay_sec", 0)),
                ram_threshold=float(r.get("ram_threshold", 0)),
                wsl_distro=r.get("wsl_distro", "Ubuntu"),
                heavy=bool(r.get("heavy", True)),
            )
        )
    return out


def sequence_to_dicts(entries: list[SequenceEntry]) -> list[dict[str, Any]]:
    return [asdict(e) for e in entries]


def node_from_dict(d: dict[str, Any]) -> NodeEntry:
    return NodeEntry(
        id=d.get("id") or str(uuid.uuid4()),
        node_type=d.get("node_type", "exe"),
        name=d.get("name", "node"),
        enabled=bool(d.get("enabled", False)),
        update_command=d.get("update_command", ""),
        log_watch_path=d.get("log_watch_path", ""),
        stale_minutes=int(d.get("stale_minutes", 10)),
        exe_path=d.get("exe_path", ""),
        exe_args=d.get("exe_args", ""),
        docker_name=d.get("docker_name", ""),
        browser_exe=d.get("browser_exe", ""),
        browser_user_data_dir=d.get("browser_user_data_dir", ""),
        browser_profile_dir=d.get("browser_profile_dir", ""),
        heavy=bool(d.get("heavy", True)),
        auto_start_if_stopped=bool(d.get("auto_start_if_stopped", True)),
        run_without_hidden_console=bool(d.get("run_without_hidden_console", False)),
        prelaunch_command=str(d.get("prelaunch_command", "")),
        login_email=str(d.get("login_email", "")),
        login_password=str(d.get("login_password", "")),
        ai_login_coords=dict(d.get("ai_login_coords", {})),
        ai_login_coord_space=str(d.get("ai_login_coord_space", "window")),
        start_delay_minutes=int(d.get("start_delay_minutes", 0)),
        start_delay_seconds=int(d.get("start_delay_seconds", 0)),
        wait_for_ram=bool(d.get("wait_for_ram", False)),
        auto_start=bool(d.get("auto_start", True)),
        auto_click_image_path=str(d.get("auto_click_image_path", "")),
        auto_click_delay=int(d.get("auto_click_delay", 15)),
        restart_on_zero_cpu=bool(d.get("restart_on_zero_cpu", False)),
        zero_cpu_minutes=int(d.get("zero_cpu_minutes", 5)),
    )


def nodes_from_dicts(rows: list[dict[str, Any]]) -> list[NodeEntry]:
    return [node_from_dict(r) for r in rows]


def nodes_to_dicts(entries: list[NodeEntry]) -> list[dict[str, Any]]:
    return [asdict(e) for e in entries]


MEMORY_PATH = _config_dir() / "node_memory.json"

def load_node_memory() -> dict[str, Any]:
    if not MEMORY_PATH.is_file():
        return {}
    try:
        with MEMORY_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_node_memory(memory: dict[str, Any]) -> None:
    try:
        tmp = MEMORY_PATH.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(memory, f, indent=2)
        tmp.replace(MEMORY_PATH)
    except Exception:
        pass

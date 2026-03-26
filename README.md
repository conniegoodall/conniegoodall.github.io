# Node-Mate Autonomous Agent

🚀 **Zero GPU Usage - Maximum Efficiency**

A lightweight, robust DePIN node monitoring system designed to run 24/7 on your PC. It uses **0% GPU** and focuses on keeping your nodes (Grass, NodePay, Titan, Pi, etc.) alive and mining automatically.

## 🎯 **Core Features**

### 🛡️ **Autonomous Watchdog**
- **0% CPU/GPU Overhead** - Extremely lightweight background monitoring.
- **Zombie Detection** - Automatically detects when a node freezes (0% CPU) and kills/restarts it.
- **Auto-Clicker Recovery** - Can automatically click 'Start' buttons inside apps that stop mining without crashing.
- **Staggered Launch Queue** - Boots your nodes up strictly one-by-one to prevent your PC from freezing during startup.
- **Docker Integration** - Monitors both standard `.exe` files and underlying Docker containers (like Pi Network).
- **Power Outage Recovery** - Remembers its state; if your PC reboots, the agent automatically starts back up where it left off.

### 🤖 **Smart Orchestration**
- **Anti-Farm Limiter** - Built-in network logic.
- **Mini-Mode** - Shrinks the app into a tiny, unobtrusive square in the corner of your screen.
- **Drag & Drop** - Easily add new nodes by dragging their desktop shortcuts directly into the app.

## 🚀 **Quick Start (For Users)**

The easiest way to use Node-Mate is to download the compiled executable:

1. Go to the **[Releases Tab](https://github.com/conniegoodall/Node-Mate-Autonomous-Agent/releases)**.
2. Download `Node-Mate-Setup.exe`.
3. Run the installer. It will place a shortcut on your desktop.
4. Open Node-Mate, drag your node shortcuts into the window, and click **Start Agent**.

---

## 🛠️ **Developer Setup (For Source Code)**

If you want to run the raw Python source code or contribute:

### 1. Install Dependencies
```bash
git clone https://github.com/conniegoodall/Node-Mate-Autonomous-Agent.git
cd Node-Mate-Autonomous-Agent
pip install -r requirements.txt
```

### 2. Run the System
```bash
python -m nodemate
```

### 3. Build the Executable
To compile the raw code into your own `.exe`:
```bash
pip install pyinstaller
python -m PyInstaller --noconfirm --onefile --windowed --name "Node-Mate" --icon="app_icon.ico" nodemate/__main__.py
```

## 🛡️ **Monitoring Logic**

### Zombie Process Detection
```text
Process is considered a zombie if:
- App CPU usage drops to exactly 0.0%
- Stays at 0.0% for the user-defined timeout period (e.g., 5 minutes)
Action: Agent triggers Auto-Clicker (if set) OR kills and restarts the process.
```

### Process Watch
```text
Every 10 seconds:
1. Check if process exists in Windows Task Manager
2. If missing → auto-relaunch using the global stagger queue
3. If Docker container linked → ensure container is 'Running'
```

## 📱 **Perfect For**
- ✅ **Airdrop Farmers** (keep 20+ nodes running smoothly)
- ✅ **Power outage areas** (auto-recovers when PC turns back on)
- ✅ **Low-End PCs** (0% GPU usage, minimal RAM footprint)

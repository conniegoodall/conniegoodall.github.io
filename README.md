# Veloce Node-Mate: Autonomous DePIN Watchdog

![Version](https://img.shields.io/badge/version-v0.1--Beta-blue.svg)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)
![License](https://img.shields.io/badge/license-Proprietary-red.svg)

**Veloce Node-Mate** is an enterprise-grade, autonomous process watchdog designed specifically for Decentralized Physical Infrastructure Networks (DePIN) and high-availability crypto nodes. 

Running decentralized network nodes often suffers from memory leaks, browser crashes, and silent failures (0% CPU drops). Veloce Node-Mate mitigates these risks by providing a lightweight, robust orchestration layer that continuously monitors, manages, and restarts your node infrastructure to guarantee maximum uptime and revenue continuity.

## Features

- **Chronological Staggered Launch:** Eliminates system freezes during startup by strictly queuing high-load node applications and headless browsers.
- **Zero-CPU Heartbeat Detection:** Identifies "zombie" processes that are technically running but no longer computing or mining, issuing targeted restart or auto-click interventions.
- **Hybrid Docker Orchestration:** Seamlessly monitors both native Windows executables and isolated Docker containers (e.g., Pi Network, Optim AI) simultaneously.
- **Resource-Optimized:** Built specifically to consume minimal system overhead, ensuring maximum compute power remains dedicated to your nodes.

## Installation

### Quick Start (Recommended)

[📥 **Download Latest Release (v0.1-Beta)**](https://github.com/connie/Veloce-Node-Mate/releases)

1. Download the standalone `Veloce_Node-Mate.exe` from the Releases page.
2. Run the executable (no installation required).
3. *Note: v0.1-Beta is currently limited to system integrity checks. Full autonomous orchestration will unlock in v1.0.*

### Building from Source

If you have been granted repository access and wish to build from source:

```bash
git clone https://github.com/connie/Veloce-Node-Mate.git
cd Veloce-Node-Mate
pip install -r requirements.txt
python main.py
```

## About the Project
Developed to meet the rigorous demands of professional DePIN farmers and automated infrastructure operators. Veloce Node-Mate ensures that your earnings never stall due to unmonitored crashes. Built for scale, optimized for profit.

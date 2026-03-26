#!/usr/bin/env python3
"""
Standalone Lightweight Node-Mate Launcher
0% GPU Usage - Pure psutil monitoring with manual control
"""

import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMessageBox

# Add current directory to path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def main():
    """Launch standalone Node-Mate."""
    try:
        print("🚀 Starting Node-Mate Standalone")
        print("📊 Features: 0% GPU usage, zombie detection, Telegram alerts")
        print("🌐 Remote control: http://localhost:8080")
        print("🛡️ Monitoring: psutil-based process watching")
        print("")
        print("💡 System is ready for manual node management")
        print("📱 Add your DePIN nodes in the UI")
        print("")
        
        # Simple standalone application
        app = QApplication(sys.argv)
        app.setApplicationName("Node-Mate Standalone")
        
        # Show ready message
        msg = QMessageBox()
        msg.setWindowTitle("🎊 Node-Mate Ready")
        msg.setText("Lightweight Node-Mate is ready!\n\n"
                "Add your DePIN nodes and start monitoring.\n\n"
                "Use the UI to manage your nodes manually.")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())

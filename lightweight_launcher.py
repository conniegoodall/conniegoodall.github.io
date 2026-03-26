#!/usr/bin/env python3
"""
Lightweight Node-Mate Launcher
0% GPU Usage - Pure psutil monitoring with manual control
"""

import sys
import os
from pathlib import Path

# Add current directory to path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def main():
    """Launch lightweight Node-Mate."""
    try:
        print("🚀 Starting Node-Mate Lightweight")
        print("📊 Features: 0% GPU usage, zombie detection, Telegram alerts")
        print("🌐 Remote control: http://localhost:8080")
        print("🛡️ Monitoring: psutil-based process watching")
        print("")
        print("💡 To use old AI system: python -m nodemate")
        print("💡 To use lightweight system: python lightweight_launcher.py")
        print("")
        
        # Import and launch lightweight main
        from nodemate.lightweight_main import main as lightweight_main
        lightweight_main()
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Make sure you installed requirements:")
        print("   pip install -r requirements.txt")
        return 1
    except Exception as e:
        print(f"❌ Startup error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())

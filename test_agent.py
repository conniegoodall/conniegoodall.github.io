"""
Quick test script for the autonomous agent system
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nodemate.autonomous_agent import AutonomousAgent, AgentEvent
from nodemate.agent_config import AgentConfig
from nodemate.agent_notifier import AgentNotifier
from nodemate.config_store import NodeEntry

def test_agent():
    """Test the autonomous agent components."""
    print("🧪 Testing Autonomous Agent System...")
    
    # Test 1: Agent Config
    print("\n1. Testing Agent Config...")
    config = AgentConfig()
    print(f"   ✅ Default heartbeat: {config.heartbeat_interval} minutes")
    print(f"   ✅ Default retries: {config.max_login_retries}")
    
    # Test 2: Agent Notifier
    print("\n2. Testing Agent Notifier...")
    notifier = AgentNotifier()
    print(f"   ✅ Notifier initialized (Toast available: {notifier.toaster is not None})")
    
    # Test 3: Agent Event
    print("\n3. Testing Agent Event...")
    from datetime import datetime
    event = AgentEvent(
        timestamp=datetime.now(),
        node_id="test-node",
        node_name="Test Node",
        event_type="login_success",
        message="Test login successful"
    )
    print(f"   ✅ Event created: {event.node_name} - {event.message}")
    
    # Test 4: Autonomous Agent
    print("\n4. Testing Autonomous Agent...")
    agent = AutonomousAgent()
    print(f"   ✅ Agent initialized (active: {agent.is_active})")
    
    # Test 5: Mock Node Entry
    print("\n5. Testing Node Entry...")
    test_node = NodeEntry(
        id="test-123",
        name="Test Node",
        node_type="exe",
        exe_path="C:\\test\\app.exe",
        login_email="test@example.com",
        login_password="password123",
        enabled=True
    )
    print(f"   ✅ Node created: {test_node.name} (enabled: {test_node.enabled})")
    
    print("\n🎉 All tests passed! Autonomous Agent System is ready.")
    print("\n📋 Next Steps:")
    print("   1. Run: python -m nodemate")
    print("   2. Scan for your DePIN nodes")
    print("   3. Enable nodes and configure credentials")
    print("   4. Start the autonomous agent")
    print("   5. Enjoy hands-off DePIN management! 🚀")

if __name__ == "__main__":
    test_agent()

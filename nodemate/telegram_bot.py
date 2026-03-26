"""
Telegram Bot Integration - Manual Control Alerts
Sends screenshots and alerts when nodes need login.
"""

from __future__ import annotations

import requests
import json
import logging
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime

logger = logging.getLogger(__name__)


class TelegramAlertBot:
    """Telegram bot for sending alerts and receiving commands."""
    
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        
        # Store last alert time to avoid spam
        self.last_alerts: Dict[str, datetime] = {}
        self.alert_cooldown = 300  # 5 minutes between same node alerts
        
        logger.info("TelegramAlertBot initialized")
    
    def send_login_alert(self, node_name: str, screenshot_path: str) -> bool:
        """Send login alert with screenshot."""
        try:
            # Check cooldown
            if self._is_on_cooldown(node_name):
                logger.debug(f"Alert for {node_name} on cooldown")
                return False
            
            # Prepare message
            message = f"⚠️ *{node_name}* needs manual login!\n\n"
            message += f"Time: {datetime.now().strftime('%H:%M:%S')}\n"
            message += "Please check the application and login manually."
            
            # Send text message
            self._send_message(message)
            
            # Send screenshot if available
            if screenshot_path and Path(screenshot_path).exists():
                self._send_photo(screenshot_path, f"{node_name} login screen")
            
            # Update cooldown
            self.last_alerts[node_name] = datetime.now()
            
            logger.info(f"Telegram alert sent for {node_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send Telegram alert: {e}")
            return False
    
    def send_status_update(self, node_name: str, status: str, message: str = "") -> bool:
        """Send status update."""
        try:
            status_emoji = {
                'healthy': '✅',
                'needs_login': '⚠️', 
                'restarted': '🔄',
                'error': '❌'
            }.get(status, '📊')
            
            text = f"{status_emoji} *{node_name}*: {status}"
            if message:
                text += f"\n{message}"
            
            return self._send_message(text)
            
        except Exception as e:
            logger.error(f"Failed to send status update: {e}")
            return False
    
    def _send_message(self, text: str) -> bool:
        """Send text message to Telegram."""
        try:
            url = f"{self.base_url}/sendMessage"
            data = {
                'chat_id': self.chat_id,
                'text': text,
                'parse_mode': 'HTML'
            }
            
            response = requests.post(url, json=data, timeout=10)
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Telegram message error: {e}")
            return False
    
    def _send_photo(self, photo_path: str, caption: str) -> bool:
        """Send photo to Telegram."""
        try:
            url = f"{self.base_url}/sendPhoto"
            
            with open(photo_path, 'rb') as photo:
                files = {
                    'photo': photo,
                    'chat_id': (None, self.chat_id),
                    'caption': (None, caption)
                }
                
                response = requests.post(url, files=files, timeout=30)
                return response.status_code == 200
                
        except Exception as e:
            logger.error(f"Telegram photo error: {e}")
            return False
    
    def _is_on_cooldown(self, node_name: str) -> bool:
        """Check if alert is on cooldown."""
        if node_name not in self.last_alerts:
            return False
            
        time_since_last = datetime.now() - self.last_alerts[node_name]
        return time_since_last.total_seconds() < self.alert_cooldown
    
    def test_connection(self) -> bool:
        """Test Telegram bot connection."""
        return self._send_message("🧪 Test message - Node-Mate watchdog is online!")
    
    def get_bot_info(self) -> str:
        """Get bot info for setup."""
        return f"""
🤖 Telegram Bot Setup Instructions:

1. Create a bot: https://t.me/BotFather
2. Get your **Bot Token**
3. Start a chat with your bot and get your **Chat ID**
4. Add both to Node-Mate settings:

Bot Token: {self.bot_token}
Chat ID: {self.chat_id}

Usage:
- Bot sends login alerts automatically
- You can send commands: /status, /help
- Screenshots included when available
        """

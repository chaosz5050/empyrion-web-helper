# FILE LOCATION: /messaging.py (root directory)
#!/usr/bin/env python3
"""
Messaging Module for Empyrion Web Helper
Handles all messaging functionality:
- Scheduled messages with configurable intervals
- Custom player status messages (welcome/goodbye)
- Global message sending
- Message history and logging

Configuration stored in empyrion_helper.conf under [messaging] section
"""

import sqlite3
import json
import logging
import os
import re
import configparser
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from threading import Timer

logger = logging.getLogger(__name__)

class MessagingManager:
    """Manages all messaging functionality for the Empyrion server"""
    
    def __init__(self, connection_handler=None, player_db=None, config_file="empyrion_helper.conf"):
        self.connection_handler = connection_handler
        self.player_db = player_db
        self.config_file = config_file
        
        # Message templates (defaults)
        self.welcome_message_template = 'Welcome to Space Cowboys, <playername>!'
        self.goodbye_message_template = 'Player <playername> has left our galaxy'
        
        # Scheduled messages state
        self.scheduled_messages = []
        self.last_message_check = {}
        self.message_timer = None
        
        # Initialize database (only for message history)
        self._init_message_database()
        
        # Load configuration from empyrion_helper.conf
        self._load_config()
        
        logger.info("MessagingManager initialized with config from empyrion_helper.conf")
    
    def _load_config(self):
        """Load messaging configuration from empyrion_helper.conf"""
        try:
            config = configparser.ConfigParser()
            
            if os.path.exists(self.config_file):
                config.read(self.config_file)
                logger.info(f"Read config file: {self.config_file}")
            else:
                logger.warning(f"Config file {self.config_file} doesn't exist")
                return
            
            # Load custom messages
            if config.has_section('messaging'):
                self.welcome_message_template = config.get('messaging', 'welcome_message', 
                                                         fallback='Welcome to Space Cowboys, <playername>!')
                self.goodbye_message_template = config.get('messaging', 'goodbye_message', 
                                                         fallback='Player <playername> has left our galaxy')
                
                # Load scheduled messages from config
                scheduled_json = config.get('messaging', 'scheduled_messages', fallback='[]')
                try:
                    self.scheduled_messages = json.loads(scheduled_json)
                except json.JSONDecodeError:
                    logger.warning("Invalid scheduled_messages JSON in config, using empty list")
                    self.scheduled_messages = []
                
                logger.info(f"Loaded messaging config: welcome='{self.welcome_message_template}', goodbye='{self.goodbye_message_template}', {len(self.scheduled_messages)} scheduled messages")
            else:
                logger.info("No [messaging] section found in config, using defaults")
                
        except Exception as e:
            logger.error(f"Error loading messaging config: {e}")
    
    def _save_config(self):
        """Save messaging configuration to empyrion_helper.conf"""
        try:
            logger.info(f"Attempting to save config to: {self.config_file}")
            
            config = configparser.ConfigParser()
            
            # Read existing config first
            if os.path.exists(self.config_file):
                config.read(self.config_file)
                logger.info(f"Read existing config from {self.config_file}")
            else:
                logger.warning(f"Config file {self.config_file} doesn't exist, creating new one")
            
            # Ensure messaging section exists
            if not config.has_section('messaging'):
                config.add_section('messaging')
                logger.info("Added [messaging] section to config")
            
            # Save custom messages
            config.set('messaging', 'welcome_message', self.welcome_message_template)
            config.set('messaging', 'goodbye_message', self.goodbye_message_template)
            logger.info(f"Set welcome_message: {self.welcome_message_template}")
            logger.info(f"Set goodbye_message: {self.goodbye_message_template}")
            
            # Save scheduled messages as JSON (pretty formatted)
            scheduled_json = json.dumps(self.scheduled_messages, indent=2)
            config.set('messaging', 'scheduled_messages', scheduled_json)
            logger.info(f"Set scheduled_messages: {len(self.scheduled_messages)} messages")
            
            # Write back to file with explicit encoding
            with open(self.config_file, 'w', encoding='utf-8') as f:
                config.write(f)
            
            # Verify the file was written
            if os.path.exists(self.config_file):
                file_size = os.path.getsize(self.config_file)
                logger.info(f"SUCCESS: Config saved to {self.config_file} (size: {file_size} bytes)")
            else:
                logger.error(f"FAILED: Config file {self.config_file} was not created!")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving messaging config: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    def _init_message_database(self):
        """Initialize database tables for messaging (ONLY message history)"""
        try:
            with sqlite3.connect('instance/players.db') as conn:
                cursor = conn.cursor()
                
                # Message history table (only this, no config tables)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS message_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        message_type TEXT NOT NULL,
                        message_text TEXT NOT NULL,
                        player_name TEXT,
                        success BOOLEAN DEFAULT TRUE
                    )
                """)
                
                conn.commit()
                logger.info("Message history database table initialized")
                
        except Exception as e:
            logger.error(f"Error initializing message database: {e}")
    
    def set_connection_handler(self, connection_handler):
        """Set the connection handler (called from main app)"""
        self.connection_handler = connection_handler
    
    # ============================================================================
    # GLOBAL MESSAGES
    # ============================================================================
    
    def send_global_message(self, message: str, message_type: str = 'manual') -> bool:
        """Send a global message to all players"""
        if not message.strip():
            logger.warning("Cannot send empty global message")
            return False
        
        if not self.connection_handler:
            logger.error("No connection handler available for messaging")
            return False
        
        try:
            # Use the connection handler's send_command method
            result = self.connection_handler.send_command(f"say '{message}'")
            
            success = result and not result.startswith('Error:')
            
            # Log the message to database (history only)
            self._store_message_log(message, message_type, success=success)
            
            if success:
                logger.info(f"Global message sent successfully: {message}")
            else:
                logger.error(f"Failed to send global message: {result}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending global message: {e}")
            self._store_message_log(message, message_type, success=False)
            return False
    
    # ============================================================================
    # CUSTOM PLAYER STATUS MESSAGES
    # ============================================================================
    
    def load_custom_messages(self) -> Dict[str, str]:
        """Load custom welcome/goodbye messages from config"""
        self._load_config()  # Reload from config file
        return {
            'welcome_message': self.welcome_message_template,
            'goodbye_message': self.goodbye_message_template
        }
    
    def save_custom_messages(self, welcome_msg: str, goodbye_msg: str) -> bool:
        """Save custom welcome/goodbye messages to config"""
        try:
            logger.info(f"Saving custom messages - Welcome: '{welcome_msg}', Goodbye: '{goodbye_msg}'")
            
            if not welcome_msg.strip():
                welcome_msg = 'Welcome to Space Cowboys, <playername>!'
            if not goodbye_msg.strip():
                goodbye_msg = 'Player <playername> has left our galaxy'
            
            # Update in memory
            old_welcome = self.welcome_message_template
            old_goodbye = self.goodbye_message_template
            
            self.welcome_message_template = welcome_msg
            self.goodbye_message_template = goodbye_msg
            
            logger.info(f"Updated templates - Old welcome: '{old_welcome}' -> New: '{welcome_msg}'")
            logger.info(f"Updated templates - Old goodbye: '{old_goodbye}' -> New: '{goodbye_msg}'")
            
            # Save to config file (NOT database)
            success = self._save_config()
            
            if success:
                logger.info("SUCCESS: Custom messages saved to empyrion_helper.conf")
            else:
                logger.error("FAILED: Could not save custom messages to config file")
            
            return success
            
        except Exception as e:
            logger.error(f"Error saving custom messages: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    def send_welcome_message(self, player_name: str) -> bool:
        """Send welcome message for a player"""
        if not player_name:
            return False
        
        message = self.welcome_message_template.replace('<playername>', player_name)
        return self.send_global_message(message, message_type='welcome')
    
    def send_goodbye_message(self, player_name: str) -> bool:
        """Send goodbye message for a player"""
        if not player_name:
            return False
        
        message = self.goodbye_message_template.replace('<playername>', player_name)
        return self.send_global_message(message, message_type='goodbye')
    
    # ============================================================================
    # SCHEDULED MESSAGES
    # ============================================================================
    
    def load_scheduled_messages(self) -> List[Dict]:
        """Load scheduled messages from config"""
        self._load_config()  # Reload from config file
        
        # Ensure we have at least 5 message slots
        while len(self.scheduled_messages) < 5:
            self.scheduled_messages.append({
                'id': len(self.scheduled_messages) + 1,
                'enabled': False,
                'text': '',
                'schedule': 'Every 5 minutes'
            })
        
        logger.info(f"Loaded {len(self.scheduled_messages)} scheduled messages from config")
        return self.scheduled_messages
    
    def save_scheduled_messages(self, messages_data: List[Dict]) -> bool:
        """Save scheduled messages to config"""
        try:
            logger.info(f"Saving {len(messages_data)} scheduled messages to config")
            
            # Validate and clean the data
            cleaned_messages = []
            for i, msg in enumerate(messages_data, 1):
                cleaned_msg = {
                    'id': i,
                    'enabled': bool(msg.get('enabled', False)),
                    'text': str(msg.get('text', '')),
                    'schedule': str(msg.get('schedule', 'Every 5 minutes'))
                }
                cleaned_messages.append(cleaned_msg)
                logger.info(f"Message {i}: enabled={cleaned_msg['enabled']}, text='{cleaned_msg['text']}', schedule='{cleaned_msg['schedule']}'")
            
            old_count = len(self.scheduled_messages)
            self.scheduled_messages = cleaned_messages
            
            logger.info(f"Updated scheduled messages: {old_count} -> {len(cleaned_messages)} messages")
            
            # Save to config file (NOT database)
            success = self._save_config()
            
            if success:
                logger.info(f"SUCCESS: Saved {len(cleaned_messages)} scheduled messages to empyrion_helper.conf")
            else:
                logger.error("FAILED: Could not save scheduled messages to config file")
            
            return success
            
        except Exception as e:
            logger.error(f"Error saving scheduled messages: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    def start_message_scheduler(self):
        """Start the scheduled message timer"""
        if self.message_timer:
            self.message_timer.cancel()
        
        self.message_timer = Timer(30.0, self._check_scheduled_messages)
        self.message_timer.daemon = True
        self.message_timer.start()
        logger.info("Message scheduler started")
    
    def stop_message_scheduler(self):
        """Stop the scheduled message timer"""
        if self.message_timer:
            self.message_timer.cancel()
            self.message_timer = None
        logger.info("Message scheduler stopped")
    
    def _check_scheduled_messages(self):
        """Check and send scheduled messages if needed"""
        try:
            current_time = datetime.now()
            
            for i, msg_data in enumerate(self.scheduled_messages):
                if not isinstance(msg_data, dict):
                    continue
                
                if not msg_data.get('enabled', False):
                    continue
                
                message_text = msg_data.get('text', '').strip()
                if not message_text:
                    continue
                
                schedule = msg_data.get('schedule', 'Every 5 minutes')
                
                if self._should_send_message(i, schedule, current_time):
                    success = self.send_global_message(message_text, message_type='scheduled')
                    if success:
                        self.last_message_check[i] = current_time
                        logger.info(f"Scheduled message {i+1} sent: {message_text}")
                    else:
                        logger.error(f"Failed to send scheduled message {i+1}: {message_text}")
            
            # Schedule next check
            self.start_message_scheduler()
            
        except Exception as e:
            logger.error(f"Error checking scheduled messages: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Restart scheduler anyway
            self.start_message_scheduler()
    
    def _should_send_message(self, msg_index: int, schedule: str, current_time: datetime) -> bool:
        """Determine if a scheduled message should be sent"""
        last_sent = self.last_message_check.get(msg_index)
        
        if not last_sent:
            # First time - don't send immediately, just record the time
            self.last_message_check[msg_index] = current_time
            return False
        
        time_diff = current_time - last_sent
        
        # Parse schedule string to determine interval
        if 'minute' in schedule.lower():
            try:
                minutes = int(re.search(r'(\d+)', schedule).group(1))
                required_interval = timedelta(minutes=minutes)
                return time_diff >= required_interval
            except (AttributeError, ValueError):
                return False
        elif 'hour' in schedule.lower():
            try:
                hours = int(re.search(r'(\d+)', schedule).group(1))
                required_interval = timedelta(hours=hours)
                return time_diff >= required_interval
            except (AttributeError, ValueError):
                return False
        
        return False
    
    # ============================================================================
    # MESSAGE HISTORY (database only)
    # ============================================================================
    
    def get_message_history(self, limit: int = 100) -> List[Dict]:
        """Get recent message history"""
        try:
            with sqlite3.connect('instance/players.db') as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT timestamp, message_type, message_text, player_name, success
                    FROM message_history 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, (limit,))
                
                history = []
                for row in cursor.fetchall():
                    history.append({
                        'timestamp': row[0],
                        'type': row[1],
                        'message': row[2],
                        'player': row[3],
                        'success': bool(row[4])
                    })
                
                return history
                
        except Exception as e:
            logger.error(f"Error getting message history: {e}")
            return []
    
    def _store_message_log(self, message: str, message_type: str, player_name: str = None, success: bool = True):
        """Store message in history log (database only)"""
        try:
            current_time = datetime.now().isoformat()
            
            with sqlite3.connect('instance/players.db') as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO message_history 
                    (timestamp, message_type, message_text, player_name, success)
                    VALUES (?, ?, ?, ?, ?)
                """, (current_time, message_type, message, player_name, success))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error storing message log: {e}")
    
    # ============================================================================
    # UTILITY METHODS
    # ============================================================================
    
    def test_welcome_message(self, test_player_name: str = "TestPlayer") -> bool:
        """Send a test welcome message"""
        return self.send_welcome_message(test_player_name)
    
    def test_goodbye_message(self, test_player_name: str = "TestPlayer") -> bool:
        """Send a test goodbye message"""
        return self.send_goodbye_message(test_player_name)
    
    def get_message_stats(self) -> Dict[str, int]:
        """Get message statistics"""
        try:
            with sqlite3.connect('instance/players.db') as conn:
                cursor = conn.cursor()
                
                # Total messages
                cursor.execute("SELECT COUNT(*) FROM message_history")
                total = cursor.fetchone()[0]
                
                # Messages by type
                cursor.execute("""
                    SELECT message_type, COUNT(*) 
                    FROM message_history 
                    GROUP BY message_type
                """)
                by_type = dict(cursor.fetchall())
                
                # Successful messages
                cursor.execute("SELECT COUNT(*) FROM message_history WHERE success = 1")
                successful = cursor.fetchone()[0]
                
                return {
                    'total': total,
                    'successful': successful,
                    'failed': total - successful,
                    'by_type': by_type
                }
                
        except Exception as e:
            logger.error(f"Error getting message stats: {e}")
            return {
                'total': 0,
                'successful': 0,
                'failed': 0,
                'by_type': {}
            }
    
    def clear_message_history(self) -> bool:
        """Clear all message history"""
        try:
            with sqlite3.connect('instance/players.db') as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM message_history")
                conn.commit()
            
            logger.info("Message history cleared")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing message history: {e}")
            return False

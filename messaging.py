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
import io

logger = logging.getLogger(__name__)

class MessagingManager:
    """
    Manages all messaging functionality for the Empyrion server.

    Handles scheduled messages, custom player status messages (welcome/goodbye), global messaging, message history logging, and configuration management.
    """
    
    def __init__(self, connection_handler=None, player_db=None, config_file="empyrion_helper.conf"):
        """
        Initialize the MessagingManager.

        Args:
            connection_handler: Handler for sending messages to the Empyrion server (optional).
            player_db: Player database instance for logging and lookups (optional).
            config_file (str, optional): Path to the configuration file. Defaults to 'empyrion_helper.conf'.
        """
        self.connection_handler = connection_handler
        self.player_db = player_db
        self.config_file = config_file
        
        # Message templates (defaults)
        self.welcome_message_template = 'Welcome to Space Cowboys, <playername>!'
        self.goodbye_message_template = 'Player <playername> has left our galaxy'
        self.welcome_enabled = True
        self.goodbye_enabled = True
        
        # Scheduled messages state
        self.scheduled_messages = []
        self.last_message_check = {}
        self.message_timer = None
        
        # Help commands state
        self.help_commands = []
        
        # Path to local copy of mod configuration file (in current directory)
        self.mod_config_path = "PlayerStatusConfig.json"
        
        # Initialize database (only for message history)
        self._init_message_database()
        
        # Load configuration from empyrion_helper.conf
        self._load_config()
        
        logger.info("MessagingManager initialized with config from empyrion_helper.conf")
    
    def _load_config(self):
        """
        Load messaging configuration from the empyrion_helper.conf file.
        """
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
                self.welcome_enabled = config.getboolean('messaging', 'welcome_enabled', fallback=True)
                self.goodbye_enabled = config.getboolean('messaging', 'goodbye_enabled', fallback=True)
                
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
        """
        Save messaging configuration to the empyrion_helper.conf file.

        Returns:
            bool: True if saved successfully, False otherwise.
        """
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
            config.set('messaging', 'welcome_enabled', str(self.welcome_enabled))
            config.set('messaging', 'goodbye_enabled', str(self.goodbye_enabled))
            logger.info(f"Set welcome_message: {self.welcome_message_template} (enabled: {self.welcome_enabled})")
            logger.info(f"Set goodbye_message: {self.goodbye_message_template} (enabled: {self.goodbye_enabled})")
            
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
    
    def _write_mod_config(self):
        """Write current message settings to mod configuration file."""
        try:
            config_data = {
                "welcome_enabled": self.welcome_enabled,
                "welcome_message": self.welcome_message_template.replace('<playername>', '{playername}'),
                "goodbye_enabled": self.goodbye_enabled,
                "goodbye_message": self.goodbye_message_template.replace('<playername>', '{playername}'),
                "scheduled_messages": [],
                "help_commands": self.help_commands if hasattr(self, 'help_commands') else []
            }
            
            # Convert scheduled messages to mod format
            for msg in self.scheduled_messages:
                if isinstance(msg, dict) and msg.get('enabled', False):
                    schedule_str = msg.get('schedule', 'Every 30 minutes')
                    # Extract minutes from schedule string
                    import re
                    match = re.search(r'(\d+)', schedule_str)
                    if match:
                        if 'hour' in schedule_str.lower():
                            interval_minutes = int(match.group(1)) * 60
                        else:
                            interval_minutes = int(match.group(1))
                    else:
                        interval_minutes = 30
                    
                    config_data["scheduled_messages"].append({
                        "enabled": True,
                        "text": msg.get('text', ''),
                        "interval_minutes": interval_minutes,
                        "last_sent": "1970-01-01T00:00:00"  # Reset timing
                    })
            
            # Ensure directory exists (only if not in current directory)
            directory = os.path.dirname(self.mod_config_path)
            if directory:  # Only create directory if path contains a directory
                os.makedirs(directory, exist_ok=True)
            
            # Write configuration
            with open(self.mod_config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Mod configuration written to {self.mod_config_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error writing mod configuration: {e}")
            return False

    def _download_mod_config_from_server(self):
        """Download mod configuration from server via FTP."""
        logger.info("[Mod Config Download] Starting download process...")
        
        if not self.player_db:
            logger.error("[Mod Config Download] No player database available for FTP credentials")
            return False
            
        try:
            # Get FTP credentials and mod path
            ftp_creds = self.player_db.get_credential('ftp')
            ftp_host = self.player_db.get_app_setting('ftp_host')
            ftp_mod_path = self.player_db.get_app_setting('ftp_mod_path')
            
            logger.info(f"[Mod Config Download] FTP creds: {'✅' if ftp_creds else '❌'}, Host: {ftp_host}, Mod path: {ftp_mod_path}")
            
            if not ftp_creds or not ftp_host or not ftp_mod_path:
                logger.warning("[Mod Config Download] FTP credentials or mod path not configured, cannot download from server")
                return False
                
            # Upload via FTP using EnhancedConnectionManager (same as other FTP operations)
            from connection_manager import EnhancedConnectionManager, UniversalFileClient
            
            # Parse host and port
            if ':' in ftp_host:
                host, port = ftp_host.split(':', 1)
                port = int(port)
            else:
                host = ftp_host
                port = 22  # Default for auto-detection
                
            # Auto-detect connection type and connect
            manager = EnhancedConnectionManager()
            connection_result = manager.detect_and_connect(host, port, ftp_creds['username'], ftp_creds['password'])
            
            if not connection_result.success:
                logger.error(f"[Mod Config Download] Cannot connect to server: {connection_result.message}")
                return False
                
            logger.info(f"[Mod Config Download] Connected using {connection_result.connection_type.upper()}")
            
            # Create UniversalFileClient with detected connection type
            client = UniversalFileClient(
                connection_result.connection_type,
                host, port,
                ftp_creds['username'], ftp_creds['password']
            )
            
            # Download from server
            remote_path = f"{ftp_mod_path}/PlayerStatusConfig.json"
            logger.info(f"[Mod Config Download] Downloading from: {remote_path}")
            
            # Use the client to download
            with client.connect() as file_client:
                # Download to memory buffer
                json_buffer = io.BytesIO()
                file_client.download_file(remote_path, json_buffer)
                json_buffer.seek(0)
                
                # Parse JSON content
                json_content = json_buffer.read().decode('utf-8')
                config_data = json.loads(json_content)
                
                # Update local configuration
                self.welcome_enabled = config_data.get('welcome_enabled', True)
                self.welcome_message_template = config_data.get('welcome_message', 'Welcome to Space Cowboys, <playername>!').replace('{playername}', '<playername>')
                self.goodbye_enabled = config_data.get('goodbye_enabled', True)
                self.goodbye_message_template = config_data.get('goodbye_message', 'Player <playername> has left our galaxy').replace('{playername}', '<playername>')
                
                # Convert scheduled messages from mod format
                self.scheduled_messages = []
                for i, msg in enumerate(config_data.get('scheduled_messages', []), 1):
                    # Convert interval_minutes back to schedule string
                    interval_minutes = msg.get('interval_minutes', 30)
                    if interval_minutes >= 60:
                        hours = interval_minutes // 60
                        schedule = f"Every {hours} hour{'s' if hours > 1 else ''}"
                    else:
                        schedule = f"Every {interval_minutes} minutes"
                    
                    self.scheduled_messages.append({
                        'id': i,
                        'enabled': msg.get('enabled', False),
                        'text': msg.get('text', ''),
                        'schedule': schedule
                    })
                
                # Save updated configuration to local conf file
                success = self._save_config()
                
                if success:
                    logger.info(f"[Mod Config Download] ✅ Successfully downloaded and applied mod configuration from server: {remote_path}")
                    return True
                else:
                    logger.error("[Mod Config Download] Downloaded config but failed to save locally")
                    return False
                
        except Exception as e:
            logger.error(f"Error downloading mod configuration from server: {e}")
            return False

    def _upload_mod_config_to_server(self):
        """Upload mod configuration to server via FTP."""
        logger.info("[Mod Config Upload] Starting upload process...")
        
        if not self.player_db:
            logger.error("[Mod Config Upload] No player database available for FTP credentials")
            return False
            
        try:
            # Get FTP credentials and mod path
            ftp_creds = self.player_db.get_credential('ftp')
            ftp_host = self.player_db.get_app_setting('ftp_host')
            ftp_mod_path = self.player_db.get_app_setting('ftp_mod_path')
            
            logger.info(f"[Mod Config Upload] FTP creds: {'✅' if ftp_creds else '❌'}, Host: {ftp_host}, Mod path: {ftp_mod_path}")
            
            if not ftp_creds or not ftp_host or not ftp_mod_path:
                logger.warning("[Mod Config Upload] FTP credentials or mod path not configured, skipping server upload")
                return False
                
            # Generate config data
            config_data = {
                "welcome_enabled": self.welcome_enabled,
                "welcome_message": self.welcome_message_template.replace('<playername>', '{playername}'),
                "goodbye_enabled": self.goodbye_enabled,
                "goodbye_message": self.goodbye_message_template.replace('<playername>', '{playername}'),
                "scheduled_messages": [],
                "help_commands": self.help_commands if hasattr(self, 'help_commands') else []
            }
            
            # Convert scheduled messages to mod format
            for msg in self.scheduled_messages:
                if isinstance(msg, dict) and msg.get('enabled', False):
                    schedule_str = msg.get('schedule', 'Every 30 minutes')
                    # Extract minutes from schedule string
                    import re
                    match = re.search(r'(\d+)', schedule_str)
                    if match:
                        if 'hour' in schedule_str.lower():
                            interval_minutes = int(match.group(1)) * 60
                        else:
                            interval_minutes = int(match.group(1))
                    else:
                        interval_minutes = 30
                    
                    config_data["scheduled_messages"].append({
                        "enabled": True,
                        "text": msg.get('text', ''),
                        "interval_minutes": interval_minutes,
                        "last_sent": "1970-01-01T00:00:00"  # Reset timing
                    })
            
            # Create JSON string
            json_content = json.dumps(config_data, indent=2, ensure_ascii=False)
            
            # Upload via FTP using EnhancedConnectionManager (same as other FTP operations)
            from connection_manager import EnhancedConnectionManager, UniversalFileClient
            
            # Parse host and port
            if ':' in ftp_host:
                host, port = ftp_host.split(':', 1)
                port = int(port)
            else:
                host = ftp_host
                port = 22  # Default for auto-detection
                
            # Auto-detect connection type and connect
            manager = EnhancedConnectionManager()
            connection_result = manager.detect_and_connect(host, port, ftp_creds['username'], ftp_creds['password'])
            
            if not connection_result.success:
                logger.error(f"[Mod Config Upload] Cannot connect to server: {connection_result.message}")
                return False
                
            logger.info(f"[Mod Config Upload] Connected using {connection_result.connection_type.upper()}")
            
            # Create UniversalFileClient with detected connection type
            client = UniversalFileClient(
                connection_result.connection_type,
                host, port,
                ftp_creds['username'], ftp_creds['password']
            )
            
            # Create file-like object from JSON string
            json_bytes = io.BytesIO(json_content.encode('utf-8'))
            
            # Upload to server
            remote_path = f"{ftp_mod_path}/PlayerStatusConfig.json"
            logger.info(f"[Mod Config Upload] Uploading to: {remote_path}")
            
            # Use the client to upload
            with client.connect() as file_client:
                file_client.upload_file(json_bytes, remote_path)
            
            logger.info(f"[Mod Config Upload] ✅ Successfully uploaded mod configuration to server: {remote_path}")
            return True
                
        except Exception as e:
            logger.error(f"Error uploading mod configuration to server: {e}")
            return False
    
    def _init_message_database(self):
        """
        Initialize the SQLite database tables for message history logging.
        """
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
        """
        Set the connection handler for sending messages to the Empyrion server.

        Args:
            connection_handler: The connection handler instance.
        """
        self.connection_handler = connection_handler
    
    # ============================================================================
    # GLOBAL MESSAGES
    # ============================================================================
    
    def send_global_message(self, message: str, message_type: str = 'manual') -> Dict:
        """
        Send a global message to all players on the Empyrion server.

        Args:
            message (str): The message to send.
            message_type (str, optional): The type of message ('manual', 'scheduled', etc.). Defaults to 'manual'.

        Returns:
            Dict: Result dictionary with 'success' and 'message' keys.
        """
        if not message.strip():
            logger.warning("Cannot send empty global message")
            return {'success': False, 'message': 'Cannot send empty global message'}
        
        if not self.connection_handler:
            logger.error("No connection handler available for messaging")
            # Still log the message attempt in history as failed
            self._store_message_log(message, message_type, success=False)
            return {'success': False, 'message': 'An internal error occurred. Please try again later.'}
        
        try:
            # Use the connection handler's send_command method
            logger.info(f"🔥 MESSAGING DEBUG: About to send command: say '{message}' (type: {message_type})")
            result = self.connection_handler.send_command(f"say '{message}'")
            
            success = result and not result.startswith('Error:')
            
            # Log the message to database (history only)
            self._store_message_log(message, message_type, success=success)
            
            if success:
                logger.info(f"Global message sent successfully: {message}")
                return {'success': True, 'message': 'Message sent successfully'}
            else:
                logger.error(f"Failed to send global message: {result}")
                return {'success': False, 'message': 'Failed to send global message'}
            
        except Exception as e:
            logger.error(f"Error sending global message: {e}", exc_info=True)
            self._store_message_log(message, message_type, success=False)
            return {'success': False, 'message': 'An internal error occurred. Please try again later.'}
    
    # ============================================================================
    # CUSTOM PLAYER STATUS MESSAGES
    # ============================================================================
    
    def load_custom_messages(self) -> Dict:
        """
        Load custom welcome and goodbye messages with enabled states from the configuration file.

        Returns:
            Dict: Dictionary with message templates and enabled states.
        """
        self._load_config()  # Reload from config file
        return {
            'welcome_message': self.welcome_message_template,
            'goodbye_message': self.goodbye_message_template,
            'welcome_enabled': self.welcome_enabled,
            'goodbye_enabled': self.goodbye_enabled
        }
    
    def save_custom_messages(self, welcome_msg: str, goodbye_msg: str, welcome_enabled: bool = True, goodbye_enabled: bool = True) -> Dict:
        """
        Save custom welcome and goodbye messages with enabled states to the configuration file.

        Args:
            welcome_msg (str): The welcome message template.
            goodbye_msg (str): The goodbye message template.
            welcome_enabled (bool): Whether welcome messages are enabled.
            goodbye_enabled (bool): Whether goodbye messages are enabled.

        Returns:
            Dict: Result dictionary with 'success' and 'message' keys.
        """
        try:
            logger.info(f"Saving custom messages - Welcome: '{welcome_msg}' (enabled: {welcome_enabled}), Goodbye: '{goodbye_msg}' (enabled: {goodbye_enabled})")
            
            if not welcome_msg.strip():
                welcome_msg = 'Welcome to Space Cowboys, <playername>!'
            if not goodbye_msg.strip():
                goodbye_msg = 'Player <playername> has left our galaxy'
            
            # Update in memory
            old_welcome = self.welcome_message_template
            old_goodbye = self.goodbye_message_template
            old_welcome_enabled = self.welcome_enabled
            old_goodbye_enabled = self.goodbye_enabled
            
            self.welcome_message_template = welcome_msg
            self.goodbye_message_template = goodbye_msg
            self.welcome_enabled = welcome_enabled
            self.goodbye_enabled = goodbye_enabled
            
            logger.info(f"Updated templates - Old welcome: '{old_welcome}' -> New: '{welcome_msg}'")
            logger.info(f"Updated templates - Old goodbye: '{old_goodbye}' -> New: '{goodbye_msg}'")
            
            # Save to config file (NOT database)
            result = self._save_config()
            
            # Also write to mod config and upload to server
            if result:
                self._write_mod_config()
                self._upload_mod_config_to_server()
            
            if result:
                logger.info("SUCCESS: Custom messages saved to empyrion_helper.conf and mod config")
                return {'success': True, 'message': 'Custom messages saved successfully'}
            else:
                logger.error("FAILED: Could not save custom messages to config file")
                return {'success': False, 'message': 'Failed to save custom messages'}
            
        except Exception as e:
            logger.error(f"Error saving custom messages: {e}", exc_info=True)
            return {'success': False, 'message': 'An internal error occurred. Please try again later.'}
    
    def send_welcome_message(self, player_name: str) -> Dict:
        """
        Send a welcome message for a player.
        
        **IMPORTANT**: Welcome/goodbye messages are now handled by PlayerStatusMod.
        This method is disabled to prevent duplicate messages.

        Args:
            player_name (str): Name of the player to welcome.

        Returns:
            Dict: Result dictionary with 'success' and 'message' keys.
        """
        # SAFETY: Always return disabled to prevent duplicate messages from PlayerStatusMod
        logger.warning(f"🚫 Blocked welcome message for {player_name} - handled by PlayerStatusMod")
        return {'success': True, 'message': 'Welcome messages handled by PlayerStatusMod (prevented duplicate)'}
    
    def send_goodbye_message(self, player_name: str) -> Dict:
        """
        Send a goodbye message for a player.
        
        **IMPORTANT**: Welcome/goodbye messages are now handled by PlayerStatusMod.
        This method is disabled to prevent duplicate messages.

        Args:
            player_name (str): Name of the player to say goodbye to.

        Returns:
            Dict: Result dictionary with 'success' and 'message' keys.
        """
        # SAFETY: Always return disabled to prevent duplicate messages from PlayerStatusMod
        logger.warning(f"🚫 Blocked goodbye message for {player_name} - handled by PlayerStatusMod")
        return {'success': True, 'message': 'Goodbye messages handled by PlayerStatusMod (prevented duplicate)'}
    
    # ============================================================================
    # SCHEDULED MESSAGES
    # ============================================================================
    
    def load_scheduled_messages(self) -> List[Dict]:
        """
        Load scheduled messages from the configuration file.

        Returns:
            List[Dict]: List of scheduled message dictionaries.
        """
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
        """
        Save scheduled messages to the configuration file.

        Args:
            messages_data (List[Dict]): List of scheduled message dictionaries to save.

        Returns:
            bool: True if saved successfully, False otherwise.
        """
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
            
            # Also write to mod config and upload to server
            if success:
                self._write_mod_config()
                self._upload_mod_config_to_server()
            
            if success:
                logger.info(f"SUCCESS: Saved {len(cleaned_messages)} scheduled messages to empyrion_helper.conf and mod config")
            else:
                logger.error("FAILED: Could not save scheduled messages to config file")
            
            return success
            
        except Exception as e:
            logger.error(f"Error saving scheduled messages: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    def start_message_scheduler(self):
        """
        Start the scheduled message timer for sending scheduled messages.
        
        NOTE: This scheduler is disabled to prevent duplicate messages.
        BackgroundService handles all scheduled message sending.
        """
        logger.info("Message scheduler disabled - BackgroundService handles scheduling")
    
    def stop_message_scheduler(self):
        """
        Stop the scheduled message timer.
        """
        if self.message_timer:
            self.message_timer.cancel()
            self.message_timer = None
        logger.info("Message scheduler stopped")
    
    def _check_scheduled_messages(self):
        """
        Check and send scheduled messages if their schedule interval has elapsed.
        
        NOTE: This method is disabled in MessagingManager to prevent duplicate messages.
        BackgroundService handles all scheduled message checking and sending.
        """
        logger.debug("MessagingManager._check_scheduled_messages() called but disabled - BackgroundService handles this")
        return
    
    def _should_send_message(self, msg_index: int, schedule: str, current_time: datetime) -> bool:
        """
        Determine if a scheduled message should be sent based on its schedule and last sent time.

        Args:
            msg_index (int): Index of the message in the scheduled messages list.
            schedule (str): Schedule string (e.g., 'Every 5 minutes').
            current_time (datetime): The current datetime.

        Returns:
            bool: True if the message should be sent, False otherwise.
        """
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
        """
        Get recent message history from the database.

        Args:
            limit (int, optional): Maximum number of history entries to retrieve. Defaults to 100.

        Returns:
            List[Dict]: List of message history entries.
        """
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
        """
        Store a message in the message history log in the database.

        Args:
            message (str): The message text.
            message_type (str): The type of message ('manual', 'scheduled', etc.).
            player_name (str, optional): Name of the player associated with the message.
            success (bool, optional): Whether the message was sent successfully. Defaults to True.
        """
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
        """
        Send a test welcome message for a given player name.

        Args:
            test_player_name (str, optional): Name of the test player. Defaults to "TestPlayer".

        Returns:
            bool: Result of sending the welcome message.
        """
        return self.send_welcome_message(test_player_name)
    
    def test_goodbye_message(self, test_player_name: str = "TestPlayer") -> bool:
        """
        Send a test goodbye message for a given player name.

        Args:
            test_player_name (str, optional): Name of the test player. Defaults to "TestPlayer".

        Returns:
            bool: Result of sending the goodbye message.
        """
        return self.send_goodbye_message(test_player_name)
    
    def get_message_stats(self) -> Dict[str, int]:
        """
        Get statistics about messages sent and stored in the database.

        Returns:
            Dict[str, int]: Dictionary with total, successful, failed, and by_type message counts.
        """
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
        """
        Clear all message history from the database.

        Returns:
            bool: True if cleared successfully, False otherwise.
        """
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

    # ============================================================================
    # HELP COMMANDS
    # ============================================================================
    
    def load_help_commands(self) -> List[Dict]:
        """
        Load help commands from the mod configuration file.
        Returns:
            List[Dict]: List of help command dictionaries with 'command' and 'description' keys.
        """
        try:
            # First try to download latest config from server
            try:
                logger.info("Attempting to download latest config from server for help commands...")
                self._download_mod_config_from_server()
            except Exception as e:
                logger.warning(f"Could not download latest config from server: {e}")
            
            # Try to load from downloaded mod config
            logger.info(f"Looking for mod config at: {self.mod_config_path}")
            if os.path.exists(self.mod_config_path):
                try:
                    with open(self.mod_config_path, 'r') as f:
                        config = json.load(f)
                    
                    help_commands = config.get('help_commands', [])
                    logger.info(f"Successfully loaded {len(help_commands)} help commands from mod config")
                    if help_commands:
                        logger.info(f"First command: {help_commands[0]}")
                    return help_commands
                    
                except Exception as e:
                    logger.error(f"Could not read mod config file: {e}")
            else:
                logger.warning(f"Mod config file does not exist at: {self.mod_config_path}")
            
            # Fallback to default help commands
            logger.info("Using default help commands")
            return [
                {"command": "/vb1", "description": "Open virtual backpack 1"},
                {"command": "/vb2", "description": "Open virtual backpack 2"},
                {"command": "/vb3", "description": "Open virtual backpack 3"},
                {"command": "/vb4", "description": "Open virtual backpack 4"},
                {"command": "/vb5", "description": "Open virtual backpack 5"},
                {"command": "/afk [reason]", "description": "Mark yourself as AFK with optional reason"},
                {"command": "/back", "description": "Return from AFK status"},
                {"command": "/afklist", "description": "View currently AFK players"},
                {"command": "/sethome", "description": "Set emergency teleport location"},
                {"command": "/home", "description": "Emergency teleport with confirmation dialog"},
                {"command": "/home uses", "description": "Check remaining daily teleport uses"}
            ]
            
        except Exception as e:
            logger.error(f"Error loading help commands: {e}")
            return []
    
    def save_help_commands(self, commands_data: List[Dict]) -> bool:
        """
        Save help commands to the configuration file and upload to server.
        Args:
            commands_data (List[Dict]): List of help command dictionaries to save.
        Returns:
            bool: True if saved successfully, False otherwise.
        """
        try:
            logger.info(f"Saving {len(commands_data)} help commands to config")
            
            # Validate and clean the data
            cleaned_commands = []
            for cmd in commands_data:
                if cmd.get('command') and cmd.get('description'):
                    cleaned_cmd = {
                        'command': str(cmd.get('command', '')).strip(),
                        'description': str(cmd.get('description', '')).strip()
                    }
                    cleaned_commands.append(cleaned_cmd)
                    logger.info(f"Command: '{cleaned_cmd['command']}' -> '{cleaned_cmd['description']}'")
            
            # Store in memory (we'll write this during mod config generation)
            self.help_commands = cleaned_commands
            
            logger.info(f"Prepared {len(cleaned_commands)} help commands for mod config")
            
            # Write to mod config and upload to server
            success = self._write_mod_config()
            if success:
                success = self._upload_mod_config_to_server()
            
            if success:
                logger.info(f"SUCCESS: Saved {len(cleaned_commands)} help commands to mod config")
            else:
                logger.error("FAILED: Could not save help commands to mod config")
            
            return success
            
        except Exception as e:
            logger.error(f"Error saving help commands: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False

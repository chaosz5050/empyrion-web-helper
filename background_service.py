# FILE LOCATION: /background_service.py (root directory)
#!/usr/bin/env python3
"""
Background Service Manager for Empyrion Web Helper

This module defines the BackgroundService class, which provides independent 24/7
server monitoring, automated messaging, and player tracking for Empyrion Galactic Survival servers.
"""

import threading
import time
import logging
from datetime import datetime
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

class BackgroundService:
    """
    Core background service for independent operation.

    Manages server connection, player monitoring, scheduled messaging, and background threads.
    """

    def __init__(self, config_manager, player_db, messaging_manager):
        """
        Initialize the BackgroundService.

        Args:
            config_manager (ConfigManager): The configuration manager instance.
            player_db (PlayerDatabase): The player database instance.
            messaging_manager (MessagingManager): The messaging manager instance.
        """
        self.config_manager = config_manager
        self.player_db = player_db
        self.messaging_manager = messaging_manager
        
        # Service state
        self.is_running = False
        self.is_connected = False  # This should start as False
        self.connection_handler = None  # This should start as None
        self.last_connection_attempt = None
        self.reconnect_attempts = 0
        
        # Background threads
        self.monitor_thread = None
        self.scheduler_thread = None
        self.stop_event = threading.Event()
        
        # Player tracking for status changes
        self.previous_players = {}
        
        # Get update interval from config file
        self.MONITOR_INTERVAL = self._get_update_interval()
        self.RECONNECT_DELAY = 30   # seconds between reconnection attempts
        self.MAX_RECONNECT_DELAY = 300  # 5 minutes max delay
        
        logger.info(f"Background service initialized with update_interval={self.MONITOR_INTERVAL}s")
    
    def _get_update_interval(self) -> int:
        """Get update interval from config file with validation."""
        try:
            interval = self.config_manager.get('update_interval')
            if interval:
                interval = int(interval)
                if interval < 10:
                    logger.warning("update_interval below minimum (10s); using 20s")
                    return 20
                return interval
        except (ValueError, TypeError):
            logger.warning("Invalid update_interval in config; using default 20s")
        
        # Default fallback
        return 20
    
    def start(self):
        """
        Start the background service.

        Launches monitoring and scheduler threads for continuous operation.
        Raises an exception if startup fails.
        """
        if self.is_running:
            logger.warning("Background service already running")
            return
        
        self.is_running = True
        self.stop_event.clear()
        
        # Reset connection state on startup
        self.is_connected = False
        self.connection_handler = None
        self.reconnect_attempts = 0
        
        logger.info("🚀 Starting Empyrion Web Helper background service")
        
        try:
            # Start monitoring thread
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True, name="MonitorThread")
            self.monitor_thread.start()
            
            # Start message scheduler thread  
            self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True, name="SchedulerThread")
            self.scheduler_thread.start()
            
            logger.info("✅ Background service started successfully")
            
        except Exception as e:
            logger.error(f"Error starting background service: {e}", exc_info=True)
            self.is_running = False
            raise
    
    def stop(self):
        """
        Stop the background service.

        Signals threads to stop, disconnects from server, and waits for threads to finish.
        """
        if not self.is_running:
            return
        
        logger.info("🛑 Stopping background service...")
        
        self.is_running = False
        self.stop_event.set()
        
        # Disconnect from server
        self._disconnect()
        
        # Wait for threads to finish
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5)
        
        logger.info("✅ Background service stopped")
    
    def get_connection_status(self) -> Dict:
        """
        Get current connection status for web UI.

        Returns:
            dict: Dictionary with connection and service status information.
        """
        return {
            'is_connected': self.is_connected,
            'last_attempt': self.last_connection_attempt,
            'reconnect_attempts': self.reconnect_attempts,
            'is_running': self.is_running
        }
    
    def get_connection_handler(self) -> Optional[object]:
        """
        Get the current connection handler for web UI commands.

        Returns:
            object or None: The connection handler if connected, else None.
        """
        return self.connection_handler if self.is_connected else None
    
    def _monitor_loop(self):
        """
        Main monitoring loop.

        Periodically checks server connection and player status while service is running.
        """
        logger.info("🔍 Starting player monitoring loop")
        
        try:
            while self.is_running and not self.stop_event.is_set():
                try:
                    logger.debug(f"Monitor cycle: is_connected={self.is_connected}, connection_handler={self.connection_handler is not None}")
                    
                    # ALWAYS check connection status first
                    if not self.is_connected or not self.connection_handler:
                        logger.info("🔌 Not connected - attempting connection...")
                        self._attempt_connection()
                    else:
                        # Test if existing connection is still alive
                        if not self.connection_handler.is_connection_alive():
                            logger.warning("🔌 Connection is dead - reconnecting...")
                            self.is_connected = False
                            self.connection_handler = None
                            self._attempt_connection()
                    
                    # If connected, monitor players
                    if self.is_connected and self.connection_handler and self.is_running:
                        logger.debug("🔍 Connected - monitoring players...")
                        self._monitor_players()
                        self.reconnect_attempts = 0  # Reset on successful operation
                    else:
                        logger.debug("🔍 Not connected - skipping player monitoring")
                    
                    # Wait for next cycle
                    self.stop_event.wait(self.MONITOR_INTERVAL)
                    
                except Exception as e:
                    logger.error(f"Exception in monitor loop: {e}", exc_info=True)
                    
                    if self.is_running:  # Only handle error if we're still supposed to be running
                        self._handle_connection_error()
                        self.stop_event.wait(5)  # Brief pause before retry
            
        except Exception as e:
            logger.error(f"Fatal error in monitor loop: {e}", exc_info=True)
        
        logger.info("🔍 Player monitoring loop stopped")
    
    def _scheduler_loop(self):
        """
        Message scheduler loop.

        Periodically checks and sends scheduled messages while service is running.
        """
        logger.info("📅 Starting message scheduler loop")
        
        try:
            while self.is_running and not self.stop_event.is_set():
                try:
                    if self.is_connected and self.messaging_manager and self.is_running:
                        self._check_scheduled_messages()
                    
                    # Check every 30 seconds (scheduled message interval)
                    self.stop_event.wait(30)
                    
                except Exception as e:
                    logger.error(f"Exception in scheduler loop: {e}", exc_info=True)
                    if self.is_running:  # Only pause if we're still supposed to be running
                        self.stop_event.wait(5)  # Brief pause before retry
            
        except Exception as e:
            logger.error(f"Fatal error in scheduler loop: {e}", exc_info=True)
        
        logger.info("📅 Message scheduler loop stopped")
    
    def _attempt_connection(self):
        """
        Attempt to connect to Empyrion server.

        Handles reconnection logic and updates connection state.
        """
        if not self.is_running:
            return False
            
        try:
            self.last_connection_attempt = datetime.now().isoformat()
            
            # Get server config from database first
            server_host = self.player_db.get_app_setting('server_host') or self.config_manager.get('host')
            server_port = self.player_db.get_app_setting('server_port')
            if server_port:
                server_port = int(server_port)
            else:
                server_port = self.config_manager.get('telnet_port')
            
            logger.info(f"🔌 Attempting connection to {server_host}:{server_port}")
            
            # Clean up any existing connection
            if self.connection_handler:
                try:
                    self.connection_handler.disconnect()
                except:
                    pass
            
            # Import here to avoid circular imports
            from connection import EmpyrionConnection
            
            # Get RCON password
            rcon_password = self.config_manager.get('telnet_password')
            if not rcon_password:
                logger.error("❌ No RCON password available")
                self._handle_connection_error()
                return False
            
            # Create new connection
            self.connection_handler = EmpyrionConnection(
                host=server_host,
                port=server_port,
                password=rcon_password,
                timeout=10
            )
            
            # Attempt connection
            connection_result = self.connection_handler.connect()
            
            if connection_result is True:
                self.is_connected = True
                self.reconnect_attempts = 0
                
                # Set connection handler for messaging
                if self.messaging_manager:
                    self.messaging_manager.set_connection_handler(self.connection_handler)
                
                logger.info(f"✅ Successfully connected to Empyrion server at {server_host}:{server_port}")
                return True
            else:
                logger.error(f"❌ Failed to connect to Empyrion server: {connection_result}")
                self._handle_connection_error()
                return False
                
        except Exception as e:
            logger.error(f"❌ Connection attempt failed: {e}", exc_info=True)
            self._handle_connection_error()
            return False
    
    def _disconnect(self):
        """
        Disconnect from server.

        Closes the current connection handler and updates connection state.
        """
        if self.connection_handler:
            try:
                self.connection_handler.disconnect()
            except Exception as e:
                logger.error(f"Error during disconnect: {e}", exc_info=True)
        
        self.is_connected = False
        self.connection_handler = None
        logger.info("🔌 Disconnected from server")
    
    def _handle_connection_error(self):
        """
        Handle connection errors.

        Logs the error and manages reconnection attempts.
        """
        self.is_connected = False
        self.reconnect_attempts += 1
        
        # Calculate delay with exponential backoff
        delay = min(self.RECONNECT_DELAY * (2 ** min(self.reconnect_attempts - 1, 3)), 
                   self.MAX_RECONNECT_DELAY)
        
        logger.warning(f"⚠️ Connection lost. Attempt #{self.reconnect_attempts}. "
                      f"Retrying in {delay} seconds...")
        
        if self.connection_handler:
            try:
                self.connection_handler.disconnect()
            except:
                pass
        self.connection_handler = None
    
    def _monitor_players(self):
        """
        Monitor players.

        Retrieves current player list and detects player status changes.
        """
        if not self.is_running:
            return
            
        try:
            if not self.connection_handler:
                logger.warning("⚠️ No connection handler available for player monitoring")
                return
            
            logger.debug("🔍 Checking player status...")
            
            # Get current players
            current_players = self.connection_handler.get_players()
            
            if current_players is None:
                logger.warning("⚠️ Failed to get player list from server")
                if self.is_running:  # Only handle error if service should be running
                    self._handle_connection_error()
                return
            
            # Handle error dictionary response
            if isinstance(current_players, dict) and not current_players.get('success', True):
                logger.warning("⚠️ Failed to get player list from server (error response)")
                if self.is_running:
                    self._handle_connection_error()
                return
            
            logger.debug(f"📊 Retrieved {len(current_players)} players from server")
            
            # Update database
            if self.player_db and self.is_running:
                updated_count = self.player_db.update_multiple_players(current_players)
                logger.debug(f"💾 Updated {updated_count} players in database")
            
            # Detect status changes and send welcome/goodbye messages
            if self.is_running:  # Only send messages if service is running
                self._detect_status_changes(current_players)
            
        except Exception as e:
            logger.error(f"❌ Error monitoring players: {e}", exc_info=True)
            if self.is_running:  # Only handle error if service should be running
                self._handle_connection_error()
    
    def _detect_status_changes(self, current_players: List[Dict]):
        """
        Detect player status changes.

        Compares current and previous player lists to identify joins and leaves.

        Args:
            current_players (list of dict): The current list of player records.
        """
        if not self.messaging_manager or not self.is_running:
            return
        
        try:
            current_players_dict = {p['steam_id']: p for p in current_players}
            
            # Check for players joining (offline -> online)
            for player in current_players:
                steam_id = player['steam_id']
                player_name = player['name']
                current_status = player['status']
                
                if steam_id in self.previous_players:
                    previous_status = self.previous_players[steam_id]['status']
                    
                    # Player joined
                    if previous_status == 'Offline' and current_status == 'Online':
                        logger.info(f"👋 Player joined: {player_name}")
                        if self.is_running:  # Only send if service is running
                            self.messaging_manager.send_welcome_message(player_name)
                    
                    # Player left
                    elif previous_status == 'Online' and current_status == 'Offline':
                        logger.info(f"👋 Player left: {player_name}")
                        if self.is_running:  # Only send if service is running
                            self.messaging_manager.send_goodbye_message(player_name)
                
                else:
                    # New player joining for first time
                    if current_status == 'Online':
                        logger.info(f"👋 New player joined: {player_name}")
                        if self.is_running:  # Only send if service is running
                            self.messaging_manager.send_welcome_message(player_name)
            
            # Update previous players for next cycle
            self.previous_players = current_players_dict.copy()
            
        except Exception as e:
            logger.error(f"❌ Error detecting status changes: {e}", exc_info=True)
    
    def _check_scheduled_messages(self):
        """
        Check scheduled messages.

        Loads scheduled messages and sends them at appropriate intervals.
        """
        if not self.messaging_manager or not self.is_running:
            return
            
        try:
            # Load current scheduled messages
            scheduled_messages = self.messaging_manager.load_scheduled_messages()
            current_time = datetime.now()
            
            for i, msg_data in enumerate(scheduled_messages):
                if not self.is_running:  # Check if we should stop
                    break
                    
                if not isinstance(msg_data, dict):
                    continue
                
                if not msg_data.get('enabled', False):
                    continue
                
                message_text = msg_data.get('text', '').strip()
                if not message_text:
                    continue
                
                schedule = msg_data.get('schedule', 'Every 5 minutes')
                
                if self._should_send_scheduled_message(i, schedule, current_time):
                    if self.is_running:  # Double-check before sending
                        success = self.messaging_manager.send_global_message(
                            message_text, message_type='scheduled'
                        )
                        if success:
                            # Update last sent time in messaging manager
                            self.messaging_manager.last_message_check[i] = current_time
                            logger.info(f"📢 Scheduled message {i+1} sent: {message_text}")
                        else:
                            logger.error(f"❌ Failed to send scheduled message {i+1}")
            
        except Exception as e:
            logger.error(f"❌ Error checking scheduled messages: {e}", exc_info=True)
    
    def _should_send_scheduled_message(self, msg_index: int, schedule: str, current_time: datetime) -> bool:
        """
        Determine if a scheduled message should be sent.

        Args:
            msg_index (int): Index of the scheduled message.
            schedule (str): Schedule string (e.g., 'Every 5 minutes').
            current_time (datetime): The current time.

        Returns:
            bool: True if the message should be sent, False otherwise.
        """
        if not self.messaging_manager:
            return False
        
        last_sent = self.messaging_manager.last_message_check.get(msg_index)
        
        if not last_sent:
            # First time - don't send immediately, just record the time
            self.messaging_manager.last_message_check[msg_index] = current_time
            return False
        
        time_diff = current_time - last_sent
        
        # Parse schedule string to determine interval
        import re
        from datetime import timedelta
        
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
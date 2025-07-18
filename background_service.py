# FILE LOCATION: /background_service.py (root directory)
#!/usr/bin/env python3
"""
Background Service Manager for Empyrion Web Helper - DEBUG VERSION
"""

import threading
import time
import logging
from datetime import datetime
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

class BackgroundService:
    """Core background service with extensive debugging"""
    
    def __init__(self, config_manager, player_db, messaging_manager):
        self.config_manager = config_manager
        self.player_db = player_db
        self.messaging_manager = messaging_manager
        
        # Service state
        self.is_running = False
        self.is_connected = False
        self.connection_handler = None
        self.last_connection_attempt = None
        self.reconnect_attempts = 0
        
        # Background threads
        self.monitor_thread = None
        self.scheduler_thread = None
        self.stop_event = threading.Event()
        
        # Player tracking for status changes
        self.previous_players = {}
        
        # Constants
        self.MONITOR_INTERVAL = 20  # seconds - hardcoded sweet spot
        self.RECONNECT_DELAY = 30   # seconds between reconnection attempts
        self.MAX_RECONNECT_DELAY = 300  # 5 minutes max delay
        
        logger.info("🔧 DEBUG: Background service initialized")
    
    def start(self):
        """Start the background service with debugging"""
        if self.is_running:
            logger.warning("🔧 DEBUG: Background service already running")
            return
        
        logger.info("🔧 DEBUG: Setting is_running = True")
        self.is_running = True
        self.stop_event.clear()
        
        logger.info("🚀 Starting Empyrion Web Helper background service")
        
        try:
            # Start monitoring thread
            logger.info("🔧 DEBUG: Creating monitor thread")
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True, name="MonitorThread")
            self.monitor_thread.start()
            logger.info("🔧 DEBUG: Monitor thread started")
            
            # Start message scheduler thread  
            logger.info("🔧 DEBUG: Creating scheduler thread")
            self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True, name="SchedulerThread")
            self.scheduler_thread.start()
            logger.info("🔧 DEBUG: Scheduler thread started")
            
            logger.info("✅ Background service started successfully")
            
        except Exception as e:
            logger.error(f"🔧 DEBUG: Error starting threads: {e}")
            self.is_running = False
            raise
    
    def stop(self):
        """Stop the background service with debugging"""
        logger.info("🔧 DEBUG: stop() called")
        
        if not self.is_running:
            logger.info("🔧 DEBUG: Service already stopped")
            return
        
        logger.info("🛑 Stopping background service...")
        
        logger.info("🔧 DEBUG: Setting is_running = False")
        self.is_running = False
        
        logger.info("🔧 DEBUG: Setting stop_event")
        self.stop_event.set()
        
        # Disconnect from server
        logger.info("🔧 DEBUG: Calling _disconnect()")
        self._disconnect()
        
        # Wait for threads to finish
        if self.monitor_thread and self.monitor_thread.is_alive():
            logger.info("🔧 DEBUG: Waiting for monitor thread to finish")
            self.monitor_thread.join(timeout=5)
            logger.info("🔧 DEBUG: Monitor thread finished")
        
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            logger.info("🔧 DEBUG: Waiting for scheduler thread to finish")
            self.scheduler_thread.join(timeout=5)
            logger.info("🔧 DEBUG: Scheduler thread finished")
        
        logger.info("✅ Background service stopped")
    
    def get_connection_status(self) -> Dict:
        """Get current connection status for web UI"""
        return {
            'is_connected': self.is_connected,
            'last_attempt': self.last_connection_attempt,
            'reconnect_attempts': self.reconnect_attempts,
            'is_running': self.is_running
        }
    
    def get_connection_handler(self) -> Optional[object]:
        """Get the current connection handler for web UI commands"""
        return self.connection_handler if self.is_connected else None
    
    def _monitor_loop(self):
        """Main monitoring loop with extensive debugging"""
        logger.info("🔧 DEBUG: Monitor loop starting")
        
        try:
            while self.is_running and not self.stop_event.is_set():
                logger.debug("🔧 DEBUG: Monitor loop iteration starting")
                logger.debug(f"🔧 DEBUG: is_running={self.is_running}, stop_event.is_set()={self.stop_event.is_set()}")
                
                try:
                    # Ensure we're connected
                    if not self.is_connected:
                        logger.debug("🔧 DEBUG: Not connected, attempting connection")
                        self._attempt_connection()
                    
                    # If connected, monitor players
                    if self.is_connected and self.is_running:
                        logger.debug("🔧 DEBUG: Connected and running, monitoring players")
                        self._monitor_players()
                        self.reconnect_attempts = 0  # Reset on successful operation
                        logger.debug("🔧 DEBUG: Player monitoring completed successfully")
                    
                    # Wait for next cycle
                    logger.debug(f"🔧 DEBUG: Waiting {self.MONITOR_INTERVAL} seconds for next cycle")
                    wait_result = self.stop_event.wait(self.MONITOR_INTERVAL)
                    logger.debug(f"🔧 DEBUG: Wait completed, stop_event triggered: {wait_result}")
                    
                except Exception as e:
                    logger.error(f"🔧 DEBUG: Exception in monitor loop iteration: {e}")
                    import traceback
                    logger.error(f"🔧 DEBUG: Traceback: {traceback.format_exc()}")
                    
                    if self.is_running:  # Only handle error if we're still supposed to be running
                        logger.debug("🔧 DEBUG: Handling connection error")
                        self._handle_connection_error()
                        wait_result = self.stop_event.wait(5)  # Brief pause before retry
                        logger.debug(f"🔧 DEBUG: Error recovery wait completed: {wait_result}")
            
            logger.info("🔧 DEBUG: Monitor loop exiting normally")
            
        except Exception as e:
            logger.error(f"🔧 DEBUG: Fatal error in monitor loop: {e}")
            import traceback
            logger.error(f"🔧 DEBUG: Fatal traceback: {traceback.format_exc()}")
        
        logger.info("🔍 Player monitoring loop stopped")
    
    def _scheduler_loop(self):
        """Message scheduler loop with debugging"""
        logger.info("🔧 DEBUG: Scheduler loop starting")
        
        try:
            while self.is_running and not self.stop_event.is_set():
                logger.debug("🔧 DEBUG: Scheduler loop iteration")
                
                try:
                    if self.is_connected and self.messaging_manager and self.is_running:
                        logger.debug("🔧 DEBUG: Checking scheduled messages")
                        self._check_scheduled_messages()
                    
                    # Check every 30 seconds (scheduled message interval)
                    logger.debug("🔧 DEBUG: Scheduler waiting 30 seconds")
                    wait_result = self.stop_event.wait(30)
                    logger.debug(f"🔧 DEBUG: Scheduler wait completed: {wait_result}")
                    
                except Exception as e:
                    logger.error(f"🔧 DEBUG: Exception in scheduler loop: {e}")
                    if self.is_running:  # Only pause if we're still supposed to be running
                        wait_result = self.stop_event.wait(5)  # Brief pause before retry
                        logger.debug(f"🔧 DEBUG: Scheduler error recovery wait: {wait_result}")
            
            logger.info("🔧 DEBUG: Scheduler loop exiting normally")
            
        except Exception as e:
            logger.error(f"🔧 DEBUG: Fatal error in scheduler loop: {e}")
            import traceback
            logger.error(f"🔧 DEBUG: Fatal traceback: {traceback.format_exc()}")
        
        logger.info("📅 Message scheduler loop stopped")
    
    def _attempt_connection(self):
        """Attempt to connect to Empyrion server with debugging"""
        if not self.is_running:
            logger.debug("🔧 DEBUG: Not running, skipping connection attempt")
            return False
            
        try:
            self.last_connection_attempt = datetime.now().isoformat()
            
            logger.info(f"🔌 Attempting connection to {self.config_manager.get('host')}:{self.config_manager.get('telnet_port')}")
            
            # Import here to avoid circular imports
            from connection import EmpyrionConnection
            
            logger.debug("🔧 DEBUG: Creating EmpyrionConnection instance")
            # Create new connection
            self.connection_handler = EmpyrionConnection(
                self.config_manager.get('host'),
                self.config_manager.get('telnet_port'),
                self.config_manager.get('telnet_password')
            )
            
            logger.debug("🔧 DEBUG: Calling connection_handler.connect()")
            if self.connection_handler.connect():
                logger.debug("🔧 DEBUG: Connection successful, setting flags")
                self.is_connected = True
                self.reconnect_attempts = 0
                
                # Set connection handler for messaging
                if self.messaging_manager:
                    logger.debug("🔧 DEBUG: Setting connection handler for messaging")
                    self.messaging_manager.set_connection_handler(self.connection_handler)
                
                logger.info("✅ Successfully connected to Empyrion server")
                logger.debug(f"🔧 DEBUG: Connection completed, is_running={self.is_running}")
                return True
            else:
                logger.error("❌ Failed to connect to Empyrion server")
                self._handle_connection_error()
                return False
                
        except Exception as e:
            logger.error(f"❌ Connection attempt failed: {e}")
            import traceback
            logger.error(f"🔧 DEBUG: Connection traceback: {traceback.format_exc()}")
            self._handle_connection_error()
            return False
    
    def _disconnect(self):
        """Disconnect from server with debugging"""
        logger.debug("🔧 DEBUG: _disconnect() called")
        
        if self.connection_handler:
            try:
                logger.debug("🔧 DEBUG: Calling connection_handler.disconnect()")
                self.connection_handler.disconnect()
            except Exception as e:
                logger.error(f"🔧 DEBUG: Error during disconnect: {e}")
        
        self.is_connected = False
        self.connection_handler = None
        logger.info("🔌 Disconnected from server")
    
    def _handle_connection_error(self):
        """Handle connection errors with debugging"""
        logger.debug("🔧 DEBUG: _handle_connection_error() called")
        
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
        
        logger.debug("🔧 DEBUG: Connection error handled, service continues")
    
    def _monitor_players(self):
        """Monitor players with debugging"""
        if not self.is_running:
            logger.debug("🔧 DEBUG: Not running, skipping player monitoring")
            return
            
        try:
            if not self.connection_handler:
                logger.debug("🔧 DEBUG: No connection handler, skipping monitoring")
                return
            
            logger.debug("🔍 Checking player status...")
            
            # Get current players
            logger.debug("🔧 DEBUG: Calling get_players()")
            current_players = self.connection_handler.get_players()
            
            if current_players is None:
                logger.warning("⚠️ Failed to get player list from server")
                if self.is_running:  # Only handle error if service should be running
                    self._handle_connection_error()
                return
            
            logger.debug(f"📊 Retrieved {len(current_players)} players from server")
            
            # Update database
            if self.player_db and self.is_running:
                logger.debug("🔧 DEBUG: Updating player database")
                updated_count = self.player_db.update_multiple_players(current_players)
                logger.debug(f"💾 Updated {updated_count} players in database")
            
            # Detect status changes and send welcome/goodbye messages
            if self.is_running:  # Only send messages if service is running
                logger.debug("🔧 DEBUG: Detecting status changes")
                self._detect_status_changes(current_players)
                logger.debug("🔧 DEBUG: Status change detection completed")
            
        except Exception as e:
            logger.error(f"❌ Error monitoring players: {e}")
            import traceback
            logger.error(f"🔧 DEBUG: Player monitoring traceback: {traceback.format_exc()}")
            if self.is_running:  # Only handle error if service should be running
                self._handle_connection_error()
    
    def _detect_status_changes(self, current_players: List[Dict]):
        """Detect player status changes with debugging"""
        if not self.messaging_manager or not self.is_running:
            logger.debug("🔧 DEBUG: No messaging manager or not running, skipping status detection")
            return
        
        try:
            logger.debug("🔧 DEBUG: Building current players dict")
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
                            logger.debug("🔧 DEBUG: Sending welcome message")
                            self.messaging_manager.send_welcome_message(player_name)
                            logger.debug("🔧 DEBUG: Welcome message sent")
                    
                    # Player left
                    elif previous_status == 'Online' and current_status == 'Offline':
                        logger.info(f"👋 Player left: {player_name}")
                        if self.is_running:  # Only send if service is running
                            logger.debug("🔧 DEBUG: Sending goodbye message")
                            self.messaging_manager.send_goodbye_message(player_name)
                            logger.debug("🔧 DEBUG: Goodbye message sent")
                
                else:
                    # New player joining for first time
                    if current_status == 'Online':
                        logger.info(f"👋 New player joined: {player_name}")
                        if self.is_running:  # Only send if service is running
                            logger.debug("🔧 DEBUG: Sending welcome message for new player")
                            self.messaging_manager.send_welcome_message(player_name)
                            logger.debug("🔧 DEBUG: New player welcome message sent")
            
            # Update previous players for next cycle
            logger.debug("🔧 DEBUG: Updating previous players for next cycle")
            self.previous_players = current_players_dict.copy()
            
        except Exception as e:
            logger.error(f"❌ Error detecting status changes: {e}")
            import traceback
            logger.error(f"🔧 DEBUG: Status detection traceback: {traceback.format_exc()}")
    
    def _check_scheduled_messages(self):
        """Check scheduled messages with minimal debugging"""
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
            logger.error(f"❌ Error checking scheduled messages: {e}")
    
    def _should_send_scheduled_message(self, msg_index: int, schedule: str, current_time: datetime) -> bool:
        """Determine if a scheduled message should be sent"""
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
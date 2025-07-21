#!/usr/bin/env python3
"""
RCON Connection module for Empyrion Galactic Survival
Handles socket-based connection and basic player management
Phase 1: Connection + Player List Only
Compatible with Python 3.13+ (no telnetlib dependency)
"""

import socket
import time
import re
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class EmpyrionConnection:
    """
    Handles RCON connection and basic player management for Empyrion Galactic Survival servers.

    Provides methods for connecting, authenticating, sending commands, retrieving player lists, and managing player status (kick, ban, unban) via the server's RCON/telnet interface.
    """
    
    def __init__(self, host: str, port: int, password: str, timeout: int = 10):
        """
        Initialize the EmpyrionConnection.

        Args:
            host (str): Server hostname or IP address.
            port (int): RCON/telnet port number.
            password (str): RCON/telnet password.
            timeout (int, optional): Socket timeout in seconds. Defaults to 10.
        """
        self.host = host
        self.port = port
        self.password = password
        self.timeout = timeout
        self.socket = None
        self.is_connected = False
        
    def connect(self) -> bool:
        """
        Connect to the Empyrion server via RCON/telnet and authenticate.

        Returns:
            bool or dict: True if successful, False or a dict with error info if connection/authentication fails.
        """
        try:
            logger.info(f"Connecting to {self.host}:{self.port}")
            
            # Create socket connection
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout)
            
            # Connect to server
            logger.info(f"Attempting socket connection to {self.host}:{self.port}")
            self.socket.connect((self.host, self.port))
            logger.info("Socket connected successfully")
            
            # Wait for server response and read any initial data
            time.sleep(1.0)
            
            # Try to read welcome message
            try:
                welcome_data = self._receive_data(timeout=2.0)
                if welcome_data:
                    logger.info(f"Server welcome message: {welcome_data}")
            except Exception as e:
                logger.info(f"No welcome message or timeout: {e}")
            
            # Try multiple authentication methods for different hosting providers
            logger.info("Testing universal authentication methods...")
            
            auth_methods = [
                ("standard", lambda: self._auth_standard()),
                ("direct_command", lambda: self._auth_direct_command()),
                ("username_password", lambda: self._auth_username_password()),
                ("newline_only", lambda: self._auth_newline_only())
            ]
            
            for method_name, auth_func in auth_methods:
                try:
                    logger.info(f"Trying authentication method: {method_name}")
                    
                    if auth_func():
                        self.is_connected = True
                        logger.info(f"✅ Authentication successful using method: {method_name}")
                        
                        # Test connection with help command
                        logger.info("Testing connection with 'help' command")
                        test_result = self.send_command("help", timeout=5.0)
                        
                        if test_result and ("Available commands" in test_result or "help" in test_result.lower()):
                            logger.info(f"Help command successful: {test_result[:100]}...")
                        else:
                            logger.warning("Help command didn't return expected data, but auth was successful")
                        
                        return True
                    else:
                        logger.debug(f"Authentication method {method_name} failed, trying next...")
                        
                except Exception as e:
                    logger.info(f"Authentication method {method_name} errored: {e}, trying next...")
                    continue
            
            # If all methods failed
            logger.error("❌ All authentication methods failed")
            self.disconnect()
            return False
                
        except Exception as e:
            logger.error(f"Connection failed: {e}", exc_info=True)
            self.disconnect()
            return {'success': False, 'message': 'An internal error occurred. Please try again later.'}
    
    def disconnect(self):
        """
        Disconnect from the server and clean up the socket.
        """
        try:
            if self.socket:
                self.socket.close()
            self.is_connected = False
            self.socket = None
            logger.info("Disconnected from server")
        except Exception as e:
            logger.error(f"Error during disconnect: {e}", exc_info=True)
    
    def _send_raw(self, data: str):
        """
        Send raw data to the server socket.

        Args:
            data (str): Data string to send.
        """
        if self.socket:
            self.socket.send(data.encode('utf-8'))
    
    def _receive_data(self, timeout: float = 5.0) -> str:
        """
        Receive data from the server socket with a specified timeout.

        Args:
            timeout (float, optional): Timeout in seconds. Defaults to 5.0.

        Returns:
            str: Decoded response string, or empty string if no data.
        """
        if not self.socket:
            return ""
        
        try:
            # Set socket timeout for this operation
            original_timeout = self.socket.gettimeout()
            self.socket.settimeout(timeout)
            
            # Receive data in chunks
            data = b""
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                try:
                    chunk = self.socket.recv(1024)  # Smaller chunks
                    if not chunk:
                        break
                    data += chunk
                    
                    # For telnet/RCON, we often get data immediately
                    # Break after first chunk if we have data
                    if data:
                        # Wait a tiny bit to see if more data comes
                        time.sleep(0.1)
                        
                        # Try to get any remaining data
                        self.socket.settimeout(0.1)
                        try:
                            while True:
                                more_chunk = self.socket.recv(1024)
                                if not more_chunk:
                                    break
                                data += more_chunk
                        except socket.timeout:
                            pass  # No more data available
                        break
                        
                except socket.timeout:
                    if data:  # We got some data, return it
                        break
                    continue
                except Exception:
                    break
            
            # Restore original timeout
            self.socket.settimeout(original_timeout)
            
            result = data.decode('utf-8', errors='ignore').strip()
            if result:
                logger.debug(f"Received data: {result[:100]}...")
            return result
            
        except Exception as e:
            logger.error(f"Error receiving data: {e}", exc_info=True)
            return ""
    
    def send_command(self, command: str, timeout: float = 5.0) -> Optional[str]:
        """
        Send a command to the server and return the response.

        Args:
            command (str): Command string to send.
            timeout (float, optional): Timeout for response. Defaults to 5.0.

        Returns:
            Optional[str] or dict: Response string if successful, None or error dict if failed.
        """
        if not self.is_connected or not self.socket:
            logger.error("Cannot send command: not connected to server")
            return None
        
        try:
            logger.debug(f"Sending command: {command}")
            
            # Send command
            self._send_raw(f"{command}\n")
            
            # Receive response
            response = self._receive_data(timeout)
            
            if response:
                logger.debug(f"Response received: {response[:100]}...")
                return response
            else:
                logger.warning(f"No response received for command: {command}")
                return None
            
        except Exception as e:
            logger.error(f"Error sending command '{command}': {e}", exc_info=True)
            # Connection might be broken, mark as disconnected
            self.is_connected = False
            return {'success': False, 'message': 'An internal error occurred. Please try again later.'}
    
    def get_players(self) -> List[Dict]:
        """
        Get a comprehensive list of players from all sections of the 'plys' command.

        Returns:
            List[Dict] or dict: List of player dictionaries with full info, or error dict if failed.
        """
        try:
            # Use 'plys' command to get comprehensive player data
            response = self.send_command("plys")
            if not response:
                logger.warning("No response from 'plys' command")
                return []
            
            logger.debug(f"Raw plys response:\n{response}")
            
            players = []
            lines = response.split('\n')
            
            # Parse the three sections of plys output
            current_section = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Identify sections
                if "Players connected" in line:
                    current_section = "connected"
                    logger.debug("Entering connected players section")
                    continue
                elif "Global online players list" in line:
                    current_section = "online"
                    logger.debug("Entering online players section")
                    continue
                elif "Global players list" in line:
                    current_section = "global"
                    logger.debug("Entering global players section")
                    continue
                elif line.startswith('---') or line.startswith('Available commands') or 'C-Id:' in line:
                    # Skip separator lines and headers
                    continue
                
                # Parse player data based on section
                if current_section == "connected":
                    player_data = self._parse_connected_player(line)
                    if player_data:
                        logger.debug(f"Connected player: {player_data}")
                        players.append(player_data)
                
                elif current_section == "online":
                    player_data = self._parse_online_player(line)
                    if player_data:
                        logger.debug(f"Online player: {player_data}")
                        players.append(player_data)
                
                elif current_section == "global":
                    player_data = self._parse_global_player(line)
                    if player_data:
                        logger.debug(f"Global player: {player_data}")
                        players.append(player_data)
            
            # Merge player data (same player might appear in multiple sections)
            merged_players = self._merge_player_data(players)
            
            logger.info(f"Retrieved {len(merged_players)} players from plys command")
            return merged_players
            
        except Exception as e:
            logger.error(f"Error getting players: {e}", exc_info=True)
            return {'success': False, 'message': 'An internal error occurred. Please try again later.'}
    
    def _parse_connected_player(self, line: str) -> Optional[Dict]:
        """
        Parse a connected player line from the 'plys' output.

        Args:
            line (str): Line of text representing a connected player.

        Returns:
            Optional[Dict]: Player info dictionary if parsed, else None.
        """
        try:
            import re
            
            # Skip header lines
            if 'C-Id:' in line or '---' in line or not line.strip():
                return None
            
            # Match pattern: "number: steam_id, name, playfield, ip|port"
            # More flexible pattern to handle varying spaces
            pattern = r'^\s*\d+:\s*(\d+),\s*([^,]+),\s*([^,]+),\s*([^|]+)'
            match = re.match(pattern, line)
            
            if match:
                steam_id = match.group(1).strip()
                name = match.group(2).strip()
                playfield = match.group(3).strip()
                ip_address = match.group(4).strip()
                
                logger.debug(f"Parsed connected player: {name} ({steam_id}) at {playfield} from {ip_address}")
                
                return {
                    'steam_id': steam_id,
                    'name': name,
                    'status': 'Online',
                    'playfield': playfield,
                    'ip_address': ip_address,
                    'faction': '',
                    'role': '',
                    'ping': 0
                }
            else:
                logger.debug(f"Connected player line didn't match pattern: '{line}'")
                
        except Exception as e:
            logger.debug(f"Error parsing connected player line '{line}': {e}")
        
        return None
    
    def _parse_online_player(self, line: str) -> Optional[Dict]:
        """
        Parse an online player line from the 'plys' output.

        Args:
            line (str): Line of text representing an online player.

        Returns:
            Optional[Dict]: Player info dictionary if parsed, else None.
        """
        try:
            import re
            
            # Extract ID
            id_match = re.search(r'id=(\d+)', line)
            if not id_match:
                return None
            
            steam_id = id_match.group(1)
            
            # Extract name (everything between name= and fac=, handling spaces)
            name_match = re.search(r'name=([^f]+?)(?:\s+fac=)', line)
            if not name_match:
                # Fallback: name until space before fac
                name_match = re.search(r'name=([^\s]+)', line)
            name = name_match.group(1).strip() if name_match else 'Unknown'
            
            # Extract faction (between brackets)
            faction_match = re.search(r'fac=\[([^\]]+)\]', line)
            faction = faction_match.group(1) if faction_match else ''
            
            # Extract role
            role_match = re.search(r'role=(\w+)', line)
            role = role_match.group(1) if role_match else ''
            
            return {
                'steam_id': steam_id,
                'name': name,
                'status': 'Online',  # Players in online section are definitely online
                'faction': faction,
                'role': role,
                'playfield': '',
                'ip_address': '',
                'ping': 0
            }
            
        except Exception as e:
            logger.debug(f"Error parsing online player line '{line}': {e}")
        
        return None
    
    def _parse_global_player(self, line: str) -> Optional[Dict]:
        """
        Parse a global player line (includes offline players) from the 'plys' output.

        Args:
            line (str): Line of text representing a global player.

        Returns:
            Optional[Dict]: Player info dictionary if parsed, else None.
        """
        try:
            import re
            
            # Extract ID
            id_match = re.search(r'id=(\d+)', line)
            if not id_match:
                return None
            
            steam_id = id_match.group(1)
            
            # Extract name (everything between name= and fac=, handling spaces)
            name_match = re.search(r'name=([^f]+?)(?:\s+fac=)', line)
            if not name_match:
                # Fallback: name until space before fac
                name_match = re.search(r'name=([^\s]+)', line)
            name = name_match.group(1).strip() if name_match else 'Unknown'
            
            # Extract faction (between brackets)
            faction_match = re.search(r'fac=\[([^\]]+)\]', line)
            faction = faction_match.group(1) if faction_match else ''
            
            # Extract role
            role_match = re.search(r'role=(\w+)', line)
            role = role_match.group(1) if role_match else ''
            
            # Check if online (presence of online= indicates they're in global list, default to offline)
            online_match = re.search(r'online=(\d+)', line)
            total_playtime = int(online_match.group(1)) if online_match else 0
            
            return {
                'steam_id': steam_id,
                'name': name,
                'status': 'Offline',  # Global list players are offline unless also in online section
                'faction': faction,
                'role': role,
                'playfield': '',
                'ip_address': '',
                'ping': 0,
                'total_playtime': total_playtime
            }
            
        except Exception as e:
            logger.debug(f"Error parsing global player line '{line}': {e}")
        
        return None
    
    def _merge_player_data(self, players: List[Dict]) -> List[Dict]:
        """
        Merge player data from different sections, combining information.

        Priority: Connected > Online > Global for status determination.

        Args:
            players (List[Dict]): List of player dictionaries from all sections.

        Returns:
            List[Dict]: Merged and deduplicated list of player dictionaries.
        """
        merged = {}
        connected_steam_ids = set()
        online_steam_ids = set()
        
        # First pass: identify connected players (they have IP/playfield data)
        for player in players:
            steam_id = player.get('steam_id')
            if not steam_id:
                continue
                
            # Skip negative Steam IDs
            if steam_id.lstrip('-').isdigit() and int(steam_id) < 0:
                logger.debug(f"Skipping negative Steam ID: {steam_id}")
                continue
            
            # Track connected players (they have IP address or playfield)
            if player.get('ip_address') or player.get('playfield'):
                connected_steam_ids.add(steam_id)
                logger.debug(f"Player {player.get('name')} ({steam_id}) is connected")
            
            # Track players from online section
            if player.get('status') == 'Online' and not player.get('total_playtime'):
                online_steam_ids.add(steam_id)
                logger.debug(f"Player {player.get('name')} ({steam_id}) is in online list")
        
        # Second pass: merge all data
        for player in players:
            steam_id = player.get('steam_id')
            if not steam_id:
                continue
            
            # Skip negative Steam IDs
            if steam_id.lstrip('-').isdigit() and int(steam_id) < 0:
                continue
            
            if steam_id in merged:
                # Merge data, prioritizing non-empty values
                existing = merged[steam_id]
                
                # Update with non-empty values, but don't overwrite good data with empty data
                for key, value in player.items():
                    if value and (not existing.get(key) or 
                                key in ['status'] or  # Always update status 
                                (key in ['ip_address', 'playfield'] and value.strip())):  # Prioritize IP/playfield from connected section
                        existing[key] = value
                        
            else:
                merged[steam_id] = player.copy()
        
        # Third pass: determine final online status based on sections
        for steam_id, player in merged.items():
            if steam_id in connected_steam_ids:
                player['status'] = 'Online'
                logger.debug(f"Setting {player['name']} to Online (connected)")
            elif steam_id in online_steam_ids:
                player['status'] = 'Online'
                logger.debug(f"Setting {player['name']} to Online (online list)")
            else:
                player['status'] = 'Offline'
                logger.debug(f"Setting {player['name']} to Offline")
        
        result = list(merged.values())
        
        # Sort by status (Online first), then by name
        result.sort(key=lambda p: (p['status'] != 'Online', p['name'].lower()))
        
        online_count = len([p for p in result if p['status'] == 'Online'])
        offline_count = len([p for p in result if p['status'] == 'Offline'])
        logger.info(f"Final result: {online_count} online, {offline_count} offline players")
        
        return result
    
    def is_connection_alive(self) -> bool:
        """
        Check if the connection is still alive and responsive.

        Returns:
            bool: True if connected and responsive, False otherwise.
        """
        if not self.is_connected or not self.socket:
            return False
        
        try:
            # Send a simple command to test connection
            response = self.send_command("help", timeout=3.0)
            return response is not None
        except Exception as e:
            logger.error(f"Error checking connection: {e}", exc_info=True)
            self.is_connected = False
            return False
    
    def kick_player(self, player_name: str, message: str = "Kicked by Admin") -> bool:
        """
        Kick a player by name with a custom message.

        Args:
            player_name (str): Name of the player to kick.
            message (str, optional): Kick message. Defaults to "Kicked by Admin".

        Returns:
            bool: True if command succeeded, False otherwise.
        """
        try:
            # Escape single quotes in message and wrap in single quotes
            escaped_message = message.replace("'", "\\'")
            command = f"kick '{player_name}' '{escaped_message}'"
            
            response = self.send_command(command)
            if response:
                logger.info(f"Kicked player {player_name} with message: {message}")
                return True
            else:
                logger.warning(f"Kick command failed for player {player_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error kicking player {player_name}: {e}")
            return False
    
    def ban_player(self, steam_id: str, duration: str = "1d") -> bool:
        """
        Ban a player by Steam ID for a specified duration.

        Args:
            steam_id (str): Steam ID of the player to ban.
            duration (str, optional): Ban duration (e.g., '1d'). Defaults to '1d'.

        Returns:
            bool: True if command succeeded, False otherwise.
        """
        try:
            command = f"ban {steam_id} {duration}"
            response = self.send_command(command)
            
            if response:
                logger.info(f"Banned player {steam_id} for {duration}")
                return True
            else:
                logger.warning(f"Ban command failed for player {steam_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error banning player {steam_id}: {e}", exc_info=True)
            return False
    
    def unban_player(self, steam_id: str) -> bool:
        """
        Unban a player by Steam ID.

        Args:
            steam_id (str): Steam ID of the player to unban.

        Returns:
            bool: True if command succeeded, False otherwise.
        """
        try:
            command = f"unban {steam_id}"
            response = self.send_command(command)
            
            if response:
                logger.info(f"Unbanned player {steam_id}")
                return True
            else:
                logger.warning(f"Unban command failed for player {steam_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error unbanning player {steam_id}: {e}", exc_info=True)
            return False
    
    def _auth_standard(self) -> bool:
        """Standard authentication: password with \\r\\n (works with most providers)"""
        try:
            self._send_raw(f"{self.password}\r\n")
            time.sleep(1.0)
            
            auth_response = self._receive_data(timeout=3.0)
            if auth_response and "Logged in successfully" in auth_response:
                logger.debug("Standard auth successful")
                return True
            return False
        except Exception as e:
            logger.debug(f"Standard auth failed: {e}")
            return False
    
    def _auth_direct_command(self) -> bool:
        """Test if server allows direct commands without authentication"""
        try:
            # Some servers don't require authentication - try direct command
            self._send_raw("help\n")
            time.sleep(1.0)
            
            test_response = self._receive_data(timeout=3.0)
            if test_response and ("Available commands" in test_response or "help" in test_response.lower()):
                logger.debug("Direct command auth successful - no password needed")
                return True
            return False
        except Exception as e:
            logger.debug(f"Direct command auth failed: {e}")
            return False
    
    def _auth_username_password(self) -> bool:
        """Try username + password authentication (some providers require both)"""
        try:
            # Try with admin/rcon as username
            for username in ["admin", "rcon", "server"]:
                self._send_raw(f"{username}\r\n")
                time.sleep(0.5)
                self._send_raw(f"{self.password}\r\n")
                time.sleep(1.0)
                
                auth_response = self._receive_data(timeout=3.0)
                if auth_response and "Logged in successfully" in auth_response:
                    logger.debug(f"Username + password auth successful with username: {username}")
                    return True
            return False
        except Exception as e:
            logger.debug(f"Username + password auth failed: {e}")
            return False
    
    def _auth_newline_only(self) -> bool:
        """Try password with only \\n (some providers are picky about line endings)"""
        try:
            self._send_raw(f"{self.password}\n")
            time.sleep(1.0)
            
            auth_response = self._receive_data(timeout=3.0)
            if auth_response and "Logged in successfully" in auth_response:
                logger.debug("Newline-only auth successful")
                return True
            return False
        except Exception as e:
            logger.debug(f"Newline-only auth failed: {e}")
            return False

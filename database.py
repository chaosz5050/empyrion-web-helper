# FILE LOCATION: /database.py (root directory)
#!/usr/bin/env python3
"""
Database manager for Empyrion Web Helper
Enhanced with secure credentials storage and IP geolocation
"""

import sqlite3
import logging
import os
import base64
import getpass
import requests
import time
import threading
import shutil
from datetime import datetime
from typing import List, Dict, Optional, Union

# Import cryptography only if available
try:
    from cryptography.fernet import Fernet
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

logger = logging.getLogger(__name__)

class PlayerDatabase:
    """
    Manages the SQLite database for Empyrion Web Helper, including player tracking, secure credential storage, and geolocation data.

    Provides methods for initializing the database, storing and retrieving encrypted credentials, updating player status, and managing geolocation data for player IP addresses.
    """
    
    def __init__(self, db_path: str = "instance/players.db"):
        """
        Initialize the PlayerDatabase.

        Args:
            db_path (str, optional): Path to the SQLite database file. Defaults to 'instance/players.db'.
        """
        self.db_path = db_path
        self.encryption_key = None
        self.geolocation_cache = {}  # Simple in-memory cache for geolocation
        self.last_geo_request = 0  # Rate limiting for API calls
        self.geo_lock = threading.Lock() # Lock for geolocation cache and API calls
        self.ensure_directory_exists()
        self.init_database()
        if CRYPTO_AVAILABLE:
            self._init_encryption()
        else:
            logger.warning("Cryptography not installed - install with: pip install cryptography")
    
    def ensure_directory_exists(self):
        """
        Ensure the database directory exists, creating it if necessary.
        """
        directory = os.path.dirname(self.db_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
    
    def _init_encryption(self):
        """Initialize encryption for credentials"""
        if not CRYPTO_AVAILABLE:
            return
            
        key_file = 'instance/.db_key'
        
        try:
            if os.path.exists(key_file):
                with open(key_file, 'rb') as f:
                    self.encryption_key = f.read()
            else:
                # Generate new key
                self.encryption_key = Fernet.generate_key()
                with open(key_file, 'wb') as f:
                    f.write(self.encryption_key)
                # Set secure permissions (owner read/write only)
                os.chmod(key_file, 0o600)
                logger.info("Created new encryption key for credentials storage")
                
        except Exception as e:
            logger.error(f"Error initializing encryption: {e}")
            self.encryption_key = None
    
    def _encrypt_credential(self, credential: str) -> str:
        """Encrypt a credential for database storage"""
        if not CRYPTO_AVAILABLE or not self.encryption_key or not credential:
            return credential
            
        try:
            f = Fernet(self.encryption_key)
            encrypted = f.encrypt(credential.encode('utf-8'))
            return base64.b64encode(encrypted).decode('utf-8')
            
        except Exception as e:
            logger.error(f"Error encrypting credential: {e}")
            return credential  # Fallback to plaintext
    
    def _decrypt_credential(self, encrypted_credential: str) -> str:
        """Decrypt a credential from database storage"""
        if not CRYPTO_AVAILABLE or not self.encryption_key or not encrypted_credential:
            return encrypted_credential
            
        try:
            encrypted_data = base64.b64decode(encrypted_credential)
            f = Fernet(self.encryption_key)
            decrypted = f.decrypt(encrypted_data)
            return decrypted.decode('utf-8')
            
        except Exception as e:
            logger.error(f"Error decrypting credential: {e}")
            return encrypted_credential  # Return as-is if can't decrypt
    
    def init_database(self):
        """
        Initialize the database tables for players, credentials, and player sessions, including geolocation support.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create players table with country column
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS players (
                        steam_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        status TEXT DEFAULT 'Offline',
                        faction TEXT DEFAULT '',
                        role TEXT DEFAULT '',
                        ip_address TEXT DEFAULT '',
                        country TEXT DEFAULT NULL,
                        playfield TEXT DEFAULT '',
                        last_seen TEXT,
                        first_seen TEXT NOT NULL,
                        total_playtime INTEGER DEFAULT 0,
                        updated_at TEXT NOT NULL
                    )
                """)
                
                # Check if country column exists, add it if missing (migration)
                cursor.execute("PRAGMA table_info(players)")
                columns = [column[1] for column in cursor.fetchall()]
                if 'country' not in columns:
                    logger.info("Adding country column to players table")
                    cursor.execute("ALTER TABLE players ADD COLUMN country TEXT DEFAULT NULL")
                    logger.info("Country column added successfully")
                
                # Create credentials table for secure storage
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS credentials (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        credential_type TEXT NOT NULL UNIQUE,
                        username TEXT,
                        password TEXT,
                        host TEXT,
                        port INTEGER,
                        additional_data TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                """)
                
                # Create player sessions table for detailed tracking
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS player_sessions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        steam_id TEXT NOT NULL,
                        session_start TEXT NOT NULL,
                        session_end TEXT,
                        ip_address TEXT,
                        playfield TEXT,
                        FOREIGN KEY (steam_id) REFERENCES players (steam_id)
                    )
                """)
                
                # Create app_settings table for general application settings
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS app_settings (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                """)
                
                # Create entities table for game entity storage
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS entities (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        type TEXT NOT NULL,
                        faction TEXT,
                        playfield TEXT,
                        time_info TEXT,
                        last_seen TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    )
                """)
                
                # Create entities_meta table for last refresh tracking
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS entities_meta (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                """)
                
                # Set secure permissions on database file
                try:
                    os.chmod(self.db_path, 0o600)
                except Exception as e:
                    logger.warning(f"Could not set secure permissions on database: {e}")
                    return {'success': False, 'message': 'An internal error occurred. Please try again later.'}
                
                conn.commit()
                logger.info("Database initialized successfully with credentials and geolocation support")
                
        except Exception as e:
            logger.error(f"Error initializing database: {e}", exc_info=True)
            return {'success': False, 'message': 'An internal error occurred. Please try again later.'}
    
    # ============================================================================
    # GEOLOCATION METHODS
    # ============================================================================
    
    def _lookup_country(self, ip_address: str) -> str:
        """
        Lookup country for IP address using ip-api.com
        Returns country name or appropriate error message
        """
        if not ip_address or ip_address.strip() == '':
            return "Unknown location"
        
        with self.geo_lock:
            # Check cache first
            if ip_address in self.geolocation_cache:
                logger.debug(f"Using cached geolocation for {ip_address}: {self.geolocation_cache[ip_address]}")
                return self.geolocation_cache[ip_address]
            
            # Rate limiting - wait at least 1 second between requests
            current_time = time.time()
            if current_time - self.last_geo_request < 1.0:
                time.sleep(1.0 - (current_time - self.last_geo_request))
            
            try:
                logger.debug(f"Looking up geolocation for IP: {ip_address}")
                
                # Make request to ip-api.com
                url = f"http://ip-api.com/json/{ip_address}"
                response = requests.get(url, timeout=10)
                self.last_geo_request = time.time()
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get('status') == 'success':
                        country = data.get('country', 'Unknown location')
                        logger.info(f"Geolocation lookup successful: {ip_address} -> {country}")
                        
                        # Cache the result
                        self.geolocation_cache[ip_address] = country
                        return country
                        
                    elif data.get('status') == 'fail':
                        error_msg = data.get('message', 'Unknown error')
                        logger.warning(f"Geolocation lookup failed for {ip_address}: {error_msg}")
                        
                        if 'private range' in error_msg.lower() or 'reserved range' in error_msg.lower():
                            result = "Local network"
                        elif 'invalid' in error_msg.lower():
                            result = "Unknown location"
                        else:
                            result = "Unknown location"
                        
                        # Cache failed lookups to avoid repeated attempts
                        self.geolocation_cache[ip_address] = result
                        return result
                        
                    else:
                        logger.warning(f"Unexpected geolocation response for {ip_address}: {data}")
                        return "Unknown location"
                        
                elif response.status_code == 429:
                    logger.warning(f"Geolocation API rate limited for {ip_address}")
                    return "Unknown location"  # Don't cache rate limits
                    
                else:
                    logger.warning(f"Geolocation API returned status {response.status_code} for {ip_address}")
                    return "Service down"
                    
            except requests.exceptions.ConnectException:
                logger.warning(f"No internet connection for geolocation lookup of {ip_address}")
                return "No Internet"
                
            except requests.exceptions.Timeout:
                logger.warning(f"Geolocation lookup timed out for {ip_address}")
                return "Service down"
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"Geolocation lookup failed for {ip_address}: {e}")
                return "Service down"
                
            except Exception as e:
                logger.error(f"Unexpected error in geolocation lookup for {ip_address}: {e}")
                return "Unknown location"
    
    def _should_update_geolocation(self, player_data: Dict, existing_player: Optional[Dict]) -> bool:
        """
        Determine if we should update the geolocation for this player
        Only lookup when:
        1. Player has no country stored (NULL)
        2. IP address changed from what's in database
        3. Current country is an error state (retry failed lookups occasionally)
        """
        current_ip = player_data.get('ip_address', '').strip()
        
        if not current_ip:
            return False  # No IP, can't lookup
        
        if not existing_player:
            return True  # New player with IP
        
        existing_ip = existing_player.get('ip_address', '').strip()
        existing_country = existing_player.get('country')
        
        # IP address changed
        if current_ip != existing_ip:
            logger.debug(f"IP changed for {player_data.get('name')}: {existing_ip} -> {current_ip}")
            return True
        
        # No country stored
        if not existing_country:
            return True
        
        # Retry error states occasionally (every 10th update to avoid spam)
        error_states = ["Unknown location", "Service down", "No Internet"]
        if existing_country in error_states:
            # Simple retry mechanism - only retry occasionally
            import random
            if random.randint(1, 10) == 1:  # 10% chance to retry
                logger.debug(f"Retrying geolocation for {player_data.get('name')} (was: {existing_country})")
                return True
        
        return False
    
    # ============================================================================
    # CREDENTIAL MANAGEMENT METHODS
    # ============================================================================
    
    def store_credential(self, credential_type: str, username: str = '', password: str = '', 
                        host: str = '', port: int = 0, additional_data: str = '') -> bool:
        """
        Store encrypted credentials in the database.
        """
        try:
            current_time = datetime.now().isoformat()
            
            encrypted_password = self._encrypt_credential(password) if password else ''
            encrypted_username = self._encrypt_credential(username) if username else ''
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO credentials 
                    (credential_type, username, password, host, port, additional_data, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, 
                            COALESCE((SELECT created_at FROM credentials WHERE credential_type = ?), ?), 
                            ?)
                """, (credential_type, encrypted_username, encrypted_password, host, port, 
                     additional_data, credential_type, current_time, current_time))
                
                conn.commit()
                logger.info(f"Stored {credential_type} credentials securely")
                return True
                
        except Exception as e:
            logger.error(f"Error storing {credential_type} credentials: {e}", exc_info=True)
            return False
    
    def get_credential(self, credential_type: str) -> Optional[Dict]:
        """
        Retrieve and decrypt credentials from the database.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT username, password, host, port, additional_data 
                    FROM credentials 
                    WHERE credential_type = ?
                """, (credential_type,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                username = self._decrypt_credential(row[0]) if row[0] else ''
                password = self._decrypt_credential(row[1]) if row[1] else ''
                
                return {
                    'username': username,
                    'password': password,
                    'host': row[2] or '',
                    'port': row[3] or 0,
                    'additional_data': row[4] or ''
                }
                
        except Exception as e:
            logger.error(f"Error retrieving {credential_type} credentials: {e}", exc_info=True)
            return None
    
    def delete_credential(self, credential_type: str) -> bool:
        """
        Delete credentials from the database.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM credentials WHERE credential_type = ?", (credential_type,))
                conn.commit()
                
                if cursor.rowcount > 0:
                    logger.info(f"Deleted {credential_type} credentials")
                    return True
                else:
                    logger.warning(f"No {credential_type} credentials found to delete")
                    return False
                    
        except Exception as e:
            logger.error(f"Error deleting {credential_type} credentials: {e}", exc_info=True)
            return False
    
    def list_stored_credentials(self) -> List[str]:
        """
        Get a list of all stored credential types in the database.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT credential_type FROM credentials")
                return [row[0] for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Error listing credentials: {e}", exc_info=True)
            return []
    
    def get_rcon_credentials(self) -> Optional[Dict]:
        """
        Retrieve RCON credentials from the database or environment variables.
        This method does not prompt the user.
        """
        env_password = os.environ.get('EMPYRION_RCON_PASSWORD')
        if env_password:
            logger.info("Using RCON password from environment variable")
            return {'username': '', 'password': env_password, 'host': '', 'port': 0, 'additional_data': ''}
        return self.get_credential('rcon')
    
    def get_ftp_credentials(self) -> Optional[Dict]:
        """
        Retrieve FTP credentials from the database or environment variables.
        This method does not prompt the user.
        """
        env_user = os.environ.get('EMPYRION_FTP_USER')
        env_password = os.environ.get('EMPYRION_FTP_PASSWORD')
        env_host = os.environ.get('EMPYRION_FTP_HOST')
        
        if env_password:
            logger.info("Using FTP credentials from environment variables")
            return {'username': env_user or '', 'password': env_password, 'host': env_host or '', 'port': 21, 'additional_data': ''}
        return self.get_credential('ftp')
    
    # ============================================================================
    # PLAYER MANAGEMENT METHODS
    # ============================================================================
    
    def update_player(self, player_data: Dict) -> bool:
        """
        Update or insert player data, handling status changes and geolocation lookup.
        """
        try:
            steam_id = str(player_data.get('steam_id', ''))
            if not steam_id or steam_id == '-1' or (steam_id.lstrip('-').isdigit() and int(steam_id) < 0):
                logger.warning(f"Skipping player with invalid Steam ID: {steam_id}")
                return False
            
            current_time = datetime.now().isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("SELECT steam_id, first_seen, ip_address, playfield, status, last_seen, country FROM players WHERE steam_id = ?", (steam_id,))
                existing = cursor.fetchone()
                
                existing_player = {
                    'steam_id': existing[0], 'first_seen': existing[1], 'ip_address': existing[2],
                    'playfield': existing[3], 'status': existing[4], 'last_seen': existing[5], 'country': existing[6]
                } if existing else None
                
                country = existing_player.get('country') if existing_player else None
                if self._should_update_geolocation(player_data, existing_player):
                    current_ip = player_data.get('ip_address', '').strip()
                    country = self._lookup_country(current_ip) if current_ip else "Unknown location"
                
                if existing_player:
                    # Player exists - update their information
                    new_status = player_data.get('status', 'Offline')
                    old_status = existing_player.get('status', 'Offline')
                    
                    # Update player information including last_seen for online players
                    update_last_seen = current_time if new_status == 'Online' else existing_player.get('last_seen')
                    
                    cursor.execute("""
                        UPDATE players 
                        SET name = ?, status = ?, faction = ?, role = ?, ip_address = ?, 
                            country = ?, playfield = ?, last_seen = ?, updated_at = ?
                        WHERE steam_id = ?
                    """, (
                        player_data.get('name', ''), new_status, player_data.get('faction', ''),
                        player_data.get('role', ''), player_data.get('ip_address', ''),
                        country, player_data.get('playfield', ''), update_last_seen, current_time, steam_id
                    ))
                    
                else:
                    # New player
                    # Set last_seen for new players if they're online
                    new_status = player_data.get('status', 'Offline')
                    initial_last_seen = current_time if new_status == 'Online' else None
                    
                    cursor.execute("""
                        INSERT INTO players (steam_id, name, status, faction, role, ip_address, country, playfield, last_seen, first_seen, updated_at) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        steam_id, player_data.get('name', ''), new_status,
                        player_data.get('faction', ''), player_data.get('role', ''), player_data.get('ip_address', ''),
                        country, player_data.get('playfield', ''), initial_last_seen, current_time, current_time
                    ))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error updating player {player_data.get('name', 'Unknown')}: {e}", exc_info=True)
            return False
    
    def update_multiple_players(self, players_data: List[Dict]) -> int:
        """
        Update multiple players at once.
        """
        updated_count = 0
        for player_data in players_data:
            if self.update_player(player_data):
                updated_count += 1
        
        self.mark_remaining_offline([p for p in players_data if p.get('steam_id')])
        self.cleanup_negative_steam_ids()
        
        logger.info(f"Updated {updated_count} players in database")
        return updated_count
    
    def mark_remaining_offline(self, current_players: List[Dict]):
        """
        Mark players as offline who did not appear in the current 'plys' data.
        """
        try:
            current_time = datetime.now().isoformat()
            current_steam_ids = {str(p.get('steam_id', '')) for p in current_players}
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("SELECT steam_id, name FROM players WHERE status = 'Online'")
                online_players = cursor.fetchall()
                
                for steam_id, name in online_players:
                    if steam_id not in current_steam_ids:
                        cursor.execute("UPDATE players SET status = 'Offline', last_seen = ?, updated_at = ? WHERE steam_id = ?", (current_time, current_time, steam_id))
                        logger.info(f"PLAYER LOGOUT (not in plys): {name} - Setting last_seen: {current_time}")
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error marking remaining players offline: {e}", exc_info=True)

    def cleanup_negative_steam_ids(self):
        """
        Remove entries with negative Steam IDs if a positive Steam ID exists for the same player name.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT n.steam_id, n.name FROM players n
                    WHERE CAST(n.steam_id AS INTEGER) < 0 AND EXISTS (
                        SELECT 1 FROM players p WHERE p.name = n.name AND CAST(p.steam_id AS INTEGER) > 0
                    )
                """)
                negative_entries = cursor.fetchall()
                
                for steam_id, name in negative_entries:
                    cursor.execute("DELETE FROM players WHERE steam_id = ?", (steam_id,))
                    logger.info(f"Removed duplicate negative Steam ID {steam_id} for player {name}")
                
                if negative_entries:
                    conn.commit()
        except Exception as e:
            logger.error(f"Error cleaning up negative Steam IDs: {e}", exc_info=True)

    def get_all_players(self, filters: Optional[Dict] = None) -> List[Dict]:
        """
        Get all players from the database, with optional filters.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                query = "SELECT * FROM players"
                params = []
                
                if filters:
                    conditions = []
                    allowed_columns = {'steam_id', 'name', 'status', 'faction', 'ip_address', 'country', 'playfield'}
                    for key, value in filters.items():
                        if key in allowed_columns:
                            conditions.append(f"{key} LIKE ?")
                            params.append(f"%{value}%")
                    if conditions:
                        query += " WHERE " + " AND ".join(conditions)
                
                query += " ORDER BY CASE WHEN status = 'Online' THEN 0 ELSE 1 END, last_seen DESC"
                
                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Error getting players from database: {e}", exc_info=True)
            return []

    def get_player_count(self) -> Dict[str, int]:
        """
        Get player statistics including online/offline counts.
        
        Returns:
            Dict containing player count statistics
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Count online players
                cursor.execute("SELECT COUNT(*) FROM players WHERE status = 'Online'")
                online_count = cursor.fetchone()[0]
                
                # Count offline players  
                cursor.execute("SELECT COUNT(*) FROM players WHERE status != 'Online'")
                offline_count = cursor.fetchone()[0]
                
                # Total count
                total_count = online_count + offline_count
                
                return {
                    'online': online_count,
                    'offline': offline_count, 
                    'total': total_count
                }
                
        except Exception as e:
            logger.error(f"Error getting player count: {e}", exc_info=True)
            return {'online': 0, 'offline': 0, 'total': 0}

    # ============================================================================
    # APP SETTINGS METHODS
    # ============================================================================

    def set_app_setting(self, key: str, value: str) -> bool:
        """
        Store or update an application setting in the app_settings table.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                now = datetime.now().isoformat()
                cursor.execute("""
                    INSERT INTO app_settings (key, value, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
                """, (key, value, now))
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error setting app setting {key}: {e}")
            return False

    def get_app_setting(self, key: str, default=None):
        """
        Retrieve an application setting from the app_settings table.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
                row = cursor.fetchone()
                if row:
                    return row[0]
        except Exception as e:
            logger.error(f"Error retrieving app setting {key}: {e}")
        return default

    def get_setting(self, key: str, default=None):
        """
        Generic method to get a setting from the app_settings table.
        """
        return self.get_app_setting(key, default)

    # ============================================================================
    # HIGH-VALUE & DATA INTEGRITY METHODS
    # ============================================================================

    def backup_database(self, backup_dir: str = 'instance/backups') -> Optional[str]:
        """
        Create a backup of the database file.
        """
        try:
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
            
            backup_filename = f"players_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            backup_path = os.path.join(backup_dir, backup_filename)
            
            shutil.copy2(self.db_path, backup_path)
            
            logger.info(f"Database backed up to {backup_path}")
            return backup_path
            
        except Exception as e:
            logger.error(f"Error backing up database: {e}")
            return None

    def restore_database(self, backup_path: str) -> bool:
        """
        Restore the database from a backup file.
        """
        try:
            if not os.path.exists(backup_path):
                logger.error(f"Backup file not found: {backup_path}")
                return False
            
            shutil.copy2(backup_path, self.db_path)
            
            logger.info(f"Database restored from {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error restoring database: {e}")
            return False

    def get_players_with_duplicate_names(self) -> Dict:
        """
        Get players with duplicate names.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name, COUNT(*) FROM players GROUP BY name HAVING COUNT(*) > 1")
                return {'success': True, 'duplicates': dict(cursor.fetchall())}
        except Exception as e:
            logger.error(f"Error getting players with duplicate names: {e}")
            return {'success': False, 'message': 'Error getting players with duplicate names'}

    def get_players_with_duplicate_ips(self) -> Dict:
        """
        Get players with duplicate IP addresses.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT ip_address, COUNT(*) FROM players WHERE ip_address IS NOT NULL AND ip_address != '' GROUP BY ip_address HAVING COUNT(*) > 1")
                return {'success': True, 'duplicates': dict(cursor.fetchall())}
        except Exception as e:
            logger.error(f"Error getting players with duplicate IPs: {e}")
            return {'success': False, 'message': 'Error getting players with duplicate IPs'}

    def get_entities_with_invalid_ids(self) -> List[Dict]:
        """
        Get entities with invalid IDs (e.g., not a number).
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM entities")
                
                invalid_entities = []
                for row in cursor.fetchall():
                    try:
                        int(row['id'])
                    except (ValueError, TypeError):
                        invalid_entities.append(dict(row))
                return invalid_entities
                
        except Exception as e:
            logger.error(f"Error getting entities with invalid IDs: {e}")
            return []
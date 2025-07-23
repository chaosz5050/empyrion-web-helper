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

        Args:
            credential_type (str): Type of credential (e.g., 'rcon', 'ftp').
            username (str, optional): Username for the credential. Defaults to ''.
            password (str, optional): Password for the credential. Defaults to ''.
            host (str, optional): Host for the credential. Defaults to ''.
            port (int, optional): Port for the credential. Defaults to 0.
            additional_data (str, optional): Any additional data. Defaults to ''.

        Returns:
            bool or dict: True if stored successfully, or error dict if failed.
        """
        try:
            current_time = datetime.now().isoformat()
            
            # Encrypt sensitive data
            encrypted_password = self._encrypt_credential(password) if password else ''
            encrypted_username = self._encrypt_credential(username) if username else ''
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Insert or update credential
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
            return {'success': False, 'message': 'An internal error occurred. Please try again later.'}
    
    def get_credential(self, credential_type: str) -> Optional[Dict]:
        """
        Retrieve and decrypt credentials from the database.

        Args:
            credential_type (str): Type of credential to retrieve.

        Returns:
            Optional[Dict] or dict: Credential dictionary if found, None or error dict otherwise.
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
                
                # Decrypt sensitive data
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
            return {'success': False, 'message': 'An internal error occurred. Please try again later.'}
    
    def delete_credential(self, credential_type: str) -> bool:
        """
        Delete credentials from the database.

        Args:
            credential_type (str): Type of credential to delete.

        Returns:
            bool or dict: True if deleted, False if not found, or error dict if failed.
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
            return {'success': False, 'message': 'An internal error occurred. Please try again later.'}
    
    def list_stored_credentials(self) -> List[str]:
        """
        Get a list of all stored credential types in the database.

        Returns:
            List[str] or dict: List of credential types, or error dict if failed.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT credential_type FROM credentials")
                return [row[0] for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Error listing credentials: {e}", exc_info=True)
            return {'success': False, 'message': 'An internal error occurred. Please try again later.'}
    
    def prompt_for_credentials(self, credential_type: str, description: str, 
                             include_host: bool = True, include_username: bool = True) -> Optional[Dict]:
        """
        Interactively prompt the user for credentials if running in a terminal.

        Args:
            credential_type (str): Type of credential (e.g., 'rcon', 'ftp').
            description (str): Description for the prompt.
            include_host (bool, optional): Whether to prompt for host. Defaults to True.
            include_username (bool, optional): Whether to prompt for username. Defaults to True.

        Returns:
            Optional[Dict] or dict: Credential dictionary if entered, None or error dict otherwise.
        """
        if not os.isatty(0):  # Not running in terminal
            logger.warning(f"Cannot prompt for {credential_type} credentials (not in terminal)")
            return None
        
        try:
            print(f"\n🔐 {description} Setup Required")
            print(f"💡 Credentials will be stored encrypted in the database")
            
            credentials = {}
            
            if include_host:
                host = input("Host/Server Address: ").strip()
                if not host:
                    print("❌ Host is required")
                    return None
                credentials['host'] = host
                
                port_str = input("Port (press Enter for default): ").strip()
                if port_str:
                    try:
                        credentials['port'] = int(port_str)
                    except ValueError:
                        print("❌ Invalid port number")
                        return None
                else:
                    credentials['port'] = 0
            
            if include_username:
                username = input("Username (optional): ").strip()
                credentials['username'] = username
            
            password = getpass.getpass("Password: ")
            if not password:
                print("❌ Password is required")
                return None
            credentials['password'] = password
            
            # Confirm save
            save = input(f"Save {credential_type} credentials to database? (Y/n): ").lower().strip()
            if save in ('', 'y', 'yes'):
                if self.store_credential(
                    credential_type=credential_type,
                    username=credentials.get('username', ''),
                    password=credentials['password'],
                    host=credentials.get('host', ''),
                    port=credentials.get('port', 0)
                ):
                    print(f"✅ {credential_type.upper()} credentials saved securely")
                    return credentials
                else:
                    print(f"❌ Failed to save {credential_type} credentials")
                    return None
            else:
                print("⚠️ Credentials not saved (will be prompted again next time)")
                return credentials
                
        except (KeyboardInterrupt, EOFError):
            print(f"\n⚠️ {credential_type.upper()} credential setup cancelled")
            return None
        except Exception as e:
            logger.error(f"Error prompting for {credential_type} credentials: {e}")
            return {'success': False, 'message': 'An internal error occurred. Please try again later.'}
    
    def get_rcon_credentials(self) -> Optional[Dict]:
        """
        Retrieve RCON credentials, prompting the user if not already stored.

        Returns:
            Optional[Dict]: Credential dictionary if found or entered, None otherwise.
        """
        # Try environment variable first
        env_password = os.environ.get('EMPYRION_RCON_PASSWORD')
        if env_password:
            logger.info("Using RCON password from environment variable")
            return {
                'username': '',
                'password': env_password,
                'host': '',
                'port': 0,
                'additional_data': ''
            }
        
        # Try database
        stored = self.get_credential('rcon')
        if stored and stored['password']:
            logger.info("Using RCON credentials from database")
            return stored
        
        # Prompt for credentials
        logger.info("No RCON credentials found, prompting user")
        return self.prompt_for_credentials(
            'rcon', 
            'RCON Server Connection',
            include_host=False,  # Host comes from config
            include_username=False  # RCON typically doesn't use username
        )
    
    def get_ftp_credentials(self) -> Optional[Dict]:
        """
        Retrieve FTP credentials, prompting the user if not already stored.

        Returns:
            Optional[Dict]: Credential dictionary if found or entered, None otherwise.
        """
        # Try environment variables first
        env_user = os.environ.get('EMPYRION_FTP_USER')
        env_password = os.environ.get('EMPYRION_FTP_PASSWORD')
        env_host = os.environ.get('EMPYRION_FTP_HOST')
        
        if env_password:
            logger.info("Using FTP credentials from environment variables")
            return {
                'username': env_user or '',
                'password': env_password,
                'host': env_host or '',
                'port': 21,
                'additional_data': ''
            }
        
        # Try database
        stored = self.get_credential('ftp')
        if stored and stored['password']:
            logger.info("Using FTP credentials from database")
            return stored
        
        # Prompt for credentials
        logger.info("No FTP credentials found, prompting user")
        return self.prompt_for_credentials(
            'ftp',
            'FTP Server Access',
            include_host=True,
            include_username=True
        )
    
    # ============================================================================
    # ENHANCED PLAYER MANAGEMENT METHODS WITH GEOLOCATION
    # ============================================================================
    
    def update_player(self, player_data: Dict) -> bool:
        """
        Update or insert player data, handling status changes and geolocation lookup.

        Args:
            player_data (Dict): Dictionary of player data to update or insert.

        Returns:
            bool or dict: True if updated/inserted, or error dict if failed.
        """
        try:
            # Validate Steam ID (no negative IDs)
            steam_id = str(player_data.get('steam_id', ''))
            if not steam_id or steam_id == '-1' or (steam_id.lstrip('-').isdigit() and int(steam_id) < 0):
                logger.warning(f"Skipping player with invalid Steam ID: {steam_id}")
                return False
            
            current_time = datetime.now().isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if player exists and get current data
                cursor.execute("""
                    SELECT steam_id, first_seen, ip_address, playfield, status, last_seen, country 
                    FROM players WHERE steam_id = ?
                """, (steam_id,))
                existing = cursor.fetchone()
                
                existing_player = None
                if existing:
                    existing_player = {
                        'steam_id': existing[0],
                        'first_seen': existing[1],
                        'ip_address': existing[2],
                        'playfield': existing[3],
                        'status': existing[4],
                        'last_seen': existing[5],
                        'country': existing[6]
                    }
                
                # Determine if we need to lookup geolocation
                should_lookup_geo = self._should_update_geolocation(player_data, existing_player)
                country = existing_player.get('country') if existing_player else None
                
                if should_lookup_geo:
                    current_ip = player_data.get('ip_address', '').strip()
                    if current_ip:
                        logger.debug(f"Performing geolocation lookup for {player_data.get('name')} ({current_ip})")
                        country = self._lookup_country(current_ip)
                    else:
                        country = "Unknown location"
                
                if existing_player:
                    # Player exists - handle status changes
                    existing_ip = existing_player['ip_address'] if existing_player['ip_address'] else ''
                    existing_playfield = existing_player['playfield'] if existing_player['playfield'] else ''
                    old_status = existing_player['status'] if existing_player['status'] else 'Offline'
                    existing_last_seen = existing_player['last_seen'] if existing_player['last_seen'] else None
                    
                    new_status = player_data.get('status', 'Offline')
                    new_ip = player_data.get('ip_address', '')
                    new_playfield = player_data.get('playfield', '')
                    
                    logger.debug(f"STATUS CHECK: {player_data.get('name', 'Unknown')} - Old: {old_status} → New: {new_status}")
                    
                    # Special IP logic: only use plys IP if it's not empty, otherwise preserve database IP
                    if new_ip and new_ip.strip():
                        final_ip = new_ip  # plys has IP, use it
                    else:
                        final_ip = existing_ip  # plys has no IP, keep database IP
                    
                    # Determine if we should update this player (only update if something meaningful changed)
                    should_update = False
                    final_last_seen = existing_last_seen
                    final_updated_at = existing_player.get('updated_at', current_time)
                    
                    # Status change logic
                    if old_status == 'Offline' and new_status == 'Online':
                        # Player logging in
                        final_playfield = new_playfield or existing_playfield
                        should_update = True
                        final_updated_at = current_time
                        logger.info(f"PLAYER LOGIN: {player_data.get('name')} - IP: plys='{new_ip}' -> final='{final_ip}', Country: {country}")
                        
                    elif old_status == 'Online' and new_status == 'Offline':
                        # Player logging out - set last_seen
                        final_playfield = ''  # Clear playfield on logout
                        final_last_seen = current_time  # Set logout time
                        should_update = True
                        final_updated_at = current_time
                        logger.info(f"PLAYER LOGOUT: {player_data.get('name')} - IP: plys='{new_ip}', existing='{existing_ip}' -> final='{final_ip}', last_seen='{final_last_seen}', Country: {country}")
                        
                    elif old_status == 'Online' and new_status == 'Online':
                        # Player staying online - update playfield and other data but keep last_seen unchanged
                        final_playfield = new_playfield or existing_playfield
                        should_update = True
                        final_updated_at = current_time
                        logger.debug(f"PLAYER ONLINE UPDATE: {player_data.get('name')} - IP: plys='{new_ip}' -> final='{final_ip}', Country: {country}")
                        
                    else:
                        # Both offline - only update if IP/country/name changed
                        final_playfield = existing_playfield  # Keep existing playfield for offline players
                        
                        if (player_data.get('name', '') != existing_player.get('name', '') or
                            final_ip != existing_ip or
                            country != existing_player.get('country') or
                            player_data.get('faction', '') != existing_player.get('faction', '') or
                            player_data.get('role', '') != existing_player.get('role', '')):
                            should_update = True
                            final_updated_at = current_time
                            logger.debug(f"OFFLINE PLAYER DATA UPDATE: {player_data.get('name')} - Updated data for offline player")
                        else:
                            logger.debug(f"NO UPDATE NEEDED: {player_data.get('name')} - No meaningful changes for offline player")
                    
                    # Only update database if something changed
                    if should_update:
                        cursor.execute("""
                            UPDATE players SET
                                name = ?,
                                status = ?,
                                faction = ?,
                                role = ?,
                                ip_address = ?,
                                country = ?,
                                playfield = ?,
                                last_seen = ?,
                                updated_at = ?
                            WHERE steam_id = ?
                        """, (
                            player_data.get('name', ''),
                            new_status,
                            player_data.get('faction', ''),
                            player_data.get('role', ''),
                            final_ip,
                            country,
                            final_playfield,
                            final_last_seen,
                            final_updated_at,
                            steam_id
                        ))
                    
                else:
                    # New player - insert with current data
                    final_last_seen = None if player_data.get('status') == 'Online' else None
                    logger.info(f"NEW PLAYER: {player_data.get('name', 'Unknown')} ({steam_id}), Country: {country}")
                    cursor.execute("""
                        INSERT INTO players (
                            steam_id, name, status, faction, role, ip_address, country,
                            playfield, last_seen, first_seen, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        steam_id,
                        player_data.get('name', ''),
                        player_data.get('status', 'Offline'),
                        player_data.get('faction', ''),
                        player_data.get('role', ''),
                        player_data.get('ip_address', ''),
                        country,
                        player_data.get('playfield', ''),
                        final_last_seen,
                        current_time,
                        current_time
                    ))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error updating player {player_data.get('name', 'Unknown')}: {e}", exc_info=True)
            return {'success': False, 'message': 'An internal error occurred. Please try again later.'}
    
    def update_multiple_players(self, players_data: List[Dict]) -> int:
        """
        Update multiple players at once.

        Args:
            players_data (List[Dict]): List of player data dictionaries.

        Returns:
            int: Number of players updated.
        """
        updated_count = 0
        
        # First, process each player to detect status changes BEFORE marking offline
        for player_data in players_data:
            if self.update_player(player_data):
                updated_count += 1
        
        # Then mark any remaining online players as offline (who didn't appear in plys)
        self.mark_remaining_offline(players_data)
        
        # Remove duplicate entries with negative Steam IDs
        self.cleanup_negative_steam_ids()
        
        logger.info(f"Updated {updated_count} players in database")
        return updated_count
    
    def mark_remaining_offline(self, current_players: List[Dict]):
        """
        Mark players as offline who did not appear in the current 'plys' data.

        Args:
            current_players (List[Dict]): List of current player data from 'plys'.
        """
        try:
            current_time = datetime.now().isoformat()
            current_steam_ids = {str(p.get('steam_id', '')) for p in current_players if p.get('steam_id')}
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get currently online players who are NOT in the current plys data
                cursor.execute("SELECT steam_id, name FROM players WHERE status = 'Online'")
                online_players = cursor.fetchall()
                
                for steam_id, name in online_players:
                    if steam_id not in current_steam_ids:
                        # This player was online but is not in current plys - they logged out
                        cursor.execute("""
                            UPDATE players SET 
                                status = 'Offline',
                                last_seen = ?,
                                updated_at = ?
                            WHERE steam_id = ?
                        """, (current_time, current_time, steam_id))
                        
                        logger.info(f"PLAYER LOGOUT (not in plys): {name} - Setting last_seen: {current_time}")
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error marking remaining players offline: {e}", exc_info=True)
            return {'success': False, 'message': 'An internal error occurred. Please try again later.'}
    
    def mark_all_offline(self):
        """
        Mark all players as offline. Called before updating online players.
        """
        try:
            current_time = datetime.now().isoformat()
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Only update existing players to offline, don't create new records
                cursor.execute("""
                    UPDATE players SET 
                        status = 'Offline',
                        updated_at = ?
                    WHERE status = 'Online'
                """, (current_time,))
                
                affected = cursor.rowcount
                if affected > 0:
                    logger.debug(f"Marked {affected} players as offline")
                
                conn.commit()
        except Exception as e:
            logger.error(f"Error marking players offline: {e}", exc_info=True)
            return {'success': False, 'message': 'An internal error occurred. Please try again later.'}
    
    def cleanup_negative_steam_ids(self):
        """
        Remove entries with negative Steam IDs if a positive Steam ID exists for the same player name.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Find negative Steam IDs that have corresponding positive Steam IDs with same name
                cursor.execute("""
                    SELECT n.steam_id, n.name 
                    FROM players n
                    WHERE CAST(n.steam_id AS INTEGER) < 0
                    AND EXISTS (
                        SELECT 1 FROM players p 
                        WHERE p.name = n.name 
                        AND CAST(p.steam_id AS INTEGER) > 0
                    )
                """)
                
                negative_entries = cursor.fetchall()
                
                for steam_id, name in negative_entries:
                    cursor.execute("DELETE FROM players WHERE steam_id = ?", (steam_id,))
                    logger.info(f"Removed duplicate negative Steam ID {steam_id} for player {name}")
                
                if negative_entries:
                    conn.commit()
                    logger.info(f"Cleaned up {len(negative_entries)} negative Steam ID entries")
                
        except Exception as e:
            logger.error(f"Error cleaning up negative Steam IDs: {e}", exc_info=True)
            return {'success': False, 'message': 'An internal error occurred. Please try again later.'}
    
    def get_all_players(self, filters: Optional[Dict] = None) -> List[Dict]:
        """
        Get all players from the database, with optional filters.

        Args:
            filters (Optional[Dict], optional): Dictionary of filter criteria. Defaults to None.

        Returns:
            List[Dict] or dict: List of player dictionaries, or error dict if failed.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Base query - now includes country column
                query = """
                    SELECT steam_id, name, status, faction, role, ip_address, country,
                           playfield, last_seen, first_seen, total_playtime
                    FROM players
                """
                params = []
                
                # Add filters if provided
                if filters:
                    conditions = []
                    
                    if filters.get('steam_id'):
                        conditions.append("steam_id LIKE ?")
                        params.append(f"%{filters['steam_id']}%")
                    
                    if filters.get('name'):
                        conditions.append("name LIKE ?")
                        params.append(f"%{filters['name']}%")
                    
                    if filters.get('status'):
                        conditions.append("status = ?")
                        params.append(filters['status'])
                    
                    if filters.get('faction'):
                        conditions.append("faction LIKE ?")
                        params.append(f"%{filters['faction']}%")
                    
                    if filters.get('ip_address'):
                        conditions.append("ip_address LIKE ?")
                        params.append(f"%{filters['ip_address']}%")
                    
                    if filters.get('country'):
                        conditions.append("country LIKE ?")
                        params.append(f"%{filters['country']}%")
                    
                    if filters.get('playfield'):
                        conditions.append("playfield LIKE ?")
                        params.append(f"%{filters['playfield']}%")
                    
                    if conditions:
                        query += " WHERE " + " AND ".join(conditions)
                
                # Order by status (Online first), then by last seen (most recent first)
                query += " ORDER BY CASE WHEN status = 'Online' THEN 0 ELSE 1 END, last_seen DESC"
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                # Convert to list of dictionaries
                players = []
                for row in rows:
                    players.append({
                        'steam_id': row[0],
                        'name': row[1],
                        'status': row[2],
                        'faction': row[3],
                        'role': row[4],
                        'ip_address': row[5],
                        'country': row[6],  # New field
                        'playfield': row[7],
                        'last_seen': row[8],
                        'first_seen': row[9],
                        'total_playtime': row[10]
                    })
                
                return players
                
        except Exception as e:
            logger.error(f"Error getting players from database: {e}", exc_info=True)
            return {'success': False, 'message': 'An internal error occurred. Please try again later.'}
    
    def get_online_players(self) -> List[Dict]:
        """
        Get only currently online players from the database.

        Returns:
            List[Dict]: List of online player dictionaries.
        """
        return self.get_all_players({'status': 'Online'})
    
    def get_player_count(self) -> Dict[str, int]:
        """
        Get player statistics (total, online, and offline counts).

        Returns:
            Dict[str, int] or dict: Dictionary with total, online, and offline player counts, or error dict if failed.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Total players
                cursor.execute("SELECT COUNT(*) FROM players")
                total = cursor.fetchone()[0]
                
                # Online players
                cursor.execute("SELECT COUNT(*) FROM players WHERE status = 'Online'")
                online = cursor.fetchone()[0]
                
                return {
                    'total': total,
                    'online': online,
                    'offline': total - online
                }
                
        except Exception as e:
            logger.error(f"Error getting player count: {e}", exc_info=True)
            return {'success': False, 'message': 'An internal error occurred. Please try again later.'}
    
    def delete_player(self, steam_id: str) -> bool:
        """
        Delete a player and their sessions from the database.

        Args:
            steam_id (str): Steam ID of the player to delete.

        Returns:
            bool: True if deleted, False otherwise.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM players WHERE steam_id = ?", (steam_id,))
                cursor.execute("DELETE FROM player_sessions WHERE steam_id = ?", (steam_id,))
                conn.commit()
                
                if cursor.rowcount > 0:
                    logger.info(f"Deleted player with Steam ID: {steam_id}")
                    return True
                else:
                    logger.warning(f"No player found with Steam ID: {steam_id}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error deleting player {steam_id}: {e}", exc_info=True)
            return False
    
    # ============================================================================
    # GEOLOCATION UTILITY METHODS
    # ============================================================================
    
    def get_geolocation_stats(self) -> Dict[str, any]:
        """
        Get statistics about geolocation data for all players.

        Returns:
            Dict[str, any]: Dictionary with geolocation stats.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Count players by country
                cursor.execute("""
                    SELECT country, COUNT(*) as count 
                    FROM players 
                    WHERE country IS NOT NULL 
                    GROUP BY country 
                    ORDER BY count DESC
                """)
                country_counts = dict(cursor.fetchall())
                
                # Total players with geolocation data
                cursor.execute("SELECT COUNT(*) FROM players WHERE country IS NOT NULL")
                with_geo = cursor.fetchone()[0]
                
                # Total players without geolocation data
                cursor.execute("SELECT COUNT(*) FROM players WHERE country IS NULL")
                without_geo = cursor.fetchone()[0]
                
                return {
                    'with_geolocation': with_geo,
                    'without_geolocation': without_geo,
                    'country_breakdown': country_counts,
                    'cache_size': len(self.geolocation_cache)
                }
                
        except Exception as e:
            logger.error(f"Error getting geolocation stats: {e}")
            return {}
    
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
            logger.info(f"Set app setting: {key} = {value}")
            return True
        except Exception as e:
            logger.error(f"Error setting app setting {key}: {e}")
            return False

    def get_app_setting(self, key: str, default=None):
        """
        Retrieve an application setting from the app_settings table.
        Returns default if not found.
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

    def set_ftp_test_success(self) -> bool:
        """
        Record that FTP connection test was successful.
        """
        return self.set_app_setting('ftp_test_status', 'success')

    def get_ftp_test_status(self) -> str:
        """
        Get FTP test status. Returns: 'success', or None if never tested.
        """
        return self.get_app_setting('ftp_test_status')

    def validate_update_interval(self, value) -> int:
        """
        Validate update_interval: must be integer >= 10. Default to 20 if invalid.
        """
        try:
            val = int(value)
            if val < 10:
                logger.warning("update_interval below minimum (10); using 20")
                return 20
            return val
        except Exception:
            logger.warning("Invalid update_interval; using 20")
            return 20
    
    def force_update_all_geolocations(self) -> int:
        """
        Force update geolocation for all players with IP addresses. (Admin function)

        Returns:
            int: Number of players updated.
        """
        try:
            updated_count = 0
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get all players with IP addresses
                cursor.execute("""
                    SELECT steam_id, name, ip_address 
                    FROM players 
                    WHERE ip_address IS NOT NULL AND ip_address != ''
                """)
                players_with_ips = cursor.fetchall()
                
                logger.info(f"Forcing geolocation update for {len(players_with_ips)} players")
                
                for steam_id, name, ip_address in players_with_ips:
                    country = self._lookup_country(ip_address)
                    
                    cursor.execute("""
                        UPDATE players SET country = ?, updated_at = ? 
                        WHERE steam_id = ?
                    """, (country, datetime.now().isoformat(), steam_id))
                    
                    updated_count += 1
                    logger.info(f"Updated geolocation for {name}: {ip_address} -> {country}")
                    
                    # Small delay to respect API rate limits
                    time.sleep(1)
                
                conn.commit()
                logger.info(f"Forced geolocation update completed: {updated_count} players updated")
                return updated_count
                
        except Exception as e:
            logger.error(f"Error in force geolocation update: {e}")
            return 0
    
    def refresh_geolocation_for_existing_players(self) -> int:
        """
        Refresh geolocation for players that do not have country data yet.

        Returns:
            int: Number of players updated.
        """
        try:
            updated_count = 0
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get players with IP but no country
                cursor.execute("""
                    SELECT steam_id, name, ip_address 
                    FROM players 
                    WHERE ip_address IS NOT NULL 
                    AND ip_address != ''
                    AND (country IS NULL OR country = '')
                    LIMIT 20
                """)
                players_needing_geo = cursor.fetchall()
                
                logger.info(f"Refreshing geolocation for {len(players_needing_geo)} players")
                
                for steam_id, name, ip_address in players_needing_geo:
                    country = self._lookup_country(ip_address)
                    
                    cursor.execute("""
                        UPDATE players SET country = ?
                        WHERE steam_id = ?
                    """, (country, steam_id))
                    
                    updated_count += 1
                    logger.info(f"Added geolocation for {name}: {ip_address} -> {country}")
                    
                    # Small delay to respect API rate limits
                    time.sleep(1)
                
                conn.commit()
                logger.info(f"Geolocation refresh completed: {updated_count} players updated")
                return updated_count
                
        except Exception as e:
            logger.error(f"Error refreshing geolocation: {e}")
            return 0
    
    def purge_old_players(self, days_threshold: int = 14) -> Dict:
        """
        Remove players with no last_seen data or who haven't been seen in the specified number of days.
        
        Args:
            days_threshold (int): Number of days threshold. Players not seen for this many days will be deleted.
                                Default is 14 days.
        
        Returns:
            Dict: Result dictionary with success status, message, and count of deleted players.
        """
        try:
            from datetime import datetime, timedelta
            
            # Calculate cutoff date
            cutoff_date = (datetime.now() - timedelta(days=days_threshold)).isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # First, count how many players will be deleted for logging
                cursor.execute("""
                    SELECT COUNT(*) FROM players 
                    WHERE last_seen IS NULL 
                       OR last_seen = '' 
                       OR last_seen < ?
                """, (cutoff_date,))
                
                count_to_delete = cursor.fetchone()[0]
                
                if count_to_delete == 0:
                    logger.info("No old player data found to purge")
                    return {
                        'success': True,
                        'message': 'No old player data found to purge',
                        'deleted_count': 0
                    }
                
                # Delete players meeting the criteria
                cursor.execute("""
                    DELETE FROM players 
                    WHERE last_seen IS NULL 
                       OR last_seen = '' 
                       OR last_seen < ?
                """, (cutoff_date,))
                
                deleted_count = cursor.rowcount
                
                # Also clean up any associated player sessions
                cursor.execute("""
                    DELETE FROM player_sessions 
                    WHERE steam_id NOT IN (SELECT steam_id FROM players)
                """)
                
                conn.commit()
                
                logger.info(f"Purged {deleted_count} old players (threshold: {days_threshold} days, cutoff: {cutoff_date})")
                
                return {
                    'success': True,
                    'message': f'Successfully deleted {deleted_count} players',
                    'deleted_count': deleted_count
                }
                
        except Exception as e:
            logger.error(f"Error purging old players: {e}", exc_info=True)
            return {
                'success': False,
                'message': 'An internal error occurred while purging player data',
                'deleted_count': 0
            }
    
    # ============================================================================
    # ENTITY MANAGEMENT METHODS
    # ============================================================================
    
    def save_entities(self, entities: List[Dict], raw_data: str) -> bool:
        """
        Save entities to the database and update last refresh timestamp.
        
        Args:
            entities (List[Dict]): List of entity dictionaries
            raw_data (str): Raw gents command output
            
        Returns:
            bool: True if saved successfully
        """
        try:
            current_time = datetime.now().isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Clear existing entities
                cursor.execute("DELETE FROM entities")
                
                # Insert new entities
                for entity in entities:
                    cursor.execute("""
                        INSERT INTO entities (id, name, type, faction, playfield, time_info, last_seen, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        entity.get('id', ''),
                        entity.get('name', ''),
                        entity.get('type', ''),
                        entity.get('faction', ''),
                        entity.get('playfield', ''),
                        entity.get('time_info', ''),
                        current_time,
                        current_time
                    ))
                
                # Update last refresh metadata
                cursor.execute("""
                    INSERT OR REPLACE INTO entities_meta (key, value, updated_at)
                    VALUES ('last_refresh', ?, ?)
                """, (current_time, current_time))
                
                cursor.execute("""
                    INSERT OR REPLACE INTO entities_meta (key, value, updated_at) 
                    VALUES ('raw_data', ?, ?)
                """, (raw_data, current_time))
                
                conn.commit()
                logger.info(f"Saved {len(entities)} entities to database")
                return True
                
        except Exception as e:
            logger.error(f"Error saving entities: {e}", exc_info=True)
            return False
    
    def get_entities(self) -> Dict:
        """
        Get all entities from database with metadata.
        
        Returns:
            Dict: Dictionary with entities, stats, and last refresh info
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get entities
                cursor.execute("""
                    SELECT id, name, type, faction, playfield, time_info, last_seen
                    FROM entities
                    ORDER BY playfield, type, name
                """)
                
                rows = cursor.fetchall()
                entities = []
                for row in rows:
                    entities.append({
                        'id': row[0],
                        'name': row[1], 
                        'type': row[2],
                        'faction': row[3],
                        'playfield': row[4],
                        'time_info': row[5],
                        'last_seen': row[6]
                    })
                
                # Get metadata
                cursor.execute("SELECT key, value FROM entities_meta")
                meta_rows = cursor.fetchall()
                metadata = {row[0]: row[1] for row in meta_rows}
                
                # Calculate stats
                stats = {
                    'total': len(entities),
                    'by_type': {},
                    'by_playfield': {}
                }
                
                for entity in entities:
                    # Count by type
                    entity_type = entity['type']
                    stats['by_type'][entity_type] = stats['by_type'].get(entity_type, 0) + 1
                    
                    # Count by playfield
                    playfield = entity['playfield'] or 'Unknown'
                    stats['by_playfield'][playfield] = stats['by_playfield'].get(playfield, 0) + 1
                
                return {
                    'success': True,
                    'entities': entities,
                    'stats': stats,
                    'last_refresh': metadata.get('last_refresh'),
                    'raw_data': metadata.get('raw_data', '')
                }
                
        except Exception as e:
            logger.error(f"Error getting entities: {e}", exc_info=True)
            return {'success': False, 'message': 'Database error'}
    
    def clear_entities(self) -> bool:
        """
        Clear all entities from database.
        
        Returns:
            bool: True if cleared successfully
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM entities")
                cursor.execute("DELETE FROM entities_meta")
                conn.commit()
                logger.info("Cleared all entities from database")
                return True
        except Exception as e:
            logger.error(f"Error clearing entities: {e}", exc_info=True)
            return False
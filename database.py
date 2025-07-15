# FILE LOCATION: /database.py (root directory)
#!/usr/bin/env python3
"""
Database manager for Empyrion Web Helper
Enhanced with secure credentials storage
"""

import sqlite3
import logging
import os
import base64
import getpass
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
    """Manages SQLite database for player tracking and secure credentials"""
    
    def __init__(self, db_path: str = "instance/players.db"):
        self.db_path = db_path
        self.encryption_key = None
        self.ensure_directory_exists()
        self.init_database()
        if CRYPTO_AVAILABLE:
            self._init_encryption()
        else:
            logger.warning("Cryptography not installed - install with: pip install cryptography")
    
    def ensure_directory_exists(self):
        """Create directory if it doesn't exist"""
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
        """Initialize database tables including credentials"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create players table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS players (
                        steam_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        status TEXT DEFAULT 'Offline',
                        faction TEXT DEFAULT '',
                        role TEXT DEFAULT '',
                        ip_address TEXT DEFAULT '',
                        playfield TEXT DEFAULT '',
                        last_seen TEXT,
                        first_seen TEXT NOT NULL,
                        total_playtime INTEGER DEFAULT 0,
                        updated_at TEXT NOT NULL
                    )
                """)
                
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
                
                # Create indexes for better performance
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_players_status ON players (status)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_players_last_seen ON players (last_seen)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_steam_id ON player_sessions (steam_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_credentials_type ON credentials (credential_type)")
                
                # Set secure permissions on database file
                try:
                    os.chmod(self.db_path, 0o600)
                except Exception as e:
                    logger.warning(f"Could not set secure permissions on database: {e}")
                
                conn.commit()
                logger.info("Database initialized successfully with credentials support")
                
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
    
    # ============================================================================
    # CREDENTIAL MANAGEMENT METHODS
    # ============================================================================
    
    def store_credential(self, credential_type: str, username: str = '', password: str = '', 
                        host: str = '', port: int = 0, additional_data: str = '') -> bool:
        """Store encrypted credentials in database"""
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
            logger.error(f"Error storing {credential_type} credentials: {e}")
            return False
    
    def get_credential(self, credential_type: str) -> Optional[Dict]:
        """Retrieve and decrypt credentials from database"""
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
            logger.error(f"Error retrieving {credential_type} credentials: {e}")
            return None
    
    def delete_credential(self, credential_type: str) -> bool:
        """Delete credentials from database"""
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
            logger.error(f"Error deleting {credential_type} credentials: {e}")
            return False
    
    def list_stored_credentials(self) -> List[str]:
        """Get list of stored credential types"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT credential_type FROM credentials")
                return [row[0] for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Error listing credentials: {e}")
            return []
    
    def prompt_for_credentials(self, credential_type: str, description: str, 
                             include_host: bool = True, include_username: bool = True) -> Optional[Dict]:
        """Interactively prompt for credentials if running in terminal"""
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
            return None
    
    def get_rcon_credentials(self) -> Optional[Dict]:
        """Get RCON credentials, prompting if not stored"""
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
        """Get FTP credentials, prompting if not stored"""
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
    # EXISTING PLAYER MANAGEMENT METHODS
    # ============================================================================
    
    def update_player(self, player_data: Dict) -> bool:
        """Update or insert player data with proper status change handling"""
        try:
            # Validate Steam ID (no negative IDs)
            steam_id = str(player_data.get('steam_id', ''))
            if not steam_id or steam_id == '-1' or (steam_id.lstrip('-').isdigit() and int(steam_id) < 0):
                logger.warning(f"Skipping player with invalid Steam ID: {steam_id}")
                return False
            
            current_time = datetime.now().isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if player exists and get current status
                cursor.execute("SELECT steam_id, first_seen, ip_address, playfield, status, last_seen FROM players WHERE steam_id = ?", (steam_id,))
                existing = cursor.fetchone()
                
                if existing:
                    # Player exists - handle status changes
                    existing_ip = existing[2] if existing[2] else ''
                    existing_playfield = existing[3] if existing[3] else ''
                    old_status = existing[4] if existing[4] else 'Offline'
                    existing_last_seen = existing[5] if existing[5] else None
                    
                    new_status = player_data.get('status', 'Offline')
                    new_ip = player_data.get('ip_address', '')
                    new_playfield = player_data.get('playfield', '')
                    
                    logger.debug(f"STATUS CHECK: {player_data.get('name', 'Unknown')} - Old: {old_status} → New: {new_status}")
                    
                    # Special IP logic: only use plys IP if it's not empty, otherwise preserve database IP
                    if new_ip and new_ip.strip():
                        final_ip = new_ip  # plys has IP, use it
                    else:
                        final_ip = existing_ip  # plys has no IP, keep database IP
                    
                    # Determine final playfield and last_seen based on status change
                    if old_status == 'Offline' and new_status == 'Online':
                        # Player logging in
                        final_playfield = new_playfield or existing_playfield
                        final_last_seen = existing_last_seen  # Keep existing last_seen
                        logger.info(f"PLAYER LOGIN: {player_data.get('name')} - IP: plys='{new_ip}' -> final='{final_ip}'")
                        
                    elif old_status == 'Online' and new_status == 'Offline':
                        # Player logging out - clear playfield, set last_seen
                        final_playfield = ''  # Clear playfield on logout
                        final_last_seen = current_time  # Set logout time
                        logger.info(f"PLAYER LOGOUT: {player_data.get('name')} - IP: plys='{new_ip}', existing='{existing_ip}' -> final='{final_ip}', last_seen='{final_last_seen}'")
                        
                    else:
                        # No status change
                        final_playfield = new_playfield or existing_playfield  
                        final_last_seen = existing_last_seen  # Don't change last_seen
                        logger.debug(f"NO STATUS CHANGE: {player_data.get('name')} - IP: plys='{new_ip}' -> final='{final_ip}'")
                    
                    # Update player
                    cursor.execute("""
                        UPDATE players SET
                            name = ?,
                            status = ?,
                            faction = ?,
                            role = ?,
                            ip_address = ?,
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
                        final_playfield,
                        final_last_seen,
                        current_time,
                        steam_id
                    ))
                    
                else:
                    # New player - insert with current data, no last_seen for fresh entries
                    cursor.execute("""
                        INSERT INTO players (
                            steam_id, name, status, faction, role, ip_address, 
                            playfield, last_seen, first_seen, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        steam_id,
                        player_data.get('name', ''),
                        player_data.get('status', 'Offline'),
                        player_data.get('faction', ''),
                        player_data.get('role', ''),
                        player_data.get('ip_address', ''),
                        player_data.get('playfield', ''),
                        None,  # last_seen = NULL for fresh entries
                        current_time,
                        current_time
                    ))
                    logger.info(f"NEW PLAYER: {player_data.get('name', 'Unknown')} ({steam_id})")
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error updating player {player_data.get('name', 'Unknown')}: {e}")
            return False
    
    def update_multiple_players(self, players_data: List[Dict]) -> int:
        """Update multiple players at once"""
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
        """Mark players as offline who didn't appear in current plys data"""
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
            logger.error(f"Error marking remaining players offline: {e}")
    
    def mark_all_offline(self):
        """Mark all players as offline (called before updating online players)"""
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
            logger.error(f"Error marking players offline: {e}")
    
    def cleanup_negative_steam_ids(self):
        """Remove entries with negative Steam IDs if a positive Steam ID exists for the same player name"""
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
            logger.error(f"Error cleaning up negative Steam IDs: {e}")
    
    def get_all_players(self, filters: Optional[Dict] = None) -> List[Dict]:
        """Get all players from database with optional filters"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Base query
                query = """
                    SELECT steam_id, name, status, faction, role, ip_address, 
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
                        'playfield': row[6],
                        'last_seen': row[7],
                        'first_seen': row[8],
                        'total_playtime': row[9]
                    })
                
                return players
                
        except Exception as e:
            logger.error(f"Error getting players from database: {e}")
            return []
    
    def get_online_players(self) -> List[Dict]:
        """Get only currently online players"""
        return self.get_all_players({'status': 'Online'})
    
    def get_player_count(self) -> Dict[str, int]:
        """Get player statistics"""
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
            logger.error(f"Error getting player count: {e}")
            return {'total': 0, 'online': 0, 'offline': 0}
    
    def delete_player(self, steam_id: str) -> bool:
        """Delete a player from the database"""
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
            logger.error(f"Error deleting player {steam_id}: {e}")
            return False

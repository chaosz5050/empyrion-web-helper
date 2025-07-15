#!/usr/bin/env python3
"""
Database manager for Empyrion Web Helper
Handles player tracking and history storage
"""

import sqlite3
import logging
import os
from datetime import datetime
from typing import List, Dict, Optional, Union

logger = logging.getLogger(__name__)

class PlayerDatabase:
    """Manages SQLite database for player tracking"""
    
    def __init__(self, db_path: str = "instance/players.db"):
        self.db_path = db_path
        self.ensure_directory_exists()
        self.init_database()
    
    def ensure_directory_exists(self):
        """Create directory if it doesn't exist"""
        directory = os.path.dirname(self.db_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
    
    def init_database(self):
        """Initialize database tables"""
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
                
                # Fix existing table if last_seen column exists with NOT NULL constraint
                try:
                    # Check if we need to recreate the table
                    cursor.execute("PRAGMA table_info(players)")
                    columns = cursor.fetchall()
                    last_seen_col = None
                    for col in columns:
                        if col[1] == 'last_seen':
                            last_seen_col = col
                            break
                    
                    # If last_seen exists and is NOT NULL, we need to recreate the table
                    if last_seen_col and last_seen_col[3] == 1:  # NOT NULL is 1
                        logger.info("Recreating players table to allow NULL last_seen values")
                        
                        # Create backup table
                        cursor.execute("""
                            CREATE TABLE players_backup AS 
                            SELECT steam_id, name, status, faction, role, ip_address, 
                                   playfield, first_seen, total_playtime, updated_at
                            FROM players
                        """)
                        
                        # Drop original table
                        cursor.execute("DROP TABLE players")
                        
                        # Recreate with correct schema
                        cursor.execute("""
                            CREATE TABLE players (
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
                        
                        # Restore data with last_seen as NULL
                        cursor.execute("""
                            INSERT INTO players (steam_id, name, status, faction, role, ip_address, 
                                               playfield, last_seen, first_seen, total_playtime, updated_at)
                            SELECT steam_id, name, status, faction, role, ip_address, 
                                   playfield, NULL, first_seen, total_playtime, updated_at
                            FROM players_backup
                        """)
                        
                        # Drop backup table
                        cursor.execute("DROP TABLE players_backup")
                        
                        logger.info("Successfully recreated players table with nullable last_seen")
                        
                except Exception as e:
                    logger.warning(f"Could not check/fix table schema: {e}")
                
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
                
                conn.commit()
                logger.info("Database initialized successfully")
                
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
    
    def update_player(self, player_data: Dict) -> bool:
        """
        Update or insert player data with proper status change handling
        Returns True if successful, False otherwise
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
        """
        Update multiple players at once
        Returns number of successfully updated players
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
        """
        Remove entries with negative Steam IDs if a positive Steam ID exists for the same player name
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
            logger.error(f"Error cleaning up negative Steam IDs: {e}")
    
    def get_all_players(self, filters: Optional[Dict] = None) -> List[Dict]:
        """
        Get all players from database with optional filters
        """
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

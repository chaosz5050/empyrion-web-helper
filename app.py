# FILE LOCATION: /app.py (root directory)
#!/usr/bin/env python3
"""
Empyrion Web Helper v0.4.1
A web-based admin tool for Empyrion Galactic Survival servers
Enhanced with background service architecture for independent operation
"""

from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit
import logging
import os
import re
import atexit
import signal

# Import our modules
from config_manager import ConfigManager
from database import PlayerDatabase
from messaging import MessagingManager
from logging_manager import LoggingManager
from background_service import BackgroundService

# Initialize logging manager first (before other logging)
logging_manager = LoggingManager()
logger = logging_manager.setup_rotating_logger()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'empyrion-web-helper-secret-key-change-me'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global state - now managed by background service
background_service = None
config_manager = None
player_db = None
messaging_manager = None

def initialize_app():
    """Initialize the application with background service"""
    global config_manager, player_db, messaging_manager, background_service
    
    # Initialize player database first (needed for credentials)
    player_db = PlayerDatabase()
    
    # Initialize configuration with database reference
    config_manager = ConfigManager()
    config_manager.set_database(player_db)
    config_manager.load_config()
    
    # Initialize messaging manager
    config_file_path = 'empyrion_helper.conf'
    messaging_manager = MessagingManager(config_file=config_file_path)
    
    # Create instance directory if it doesn't exist
    if not os.path.exists('instance'):
        os.makedirs('instance')
    
    # Clean up old logs on startup
    cleanup_result = logging_manager.cleanup_old_logs()
    if cleanup_result['deleted_files'] > 0:
        logger.info(f"Startup cleanup: removed {cleanup_result['deleted_files']} old log files ({cleanup_result['deleted_bytes']} bytes)")
    
    # Initialize background service
    background_service = BackgroundService(config_manager, player_db, messaging_manager)
    
    logger.info("Empyrion Web Helper v0.4.1 initialized with background service architecture")
    logger.info(f"Target server: {config_manager.get('host')}:{config_manager.get('telnet_port')}")
    
    # Check credential status
    stored_creds = player_db.list_stored_credentials()
    if 'rcon' in stored_creds:
        logger.info("✅ RCON credentials available in database")
    elif os.environ.get('EMPYRION_RCON_PASSWORD'):
        logger.info("✅ RCON password available via environment variable")
    else:
        logger.warning("⚠️ No RCON credentials found - configure via web UI first")
        logger.warning("⚠️ Background service will not start until credentials are configured")
        return False
    
    return True

def start_background_service():
    """Start the background service if credentials are available"""
    global background_service
    
    if not background_service:
        logger.error("Background service not initialized")
        return False
    
    # Check if we have credentials
    rcon_creds = player_db.get_rcon_credentials()
    if not rcon_creds or not rcon_creds.get('password'):
        logger.warning("Cannot start background service: No RCON credentials configured")
        logger.info("💡 Configure credentials via web UI first, then restart the application")
        return False
    
    # Start the background service
    background_service.start()
    return True

def stop_background_service():
    """Stop the background service"""
    global background_service
    if background_service:
        background_service.stop()

# Register cleanup handlers
def cleanup_handler(signum=None, frame=None):
    """Clean shutdown handler"""
    logger.info("🛑 Shutdown signal received, stopping background service...")
    stop_background_service()
    
atexit.register(cleanup_handler)
signal.signal(signal.SIGTERM, cleanup_handler)
signal.signal(signal.SIGINT, cleanup_handler)

@app.route('/')
def index():
    """Main page"""
    if player_db:
        db_players = player_db.get_all_players()
    else:
        db_players = []
    
    # Get connection status from background service
    connection_status = background_service.get_connection_status() if background_service else {
        'is_connected': False, 'is_running': False
    }
    
    return render_template('index.html', 
                         connected=connection_status['is_connected'],
                         players=db_players,
                         config=config_manager.get_all(),
                         service_status=connection_status)

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files (like favicon)"""
    return send_from_directory('.', filename)

@app.route('/status')
def get_status():
    """Get current service and connection status"""
    if not background_service:
        return jsonify({
            'success': True,
            'service_running': False,
            'connected': False,
            'message': 'Background service not initialized'
        })
    
    status = background_service.get_connection_status()
    return jsonify({
        'success': True,
        'service_running': status['is_running'],
        'connected': status['is_connected'],
        'last_attempt': status['last_attempt'],
        'reconnect_attempts': status['reconnect_attempts']
    })

@app.route('/service/start', methods=['POST'])
def start_service():
    """Start the background service (only needed if credentials were just configured)"""
    if not background_service:
        return jsonify({'success': False, 'message': 'Background service not initialized'})
    
    if background_service.is_running:
        return jsonify({'success': True, 'message': 'Background service already running'})
    
    success = start_background_service()
    if success:
        return jsonify({'success': True, 'message': 'Background service started successfully'})
    else:
        return jsonify({'success': False, 'message': 'Failed to start background service - check credentials'})

@app.route('/service/stop', methods=['POST'])
def stop_service():
    """Stop the background service"""
    if not background_service:
        return jsonify({'success': False, 'message': 'Background service not initialized'})
    
    background_service.stop()
    return jsonify({'success': True, 'message': 'Background service stopped'})

# Legacy routes for backward compatibility (now just return status)
@app.route('/connect', methods=['POST'])
def connect():
    """Legacy connect route - now managed by background service"""
    if not background_service:
        return jsonify({'success': False, 'message': 'Background service not available'})
    
    status = background_service.get_connection_status()
    if status['is_connected']:
        return jsonify({'success': True, 'message': 'Already connected via background service'})
    else:
        return jsonify({'success': False, 'message': 'Connection managed by background service - check logs'})

@app.route('/disconnect', methods=['POST'])
def disconnect():
    """Legacy disconnect route - now managed by background service"""
    return jsonify({'success': True, 'message': 'Connection managed by background service'})

@app.route('/players')
def get_players():
    """Get current player list from database (no longer queries server directly)"""
    if not player_db:
        return jsonify({'success': False, 'message': 'Database not initialized'})
    
    try:
        # Get players from database (updated by background service)
        players = player_db.get_all_players()
        
        logger.info(f"=== /players route returning {len(players)} players from database ===")
        return jsonify({'success': True, 'players': players})
        
    except Exception as e:
        logger.error(f"Error getting players: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/players/all')
def get_all_players():
    """Get all players from database with filtering"""
    if not player_db:
        return jsonify({'success': False, 'message': 'Database not initialized'})
    
    try:
        filters = {}
        for param in ['steam_id', 'name', 'status', 'faction', 'ip_address', 'country', 'playfield']:
            value = request.args.get(param)
            if value:
                filters[param] = value
        
        players = player_db.get_all_players(filters)
        player_stats = player_db.get_player_count()
        
        logger.debug(f"=== /players/all returning {len(players)} players ===")
        
        return jsonify({
            'success': True, 
            'players': players,
            'stats': player_stats
        })
        
    except Exception as e:
        logger.error(f"Error getting all players: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/player_action', methods=['POST'])
def player_action():
    """Execute player action using background service connection"""
    if not background_service:
        return jsonify({'success': False, 'message': 'Background service not available'})
    
    connection_handler = background_service.get_connection_handler()
    if not connection_handler:
        return jsonify({'success': False, 'message': 'Not connected to server'})
    
    data = request.json
    action = data.get('action')
    
    try:
        if action == 'kick':
            player_name = data.get('player_name')
            message = data.get('message', 'Kicked by Admin')
            if not player_name:
                return jsonify({'success': False, 'message': 'Player name required'})
            result = connection_handler.kick_player(player_name, message)
            
        elif action == 'ban':
            steam_id = data.get('steam_id')
            duration = data.get('duration', '1d')
            if not steam_id:
                return jsonify({'success': False, 'message': 'Steam ID required'})
            result = connection_handler.ban_player(steam_id, duration)
            
        elif action == 'unban':
            steam_id = data.get('steam_id')
            if not steam_id:
                return jsonify({'success': False, 'message': 'Steam ID required'})
            result = connection_handler.unban_player(steam_id)
            
        else:
            return jsonify({'success': False, 'message': 'Invalid action'})
        
        if result:
            return jsonify({'success': True, 'message': f'{action.title()} successful'})
        else:
            return jsonify({'success': False, 'message': f'{action.title()} failed'})
            
    except Exception as e:
        logger.error(f"Player action error: {e}")
        return jsonify({'success': False, 'message': str(e)})

# ============================================================================
# ENTITIES ROUTES
# ============================================================================

@app.route('/entities')
def get_entities():
    """Get entities list using gents command"""
    if not background_service:
        return jsonify({'success': False, 'message': 'Background service not available'})
    
    connection_handler = background_service.get_connection_handler()
    if not connection_handler:
        return jsonify({'success': False, 'message': 'Not connected to server'})
    
    try:
        logger.info("=== STARTING /entities route ===")
        
        # Send gents command - this can take several seconds
        logger.info("Sending 'gents' command to server...")
        raw_data = connection_handler.send_command("gents", timeout=30.0)
        
        if not raw_data:
            logger.error("No response from 'gents' command")
            return jsonify({'success': False, 'message': 'No response from gents command'})
        
        logger.info(f"Received gents data: {len(raw_data)} characters")
        
        # Parse the gents output
        entities = parse_gents_data(raw_data)
        
        logger.info(f"Parsed {len(entities)} entities from gents output")
        logger.info("=== ENDING /entities route ===")
        
        return jsonify({
            'success': True, 
            'entities': entities,
            'raw_data': raw_data,
            'total_count': len(entities)
        })
        
    except Exception as e:
        logger.error(f"Error getting entities: {e}")
        return jsonify({'success': False, 'message': str(e)})

def parse_gents_data(raw_data):
    """Parse the output from gents command"""
    entities = []
    lines = raw_data.split('\n')
    current_playfield = ''
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Check if this is a playfield header
        if not re.match(r'^\s*\d+\.\s*\d+', line):
            current_playfield = line
            logger.debug(f"Found playfield: {current_playfield}")
            continue
        
        # Parse entity line
        entity = parse_entity_line(line, current_playfield)
        if entity:
            entities.append(entity)
    
    logger.info(f"Parsed {len(entities)} entities from {len(lines)} total lines")
    return entities

def parse_entity_line(line, playfield):
    """Parse a single entity line from gents output"""
    try:
        # Remove leading number and dot
        clean_line = re.sub(r'^\s*\d+\.\s*', '', line)
        
        # Parse: "042419 AstVoxel [NoF] False False 'Silicon Asteroid' (-)"
        pattern = r'^(\d+)\s+(\w+)\s+\[([^\]]+)\]\s+\w+\s+\w+\s+\'([^\']+)\'\s*\([^)]*\)'
        match = re.match(pattern, clean_line)
        
        if not match:
            pattern_alt = r'^(\d+)\s+(\w+)\s+\[([^\]]+)\]\s+\w+\s+\w+\s+\'([^\']+)\''
            match = re.match(pattern_alt, clean_line)
        
        if not match:
            return None
        
        entity_id, entity_type, faction, name = match.groups()
        
        return {
            'entity_id': entity_id.strip(),
            'type': entity_type.strip(),
            'faction': faction.strip(),
            'name': name.strip(),
            'playfield': playfield,
            'category': categorize_entity(entity_type, faction, name)
        }
        
    except Exception as e:
        logger.debug(f"Error parsing entity line '{line}': {e}")
        return None

def categorize_entity(entity_type, faction, name):
    """Categorize entity for easier filtering"""
    if entity_type == 'AstVoxel':
        return 'asteroid'
    
    if (faction == 'Wreck' or 
        'wreck' in name.lower() or 
        'debris' in name.lower() or 
        'abandoned' in name.lower() or
        'destroyed' in name.lower()):
        return 'wreck'
    
    if entity_type == 'BA':
        return 'structure'
    
    if entity_type in ['CV', 'SV']:
        return 'ship'
    
    return 'other'

# ============================================================================
# MESSAGING ROUTES
# ============================================================================

@app.route('/messaging/send', methods=['POST'])
def send_global_message():
    """Send a global message to all players"""
    if not background_service:
        return jsonify({'success': False, 'message': 'Background service not available'})
    
    connection_handler = background_service.get_connection_handler()
    if not connection_handler or not messaging_manager:
        return jsonify({'success': False, 'message': 'Not connected to server or messaging not available'})
    
    try:
        data = request.json
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({'success': False, 'message': 'Message cannot be empty'})
        
        success = messaging_manager.send_global_message(message, message_type='manual')
        
        if success:
            return jsonify({'success': True, 'message': 'Global message sent successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to send global message'})
            
    except Exception as e:
        logger.error(f"Error sending global message: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/messaging/custom', methods=['GET', 'POST'])
def custom_messages():
    """Get or save custom welcome/goodbye messages"""
    if not messaging_manager:
        return jsonify({'success': False, 'message': 'Messaging not available'})
    
    try:
        if request.method == 'GET':
            messages = messaging_manager.load_custom_messages()
            return jsonify({'success': True, 'messages': messages})
        
        elif request.method == 'POST':
            data = request.json
            welcome_msg = data.get('welcome_message', '').strip()
            goodbye_msg = data.get('goodbye_message', '').strip()
            
            success = messaging_manager.save_custom_messages(welcome_msg, goodbye_msg)
            
            if success:
                return jsonify({'success': True, 'message': 'Custom messages saved successfully'})
            else:
                return jsonify({'success': False, 'message': 'Failed to save custom messages'})
                
    except Exception as e:
        logger.error(f"Error handling custom messages: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/messaging/test', methods=['POST'])
def test_message():
    """Send a test welcome or goodbye message"""
    if not background_service:
        return jsonify({'success': False, 'message': 'Background service not available'})
    
    connection_handler = background_service.get_connection_handler()
    if not connection_handler or not messaging_manager:
        return jsonify({'success': False, 'message': 'Not connected to server or messaging not available'})
    
    try:
        data = request.json
        message_type = data.get('type', '')
        test_player = data.get('player_name', 'TestPlayer')
        
        if message_type == 'welcome':
            success = messaging_manager.test_welcome_message(test_player)
            msg = f"Test welcome message sent for {test_player}"
        elif message_type == 'goodbye':
            success = messaging_manager.test_goodbye_message(test_player)
            msg = f"Test goodbye message sent for {test_player}"
        else:
            return jsonify({'success': False, 'message': 'Invalid test message type'})
        
        if success:
            return jsonify({'success': True, 'message': msg})
        else:
            return jsonify({'success': False, 'message': 'Failed to send test message'})
            
    except Exception as e:
        logger.error(f"Error sending test message: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/messaging/scheduled', methods=['GET', 'POST'])
def scheduled_messages():
    """Get or save scheduled messages"""
    if not messaging_manager:
        return jsonify({'success': False, 'message': 'Messaging not available'})
    
    try:
        if request.method == 'GET':
            messages = messaging_manager.load_scheduled_messages()
            return jsonify({'success': True, 'messages': messages})
        
        elif request.method == 'POST':
            data = request.json
            messages_data = data.get('messages', [])
            
            success = messaging_manager.save_scheduled_messages(messages_data)
            
            if success:
                return jsonify({'success': True, 'message': 'Scheduled messages saved successfully'})
            else:
                return jsonify({'success': False, 'message': 'Failed to save scheduled messages'})
                
    except Exception as e:
        logger.error(f"Error handling scheduled messages: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/messaging/history')
def message_history():
    """Get message history"""
    if not messaging_manager:
        return jsonify({'success': False, 'message': 'Messaging not available'})
    
    try:
        limit = request.args.get('limit', 50, type=int)
        history = messaging_manager.get_message_history(limit)
        stats = messaging_manager.get_message_stats()
        
        return jsonify({
            'success': True, 
            'history': history,
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"Error getting message history: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/messaging/history/clear', methods=['POST'])
def clear_message_history():
    """Clear message history"""
    if not messaging_manager:
        return jsonify({'success': False, 'message': 'Messaging not available'})
    
    try:
        success = messaging_manager.clear_message_history()
        
        if success:
            return jsonify({'success': True, 'message': 'Message history cleared successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to clear message history'})
            
    except Exception as e:
        logger.error(f"Error clearing message history: {e}")
        return jsonify({'success': False, 'message': str(e)})

# ============================================================================
# LOGGING ROUTES
# ============================================================================

@app.route('/logging/stats')
def get_logging_stats():
    """Get logging statistics"""
    try:
        stats = logging_manager.get_log_stats()
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"Error getting logging stats: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/logging/settings', methods=['GET', 'POST'])
def logging_settings():
    """Get or update logging settings"""
    try:
        if request.method == 'GET':
            return jsonify({
                'success': True,
                'settings': {
                    'max_size_mb': logging_manager.max_bytes // (1024 * 1024),
                    'backup_count': logging_manager.backup_count,
                    'max_age_days': logging_manager.max_age_days
                }
            })
        
        elif request.method == 'POST':
            data = request.json
            max_size_mb = data.get('max_size_mb', 1)
            backup_count = data.get('backup_count', 3)
            max_age_days = data.get('max_age_days', 7)
            
            success = logging_manager.update_settings(max_size_mb, backup_count, max_age_days)
            
            if success:
                return jsonify({'success': True, 'message': 'Logging settings updated successfully'})
            else:
                return jsonify({'success': False, 'message': 'Failed to update logging settings'})
                
    except Exception as e:
        logger.error(f"Error handling logging settings: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/logging/recent')
def get_recent_logs():
    """Get recent log entries"""
    try:
        lines = request.args.get('lines', 100, type=int)
        logs = logging_manager.get_recent_logs(lines)
        
        return jsonify({
            'success': True,
            'logs': logs
        })
        
    except Exception as e:
        logger.error(f"Error getting recent logs: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/logging/cleanup', methods=['POST'])
def cleanup_old_logs():
    """Clean up old log files"""
    try:
        result = logging_manager.cleanup_old_logs()
        
        message = f"Cleaned up {result['deleted_files']} old log files ({result['deleted_bytes']} bytes)"
        
        return jsonify({
            'success': True,
            'message': message,
            'deleted_files': result['deleted_files'],
            'deleted_bytes': result['deleted_bytes']
        })
        
    except Exception as e:
        logger.error(f"Error cleaning up logs: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/logging/clear', methods=['POST'])
def clear_all_logs():
    """Clear all log files"""
    try:
        success = logging_manager.clear_all_logs()
        
        if success:
            return jsonify({'success': True, 'message': 'All log files cleared successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to clear log files'})
            
    except Exception as e:
        logger.error(f"Error clearing logs: {e}")
        return jsonify({'success': False, 'message': str(e)})

# ============================================================================
# GEOLOCATION ROUTES
# ============================================================================

@app.route('/geolocation/stats')
def get_geolocation_stats():
    """Get geolocation statistics"""
    if not player_db:
        return jsonify({'success': False, 'message': 'Database not initialized'})
    
    try:
        stats = player_db.get_geolocation_stats()
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"Error getting geolocation stats: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/geolocation/force_update', methods=['POST'])
def force_update_geolocation():
    """Force update geolocation for all players (admin function)"""
    if not player_db:
        return jsonify({'success': False, 'message': 'Database not initialized'})
    
    try:
        updated_count = player_db.force_update_all_geolocations()
        
        return jsonify({
            'success': True,
            'message': f'Updated geolocation for {updated_count} players',
            'updated_count': updated_count
        })
        
    except Exception as e:
        logger.error(f"Error in force geolocation update: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/geolocation/clear_cache', methods=['POST'])
def clear_geolocation_cache():
    """Clear the geolocation cache"""
    if not player_db:
        return jsonify({'success': False, 'message': 'Database not initialized'})
    
    try:
        player_db.clear_geolocation_cache()
        
        return jsonify({
            'success': True,
            'message': 'Geolocation cache cleared successfully'
        })
        
    except Exception as e:
        logger.error(f"Error clearing geolocation cache: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/players/refresh_geolocation', methods=['POST'])
def refresh_player_geolocation():
    """Refresh geolocation for players without country data"""
    if not player_db:
        return jsonify({'success': False, 'message': 'Database not initialized'})
    
    try:
        updated_count = player_db.refresh_geolocation_for_existing_players()
        
        return jsonify({
            'success': True,
            'message': f'Updated geolocation for {updated_count} players',
            'updated_count': updated_count
        })
        
    except Exception as e:
        logger.error(f"Error refreshing player geolocation: {e}")
        return jsonify({'success': False, 'message': str(e)})

# ============================================================================
# WEBSOCKET HANDLERS
# ============================================================================

@socketio.on('connect')
def handle_connect():
    """Handle WebSocket client connection"""
    logger.info('Web client connected')
    
    # Send current status
    if background_service:
        status = background_service.get_connection_status()
        emit('connection_status', {'connected': status['is_connected']})
    else:
        emit('connection_status', {'connected': False})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket client disconnection"""
    logger.info('Web client disconnected')

@socketio.on('request_message_history')
def handle_message_history_request():
    """Handle request for message history updates"""
    if messaging_manager:
        try:
            history = messaging_manager.get_message_history(20)
            emit('message_history_update', {'history': history})
        except Exception as e:
            logger.error(f"Error sending message history update: {e}")

if __name__ == '__main__':
    # Initialize the application
    init_success = initialize_app()
    
    if init_success:
        # Check if we have credentials to auto-start
        rcon_creds = player_db.get_rcon_credentials()
        if rcon_creds and rcon_creds.get('password'):
            logger.info("🔑 RCON credentials found - starting background service automatically")
            service_started = start_background_service()
            if service_started:
                logger.info("🚀 Background service started successfully")
            else:
                logger.error("❌ Failed to start background service")
        else:
            logger.warning("⚠️ No RCON credentials found")
            logger.info("💡 Configure credentials via web interface:")
            logger.info("💡 1. Open http://your-server-ip:5001")
            logger.info("💡 2. Click 'Start Service' and enter RCON password")
            logger.info("💡 3. Restart application for automatic startup")
    else:
        logger.error("❌ Application initialization failed")
    
    # Get local IP for network access
    import socket
    
    def get_local_ip():
        """Get the local network IP address"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
            
            if local_ip.startswith('127.'):
                raise Exception("Got localhost IP")
                
            return local_ip
            
        except Exception:
            return '0.0.0.0'
    
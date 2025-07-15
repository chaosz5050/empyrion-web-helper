# FILE LOCATION: /app.py (root directory)
#!/usr/bin/env python3
"""
Empyrion Web Helper v0.3.0
A web-based admin tool for Empyrion Galactic Survival servers
Enhanced with modular messaging system and professional log rotation
"""

from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit
import logging
import os

# Import our modules
from config_manager import ConfigManager
from connection import EmpyrionConnection
from database import PlayerDatabase
from messaging import MessagingManager
from logging_manager import LoggingManager  # NEW: Import logging manager

# Initialize logging manager first (before other logging)
logging_manager = LoggingManager()
logger = logging_manager.setup_rotating_logger()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'empyrion-web-helper-secret-key-change-me'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global state
current_players = []
is_connected = False
connection_handler = None
config_manager = None
player_db = None
messaging_manager = None

# DEBUG: Log that logging manager was initialized
logger.info(f"DEBUG: Logging manager initialized: {logging_manager}")
logger.info(f"DEBUG: Log file path: {logging_manager.log_file}")
logger.info(f"DEBUG: Log file exists: {os.path.exists(logging_manager.log_file)}")

def initialize_app():
    """Initialize the application"""
    global config_manager, player_db, messaging_manager
    
    # Initialize configuration
    config_manager = ConfigManager()
    config_manager.load_config()
    
    # Initialize player database
    player_db = PlayerDatabase()
    
    # Initialize messaging manager with explicit config file path
    config_file_path = 'empyrion_helper.conf'
    messaging_manager = MessagingManager(config_file=config_file_path)
    
    # Create instance directory if it doesn't exist
    if not os.path.exists('instance'):
        os.makedirs('instance')
    
    # Clean up old logs on startup
    cleanup_result = logging_manager.cleanup_old_logs()
    if cleanup_result['deleted_files'] > 0:
        logger.info(f"Startup cleanup: removed {cleanup_result['deleted_files']} old log files ({cleanup_result['deleted_bytes']} bytes)")
    
    logger.info("Empyrion Web Helper v0.3.0 initialized with messaging support and log rotation")
    logger.info(f"Target server: {config_manager.get('host')}:{config_manager.get('telnet_port')}")
    logger.info(f"Messaging manager initialized with config file: {config_file_path}")
    
    # Log current log settings
    log_stats = logging_manager.get_log_stats()
    logger.info(f"Log rotation: {log_stats['total_files']} files, {log_stats['total_size_mb']:.1f}MB total")

@app.route('/')
def index():
    """Main page"""
    if player_db:
        db_players = player_db.get_all_players()
    else:
        db_players = []
    
    return render_template('index.html', 
                         connected=is_connected,
                         players=db_players,
                         config=config_manager.get_all())

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files (like favicon)"""
    return send_from_directory('.', filename)

@app.route('/connect', methods=['POST'])
def connect():
    """Connect to the Empyrion server"""
    global is_connected, connection_handler
    
    try:
        logger.info(f"Attempting connection to {config_manager.get('host')}:{config_manager.get('telnet_port')}")
        
        connection_handler = EmpyrionConnection(
            config_manager.get('host'),
            config_manager.get('telnet_port'),
            config_manager.get('telnet_password')
        )
        
        if connection_handler.connect():
            is_connected = True
            
            # NEW: Set connection handler for messaging
            if messaging_manager:
                messaging_manager.set_connection_handler(connection_handler)
                messaging_manager.start_message_scheduler()
            
            logger.info(f"Successfully connected to server")
            socketio.emit('connection_status', {'connected': True})
            return jsonify({'success': True, 'message': 'Connected to server'})
        else:
            logger.error("Connection failed")
            return jsonify({'success': False, 'message': 'Failed to connect to server'})
            
    except Exception as e:
        logger.error(f"Connection error: {e}")
        return jsonify({'success': False, 'message': str(e)})

# ============================================================================
# NEW LOGGING ROUTES
# ============================================================================

@app.route('/logging/stats')
def get_log_stats():
    """Get logging statistics"""
    logger.info("DEBUG: /logging/stats route called")
    try:
        if not logging_manager:
            logger.error("DEBUG: logging_manager is None!")
            return jsonify({'success': False, 'message': 'Logging manager not initialized'})
        
        logger.info("DEBUG: Calling logging_manager.get_log_stats()")
        stats = logging_manager.get_log_stats()
        logger.info(f"DEBUG: Got stats from logging_manager: {stats}")
        
        return jsonify({'success': True, 'stats': stats})
        
    except Exception as e:
        logger.error(f"Error getting log stats: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/logging/recent')
def get_recent_logs():
    """Get recent log entries"""
    logger.info("DEBUG: /logging/recent route called")
    try:
        if not logging_manager:
            logger.error("DEBUG: logging_manager is None!")
            return jsonify({'success': False, 'message': 'Logging manager not initialized'})
        
        lines = request.args.get('lines', 100, type=int)
        logger.info(f"DEBUG: Getting recent logs, lines={lines}")
        
        recent_logs = logging_manager.get_recent_logs(lines)
        logger.info(f"DEBUG: Got {len(recent_logs)} log lines")
        
        return jsonify({'success': True, 'logs': recent_logs})
        
    except Exception as e:
        logger.error(f"Error getting recent logs: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/logging/clear', methods=['POST'])
def clear_logs():
    """Clear all log files"""
    try:
        success = logging_manager.clear_all_logs()
        
        if success:
            return jsonify({'success': True, 'message': 'All log files cleared successfully'})
        else:
            return jsonify({'success': False, 'message': 'No log files to clear'})
            
    except Exception as e:
        logger.error(f"Error clearing logs: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/logging/cleanup', methods=['POST'])
def cleanup_old_logs():
    """Clean up old log files"""
    try:
        result = logging_manager.cleanup_old_logs()
        
        if result['deleted_files'] > 0:
            message = f"Cleaned up {result['deleted_files']} old log files ({result['deleted_bytes']} bytes)"
            return jsonify({'success': True, 'message': message, 'result': result})
        else:
            return jsonify({'success': True, 'message': 'No old log files to clean up', 'result': result})
            
    except Exception as e:
        logger.error(f"Error cleaning up logs: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/logging/settings', methods=['GET', 'POST'])
def log_settings():
    """Get or update logging settings"""
    try:
        if request.method == 'GET':
            return jsonify({
                'success': True,
                'settings': {
                    'max_size_mb': logging_manager.max_bytes // (1024 * 1024),
                    'backup_count': logging_manager.backup_count,
                    'max_age_days': logging_manager.max_age_days,
                    'log_file': logging_manager.log_file
                }
            })
        
        elif request.method == 'POST':
            data = request.json
            
            max_size_mb = data.get('max_size_mb')
            backup_count = data.get('backup_count')
            max_age_days = data.get('max_age_days')
            
            success = logging_manager.update_settings(max_size_mb, backup_count, max_age_days)
            
            if success:
                return jsonify({'success': True, 'message': 'Logging settings updated successfully'})
            else:
                return jsonify({'success': False, 'message': 'Failed to update logging settings'})
                
    except Exception as e:
        logger.error(f"Error handling log settings: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/disconnect', methods=['POST'])
def disconnect():
    """Disconnect from the server"""
    global is_connected, connection_handler
    
    try:
        # NEW: Stop message scheduler
        if messaging_manager:
            messaging_manager.stop_message_scheduler()
        
        if connection_handler:
            connection_handler.disconnect()
        is_connected = False
        logger.info("Disconnected from server")
        socketio.emit('connection_status', {'connected': False})
        return jsonify({'success': True, 'message': 'Disconnected from server'})
        
    except Exception as e:
        logger.error(f"Disconnect error: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/players')
def get_players():
    """Get current player list and update database"""
    global current_players
    
    if not is_connected or not connection_handler:
        return jsonify({'success': False, 'message': 'Not connected to server'})
    
    try:
        logger.info("=== STARTING /players route ===")
        
        players = connection_handler.get_players()
        current_players = players
        
        logger.info(f"Got {len(players)} players from connection")
        
        if player_db and players:
            # Store previous state for status change detection
            previous_players = {p['steam_id']: p for p in player_db.get_all_players()}
            
            updated_count = player_db.update_multiple_players(players)
            logger.info(f"DATABASE UPDATE COMPLETE: Updated {updated_count} players")
            
            # NEW: Check for status changes and send welcome/goodbye messages
            if messaging_manager:
                current_players_dict = {p['steam_id']: p for p in players}
                
                for player in players:
                    steam_id = player['steam_id']
                    player_name = player['name']
                    current_status = player['status']
                    
                    if steam_id in previous_players:
                        previous_status = previous_players[steam_id]['status']
                        
                        # Player went from offline to online
                        if previous_status == 'Offline' and current_status == 'Online':
                            messaging_manager.send_welcome_message(player_name)
                            logger.info(f"Sent welcome message for {player_name}")
                        
                        # Player went from online to offline
                        elif previous_status == 'Online' and current_status == 'Offline':
                            messaging_manager.send_goodbye_message(player_name)
                            logger.info(f"Sent goodbye message for {player_name}")
                    else:
                        # New player joining
                        if current_status == 'Online':
                            messaging_manager.send_welcome_message(player_name)
                            logger.info(f"Sent welcome message for new player {player_name}")
                
                # Check for players who disconnected (in previous but not in current)
                for steam_id, prev_player in previous_players.items():
                    if steam_id not in current_players_dict and prev_player['status'] == 'Online':
                        messaging_manager.send_goodbye_message(prev_player['name'])
                        logger.info(f"Sent goodbye message for disconnected player {prev_player['name']}")
        
        logger.info("=== ENDING /players route ===")
        return jsonify({'success': True, 'players': players})
        
    except Exception as e:
        logger.error(f"Error getting players: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/players/all')
def get_all_players():
    """Get all players from database"""
    if not player_db:
        return jsonify({'success': False, 'message': 'Database not initialized'})
    
    try:
        filters = {}
        for param in ['steam_id', 'name', 'status', 'faction', 'ip_address', 'playfield']:
            value = request.args.get(param)
            if value:
                filters[param] = value
        
        players = player_db.get_all_players(filters)
        player_stats = player_db.get_player_count()
        
        logger.info(f"=== /players/all returning {len(players)} players ===")
        
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
    """Execute player action"""
    if not is_connected or not connection_handler:
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
# NEW MESSAGING ROUTES
# ============================================================================

@app.route('/messaging/send', methods=['POST'])
def send_global_message():
    """Send a global message to all players"""
    if not is_connected or not messaging_manager:
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
    logger.info(f"Custom messages route called with method: {request.method}")
    
    if not messaging_manager:
        logger.error("Messaging manager not available!")
        return jsonify({'success': False, 'message': 'Messaging not available'})
    
    try:
        if request.method == 'GET':
            logger.info("Loading custom messages...")
            messages = messaging_manager.load_custom_messages()
            logger.info(f"Custom messages loaded: {messages}")
            return jsonify({'success': True, 'messages': messages})
        
        elif request.method == 'POST':
            data = request.json
            logger.info(f"Saving custom messages with data: {data}")
            
            welcome_msg = data.get('welcome_message', '').strip()
            goodbye_msg = data.get('goodbye_message', '').strip()
            
            logger.info(f"Extracted messages - Welcome: '{welcome_msg}', Goodbye: '{goodbye_msg}'")
            
            success = messaging_manager.save_custom_messages(welcome_msg, goodbye_msg)
            
            if success:
                logger.info("Custom messages saved successfully via route")
                return jsonify({'success': True, 'message': 'Custom messages saved successfully'})
            else:
                logger.error("Failed to save custom messages via route")
                return jsonify({'success': False, 'message': 'Failed to save custom messages'})
                
    except Exception as e:
        logger.error(f"Error handling custom messages: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/messaging/test', methods=['POST'])
def test_message():
    """Send a test welcome or goodbye message"""
    if not is_connected or not messaging_manager:
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
    logger.info(f"Scheduled messages route called with method: {request.method}")
    
    if not messaging_manager:
        logger.error("Messaging manager not available!")
        return jsonify({'success': False, 'message': 'Messaging not available'})
    
    try:
        if request.method == 'GET':
            logger.info("Loading scheduled messages...")
            messages = messaging_manager.load_scheduled_messages()
            logger.info(f"Loaded {len(messages)} scheduled messages")
            return jsonify({'success': True, 'messages': messages})
        
        elif request.method == 'POST':
            data = request.json
            logger.info(f"Saving scheduled messages with data: {data}")
            
            messages_data = data.get('messages', [])
            logger.info(f"Extracted {len(messages_data)} messages to save")
            
            success = messaging_manager.save_scheduled_messages(messages_data)
            
            if success:
                logger.info("Scheduled messages saved successfully via route")
                return jsonify({'success': True, 'message': 'Scheduled messages saved successfully'})
            else:
                logger.error("Failed to save scheduled messages via route")
                return jsonify({'success': False, 'message': 'Failed to save scheduled messages'})
                
    except Exception as e:
        logger.error(f"Error handling scheduled messages: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
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
# WEBSOCKET HANDLERS
# ============================================================================

@socketio.on('connect')
def handle_connect():
    """Handle WebSocket client connection"""
    logger.info('Web client connected')
    emit('connection_status', {'connected': is_connected})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket client disconnection"""
    logger.info('Web client disconnected')

@socketio.on('request_message_history')
def handle_message_history_request():
    """Handle request for message history updates"""
    if messaging_manager:
        try:
            history = messaging_manager.get_message_history(20)  # Last 20 messages
            emit('message_history_update', {'history': history})
        except Exception as e:
            logger.error(f"Error sending message history update: {e}")

if __name__ == '__main__':
    # Initialize the application
    initialize_app()
    
    logger.info("Starting Empyrion Web Helper v0.3.0 with messaging support")
    
    # Debug: Log all registered routes
    logger.info("Registered routes:")
    for rule in app.url_map.iter_rules():
        logger.info(f"  {rule.rule} -> {rule.endpoint}")
    
    # Start the Flask app
    socketio.run(app, debug=True, host='0.0.0.0', port=5001)
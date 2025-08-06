# FILE LOCATION: /app.py (root directory)
#!/usr/bin/env python3
"""
Empyrion Web Helper v0.5.4
A web-based admin tool for Empyrion Galactic Survival servers.

This Flask-based application provides a web interface for server administration, with
background service architecture for independent operation and robust error handling.
"""

from version import __version__

from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit
import logging
import os
import re
import atexit
import threading
from datetime import datetime

# Import our modules
from config_manager import ConfigManager
from database import PlayerDatabase
from messaging import MessagingManager
from logging_manager import LoggingManager
from background_service import BackgroundService
from connection import EmpyrionConnection
from connection_manager import EnhancedConnectionManager, UniversalFileClient

# Initialize logging manager first (before other logging)
logging_manager = LoggingManager()
logger = logging_manager.setup_rotating_logger()

# Thread-safe locks for shared resources
app_lock = threading.Lock()
db_lock = threading.Lock()

# Global state - now managed by background service
background_service = None
config_manager = None
player_db = None
messaging_manager = None

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

def create_app():
    """
    Factory function to create and configure the Flask application and its components.
    Ensures a predictable and thread-safe initialization sequence.
    """
    global player_db, config_manager, messaging_manager, background_service
    
    def get_or_create_secret_key(key_path='instance/ewh_secret.key'):
        import secrets
        if os.path.exists(key_path):
            with open(key_path, 'rb') as f:
                return f.read()
        else:
            key = secrets.token_bytes(32)
            os.makedirs(os.path.dirname(key_path), exist_ok=True)
            with open(key_path, 'wb') as f:
                f.write(key)
            return key

    app.config['SECRET_KEY'] = get_or_create_secret_key()

    with app_lock:
        if not os.path.exists('instance'):
            os.makedirs('instance')

        # 1. Initialize Database
        with db_lock:
            player_db = PlayerDatabase()

        # 2. Initialize ConfigManager with database reference
        config_manager = ConfigManager(player_db=player_db)
        config_manager.load_config()

        # 3. Initialize MessagingManager
        messaging_manager = MessagingManager(player_db=player_db, config_file='empyrion_helper.conf')

        # 4. Initialize BackgroundService
        background_service = BackgroundService(config_manager, player_db, messaging_manager)

        # 5. Start BackgroundService if credentials are available
        rcon_creds = player_db.get_rcon_credentials()
        if rcon_creds and rcon_creds.get('password'):
            logger.info("✅ RCON credentials found, starting background service.")
            background_service.start()
        else:
            logger.warning("⚠️ No RCON credentials. Background service will not start until configured via UI.")

    # Register cleanup function
    atexit.register(lambda: background_service.stop() if background_service else None)
    
    return app, socketio

@app.route('/')
def index():
    """
    Render the main page of the web interface.

    Returns:
        Response: Rendered HTML for the main page.
    """
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
    """
    Serve static files such as images, CSS, or JavaScript.

    Args:
        filename (str): The name of the static file to serve.

    Returns:
        Response: The static file response.
    """
    return send_from_directory('static', filename)

@app.route('/status')
def get_status():
    """
    Get the current status of the background service and connection.

    Returns:
        Response: JSON with status information.
    """
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
    """
    API endpoint to start the background service.

    Returns:
        Response: JSON indicating success or failure.
    """
    if not background_service:
        return jsonify({'success': False, 'message': 'Background service not initialized'})
    
    if background_service.is_running:
        return jsonify({'success': True, 'message': 'Background service already running'})
    
    rcon_creds = player_db.get_rcon_credentials()
    if rcon_creds and rcon_creds.get('password'):
        background_service.start()
        return jsonify({'success': True, 'message': 'Background service started successfully'})
    else:
        return jsonify({'success': False, 'message': 'Failed to start background service - check credentials'})

@app.route('/service/stop', methods=['POST'])
def stop_service():
    """
    API endpoint to stop the background service.

    Returns:
        Response: JSON indicating success or failure.
    """
    if not background_service:
        return jsonify({'success': False, 'message': 'Background service not initialized'})
    
    background_service.stop()
    return jsonify({'success': True, 'message': 'Background service stopped'})

# Legacy routes for backward compatibility (now just return status)
@app.route('/connect', methods=['POST'])
def connect():
    """
    Legacy API endpoint for connecting to the server (now managed by background service).

    Returns:
        Response: JSON indicating connection status.
    """
    if not background_service:
        return jsonify({'success': False, 'message': 'Background service not available'})
    
    status = background_service.get_connection_status()
    if status['is_connected']:
        return jsonify({'success': True, 'message': 'Already connected via background service'})
    else:
        return jsonify({'success': False, 'message': 'Connection managed by background service - check logs'})

@app.route('/disconnect', methods=['POST'])
def disconnect():
    """
    Legacy API endpoint for disconnecting from the server (now managed by background service).

    Returns:
        Response: JSON indicating disconnection status.
    """
    return jsonify({'success': True, 'message': 'Connection managed by background service'})

@app.route('/players', methods=['GET'])
def get_players():
    """
    Get the current list of players from the database.

    Returns:
        Response: JSON with player list and statistics.
    """
    if not player_db:
        return jsonify({'success': False, 'message': 'Database not initialized'})
    
    try:
        # Get players from database (updated by background service)
        players = player_db.get_all_players()
        
        logger.info(f"=== /players route returning {len(players)} players from database ===")
        return jsonify({'success': True, 'players': players})
        
    except Exception as e:
        logger.error(f"Error getting players: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An internal error occurred. Please try again later.'})

@app.route('/players/all', methods=['GET'])
def get_all_players():
    """
    Get all players from the database, with optional filtering.

    Returns:
        Response: JSON with all player records and statistics.
    """
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
        logger.error(f"Error getting all players: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An internal error occurred. Please try again later.'})

# Simplified messaging and other routes - keeping them but focusing on the main issue
@app.route('/messaging/send', methods=['POST'])
def send_global_message():
    """
    Send a global message to all players via the messaging manager.

    Returns:
        Response: JSON indicating success or failure.
    """
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
        
        if len(message) > 500:
            return jsonify({'success': False, 'message': 'Message too long (max 500 characters)'})
        
        success = messaging_manager.send_global_message(message, message_type='manual')
        
        if success:
            return jsonify({'success': True, 'message': 'Global message sent successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to send global message'})
            
    except Exception as e:
        logger.error(f"Error sending global message: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An internal error occurred. Please try again later.'})

# Additional routes would go here - keeping it simple for now

if __name__ == '__main__':
    app, socketio = create_app()
    logger.info("Starting Empyrion Web Helper server...")
    try:
        socketio.run(app, host='0.0.0.0', port=5001, allow_unsafe_werkzeug=True)
    except Exception as e:
        logger.error(f"Failed to start server: {e}", exc_info=True)

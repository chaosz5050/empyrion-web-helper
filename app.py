# FILE LOCATION: /app.py (root directory)
#!/usr/bin/env python3
"""
Empyrion Web Helper v0.4.1
A web-based admin tool for Empyrion Galactic Survival servers.

This Flask-based application provides a web interface for server administration, with
background service architecture for independent operation and robust error handling.
"""

from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit
import logging
import os
import re
import atexit

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

def get_or_create_secret_key(key_path='instance/ewh_secret.key'):
    """
    Retrieve or generate a persistent secret key for Flask session security.

    Args:
        key_path (str): Path to the secret key file.

    Returns:
        bytes: The secret key.
    """
    import secrets
    if os.path.exists(key_path):
        with open(key_path, 'rb') as f:
            return f.read()
    else:
        key = secrets.token_bytes(32)  # 256-bit key
        os.makedirs(os.path.dirname(key_path), exist_ok=True)
        with open(key_path, 'wb') as f:
            f.write(key)
        return key

app.config['SECRET_KEY'] = get_or_create_secret_key()
socketio = SocketIO(app, cors_allowed_origins="*")

# Global state - now managed by background service
background_service = None
config_manager = None
player_db = None
messaging_manager = None

def initialize_app():
    """
    Initialize the application and its core components.

    Sets up the player database, configuration manager, messaging manager, logging, and background service.
    Checks for required credentials and prepares the environment for operation.

    Returns:
        bool: True if initialization is successful and credentials are present, False otherwise.
    """
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
    """
    Start the background service if RCON credentials are available.

    Returns:
        bool: True if the background service was started successfully, False otherwise.
    """
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
    """
    Stop the background service if it is running.

    Returns:
        bool: True if the service was stopped, False otherwise.
    """
    """Stop the background service"""
    global background_service
    if background_service:
        background_service.stop()

# Only register cleanup for normal exit, not signals during development
def cleanup_on_exit():
    """
    Perform cleanup actions when the application exits.

    Ensures background services are stopped and resources are released.
    """
    """Clean shutdown handler for normal exit only"""
    logger.info("🛑 Application shutting down, stopping background service...")
    stop_background_service()
    
atexit.register(cleanup_on_exit)

@app.route('/')
@app.route('/')
def index():
    """
    Render the main page of the web interface.

    Returns:
        Response: Rendered HTML for the main page.
    """
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
@app.route('/static/<path:filename>')
def serve_static(filename):
    """
    Serve static files such as images, CSS, or JavaScript.

    Args:
        filename (str): The name of the static file to serve.

    Returns:
        Response: The static file response.
    """
    """Serve static files (like favicon)"""
    return send_from_directory('.', filename)

@app.route('/status')
@app.route('/status')
def get_status():
    """
    Get the current status of the background service and connection.

    Returns:
        Response: JSON with status information.
    """
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
@app.route('/service/start', methods=['POST'])
def start_service():
    """
    API endpoint to start the background service.

    Returns:
        Response: JSON indicating success or failure.
    """
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
@app.route('/service/stop', methods=['POST'])
def stop_service():
    """
    API endpoint to stop the background service.

    Returns:
        Response: JSON indicating success or failure.
    """
    """Stop the background service"""
    if not background_service:
        return jsonify({'success': False, 'message': 'Background service not initialized'})
    
    background_service.stop()
    return jsonify({'success': True, 'message': 'Background service stopped'})

# Legacy routes for backward compatibility (now just return status)
@app.route('/connect', methods=['POST'])
@app.route('/connect', methods=['POST'])
def connect():
    """
    Legacy API endpoint for connecting to the server (now managed by background service).

    Returns:
        Response: JSON indicating connection status.
    """
    """Legacy connect route - now managed by background service"""
    if not background_service:
        return jsonify({'success': False, 'message': 'Background service not available'})
    
    status = background_service.get_connection_status()
    if status['is_connected']:
        return jsonify({'success': True, 'message': 'Already connected via background service'})
    else:
        return jsonify({'success': False, 'message': 'Connection managed by background service - check logs'})

@app.route('/disconnect', methods=['POST'])
@app.route('/disconnect', methods=['POST'])
def disconnect():
    """
    Legacy API endpoint for disconnecting from the server (now managed by background service).

    Returns:
        Response: JSON indicating disconnection status.
    """
    """Legacy disconnect route - now managed by background service"""
    return jsonify({'success': True, 'message': 'Connection managed by background service'})

@app.route('/players')
@app.route('/players', methods=['GET'])
def get_players():
    """
    Get the current list of players from the database.

    Returns:
        Response: JSON with player list and statistics.
    """
    """Get current player list from database (no longer queries server directly)"""
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

@app.route('/players/all')
@app.route('/players/all', methods=['GET'])
def get_all_players():
    """
    Get all players from the database, with optional filtering.

    Returns:
        Response: JSON with all player records and statistics.
    """
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
        logger.error(f"Error getting all players: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An internal error occurred. Please try again later.'})

@app.route('/api/settings/monitoring', methods=['GET'])
def get_monitoring_settings():
    """Return current monitoring settings (update_interval) from the database."""
    val = player_db.get_app_setting('update_interval')
    try:
        val = int(val)
    except Exception:
        val = 20
    return jsonify({'update_interval': val})

@app.route('/api/settings/monitoring', methods=['POST'])
def set_monitoring_settings():
    """Set monitoring settings (update_interval) in the database, with validation."""
    data = request.get_json(force=True)
    interval = data.get('update_interval')
    try:
        interval = int(interval)
    except Exception:
        return jsonify({'success': False, 'error': 'Invalid update_interval'}), 400
    if interval < 10:
        return jsonify({'success': False, 'error': 'Update interval must be at least 10 seconds.'}), 400
    player_db.set_app_setting('update_interval', str(interval))
    return jsonify({'success': True, 'update_interval': interval})

# --- RESTORED API ENDPOINTS FOR FRONTEND INTEGRATION ---

@app.route('/entities', methods=['GET'])
def get_entities():
    """
    Placeholder endpoint for entities. Should return a list of entities (ships, bases, etc.).
    """
    # TODO: Replace with real entity data from database/service
    return jsonify({'success': True, 'entities': []})

@app.route('/messaging/custom', methods=['GET'])
def get_custom_messages():
    """
    Placeholder endpoint for custom messages. Should return a list of custom messages.
    """
    # TODO: Replace with real data
    return jsonify({'success': True, 'messages': []})

@app.route('/messaging/scheduled', methods=['GET'])
def get_scheduled_messages():
    """
    Placeholder endpoint for scheduled messages. Should return a list of scheduled messages.
    """
    # TODO: Replace with real data
    return jsonify({'success': True, 'messages': []})

@app.route('/messaging/history', methods=['GET'])
def get_message_history():
    """
    Placeholder endpoint for message history. Should return recent message history.
    """
    # TODO: Replace with real data
    return jsonify({'success': True, 'history': []})

@app.route('/logging/stats', methods=['GET'])
def get_logging_stats():
    """
    Placeholder endpoint for logging stats. Should return stats about logs.
    """
    # TODO: Replace with real data
    return jsonify({'success': True, 'stats': {}})

@app.route('/logging/recent', methods=['GET'])
def get_recent_logs():
    """
    Placeholder endpoint for recent logs. Should return recent log entries.
    """
    # TODO: Replace with real data
    return jsonify({'success': True, 'logs': []})

@app.route('/logging/settings', methods=['GET'])
def get_logging_settings():
    """
    Placeholder endpoint for logging settings. Should return log configuration/settings.
    """
    # TODO: Replace with real data
    return jsonify({'success': True, 'settings': {}})

# Simplified messaging and other routes - keeping them but focusing on the main issue
@app.route('/messaging/send', methods=['POST'])
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
        
        success = messaging_manager.send_global_message(message, message_type='manual')
        
        if success:
            return jsonify({'success': True, 'message': 'Global message sent successfully'})
        else:
            return jsonify({'success': False, 'message': 'An internal error occurred. Please try again later.'})
            return jsonify({'success': False, 'message': 'Failed to send global message'})
            
    except Exception as e:
        logger.error(f"Error sending global message: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An internal error occurred. Please try again later.'})

@app.route('/api/credentials/status', methods=['GET'])
def api_credential_status():
    """
    Returns JSON indicating whether all required credentials and connection info are present in the database.
    """
    rcon_creds = player_db.get_credential('rcon')
    ftp_creds = player_db.get_credential('ftp')
    server_host = player_db.get_app_setting('server_host')
    server_port = player_db.get_app_setting('server_port')
    ftp_host = player_db.get_app_setting('ftp_host')
    ftp_remote_log_path = player_db.get_app_setting('ftp_remote_log_path')
    status = {
        'rcon': bool(rcon_creds and rcon_creds.get('password')),
        'ftp': bool(ftp_creds and ftp_creds.get('password') and ftp_creds.get('username')),
        'server_host': bool(server_host),
        'server_port': bool(server_port),
        'ftp_host': bool(ftp_host),
        'ftp_remote_log_path': bool(ftp_remote_log_path)
    }
    return jsonify(status)


@app.route('/api/credentials/set', methods=['POST'])
def api_set_credentials():
    """
    Accepts JSON with RCON, FTP, server, and FTP connection info and stores them securely in the database.
    """
    data = request.get_json(force=True)
    errors = {}
    updated = []

    # RCON
    rcon_pw = data.get('rcon_password')
    if rcon_pw is not None:
        if not isinstance(rcon_pw, str) or len(rcon_pw.strip()) < 4:
            errors['rcon'] = 'RCON password must be at least 4 characters.'
        else:
            player_db.store_credential('rcon', password=rcon_pw.strip())
            updated.append('rcon')

    # FTP
    ftp_user = data.get('ftp_user')
    ftp_pw = data.get('ftp_password')
    if ftp_user is not None or ftp_pw is not None:
        if not ftp_user or not isinstance(ftp_user, str) or len(ftp_user.strip()) < 3:
            errors['ftp_user'] = 'FTP username must be at least 3 characters.'
        if not ftp_pw or not isinstance(ftp_pw, str) or len(ftp_pw.strip()) < 4:
            errors['ftp_password'] = 'FTP password must be at least 4 characters.'
        if not errors.get('ftp_user') and not errors.get('ftp_password'):
            player_db.store_credential('ftp', username=ftp_user.strip(), password=ftp_pw.strip())
            updated.append('ftp')

    # SERVER HOST/PORT
    server_host = data.get('server_host')
    server_port = data.get('server_port')
    if server_host is not None:
        if not isinstance(server_host, str) or not server_host.strip():
            errors['server_host'] = 'Server host is required.'
        else:
            player_db.set_app_setting('server_host', server_host.strip())
            updated.append('server_host')
    if server_port is not None:
        try:
            port_val = int(server_port)
            if not (1 <= port_val <= 65535):
                raise ValueError
            player_db.set_app_setting('server_port', str(port_val))
            updated.append('server_port')
        except Exception:
            errors['server_port'] = 'Server port must be a number between 1 and 65535.'

    # FTP HOST/REMOTE LOG PATH
    ftp_host = data.get('ftp_host')
    ftp_remote_log_path = data.get('ftp_remote_log_path')
    if ftp_host is not None:
        if not isinstance(ftp_host, str) or not ftp_host.strip():
            errors['ftp_host'] = 'FTP host is required.'
        else:
            player_db.set_app_setting('ftp_host', ftp_host.strip())
            updated.append('ftp_host')
    if ftp_remote_log_path is not None:
        if not isinstance(ftp_remote_log_path, str) or not ftp_remote_log_path.strip():
            errors['ftp_remote_log_path'] = 'FTP remote log path is required.'
        else:
            player_db.set_app_setting('ftp_remote_log_path', ftp_remote_log_path.strip())
            updated.append('ftp_remote_log_path')

    if errors:
        return jsonify({'success': False, 'errors': errors}), 400
    return jsonify({'success': True, 'updated': updated})


if __name__ == '__main__':
    # Initialize the application
    logger.info("🚀 Starting Empyrion Web Helper v0.4.1...")
    
    init_success = initialize_app()
    
    if init_success:
        # AUTO-START: Check if we have credentials to start automatically
        rcon_creds = player_db.get_rcon_credentials()
        if rcon_creds and rcon_creds.get('password'):
            logger.info("🔑 RCON credentials found - starting background service automatically")
            service_started = start_background_service()
            if service_started:
                logger.info("🚀 Background service started successfully - operating headless!")

                # --- One-time, silent geolocation refresh after service start ---
                import threading
                def silent_geo_refresh():
                    logger.info("🌍 Running one-time geolocation refresh for players with missing country data...")
                    try:
                        updated_count = player_db.refresh_geolocation_for_existing_players()
                        if updated_count > 0:
                            logger.info(f"🌍 Geolocation updated for {updated_count} players. Notifying frontend.")
                            socketio.emit('players_updated', {'reason': 'geo_refresh'})
                        else:
                            logger.info("🌍 No player geolocations needed updating.")
                    except Exception as e:
                        logger.error(f"Error during silent geolocation refresh: {e}")
                # Run in background so web UI is not blocked
                threading.Thread(target=silent_geo_refresh, daemon=True).start()
            else:
                logger.error("❌ Failed to start background service")
        else:
            logger.warning("⚠️ No RCON credentials found")
            logger.info("💡 Configure credentials via web interface and restart")
    else:
        logger.error("❌ Application initialization failed")
    
    # Get local IP for network access
    import socket
    
    def get_local_ip():
        """
        Get the local network IP address for displaying network access info.

        Returns:
            str: The detected local IP address, or '0.0.0.0' if unavailable.
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
            
            if local_ip.startswith('127.'):
                raise Exception("Got localhost IP")
                
            return local_ip
            
        except Exception:
            return '0.0.0.0'
    
    local_ip = get_local_ip()
    
    logger.info("🌐 Web interface starting...")
    logger.info(f"🌐 Local access: http://localhost:5001")
    if local_ip != '0.0.0.0':
        logger.info(f"🌐 Network access: http://{local_ip}:5001")
    
    try:
        # Run Flask development server
        socketio.run(app, 
                    host='0.0.0.0', 
                    port=5001, 
                    debug=False,
                    allow_unsafe_werkzeug=True)
    except KeyboardInterrupt:
        logger.info("🛑 Received Ctrl+C, shutting down...")
        stop_background_service()
    except Exception as e:
        logger.error(f"❌ Server error: {e}")
        stop_background_service()
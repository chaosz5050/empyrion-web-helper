# FILE LOCATION: /app.py (root directory)
#!/usr/bin/env python3
"""
Empyrion Web Helper v0.5.2
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
from datetime import datetime

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
    
    logger.info("Empyrion Web Helper v0.5.1 initialized with background service architecture")
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

@app.route('/players/purge', methods=['POST'])
def purge_old_players():
    """
    Purge old player data from the database.
    
    Removes players with no last_seen data or who haven't been seen in the last 14 days.
    
    Returns:
        Response: JSON with success status and count of deleted players.
    """
    if not player_db:
        return jsonify({'success': False, 'message': 'Database not initialized'})
    
    try:
        logger.info("Player data purge requested")
        
        # Call the database purge method with 14-day threshold
        result = player_db.purge_old_players(days_threshold=14)
        
        if result['success']:
            logger.info(f"Player purge completed: {result['deleted_count']} players removed")
            return jsonify({
                'success': True,
                'message': result['message'],
                'deleted_count': result['deleted_count']
            })
        else:
            logger.error(f"Player purge failed: {result['message']}")
            return jsonify({
                'success': False,
                'message': result['message']
            })
            
    except Exception as e:
        logger.error(f"Error purging old players: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An internal error occurred while purging player data'})

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

# App Settings API endpoints
@app.route('/api/settings/<setting_key>', methods=['GET'])
def get_app_setting(setting_key):
    """Get a specific app setting from the database."""
    if not player_db:
        return jsonify({'success': False, 'message': 'Database not initialized'}), 500
    
    try:
        value = player_db.get_app_setting(setting_key)
        return jsonify({'success': True, 'value': value})
    except Exception as e:
        logger.error(f"Error getting app setting {setting_key}: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An internal error occurred. Please try again later.'}), 500

@app.route('/api/settings/<setting_key>', methods=['POST'])
def set_app_setting(setting_key):
    """Set a specific app setting in the database."""
    if not player_db:
        return jsonify({'success': False, 'message': 'Database not initialized'}), 500
    
    try:
        data = request.get_json(force=True)
        value = data.get('value')
        
        if value is None:
            return jsonify({'success': False, 'message': 'Value is required'}), 400
        
        success = player_db.set_app_setting(setting_key, str(value))
        
        if success:
            return jsonify({'success': True, 'value': value})
        else:
            return jsonify({'success': False, 'message': 'Failed to save setting'}), 500
            
    except Exception as e:
        logger.error(f"Error setting app setting {setting_key}: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An internal error occurred. Please try again later.'}), 500

# Test endpoints for connection testing
@app.route('/api/test/rcon', methods=['POST'])
def test_rcon_connection():
    """Test RCON connection with real connectivity check."""
    try:
        data = request.get_json(force=True)
        host = data.get('host', '').strip()
        port_str = data.get('port', '30004')
        password = data.get('password', '').strip()
        
        if not host:
            return jsonify({'success': False, 'message': 'Server host is required'})
        
        if not password:
            return jsonify({'success': False, 'message': 'RCON password is required'})
            
        try:
            port = int(port_str)
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': 'Invalid port number'})
        
        # Import here to avoid circular imports
        from connection import EmpyrionConnection
        
        # Create temporary connection for testing
        logger.info(f"Testing RCON connection to {host}:{port}")
        test_conn = EmpyrionConnection(host=host, port=port, password=password, timeout=10)
        
        # Attempt connection
        result = test_conn.connect()
        
        if result is True:
            # Test with a simple command
            help_result = test_conn.send_command("help", timeout=5.0)
            test_conn.disconnect()
            
            if help_result and ("Available commands" in help_result or "help" in help_result.lower()):
                logger.info(f"✅ RCON test successful to {host}:{port}")
                return jsonify({
                    'success': True, 
                    'message': f'✅ RCON connection successful to {host}:{port}',
                    'details': 'Authentication and command execution working properly'
                })
            else:
                logger.warning(f"RCON connected but help command failed to {host}:{port}")
                return jsonify({
                    'success': True, 
                    'message': f'⚠️ RCON connected to {host}:{port} but command test failed',
                    'details': 'Connection works but server may not be responding to commands'
                })
        else:
            test_conn.disconnect()
            error_msg = result.get('message', 'Connection failed') if isinstance(result, dict) else 'Connection failed'
            logger.warning(f"❌ RCON test failed to {host}:{port}: {error_msg}")
            return jsonify({
                'success': False, 
                'message': f'❌ RCON connection failed to {host}:{port}',
                'details': error_msg
            })
            
    except Exception as e:
        logger.error(f"Error testing RCON connection: {e}", exc_info=True)
        return jsonify({
            'success': False, 
            'message': 'Connection test failed due to internal error',
            'details': 'Check logs for more details'
        })

@app.route('/api/test/ftp', methods=['POST'])
def test_ftp_connection():
    """Test FTP/SFTP connection with automatic detection and enhanced compatibility."""
    try:
        from connection_manager import EnhancedConnectionManager, UniversalFileClient
        
        data = request.get_json(force=True)
        host_port = data.get('host', '').strip()
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        if not host_port:
            return jsonify({'success': False, 'message': 'Server host is required'})
            
        # Parse host and port
        if ':' in host_port:
            host, port_str = host_port.split(':', 1)
            try:
                port = int(port_str)
            except ValueError:
                return jsonify({'success': False, 'message': 'Invalid port in server host'})
        else:
            host = host_port
            # Try common ports for auto-detection
            port = 22  # Default to SFTP port, will try FTP (21) as fallback
        
        if not username or not password:
            return jsonify({'success': False, 'message': 'Username and password are required'})
        
        logger.info(f"🔍 Testing connection to {host}:{port} with auto-detection")
        
        # Use enhanced connection manager for auto-detection
        manager = EnhancedConnectionManager()
        result = manager.detect_and_connect(host, port, username, password)
        
        if result.success:
            logger.info(f"✅ {result.connection_type.upper()} connection successful to {host}:{port}")
            
            # Record successful test in database
            player_db.set_ftp_test_success()
            
            # Create detailed success message
            connection_details = []
            if result.details:
                if 'files_found' in result.details:
                    connection_details.append(f"Found {result.details['files_found']} items in root directory")
                if result.details.get('supports_certificates'):
                    connection_details.append("Certificate handling supported")
                if result.details.get('ssl_enabled'):
                    connection_details.append("SSL/TLS encryption enabled")
            
            details_text = '; '.join(connection_details) if connection_details else 'Connection established successfully'
            
            return jsonify({
                'success': True,
                'message': f'✅ {result.connection_type.upper()} connection successful to {host}:{port}',
                'details': details_text,
                'connection_type': result.connection_type,
                'supports_certificates': result.details.get('supports_certificates', False),
                'ssl_enabled': result.details.get('ssl_enabled', False)
            })
        else:
            logger.warning(f"❌ All connection types failed to {host}:{port}: {result.message}")
            
            # Provide helpful error message based on common issues
            error_message = result.message
            helpful_details = "Try checking: 1) Server address and port, 2) Username and password, 3) Firewall settings"
            
            if "timeout" in result.message.lower():
                helpful_details = "Connection timeout - check if server is reachable and port is correct"
            elif "authentication" in result.message.lower():
                helpful_details = "Authentication failed - verify username and password are correct"
            elif "certificate" in result.message.lower():
                helpful_details = "Certificate issue - this is automatically handled for SFTP connections"
            
            return jsonify({
                'success': False,
                'message': f'❌ Connection failed to {host}:{port}',
                'details': f'{error_message}. {helpful_details}',
                'connection_type': None
            })
            
    except Exception as e:
        logger.error(f"Error testing connection: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': 'Connection test failed due to internal error',
            'details': f'Error: {str(e)}. Check logs for more details'
        })

@app.route('/api/ftp/status', methods=['GET'])
def get_ftp_status():
    """Get smart FTP status with progressive states."""
    try:
        # Check if credentials are configured
        credentials = player_db.get_ftp_credentials()
        if not credentials:
            return jsonify({
                'status': 'not_configured',
                'message': '❌ Not configured',
                'color': 'var(--accent-red)',
                'tooltip': 'FTP credentials not configured'
            })
        
        # Check if FTP has been successfully tested
        test_status = player_db.get_ftp_test_status()
        if test_status == 'success':
            # Get host for tooltip
            host = player_db.get_app_setting('ftp_host', 'Unknown')
            return jsonify({
                'status': 'available',
                'message': '✅ Available',
                'color': 'var(--accent-green)',
                'tooltip': f'FTP available on {host}'
            })
        else:
            return jsonify({
                'status': 'test_ftp',
                'message': '🔧 Test FTP',
                'color': 'var(--accent-orange)',
                'tooltip': 'FTP configured but not tested - click Settings to test'
            })
            
    except Exception as e:
        logger.error(f"Error getting FTP status: {e}")
        return jsonify({
            'status': 'error',
            'message': '❓ Error',
            'color': 'var(--text-secondary)',
            'tooltip': 'Unable to check FTP status'
        })

# --- RESTORED API ENDPOINTS FOR FRONTEND INTEGRATION ---

@app.route('/entities', methods=['GET'])
def get_entities():
    """
    Get cached entities from database.
    """
    if not player_db:
        return jsonify({'success': False, 'message': 'Database not initialized'})
    
    try:
        result = player_db.get_entities()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting entities: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An internal error occurred. Please try again later.'})

@app.route('/entities/refresh', methods=['POST'])
def refresh_entities():
    """
    Refresh entities from the Empyrion server using 'gents' command.
    """
    global background_service
    
    logger.info("Entities refresh requested")
    
    if not background_service:
        logger.error("Background service not initialized")
        return jsonify({'success': False, 'message': 'Background service not initialized'})
    
    try:
        # Get the connection from background service
        connection = background_service.get_connection_handler()
        logger.info(f"Connection status: {connection is not None}, Alive: {connection.is_connection_alive() if connection else 'N/A'}")
        
        if not connection:
            logger.error("No connection available from background service")
            return jsonify({'success': False, 'message': 'No connection available from background service'})
            
        if not connection.is_connection_alive():
            logger.error("Not connected to Empyrion server")
            return jsonify({'success': False, 'message': 'Not connected to Empyrion server'})
        
        logger.info("Refreshing entities from server using 'gents' command")
        
        # Send 'gents' command to get entity list
        response = connection.send_command('gents')
        
        if not response:
            logger.error("No response from 'gents' command")
            return jsonify({'success': False, 'message': 'No response from gents command'})
        
        # Handle error dict response
        if isinstance(response, dict) and not response.get('success', True):
            error_msg = response.get('message', 'Failed to execute gents command')
            logger.error(f"Failed to get entity list: {error_msg}")
            return jsonify({'success': False, 'message': f'Failed to get entity list: {error_msg}'})
        
        # Response should be a string with the gents output
        raw_data = response if isinstance(response, str) else str(response)
        logger.info(f"Received entity data: {len(raw_data)} characters")
        
        # Parse the entity data using the Empyrion gents format
        entities = []
        current_playfield = ''
        
        if raw_data:
            lines = raw_data.strip().split('\n')
            for line in lines:
                line_stripped = line.strip()
                
                # Skip empty lines or command responses
                if not line_stripped or line_stripped.startswith('gents:') or line_stripped.startswith('No'):
                    continue
                
                # Check if this is a playfield header (no leading spaces, not an entity line)
                if not line.startswith('  ') and not line_stripped.startswith(tuple('0123456789')):
                    current_playfield = line_stripped
                    logger.debug(f"Found playfield: {current_playfield}")
                    continue
                
                # Parse entity lines (start with "  XX. ")
                if line.startswith('  ') and '. ' in line:
                    try:
                        # Format: "  01. 051001 BA [Zrx] False False 'Drone Base' (-)"
                        parts = line_stripped.split(' ', 6)  # Split into max 7 parts
                        if len(parts) >= 7:
                            # Extract components
                            num_part = parts[0].rstrip('.')  # "01"
                            entity_id = parts[1]  # "051001"
                            entity_type = parts[2]  # "BA", "HV", "SV", "CV"
                            faction_part = parts[3]  # "[Zrx]"
                            # Skip parts[4] and parts[5] (boolean flags)
                            name_and_time = parts[6]  # "'Drone Base' (-)"
                            
                            # Extract faction (remove brackets)
                            faction = faction_part.strip('[]') if faction_part.startswith('[') else ''
                            
                            # Extract name and time from the last part
                            name = ''
                            time_info = ''
                            if "'" in name_and_time:
                                # Split by quotes to get name
                                quote_parts = name_and_time.split("'")
                                if len(quote_parts) >= 2:
                                    name = quote_parts[1]
                                    # Get time info (everything after the name)
                                    remaining = "'".join(quote_parts[2:])
                                    if '(' in remaining and ')' in remaining:
                                        time_info = remaining[remaining.find('(')+1:remaining.find(')')]
                            
                            entity = {
                                'id': entity_id,
                                'name': name,
                                'type': entity_type,
                                'faction': faction,
                                'playfield': current_playfield,
                                'time_info': time_info
                            }
                            entities.append(entity)
                            logger.debug(f"Parsed entity: {entity}")
                            
                    except Exception as e:
                        logger.warning(f"Failed to parse entity line: '{line_stripped}' - {e}")
                        continue
        
        # Update timestamp
        from datetime import datetime
        last_refresh = datetime.now().isoformat()
        
        logger.info(f"Parsed {len(entities)} entities from server")
        
        # Save entities to database
        if player_db:
            saved = player_db.save_entities(entities, raw_data)
            if not saved:
                logger.warning("Failed to save entities to database")
        else:
            logger.warning("Database not available - entities not saved")
        
        # Calculate detailed stats
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
        
        return jsonify({
            'success': True,
            'entities': entities,
            'raw_data': raw_data,
            'last_refresh': last_refresh,
            'stats': stats,
            'updated_count': len(entities)
        })
        
    except Exception as e:
        logger.error(f"Error refreshing entities: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An internal error occurred. Please try again later.'})

@app.route('/entities/clear', methods=['POST'])
def clear_entities():
    """
    Clear all entities from the database.
    """
    if not player_db:
        return jsonify({'success': False, 'message': 'Database not initialized'})
    
    try:
        success = player_db.clear_entities()
        if success:
            logger.info("All entities cleared from database")
            return jsonify({'success': True, 'message': 'All entities cleared successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to clear entities'})
    except Exception as e:
        logger.error(f"Error clearing entities: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An internal error occurred. Please try again later.'})

# ===============================
# Player Structure Detection (Test)
# ===============================

# DEFINITIVE NPC faction codes from Factions.ecf (IDs 1-99)
NPC_FACTIONS = {
    # Hardcoded Core Factions (IDs 1-8)
    'Pub': 'Public',           # ID 1
    'Zrx': 'Zirax',           # ID 2 
    'Prd': 'Predator',        # ID 3
    'Pry': 'Prey',            # ID 4
    'Adm': 'Admin',           # ID 5
    'Tal': 'Talon',           # ID 6 - Main Story Faction
    'Pol': 'Polaris',         # ID 7 - Main Story Faction (Arkenian Republic)
    'Aln': 'Alien',           # ID 8
    
    # Custom Static Factions (IDs 9-40)
    'DSC': 'DESC',            # ID 9
    'Lgc': 'TheLegacy',       # ID 10 - Main Story Faction
    'Prg': 'Progenitor',      # ID 12 - Main Story Faction
    'Voi': 'Void',            # ID 13 - Main Story Faction
    'GLD': 'GLaD',            # ID 14 - Main Story Faction
    'Civ': 'Civilian',        # ID 15
    'War': 'Warlord',         # ID 27
    'NTY': 'NTY',             # ID 31
    'HIS': 'Hishkal',         # ID 32
    'DRK': 'DarkFaction',     # ID 40
    
    # Custom Dynamic Factions (IDs 11, 16-30, 33-38)
    'UCH': 'UCH',             # ID 11 - Main Story Faction
    'Pir': 'Pirates',         # ID 16
    'Kri': 'Kriel',           # ID 17
    'Tra': 'Trader',          # ID 18 - Main Story Faction (Prenn Trading Federation)
    'Col': 'Colonists',       # ID 19
    'Tsc': 'Tesch',           # ID 20
    'BoF': 'Farr',            # ID 28 - Brotherhood of Farr
    'WST': 'Wastelanders',    # ID 29
    'ARC': 'ARC',             # ID 30
    'Ark': 'ArkenianRepublic', # ID 33
    'Pre': 'PrennFederation', # ID 34
    'HLS': 'Helios',          # ID 35
    'RAV': 'Ravagers',        # ID 36
    'KRN': 'Karana',          # ID 37
    'TRS': 'Tresari',         # ID 38
    
    # Zirax Sub-Factions (IDs 21-26)
    'Xen': 'Xenu',            # ID 21 - Zirax Empire Military
    'Rad': 'Rados',           # ID 22 - Zirax Empire Support
    'Eps': 'Epsilon',         # ID 23 - Zirax Empire Communication  
    'Ghy': 'Ghyst',           # ID 24 - Zirax Empire Recon
    'Ser': 'Serdu',           # ID 25 - Zirax Empire Religion
    'Aby': 'Abyssal',         # ID 26 - Zirax Empire Science
    
    # Special Factions (IDs 39, 41)
    'PDH': 'PlayerAssist',    # ID 39
    'STR': 'STRY',            # ID 41 - Dynamic story faction
    
    # Star Salvage Scenario-Specific NPC Factions (Custom IDs)
    'Gst': 'GhostShip',       # Custom faction
    'Mys': 'Mystery',         # Custom faction  
    'Slv': 'Salvage',         # Custom faction
    'Isi': 'Interspace',      # ID 36 - Interspace Salvage Industries
    'UEF': 'UEF',             # ID 37 - United Earth Fleet
    'AJS': 'AJS',             # Custom faction (likely NPC based on ID pattern)
    'SAS': 'SAS',             # Custom faction
}

NEUTRAL_FACTIONS = {'NoF'}  # No Faction - abandoned/neutral

def classify_entity_faction(faction):
    """Classify an entity's faction as NPC, Player, or Neutral"""
    if faction in NPC_FACTIONS:
        return 'NPC', NPC_FACTIONS[faction]
    elif faction in NEUTRAL_FACTIONS:
        return 'Neutral', 'Abandoned/No Faction'
    elif faction.isdigit():
        return 'Player', f'Player Faction {faction}'
    elif faction == '':
        return 'Player', 'Private/No Faction'
    else:
        # Based on Factions.ecf rule: "The id must be < 100 else a player faction will be created!"
        # Unknown 3-letter codes are likely player factions (ID 100+)
        return 'Player', f'Player Faction: {faction}'

@app.route('/api/test/regenerate-2015', methods=['POST'])
def test_regenerate_2015():
    """Test regeneration of entity ID 2015 using remoteex regenerate command."""
    logger.info("Test regeneration of entity 2015 requested")
    
    try:
        # Check if background service is available and connected
        if not background_service:
            return jsonify({
                'success': False,
                'message': 'Background service not available'
            })
        
        connection_handler = background_service.get_connection_handler()
        if not connection_handler or not connection_handler.is_connection_alive():
            return jsonify({
                'success': False,
                'message': 'Not connected to server'
            })
        
        # First get playfield server info to find the PID for 'Mard Orntell'
        servers_command = "servers"
        logger.info(f"Getting playfield server info: {servers_command}")
        
        servers_result = connection_handler.send_command(servers_command)
        if not servers_result:
            return jsonify({
                'success': False,
                'message': 'Failed to get playfield server information'
            })
        
        # Parse servers output to find PID for 'Mard Orntell'
        playfield_pid = None
        for line in servers_result.split('\n'):
            if "'Mard Orntell'" in line:
                # Look for PID in previous lines or current context
                lines = servers_result.split('\n')
                for i, server_line in enumerate(lines):
                    if "'Mard Orntell'" in server_line:
                        # Look backwards for PID line
                        for j in range(i-1, max(i-5, -1), -1):
                            if 'PID:' in lines[j]:
                                pid_part = lines[j].split('PID:')[1].strip()
                                playfield_pid = pid_part.split()[0]  # Get first part before any spaces
                                break
                        break
                break
        
        if not playfield_pid:
            return jsonify({
                'success': False,
                'message': f'Could not find PID for playfield "Mard Orntell" in servers output: {servers_result}'
            })
        
        # Send remoteex regenerate command using the found PID
        regenerate_command = f"remoteex pf={playfield_pid} regenerate 2015"
        logger.info(f"Executing RCON command: {regenerate_command}")
        
        result = connection_handler.send_command(regenerate_command)
        
        if result and isinstance(result, str):
            logger.info(f"Test regenerate command result: {result}")
            return jsonify({
                'success': True,
                'message': 'Entity 2015 regeneration command sent successfully',
                'server_response': result.strip(),
                'command': regenerate_command
            })
        else:
            logger.warning(f"Unexpected result from test regenerate command: {result}")
            return jsonify({
                'success': False,
                'message': 'No response from server or command failed',
                'command': regenerate_command
            })
        
    except Exception as e:
        logger.error(f"Error in test regeneration: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': 'An internal error occurred during test regeneration'
        })

@app.route('/api/test/active-playfields', methods=['GET'])
def get_active_playfields():
    """Get active playfields with entity counts for selective regeneration"""
    if not background_service:
        return jsonify({'success': False, 'message': 'Background service not available'})
    
    try:
        connection_handler = background_service.get_connection_handler()
        if not connection_handler or not connection_handler.is_connection_alive():
            return jsonify({'success': False, 'message': 'Not connected to server'})
        
        # Get active playfield servers
        servers_result = connection_handler.send_command("servers")
        if not servers_result:
            return jsonify({'success': False, 'message': 'Failed to get server information'})
        
        # Parse servers output to extract playfields and PIDs
        playfields = []
        lines = servers_result.split('\n')
        current_pid = None
        
        for line in lines:
            line = line.strip()
            if 'PID:' in line:
                current_pid = line.split('PID:')[1].strip().split()[0]
            elif line.startswith("*'") and line.endswith("'"):
                # Extract playfield name
                playfield_name = line[2:-1]  # Remove *' and '
                if current_pid:
                    playfields.append({
                        'name': playfield_name,
                        'pid': current_pid
                    })
        
        # Get entity data and classify by playfield
        entities_response = player_db.get_entities()
        if not entities_response.get('success'):
            return jsonify({'success': False, 'message': 'Failed to retrieve entities from database'})
        
        entities = entities_response.get('entities', [])
        
        # Calculate entity counts per playfield
        playfield_stats = {}
        for entity in entities:
            playfield = entity.get('playfield', 'Unknown')
            faction = entity.get('faction', '')
            
            if playfield not in playfield_stats:
                playfield_stats[playfield] = {
                    'npc_count': 0,
                    'player_count': 0,
                    'neutral_count': 0,
                    'total_count': 0
                }
            
            # Classify entity
            category, _ = classify_entity_faction(faction)
            playfield_stats[playfield]['total_count'] += 1
            
            if category == 'NPC':
                playfield_stats[playfield]['npc_count'] += 1
            elif category == 'Player':
                playfield_stats[playfield]['player_count'] += 1
            else:
                playfield_stats[playfield]['neutral_count'] += 1
        
        # Debug logging
        logger.info(f"Parsed playfields from servers: {[pf['name'] for pf in playfields]}")
        logger.info(f"Playfields with entity stats: {list(playfield_stats.keys())}")
        logger.info(f"Total entities processed: {len(entities)}")
        
        # Merge playfield info with statistics
        result_playfields = []
        for pf in playfields:
            pf_name = pf['name']
            
            # Try exact match first
            stats = playfield_stats.get(pf_name, None)
            
            # If no exact match, try with "(loaded)" suffix
            if stats is None:
                loaded_name = f"{pf_name} (loaded)"
                stats = playfield_stats.get(loaded_name, {
                    'npc_count': 0,
                    'player_count': 0,
                    'neutral_count': 0,
                    'total_count': 0
                })
                if stats['total_count'] > 0:
                    logger.info(f"Found entities for '{pf_name}' using loaded name '{loaded_name}'")
            
            logger.info(f"Playfield '{pf_name}' final stats: {stats}")
            
            result_playfields.append({
                'name': pf_name,
                'pid': pf['pid'],
                'npc_count': stats['npc_count'],
                'player_count': stats['player_count'],
                'neutral_count': stats['neutral_count'],
                'total_count': stats['total_count']
            })
        
        logger.info(f"Found {len(result_playfields)} active playfields")
        
        return jsonify({
            'success': True,
            'playfields': result_playfields,
            'total_active_playfields': len(result_playfields),
            'raw_servers_output': servers_result
        })
        
    except Exception as e:
        logger.error(f"Error getting active playfields: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': 'Failed to get active playfields'
        })

@app.route('/api/test/bulk-regenerate-stream', methods=['GET'])
def bulk_regenerate_stream():
    """Stream bulk regeneration progress using Server-Sent Events"""
    import json
    import time
    from flask import Response
    
    if not background_service:
        return jsonify({'success': False, 'message': 'Background service not available'})
    
    # Get playfields from query parameter
    playfields_param = request.args.get('playfields', '[]')
    try:
        selected_playfields = json.loads(playfields_param)
    except:
        return jsonify({'success': False, 'message': 'Invalid playfields parameter'})
    
    if not selected_playfields:
        return jsonify({'success': False, 'message': 'No playfields selected'})
    
    def generate_progress():
        try:
            connection_handler = background_service.get_connection_handler()
            if not connection_handler or not connection_handler.is_connection_alive():
                yield f"data: {json.dumps({'type': 'error', 'message': 'Not connected to server'})}\n\n"
                return
            
            logger.info(f"Starting streaming bulk regeneration for playfields: {selected_playfields}")
            
            # Get active playfield PIDs - same logic as bulk_regenerate_npc_entities
            servers_result = connection_handler.send_command("servers")
            if not servers_result:
                yield f"data: {json.dumps({'type': 'error', 'message': 'Failed to get server information'})}\n\n"
                return
            
            # Parse PIDs for selected playfields
            playfield_pids = {}
            lines = servers_result.split('\n')
            
            for i, line in enumerate(lines):
                line = line.strip()
                if line.startswith("*'") and line.endswith("'"):
                    playfield_name = line[2:-1]
                    if playfield_name in selected_playfields:
                        for j in range(i-1, max(i-10, -1), -1):
                            prev_line = lines[j].strip()
                            if 'PID:' in prev_line:
                                pid = prev_line.split('PID:')[1].strip().split()[0]
                                playfield_pids[playfield_name] = pid
                                break
            
            # Get entities - same logic as bulk_regenerate_npc_entities
            entities_response = player_db.get_entities()
            if not entities_response.get('success') or len(entities_response.get('entities', [])) == 0:
                logger.info("Database is empty or failed, fetching live entity data from server...")
                live_entities = connection_handler.get_entities()
                if not live_entities:
                    yield f"data: {json.dumps({'type': 'error', 'message': 'Failed to retrieve live entity data from server'})}\n\n"
                    return
                entities = live_entities
            else:
                entities = entities_response.get('entities', [])
            
            entities_to_regenerate = []
            
            for entity in entities:
                entity_playfield = entity.get('playfield', '')
                
                # Check if entity is on a selected playfield
                is_on_selected_playfield = False
                for selected_pf in selected_playfields:
                    if entity_playfield == selected_pf or entity_playfield == f"{selected_pf} (loaded)":
                        is_on_selected_playfield = True
                        break
                
                if not is_on_selected_playfield:
                    continue
                
                # Classify entity faction
                faction = entity.get('faction', '')
                category, description = classify_entity_faction(faction)
                
                # Only regenerate NPC and Neutral entities
                if category in ['NPC', 'Neutral']:
                    # Find the PID for this entity's playfield
                    entity_pid = None
                    for selected_pf in selected_playfields:
                        if entity_playfield == selected_pf or entity_playfield == f"{selected_pf} (loaded)":
                            entity_pid = playfield_pids.get(selected_pf)
                            break
                    
                    if entity_pid:
                        entities_to_regenerate.append({
                            'id': entity.get('id'),
                            'name': entity.get('name'),
                            'playfield': entity_playfield,
                            'pid': entity_pid,
                            'faction': faction,
                            'faction_description': description
                        })
            
            total_entities = len(entities_to_regenerate)
            
            # Send start event
            yield f"data: {json.dumps({'type': 'start', 'total': total_entities})}\n\n"
            
            if total_entities == 0:
                yield f"data: {json.dumps({'type': 'complete', 'regenerated_count': 0, 'failed_count': 0, 'total_processed': 0})}\n\n"
                return
            
            # Process entities with streaming progress
            successful_count = 0
            failed_count = 0
            start_time = time.time()
            
            for i, entity in enumerate(entities_to_regenerate):
                try:
                    regenerate_command = f"remoteex pf={entity['pid']} regenerate {entity['id']}"
                    
                    result = connection_handler.send_command(regenerate_command)
                    
                    current = i + 1
                    success = bool(result and isinstance(result, str))
                    
                    if success:
                        successful_count += 1
                    else:
                        failed_count += 1
                    
                    # Calculate ETA
                    elapsed = time.time() - start_time
                    avg_time_per_entity = elapsed / current
                    remaining_entities = total_entities - current
                    eta_seconds = remaining_entities * avg_time_per_entity
                    
                    # Send progress event
                    progress_data = {
                        'type': 'progress',
                        'processed': current,
                        'total': total_entities,
                        'entity_id': entity['id'],
                        'entity_name': entity['name'],
                        'success': success,
                        'successful': successful_count,
                        'failed_count': failed_count,
                        'eta_seconds': int(eta_seconds) if eta_seconds > 0 else 0
                    }
                    
                    yield f"data: {json.dumps(progress_data)}\n\n"
                    
                    # Small delay between commands
                    time.sleep(0.2)
                    
                except Exception as e:
                    failed_count += 1
                    logger.error(f"Error regenerating entity {entity['id']}: {e}")
                    
                    # Send error event but continue processing
                    error_data = {
                        'type': 'progress',
                        'processed': i + 1,
                        'total': total_entities,
                        'entity_id': entity['id'],
                        'entity_name': entity['name'],
                        'success': False,
                        'successful': successful_count,
                        'failed_count': failed_count,
                        'error': str(e)
                    }
                    yield f"data: {json.dumps(error_data)}\n\n"
            
            # Send completion event
            complete_data = {
                'type': 'complete',
                'regenerated_count': successful_count,
                'failed_count': failed_count,
                'total_processed': total_entities
            }
            
            yield f"data: {json.dumps(complete_data)}\n\n"
            
            logger.info(f"Streaming regeneration complete: {successful_count} successful, {failed_count} failed")
            
        except Exception as e:
            logger.error(f"Error in streaming regeneration: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return Response(generate_progress(), mimetype='text/event-stream',
                   headers={'Cache-Control': 'no-cache', 'Connection': 'keep-alive'})

@app.route('/api/test/bulk-regenerate', methods=['POST'])
def bulk_regenerate_npc_entities():
    """Execute bulk regeneration of NPC entities on selected playfields"""
    if not background_service:
        return jsonify({'success': False, 'message': 'Background service not available'})
    
    try:
        data = request.get_json(force=True)
        selected_playfields = data.get('playfields', [])
        
        if not selected_playfields:
            return jsonify({'success': False, 'message': 'No playfields selected'})
        
        connection_handler = background_service.get_connection_handler()
        if not connection_handler or not connection_handler.is_connection_alive():
            return jsonify({'success': False, 'message': 'Not connected to server'})
        
        logger.info(f"Starting bulk regeneration for playfields: {selected_playfields}")
        
        # Get active playfield PIDs
        servers_result = connection_handler.send_command("servers")
        if not servers_result:
            return jsonify({'success': False, 'message': 'Failed to get server information'})
        
        # Parse PIDs for selected playfields
        playfield_pids = {}
        lines = servers_result.split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            # Look for playfield names first
            if line.startswith("*'") and line.endswith("'"):
                playfield_name = line[2:-1]  # Remove *' and '
                if playfield_name in selected_playfields:
                    # Look backwards to find the PID for this playfield
                    for j in range(i-1, max(i-10, -1), -1):
                        prev_line = lines[j].strip()
                        if 'PID:' in prev_line:
                            pid = prev_line.split('PID:')[1].strip().split()[0]
                            playfield_pids[playfield_name] = pid
                            logger.info(f"Mapped playfield '{playfield_name}' to PID {pid}")
                            break
        
        logger.info(f"Final playfield PID mapping: {playfield_pids}")
        
        # Get entities and filter for NPC entities on selected playfields
        entities_response = player_db.get_entities()
        if not entities_response.get('success') or len(entities_response.get('entities', [])) == 0:
            # Database is empty or failed, fetch live entity data
            logger.info("Database is empty or failed, fetching live entity data from server...")
            live_entities = connection_handler.get_entities()
            if not live_entities:
                return jsonify({'success': False, 'message': 'Failed to retrieve live entity data from server'})
            entities = live_entities
        else:
            entities = entities_response.get('entities', [])
        entities_to_regenerate = []
        
        for entity in entities:
            entity_playfield = entity.get('playfield', '')
            
            # Check if entity is on a selected playfield (handle both formats)
            is_on_selected_playfield = False
            for selected_pf in selected_playfields:
                if entity_playfield == selected_pf or entity_playfield == f"{selected_pf} (loaded)":
                    is_on_selected_playfield = True
                    break
            
            if not is_on_selected_playfield:
                continue
            
            # Classify entity faction
            faction = entity.get('faction', '')
            category, description = classify_entity_faction(faction)
            
            # Only regenerate NPC and Neutral entities (preserve Player entities)
            if category in ['NPC', 'Neutral']:
                # Find the PID for this entity's playfield
                entity_pid = None
                for selected_pf in selected_playfields:
                    if entity_playfield == selected_pf or entity_playfield == f"{selected_pf} (loaded)":
                        entity_pid = playfield_pids.get(selected_pf)
                        break
                
                if entity_pid:
                    entities_to_regenerate.append({
                        'id': entity.get('id'),
                        'name': entity.get('name'),
                        'playfield': entity_playfield,
                        'pid': entity_pid,
                        'faction': faction,
                        'faction_description': description
                    })
        
        logger.info(f"Found {len(entities_to_regenerate)} NPC+Neutral entities to regenerate")
        
        if len(entities_to_regenerate) == 0:
            return jsonify({
                'success': True,
                'message': 'No NPC+Neutral entities found to regenerate',
                'regenerated_count': 0,
                'failed_count': 0,
                'results': []
            })
        
        # Execute regeneration commands
        successful_regenerations = []
        failed_regenerations = []
        commands_sent = 0
        replies_received = 0
        
        logger.info(f"=== BULK REGENERATION DEBUG START ===")
        logger.info(f"Total entities to process: {len(entities_to_regenerate)}")
        
        for i, entity in enumerate(entities_to_regenerate):
            try:
                regenerate_command = f"remoteex pf={entity['pid']} regenerate {entity['id']}"
                logger.info(f"RCON SEND ({i+1}/{len(entities_to_regenerate)}): {regenerate_command}")
                commands_sent += 1
                
                result = connection_handler.send_command(regenerate_command)
                
                if result and isinstance(result, str):
                    replies_received += 1
                    logger.info(f"RCON REPLY ({i+1}): {result.strip()}")
                    successful_regenerations.append({
                        'entity_id': entity['id'],
                        'entity_name': entity['name'],
                        'playfield': entity['playfield'],
                        'command': regenerate_command,
                        'server_response': result.strip()
                    })
                else:
                    logger.warning(f"RCON NO REPLY ({i+1}): Command sent but no response received for entity {entity['id']}")
                    failed_regenerations.append({
                        'entity_id': entity['id'],
                        'entity_name': entity['name'],
                        'playfield': entity['playfield'],
                        'command': regenerate_command,
                        'error': 'No response from server'
                    })
                
                # Small delay between commands to avoid overwhelming the server
                import time
                time.sleep(0.2)  # 200ms delay
                
            except Exception as e:
                failed_regenerations.append({
                    'entity_id': entity['id'],
                    'entity_name': entity['name'],
                    'playfield': entity['playfield'],
                    'command': regenerate_command,
                    'error': str(e)
                })
                logger.error(f"Error regenerating entity {entity['id']}: {e}")
        
        # Debug summary
        logger.info(f"=== BULK REGENERATION DEBUG SUMMARY ===")
        logger.info(f"Commands sent: {commands_sent}")
        logger.info(f"Replies received: {replies_received}")
        logger.info(f"Success rate: {replies_received}/{commands_sent} ({100*replies_received/commands_sent:.1f}%)" if commands_sent > 0 else "Success rate: N/A")
        logger.info(f"Successful regenerations: {len(successful_regenerations)}")
        logger.info(f"Failed regenerations: {len(failed_regenerations)}")
        logger.info(f"=== BULK REGENERATION DEBUG END ===")
        
        logger.info(f"Bulk regeneration complete: {len(successful_regenerations)} successful, {len(failed_regenerations)} failed")
        
        return jsonify({
            'success': True,
            'message': f'Successfully regenerated {len(successful_regenerations)} NPC+Neutral entities',
            'regenerated_count': len(successful_regenerations),
            'failed_count': len(failed_regenerations),
            'total_processed': len(entities_to_regenerate),
            'successful_regenerations': successful_regenerations,
            'failed_regenerations': failed_regenerations
        })
        
    except Exception as e:
        logger.error(f"Error in bulk regeneration: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': 'An internal error occurred during bulk regeneration'
        })

@app.route('/api/test/player-structures', methods=['GET'])
def get_player_structures():
    """Get all player-owned structures for testing selective POI regeneration"""
    if not player_db:
        return jsonify({'success': False, 'message': 'Database not initialized'})
    
    try:
        # Get all entities from database
        entities_response = player_db.get_entities()
        if not entities_response.get('success'):
            return jsonify({'success': False, 'message': 'Failed to retrieve entities from database'})
        
        entities = entities_response.get('entities', [])
        
        # Classify entities by faction
        player_entities = []
        npc_entities = []
        neutral_entities = []
        faction_breakdown = {}
        
        for entity in entities:
            faction = entity.get('faction', '')
            category, description = classify_entity_faction(faction)
            
            # Add faction to breakdown
            if faction not in faction_breakdown:
                faction_breakdown[faction] = {
                    'count': 0,
                    'category': category,
                    'description': description
                }
            faction_breakdown[faction]['count'] += 1
            
            # Categorize entity
            entity_data = {
                'id': entity.get('id'),
                'name': entity.get('name'),
                'type': entity.get('type'),
                'faction': faction,
                'faction_description': description,
                'playfield': entity.get('playfield'),
                'time_info': entity.get('time_info'),
                'last_seen': entity.get('last_seen')
            }
            
            if category == 'Player':
                player_entities.append(entity_data)
            elif category == 'NPC':
                npc_entities.append(entity_data)
            else:  # Neutral
                neutral_entities.append(entity_data)
        
        # Sort player entities by playfield and name
        player_entities.sort(key=lambda x: (x['playfield'] or '', x['name'] or ''))
        
        logger.info(f"Player structure detection: {len(player_entities)} player, {len(npc_entities)} NPC, {len(neutral_entities)} neutral")
        
        # Fix faction breakdown data structure for frontend
        frontend_faction_breakdown = {}
        for faction, data in faction_breakdown.items():
            frontend_faction_breakdown[faction] = {
                'name': data['description'],
                'count': data['count'],
                'category': data['category']
            }
        
        return jsonify({
            'success': True,
            'player_entities': player_entities,
            'statistics': {
                'total_entities': len(entities),
                'player_entities': len(player_entities),
                'npc_entities': len(npc_entities),
                'neutral_entities': len(neutral_entities)
            },
            'faction_breakdown': frontend_faction_breakdown,
            'analysis_time': datetime.now().isoformat(),
            'message': f'Found {len(player_entities)} player-owned structures'
        })
        
    except Exception as e:
        logger.error(f"Error getting player structures: {e}", exc_info=True)
        return jsonify({
            'success': False, 
            'message': 'Failed to analyze player structures'
        })

@app.route('/messaging/custom', methods=['GET'])
def get_custom_messages():
    """Get custom welcome and goodbye messages."""
    if not messaging_manager:
        return jsonify({'success': False, 'message': 'Messaging manager not initialized'})
    
    try:
        messages = messaging_manager.load_custom_messages()
        return jsonify({'success': True, 'messages': messages})
    except Exception as e:
        logger.error(f"Error getting custom messages: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An internal error occurred. Please try again later.'})

@app.route('/messaging/custom', methods=['POST'])
def save_custom_messages():
    """Save custom welcome and goodbye messages with enabled states."""
    if not messaging_manager:
        return jsonify({'success': False, 'message': 'Messaging manager not initialized'})
    
    try:
        data = request.get_json()
        welcome_msg = data.get('welcome_message', '').strip()
        goodbye_msg = data.get('goodbye_message', '').strip()
        welcome_enabled = data.get('welcome_enabled', True)
        goodbye_enabled = data.get('goodbye_enabled', True)
        
        result = messaging_manager.save_custom_messages(welcome_msg, goodbye_msg, welcome_enabled, goodbye_enabled)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error saving custom messages: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An internal error occurred. Please try again later.'})

@app.route('/messaging/scheduled', methods=['GET'])
def get_scheduled_messages():
    """Get scheduled messages."""
    if not messaging_manager:
        return jsonify({'success': False, 'message': 'Messaging manager not initialized'})
    
    try:
        messages = messaging_manager.load_scheduled_messages()
        return jsonify({'success': True, 'messages': messages})
    except Exception as e:
        logger.error(f"Error getting scheduled messages: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An internal error occurred. Please try again later.'})

@app.route('/messaging/scheduled', methods=['POST'])
def save_scheduled_messages():
    """Save scheduled messages."""
    if not messaging_manager:
        return jsonify({'success': False, 'message': 'Messaging manager not initialized'})
    
    try:
        data = request.get_json()
        messages = data.get('messages', [])
        
        success = messaging_manager.save_scheduled_messages(messages)
        if success:
            return jsonify({'success': True, 'message': 'Scheduled messages saved successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to save scheduled messages'})
        
    except Exception as e:
        logger.error(f"Error saving scheduled messages: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An internal error occurred. Please try again later.'})

@app.route('/messaging/history', methods=['GET'])
def get_message_history():
    """Get message history."""
    if not messaging_manager:
        return jsonify({'success': False, 'message': 'Messaging manager not initialized'})
    
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
        logger.error(f"Error getting message history: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An internal error occurred. Please try again later.'})

@app.route('/messaging/history/clear', methods=['POST'])
def clear_message_history():
    """Clear message history."""
    if not messaging_manager:
        return jsonify({'success': False, 'message': 'Messaging manager not initialized'})
    
    try:
        success = messaging_manager.clear_message_history()
        if success:
            return jsonify({'success': True, 'message': 'Message history cleared successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to clear message history'})
    except Exception as e:
        logger.error(f"Error clearing message history: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An internal error occurred. Please try again later.'})

@app.route('/messaging/test', methods=['POST'])
def test_message():
    """Send a test message."""
    if not background_service:
        return jsonify({'success': False, 'message': 'Background service not available'})
    
    connection_handler = background_service.get_connection_handler()
    if not connection_handler or not connection_handler.is_connection_alive():
        return jsonify({'success': False, 'message': 'Not connected to server'})
    
    if not messaging_manager:
        return jsonify({'success': False, 'message': 'Messaging manager not initialized'})
    
    try:
        data = request.get_json()
        message_type = data.get('type')
        player_name = data.get('player_name', 'TestPlayer')
        
        if message_type == 'welcome':
            result = messaging_manager.send_welcome_message(player_name)
        elif message_type == 'goodbye':
            result = messaging_manager.send_goodbye_message(player_name)
        else:
            return jsonify({'success': False, 'message': 'Invalid message type'})
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error sending test message: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An internal error occurred. Please try again later.'})

@app.route('/logging/stats', methods=['GET'])
def get_logging_stats():
    """Get logging statistics."""
    try:
        stats = logging_manager.get_log_stats()
        return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        logger.error(f"Error getting logging stats: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An internal error occurred. Please try again later.'})

@app.route('/logging/recent', methods=['GET'])
def get_recent_logs():
    """Get recent log entries."""
    try:
        lines = request.args.get('lines', 100, type=int)
        logs = logging_manager.get_recent_logs(lines)
        return jsonify({'success': True, 'logs': logs})
    except Exception as e:
        logger.error(f"Error getting recent logs: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An internal error occurred. Please try again later.'})

@app.route('/logging/settings', methods=['GET'])
def get_logging_settings():
    """Get logging configuration settings."""
    try:
        settings = {
            'max_size_mb': logging_manager.max_bytes // (1024 * 1024),
            'backup_count': logging_manager.backup_count,
            'max_age_days': logging_manager.max_age_days
        }
        return jsonify({'success': True, 'settings': settings})
    except Exception as e:
        logger.error(f"Error getting logging settings: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An internal error occurred. Please try again later.'})

@app.route('/logging/settings', methods=['POST'])
def save_logging_settings():
    """Save logging configuration settings."""
    try:
        data = request.get_json()
        max_size_mb = data.get('max_size_mb')
        backup_count = data.get('backup_count')
        max_age_days = data.get('max_age_days')
        
        success = logging_manager.update_settings(max_size_mb, backup_count, max_age_days)
        
        if success:
            return jsonify({'success': True, 'message': 'Logging settings saved successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to save logging settings'})
        
    except Exception as e:
        logger.error(f"Error saving logging settings: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An internal error occurred. Please try again later.'})

@app.route('/logging/cleanup', methods=['POST'])
def cleanup_logs():
    """Clean up old log files."""
    try:
        result = logging_manager.cleanup_old_logs()
        message = f"Deleted {result['deleted_files']} old log files ({result['deleted_bytes']} bytes)"
        return jsonify({'success': True, 'message': message})
    except Exception as e:
        logger.error(f"Error cleaning up logs: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An internal error occurred. Please try again later.'})

@app.route('/logging/clear', methods=['POST'])
def clear_logs():
    """Clear all log files."""
    try:
        success = logging_manager.clear_all_logs()
        if success:
            return jsonify({'success': True, 'message': 'All log files cleared successfully'})
        else:
            return jsonify({'success': False, 'message': 'No log files to clear'})
    except Exception as e:
        logger.error(f"Error clearing logs: {e}", exc_info=True)
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
    if not connection_handler or not connection_handler.is_connection_alive():
        return jsonify({'success': False, 'message': 'Not connected to server'})
    
    if not messaging_manager:
        return jsonify({'success': False, 'message': 'Messaging manager not available'})
    
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
    empyrion_root = player_db.get_app_setting('empyrion_root')
    scenario_name = player_db.get_app_setting('scenario_name')
    
    status = {
        'rcon': bool(rcon_creds and rcon_creds.get('password')),
        'ftp': bool(ftp_creds and ftp_creds.get('password') and ftp_creds.get('username')),
        'server_host': bool(server_host),
        'server_port': bool(server_port),
        'ftp_host': bool(ftp_host),
        'ftp_remote_log_path': bool(ftp_remote_log_path),
        'empyrion_root': bool(empyrion_root),
        'scenario_name': bool(scenario_name),
        'advanced_ftp': bool(empyrion_root and scenario_name)  # Both new settings configured
    }
    return jsonify(status)

@app.route('/api/credentials/get/rcon', methods=['GET'])
def api_get_rcon_credentials():
    """Get RCON credentials for testing purposes."""
    try:
        rcon_creds = player_db.get_credential('rcon')
        server_host = player_db.get_app_setting('server_host')
        server_port = player_db.get_app_setting('server_port')
        
        return jsonify({
            'success': True,
            'host': server_host or '',
            'port': server_port or '30004',
            'password': rcon_creds.get('password', '') if rcon_creds else ''
        })
    except Exception as e:
        logger.error(f"Error getting RCON credentials: {e}")
        return jsonify({'success': False, 'message': 'Error retrieving credentials'})

@app.route('/api/credentials/get/ftp', methods=['GET'])
def api_get_ftp_credentials():
    """Get FTP credentials for testing purposes."""
    try:
        ftp_creds = player_db.get_credential('ftp')
        ftp_host = player_db.get_app_setting('ftp_host')
        
        return jsonify({
            'success': True,
            'host': ftp_host or '',
            'username': ftp_creds.get('username', '') if ftp_creds else '',
            'password': ftp_creds.get('password', '') if ftp_creds else ''
        })
    except Exception as e:
        logger.error(f"Error getting FTP credentials: {e}")
        return jsonify({'success': False, 'message': 'Error retrieving credentials'})

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

    # FTP HOST/REMOTE LOG PATH (Legacy support)
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

    # NEW FTP ROOT PATH SETTINGS (For playfield wipe automation)
    empyrion_root = data.get('empyrion_root')
    scenario_name = data.get('scenario_name')
    if empyrion_root is not None:
        if not isinstance(empyrion_root, str) or not empyrion_root.strip():
            errors['empyrion_root'] = 'Empyrion root path is required.'
        else:
            # Normalize path (remove trailing slash)
            root_path = empyrion_root.strip().rstrip('/')
            player_db.set_app_setting('empyrion_root', root_path)
            updated.append('empyrion_root')
            
    if scenario_name is not None:
        if not isinstance(scenario_name, str) or not scenario_name.strip():
            errors['scenario_name'] = 'Scenario name is required.'
        else:
            player_db.set_app_setting('scenario_name', scenario_name.strip())
            updated.append('scenario_name')

    if errors:
        return jsonify({'success': False, 'errors': errors}), 400
    return jsonify({'success': True, 'updated': updated})

# ===============================
# FTP Path Calculation Utilities
# ===============================


# Legacy path calculation functions removed - now using direct path configuration



# ===============================
# Advanced FTP API Endpoints
# ===============================


@app.route('/api/ftp/validate-paths', methods=['POST'])
def validate_ftp_paths():
    """Validate direct Empyrion paths via FTP/SFTP connection with auto-detection."""
    try:
        import socket
        from connection_manager import EnhancedConnectionManager, UniversalFileClient
        
        data = request.get_json(force=True)
        items_config_path = data.get('items_config_path', '').strip()
        playfields_path = data.get('playfields_path', '').strip()
        
        if not items_config_path or not playfields_path:
            return jsonify({
                'success': False, 
                'message': 'Both items config path and playfields path are required'
            })
            
        # Get FTP credentials
        credentials = player_db.get_ftp_credentials()
        if not credentials or not credentials.get('username') or not credentials.get('password'):
            return jsonify({'success': False, 'message': 'Server credentials not configured'})
            
        ftp_host = player_db.get_app_setting('ftp_host')
        if not ftp_host:
            return jsonify({'success': False, 'message': 'Server host not configured'})
            
        # Parse host and port
        if ':' in ftp_host:
            host, port_str = ftp_host.split(':', 1)
            try:
                port = int(port_str)
            except ValueError:
                port = 22  # Default to SFTP port for auto-detection
        else:
            host = ftp_host
            port = 22  # Default to SFTP port for auto-detection
            
        # Paths to test (direct user input)
        paths = {
            'items_config_path': items_config_path,
            'playfields_path': playfields_path
        }
        
        logger.info(f"🔍 Validating direct paths with auto-detection")
        
        try:
            # Auto-detect connection type and connect
            manager = EnhancedConnectionManager()
            connection_result = manager.detect_and_connect(host, port, credentials['username'], credentials['password'])
            
            if not connection_result.success:
                return jsonify({
                    'success': False,
                    'message': f'Cannot connect to server: {connection_result.message}'
                })
            
            logger.info(f"Connected using {connection_result.connection_type.upper()} for path validation")
            
            # Use universal client for file operations
            client = UniversalFileClient(
                connection_result.connection_type,
                host, port,
                credentials['username'], credentials['password']
            )
            
            # Test each direct path
            results = {}
            
            with client.connect():
                for path_type, path_value in paths.items():
                    if path_value:  # Skip empty paths
                        try:
                            # Test if path exists by listing its contents
                            client.list_directory(path_value)
                            results[path_type] = {
                                'exists': True,
                                'path': path_value
                            }
                        except Exception:
                            results[path_type] = {
                                'exists': False,
                                'path': path_value
                            }
            
            # Count successful validations
            valid_count = sum(1 for r in results.values() if r['exists'])
            total_count = len(results)
            
            logger.info(f"Path validation completed: {valid_count}/{total_count} paths exist")
            
            return jsonify({
                'success': True,
                'results': results,
                'summary': f'{valid_count}/{total_count} paths exist',
                'message': f'Validated {total_count} paths successfully',
                'connection_type': connection_result.connection_type
            })
            
        except Exception as connection_error:
            logger.error(f"Connection error validating paths: {connection_error}")
            return jsonify({
                'success': False,
                'message': f'Connection failed: {str(connection_error)}'
            })
            
    except Exception as e:
        logger.error(f"Error validating FTP paths: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': 'Internal error validating paths'
        })

@app.route('/api/ftp/list-playfields', methods=['POST'])
def list_playfields_via_ftp():
    """List available playfields by browsing playfields directory via FTP/SFTP with auto-detection."""
    try:
        import socket
        from connection_manager import EnhancedConnectionManager, UniversalFileClient
        
        data = request.get_json(force=True) 
        playfields_path = data.get('playfields_path', '').strip()
        
        if not playfields_path:
            return jsonify({
                'success': False, 
                'message': 'Playfields path is required'
            })
            
        # Get FTP credentials
        credentials = player_db.get_ftp_credentials()
        if not credentials or not credentials.get('username') or not credentials.get('password'):
            return jsonify({'success': False, 'message': 'Server credentials not configured'})
            
        ftp_host = player_db.get_app_setting('ftp_host')
        if not ftp_host:
            return jsonify({'success': False, 'message': 'Server host not configured'})
            
        # Parse host and port
        if ':' in ftp_host:
            host, port_str = ftp_host.split(':', 1)
            try:
                port = int(port_str)
            except ValueError:
                port = 22  # Default to SFTP port for auto-detection
        else:
            host = ftp_host
            port = 22  # Default to SFTP port for auto-detection
            
        logger.info(f"🔍 Listing playfields from {playfields_path} with auto-detection")
        
        try:
            # Auto-detect connection type and connect
            manager = EnhancedConnectionManager()
            connection_result = manager.detect_and_connect(host, port, credentials['username'], credentials['password'])
            
            if not connection_result.success:
                return jsonify({
                    'success': False,
                    'message': f'Cannot connect to server: {connection_result.message}'
                })
            
            logger.info(f"Connected using {connection_result.connection_type.upper()} for playfield listing")
            
            # Use universal client for file operations
            client = UniversalFileClient(
                connection_result.connection_type,
                host, port,
                credentials['username'], credentials['password']
            )
            
            with client.connect():
                try:
                    # List directories (playfields) in the playfields path
                    playfield_names = client.list_directories_only(playfields_path)
                    
                    # Process and filter playfields
                    playfields = []
                    for playfield_name in playfield_names:
                        # Skip system directories
                        if playfield_name.startswith('.') or playfield_name in ['Templates', 'Cache']:
                            continue
                            
                        # Get additional info about playfield
                        playfield_info = {
                            'name': playfield_name,
                            'display_name': playfield_name.replace('_', ' '),  # Make more readable
                            'path': f"{playfields_path}/{playfield_name}",
                            'type': 'Unknown'  # We'll determine this later if needed
                        }
                        
                        # Try to determine playfield type from name patterns
                        name_lower = playfield_name.lower()
                        if any(x in name_lower for x in ['space', 'orbit', 'asteroid']):
                            playfield_info['type'] = 'Space'
                        elif any(x in name_lower for x in ['planet', 'moon', 'desert', 'temperate', 'alien']):
                            playfield_info['type'] = 'Planet/Moon'
                        elif 'trading' in name_lower or 'station' in name_lower:
                            playfield_info['type'] = 'Trading Station'
                        
                        playfields.append(playfield_info)
                    
                    # Sort playfields alphabetically
                    playfields.sort(key=lambda x: x['name'])
                    
                    logger.info(f"Found {len(playfields)} playfields")
                    
                    return jsonify({
                        'success': True,
                        'playfields': playfields,
                        'count': len(playfields),
                        'message': f'Found {len(playfields)} playfields',
                        'connection_type': connection_result.connection_type
                    })
                    
                except Exception as browse_error:
                    logger.error(f"Error browsing playfields directory: {browse_error}")
                    return jsonify({
                        'success': False,
                        'message': f'Playfields directory not found or inaccessible: {playfields_path}'
                    })
            
        except Exception as connection_error:
            logger.error(f"Connection error listing playfields: {connection_error}")
            return jsonify({
                'success': False,
                'message': f'Connection failed: {str(connection_error)}'
            })
            
    except Exception as e:
        logger.error(f"Error listing playfields: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': 'Internal error listing playfields'
        })

def generate_wipe_file_content(wipe_types: list) -> str:
    """Generate content for wipeinfo.txt file based on requested wipe types.
    
    Args:
        wipe_types: List of wipe types (poi, deposit, terrain, all)
        
    Returns:
        String content for wipeinfo.txt file
    """
    # Normalize input
    wipe_types = [w.lower().strip() for w in wipe_types if w]
    
    # Handle 'all' option
    if 'all' in wipe_types:
        wipe_types = ['poi', 'deposit', 'terrain']
    
    # Remove duplicates and sort for consistency
    wipe_types = sorted(list(set(wipe_types)))
    
    # Generate content (one type per line)
    content_lines = []
    for wipe_type in wipe_types:
        if wipe_type in ['poi', 'deposit', 'terrain']:
            content_lines.append(wipe_type)
    
    # Add empty line at end (matches the format from temp/wipeinfo.txt)
    return '\n'.join(content_lines) + '\n'

@app.route('/api/wipe/generate-file', methods=['POST'])
def generate_wipe_file():
    """Generate wipeinfo.txt file content for specified playfields and wipe types."""
    try:
        data = request.get_json(force=True)
        playfields = data.get('playfields', [])  # List of playfield names
        wipe_types = data.get('wipe_types', [])   # List of wipe types (poi, deposit, terrain)
        
        if not playfields:
            return jsonify({'success': False, 'message': 'No playfields specified'})
            
        if not wipe_types:
            return jsonify({'success': False, 'message': 'No wipe types specified'})
            
        # Generate wipe file content
        wipe_content = generate_wipe_file_content(wipe_types)
        
        logger.info(f"Generated wipe file for {len(playfields)} playfields with types: {wipe_types}")
        
        return jsonify({
            'success': True,
            'content': wipe_content,
            'playfields': playfields,
            'wipe_types': wipe_types,
            'message': f'Generated wipe file for {len(playfields)} playfields'
        })
        
    except Exception as e:
        logger.error(f"Error generating wipe file: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': 'Internal error generating wipe file'
        })

@app.route('/api/wipe/deploy-files', methods=['POST'])
def deploy_wipe_files():
    """Deploy wipeinfo.txt files to specified playfields via FTP/SFTP with auto-detection."""
    try:
        import socket
        import io
        
        data = request.get_json(force=True)
        playfields_path = data.get('playfields_path', '').strip()
        playfields = data.get('playfields', [])  # List of playfield names
        wipe_types = data.get('wipe_types', [])   # List of wipe types
        
        if not playfields_path:
            return jsonify({
                'success': False, 
                'message': 'Playfields path is required'
            })
            
        if not playfields:
            return jsonify({'success': False, 'message': 'No playfields specified'})
            
        if not wipe_types:
            return jsonify({'success': False, 'message': 'No wipe types specified'})
            
        # Get FTP credentials
        credentials = player_db.get_ftp_credentials()
        if not credentials or not credentials.get('username') or not credentials.get('password'):
            return jsonify({'success': False, 'message': 'FTP credentials not configured'})
            
        ftp_host = player_db.get_app_setting('ftp_host')
        if not ftp_host:
            return jsonify({'success': False, 'message': 'FTP host not configured'})
            
        # Parse host and port
        if ':' in ftp_host:
            host, port_str = ftp_host.split(':', 1)
            try:
                port = int(port_str)
            except ValueError:
                port = 21
        else:
            host = ftp_host
            port = 21
            
        # Use direct playfields path (already validated above)
            
        # Generate wipe file content
        wipe_content = generate_wipe_file_content(wipe_types)
        
        logger.info(f"Deploying wipe files to {len(playfields)} playfields with content: {wipe_content.strip()}")
        
        try:
            # Auto-detect connection type and connect
            from connection_manager import EnhancedConnectionManager, UniversalFileClient
            
            manager = EnhancedConnectionManager()
            connection_result = manager.detect_and_connect(host, port, credentials['username'], credentials['password'])
            
            if not connection_result.success:
                return jsonify({
                    'success': False,
                    'message': f'Cannot connect to server: {connection_result.message}'
                })
            
            logger.info(f"Connected using {connection_result.connection_type.upper()} for wipe file deployment")
            
            # Use universal client for file operations
            client = UniversalFileClient(
                connection_result.connection_type,
                host, port,
                credentials['username'], credentials['password']
            )
            
            # Deploy to each playfield
            deployed_playfields = []
            failed_playfields = []
            
            with client.connect():
                for playfield_name in playfields:
                    try:
                        # Upload wipeinfo.txt file to playfield directory
                        playfield_path = f"{playfields_path}/{playfield_name}/wipeinfo.txt"
                        wipe_file_bytes = io.BytesIO(wipe_content.encode('utf-8'))
                        
                        client.upload_file(wipe_file_bytes, playfield_path)
                        
                        deployed_playfields.append(playfield_name)
                        logger.info(f"Successfully deployed wipeinfo.txt to {playfield_name}")
                        
                    except Exception as e:
                        failed_playfields.append({'name': playfield_name, 'error': str(e)})
                        logger.error(f"Failed to deploy to {playfield_name}: {e}")
                        continue
            
            # Prepare response
            success_count = len(deployed_playfields)
            total_count = len(playfields)
            
            if success_count == total_count:
                return jsonify({
                    'success': True,
                    'deployed': deployed_playfields,
                    'failed': failed_playfields,
                    'summary': f'Successfully deployed to all {success_count} playfields',
                    'message': f'✅ Wipe files deployed to {success_count} playfields. Server restart required to activate.'
                })
            elif success_count > 0:
                return jsonify({
                    'success': True,  # Partial success
                    'deployed': deployed_playfields,
                    'failed': failed_playfields,
                    'summary': f'Deployed to {success_count}/{total_count} playfields',
                    'message': f'⚠️ Deployed to {success_count}/{total_count} playfields. Check failed deployments.'
                })
            else:
                return jsonify({
                    'success': False,
                    'deployed': deployed_playfields,
                    'failed': failed_playfields,
                    'summary': 'Failed to deploy to any playfields',
                    'message': '❌ All deployments failed. Check FTP permissions and paths.'
                })
                
        except Exception as deploy_error:
            logger.error(f"Connection error deploying wipe files: {deploy_error}")
            return jsonify({
                'success': False,
                'message': f'Deployment failed: {str(deploy_error)}'
            })
            
    except Exception as e:
        logger.error(f"Error deploying wipe files: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': 'Internal error deploying wipe files'
        })

# ===============================
# Items Config API Endpoints
# ===============================

@app.route('/itemsconfig/test', methods=['POST'])
def test_itemsconfig_connection():
    """Test FTP/SFTP connection and check for ItemsConfig.ecf file with auto-detection."""
    logger.info("🔍 Testing ItemsConfig connection with auto-detection")
    
    try:
        import socket
        from connection_manager import EnhancedConnectionManager, UniversalFileClient
        from urllib.parse import urlparse
        
        # Get FTP credentials and configuration path
        ftp_host = player_db.get_app_setting('ftp_host')
        credentials = player_db.get_ftp_credentials()
        ftp_user = credentials.get('username') if credentials else None
        ftp_password = credentials.get('password') if credentials else None
        
        # Get direct items config path from settings
        items_config_path = player_db.get_app_setting('items_config_path')
        
        if not all([ftp_host, ftp_user, ftp_password]):
            return jsonify({
                'success': False, 
                'connected': False,
                'file_exists': False,
                'message': 'Server credentials not configured. Please check Settings.'
            })
        
        if not items_config_path:
            return jsonify({
                'success': False, 
                'connected': False,
                'file_exists': False,
                'message': 'Items config path not set. Please configure ItemsConfig path in Settings.'
            })
        
        # Parse host and port
        if ':' in ftp_host:
            host, port_str = ftp_host.split(':', 1)
            try:
                port = int(port_str)
            except ValueError:
                port = 22  # Default to SFTP port for auto-detection
        else:
            host = ftp_host
            port = 22  # Default to SFTP port for auto-detection
        
        logger.info(f"🔍 Testing connection to {host}:{port} for ItemsConfig.ecf")
        
        try:
            # Auto-detect connection type and connect
            manager = EnhancedConnectionManager()
            connection_result = manager.detect_and_connect(host, port, ftp_user, ftp_password)
            
            if not connection_result.success:
                return jsonify({
                    'success': False,
                    'connected': False,
                    'file_exists': False,
                    'message': f'Cannot connect to server: {connection_result.message}'
                })
            
            logger.info(f"Connected using {connection_result.connection_type.upper()} for ItemsConfig test")
            
            # Use universal client for file operations
            client = UniversalFileClient(
                connection_result.connection_type,
                host, port,
                ftp_user, ftp_password
            )
            
            with client.connect():
                # Check if ItemsConfig.ecf exists
                itemsconfig_path = f"{items_config_path}/ItemsConfig.ecf"
                
                file_info_result = client.get_file_info(itemsconfig_path)
                file_exists = file_info_result.get('exists', False)
                file_info = None
                
                if file_exists:
                    # Format file information
                    file_size = file_info_result.get('size', 0)
                    file_size_mb = round(file_size / 1024 / 1024, 1) if file_size else 0
                    
                    # Get modification time if available
                    file_modified = 'Unknown'
                    if 'modified' in file_info_result:
                        try:
                            from datetime import datetime
                            mod_time = datetime.fromtimestamp(file_info_result['modified'])
                            file_modified = mod_time.strftime('%Y-%m-%d %H:%M:%S')
                        except:
                            file_modified = 'Unknown'
                    
                    file_info = {
                        'size': f'{file_size_mb} MB',
                        'modified': file_modified
                    }
                
                logger.info(f"✅ Connection test successful - ItemsConfig.ecf {'found' if file_exists else 'not found'}")
                
                return jsonify({
                    'success': True,
                    'connected': True,
                    'file_exists': file_exists,
                    'file_info': file_info,
                    'connection_type': connection_result.connection_type,
                    'message': f'{connection_result.connection_type.upper()} connection successful. ItemsConfig.ecf {'found' if file_exists else 'not found'} in {items_config_path}'
                })
            
        except Exception as connection_error:
            logger.warning(f"❌ Connection error: {connection_error}")
            return jsonify({
                'success': False,
                'connected': False,
                'file_exists': False,
                'message': f'Connection failed: {str(connection_error)}'
            })
        
    except Exception as e:
        logger.error(f"Error testing ItemsConfig connection: {e}", exc_info=True)
        return jsonify({
            'success': False, 
            'connected': False,
            'file_exists': False,
            'message': 'An internal error occurred testing the connection.'
        })

@app.route('/itemsconfig/download', methods=['POST'])
def download_itemsconfig():
    """Download and parse ItemsConfig.ecf file via FTP/FTPS/SFTP with automatic detection."""
    logger.info("Downloading ItemsConfig.ecf file via auto-detected connection")
    
    try:
        import os
        import tempfile
        from ecf_parser import ECFParser
        from connection_manager import EnhancedConnectionManager, UniversalFileClient
        
        # Get FTP credentials and configuration path
        ftp_host = player_db.get_app_setting('ftp_host')
        ftp_user = player_db.get_ftp_credentials().get('username')
        ftp_password = player_db.get_ftp_credentials().get('password')
        ftp_config_path = player_db.get_app_setting('ftp_remote_log_path')
        
        if not all([ftp_host, ftp_user, ftp_password]):
            return jsonify({
                'success': False,
                'message': 'Server credentials not configured. Please check Settings.'
            })
        
        if not ftp_config_path:
            return jsonify({
                'success': False,
                'message': 'Remote server path not set. Please configure it in Settings.'
            })
        
        # Parse host and port
        if ':' in ftp_host:
            host, port_str = ftp_host.split(':', 1)
            try:
                port = int(port_str)
            except ValueError:
                port = 21
        else:
            host = ftp_host
            port = 21
        
        logger.info(f"Downloading ItemsConfig.ecf from {host}:{port}")
        
        # Auto-detect connection type and establish connection
        connection_manager = EnhancedConnectionManager()
        connection_result = connection_manager.detect_and_connect(host, port, ftp_user, ftp_password)
        
        if not connection_result.success:
            return jsonify({
                'success': False,
                'message': f'Failed to connect to server: {connection_result.message}'
            })
        
        logger.info(f"Connected using {connection_result.connection_type.upper()}")
        
        # Create temporary file for download
        temp_file = None
        try:
            # Create UniversalFileClient
            client = UniversalFileClient(
                connection_result.connection_type, 
                host, 
                port, 
                ftp_user, 
                ftp_password
            )
            
            with client.connect():
                # Check if file exists in the configured path
                remote_file_path = f"{ftp_config_path}/ItemsConfig.ecf" if ftp_config_path != '.' else 'ItemsConfig.ecf'
                
                # List directory to check if file exists
                try:
                    files = client.list_directory(ftp_config_path)
                    if 'ItemsConfig.ecf' not in files:
                        return jsonify({
                            'success': False,
                            'message': f'ItemsConfig.ecf not found in {ftp_config_path}'
                        })
                except Exception as list_error:
                    logger.warning(f"Could not list directory {ftp_config_path}: {list_error}")
                    # Continue anyway, maybe file exists but listing failed
                
                # Create temporary file
                temp_file = tempfile.NamedTemporaryFile(mode='wb', suffix='.ecf', delete=False)
                temp_file_path = temp_file.name
                
                # Download the file
                logger.info(f"Downloading ItemsConfig.ecf to {temp_file_path}")
                client.download_file(remote_file_path, temp_file)
                temp_file.close()
                
                # Get file info for response
                try:
                    file_info = client.get_file_info(remote_file_path)
                    if file_info.get('exists') and file_info.get('size'):
                        file_size_mb = round(file_info['size'] / 1024 / 1024, 1)
                    else:
                        file_size_mb = round(os.path.getsize(temp_file_path) / 1024 / 1024, 1)
                except:
                    file_size_mb = round(os.path.getsize(temp_file_path) / 1024 / 1024, 1)
            
            logger.info(f"Successfully downloaded ItemsConfig.ecf ({file_size_mb} MB)")
            
            # Parse the downloaded ECF file
            parser = ECFParser()
            parse_result = parser.parse_file(temp_file_path)
            
            # Convert parsed items to our frontend format
            formatted_items = []
            for item in parse_result['items']:
                formatted_item = {
                    'id': item['id'],
                    'name': item['name'],
                    'type': item['type'],
                    'stacksize': item.get('stacksize', ''),
                    'mass': item.get('mass', ''),
                    'volume': item.get('volume', ''),
                    'marketprice': item.get('marketprice', ''),
                    'template': item.get('template', '')
                }
                formatted_items.append(formatted_item)
            
            # Get file stats from downloaded file
            file_stats = os.stat(temp_file_path)
            download_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            logger.info(f"Successfully parsed {len(formatted_items)} items from downloaded ItemsConfig.ecf")
            logger.info(f"Templates: {parse_result['template_count']}, Items: {parse_result['item_count']}")
            
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
                logger.debug(f"Cleaned up temporary file: {temp_file_path}")
            except Exception as cleanup_error:
                logger.warning(f"Could not clean up temporary file {temp_file_path}: {cleanup_error}")
            
            return jsonify({
                'success': True,
                'items': formatted_items,
                'file_info': {
                    'size': f'{file_size_mb} MB',
                    'item_count': len(formatted_items),
                    'template_count': parse_result['template_count'],
                    'regular_item_count': parse_result['item_count'],
                    'downloaded': download_time,
                    'parsed_at': datetime.now().isoformat()
                },
                'message': f'Successfully downloaded and parsed {len(formatted_items)} items ({parse_result["template_count"]} templates, {parse_result["item_count"]} items)'
            })
            
        except Exception as download_error:
            logger.error(f"Error during file download or parsing: {download_error}")
            return jsonify({
                'success': False,
                'message': f'Download or parsing error: {str(download_error)}'
            })
            
        finally:
            # Ensure temp file cleanup even if parsing fails
            if temp_file and hasattr(temp_file, 'name') and os.path.exists(temp_file.name):
                try:
                    if not temp_file.closed:
                        temp_file.close()
                    os.unlink(temp_file.name)
                    logger.debug(f"Cleaned up temporary file in finally block: {temp_file.name}")
                except Exception as cleanup_error:
                    logger.warning(f"Could not clean up temporary file in finally block: {cleanup_error}")
        
    except Exception as e:
        logger.error(f"Error downloading ItemsConfig: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': 'An internal error occurred downloading or parsing the file.'
        })

# ===============================
# POI Regeneration API Endpoints
# ===============================

@app.route('/api/regenerate-poi', methods=['POST'])
def regenerate_poi():
    """Regenerate a specific POI by entity ID."""
    logger.info("POI regeneration requested")
    
    try:
        data = request.get_json(force=True)
        entity_id = data.get('entity_id')
        
        if not entity_id:
            return jsonify({
                'success': False,
                'message': 'Entity ID is required'
            }), 400
        
        # Check if background service is available and connected
        if not background_service:
            return jsonify({
                'success': False,
                'message': 'Background service not available'
            })
        
        connection_handler = background_service.get_connection_handler()
        if not connection_handler or not connection_handler.is_connection_alive():
            return jsonify({
                'success': False,
                'message': 'Not connected to server'
            })
        
        # Send regenerate command
        regenerate_command = f"regenerate {entity_id}"
        logger.info(f"Executing RCON command: {regenerate_command}")
        
        result = connection_handler.send_command(regenerate_command)
        
        if result and isinstance(result, str):
            logger.info(f"Regenerate command result: {result}")
            return jsonify({
                'success': True,
                'message': f'POI {entity_id} regeneration command sent successfully',
                'server_response': result.strip()
            })
        else:
            logger.warning(f"Unexpected result from regenerate command: {result}")
            return jsonify({
                'success': False,
                'message': 'No response from server or command failed'
            })
        
    except Exception as e:
        logger.error(f"Error regenerating POI: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': 'An internal error occurred while regenerating POI'
        })

# POI Management endpoint removed - wipe command only destroys POIs without regenerating them
# For POI regeneration, use 'regenerate <entityid>' in-game console or manual playfield file deletion


if __name__ == '__main__':
    # Initialize the application
    logger.info("🚀 Starting Empyrion Web Helper v0.5.1...")
    
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
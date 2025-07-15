#!/usr/bin/env python3
"""
Empyrion Web Helper v0.3.0
A web-based admin tool for Empyrion Galactic Survival servers
"""

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import logging
import os

# Import our modules
from config_manager import ConfigManager
from connection import EmpyrionConnection
from database import PlayerDatabase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('empyrion_helper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

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

def initialize_app():
    """Initialize the application"""
    global config_manager, player_db
    
    # Initialize configuration
    config_manager = ConfigManager()
    config_manager.load_config()
    
    # Initialize player database
    player_db = PlayerDatabase()
    
    # Create instance directory if it doesn't exist
    if not os.path.exists('instance'):
        os.makedirs('instance')
    
    logger.info("Empyrion Web Helper v0.3.0 initialized")
    logger.info(f"Target server: {config_manager.get('host')}:{config_manager.get('telnet_port')}")

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
            logger.info(f"Successfully connected to server")
            socketio.emit('connection_status', {'connected': True})
            return jsonify({'success': True, 'message': 'Connected to server'})
        else:
            logger.error("Connection failed")
            return jsonify({'success': False, 'message': 'Failed to connect to server'})
            
    except Exception as e:
        logger.error(f"Connection error: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/disconnect', methods=['POST'])
def disconnect():
    """Disconnect from the server"""
    global is_connected, connection_handler
    
    try:
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
            updated_count = player_db.update_multiple_players(players)
            logger.info(f"DATABASE UPDATE COMPLETE: Updated {updated_count} players")
        else:
            logger.info("No database or no players - skipping database update")
        
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
        
        # Log specific player data to debug IP issue
        for player in players:
            if player['name'] == 'ChaoszMind':
                logger.info(f"DEBUG ChaoszMind: status={player['status']}, ip={player['ip_address']}, last_seen={player['last_seen']}")
                break
        
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

@socketio.on('connect')
def handle_connect():
    """Handle WebSocket client connection"""
    logger.info('Web client connected')
    emit('connection_status', {'connected': is_connected})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket client disconnection"""
    logger.info('Web client disconnected')

if __name__ == '__main__':
    # Initialize the application
    initialize_app()
    
    logger.info("Starting Empyrion Web Helper v0.3.0")
    
    # Debug: Log all registered routes
    logger.info("Registered routes:")
    for rule in app.url_map.iter_rules():
        logger.info(f"  {rule.rule} -> {rule.endpoint}")
    
    # Start the Flask app
    socketio.run(app, debug=True, host='0.0.0.0', port=5001)

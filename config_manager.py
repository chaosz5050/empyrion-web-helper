# FILE LOCATION: /config_manager.py (root directory)
#!/usr/bin/env python3
"""
Configuration Manager for Empyrion Web Helper
Enhanced to use database for secure credential storage
"""

import configparser
import os
import logging

logger = logging.getLogger(__name__)

class ConfigManager:
    """
    Manages application configuration for Empyrion Web Helper.

    Provides configuration loading, saving, and runtime management, with secure credential storage via database integration. Handles migration of legacy credentials, supports interactive credential setup, and ensures no sensitive data is written to config files.
    """
    
    def __init__(self, config_file: str = 'empyrion_helper.conf', player_db=None):
        """
        Initialize the ConfigManager.

        Args:
            config_file (str): Path to the configuration file. Defaults to 'empyrion_helper.conf'.
            player_db (PlayerDatabase, optional): Player database instance for credential management.
        """
        self.config_file = config_file
        self.config = {}
        self.player_db = player_db  # Reference to PlayerDatabase for credentials
        self._set_defaults()
    
    def set_database(self, player_db):
        """
        Set the player database reference after initialization.

        Args:
            player_db (PlayerDatabase): The player database instance.
        """
        self.player_db = player_db
    
    def _set_defaults(self):
        """
        Set default configuration values for the application.

        No sensitive data is included in these defaults.
        """
        self.config = {
            # Server settings (no password here anymore)
            'host': '192.168.1.100',
            'telnet_port': 30004,
            # Monitoring settings
            'update_interval': 40,
            # FTP settings (no sensitive data here)
            'ftp_host': '192.168.1.100:21',
            'remote_log_path': '/path/to/your/scenario/Content/Configuration',
            # Message settings
            'welcome_message': 'Welcome to Space Cowboys, <playername>!',
            'goodbye_message': 'Player <playername> has left our galaxy'
        }
    
    def load_config(self) -> bool:
        """
        Load configuration from file, with credentials retrieved from the database.

        Returns:
            bool: True if configuration loaded successfully, False otherwise.
        """
        if not os.path.exists(self.config_file):
            logger.warning(f"Config file {self.config_file} not found, using defaults")
            self._load_from_database()  # Load from database if no config file
            return False
        
        try:
            parser = configparser.ConfigParser()
            parser.read(self.config_file)
            
            # Load server settings (no password)
            if parser.has_section('server'):
                self.config.update({
                    'host': parser.get('server', 'host', fallback=self.config['host']),
                    'telnet_port': parser.getint('server', 'telnet_port', fallback=self.config['telnet_port'])
                })
                
                # Handle legacy password in config (migrate to database)
                legacy_password = parser.get('server', 'telnet_password', fallback=None)
                if (legacy_password and 
                    legacy_password != 'your_rcon_password_here' and 
                    self.player_db):
                    
                    # Check if we already have credentials in database
                    existing_creds = self.player_db.get_credential('rcon')
                    if not existing_creds:
                        logger.info("Migrating RCON password from config to database")
                        self.player_db.store_credential('rcon', password=legacy_password)
                        logger.info("✅ RCON password migrated to secure database storage")
            
            # Load monitoring settings
            if parser.has_section('monitoring'):
                self.config.update({
                    'update_interval': parser.getint('monitoring', 'update_interval', fallback=self.config['update_interval'])
                })
            
            # Load FTP settings (migrate credentials if present)
            if parser.has_section('ftp'):
                self.config.update({
                    'ftp_host': parser.get('ftp', 'host', fallback=self.config['ftp_host']),
                    'remote_log_path': parser.get('ftp', 'remote_log_path', fallback=self.config['remote_log_path'])
                })
                
                # Handle legacy FTP credentials
                legacy_ftp_user = parser.get('ftp', 'user', fallback=None)
                legacy_ftp_password = parser.get('ftp', 'password', fallback=None)
                
                if (legacy_ftp_password and 
                    legacy_ftp_password != 'your_ftp_password' and 
                    self.player_db):
                    
                    existing_ftp_creds = self.player_db.get_credential('ftp')
                    if not existing_ftp_creds:
                        logger.info("Migrating FTP credentials from config to database")
                        self.player_db.store_credential(
                            'ftp', 
                            username=legacy_ftp_user or '',
                            password=legacy_ftp_password,
                            host=self.config['ftp_host']
                        )
                        logger.info("✅ FTP credentials migrated to secure database storage")
            
            # Load message settings
            if parser.has_section('messages'):
                self.config.update({
                    'welcome_message': parser.get('messages', 'welcome_message', fallback=self.config['welcome_message']),
                    'goodbye_message': parser.get('messages', 'goodbye_message', fallback=self.config['goodbye_message'])
                })
            
            # Load general settings
            if parser.has_section('general'):
                self.config.update({
                    'autoconnect': parser.getboolean('general', 'autoconnect', fallback=True)
                })
            
            # IMPORTANT: Override with database values if they exist
            self._load_from_database()
            
            logger.info(f"Configuration loaded from {self.config_file}")
            return True
        
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return False
    
    def _load_from_database(self):
        """
        Load configuration values from database, overriding config file values.
        This ensures the header shows the REAL values that are being used.
        """
        if not self.player_db:
            return
            
        # Load server settings from database (these are the REAL values being used)
        server_host = self.player_db.get_app_setting('server_host')
        server_port = self.player_db.get_app_setting('server_port')
        ftp_host = self.player_db.get_app_setting('ftp_host')
        ftp_remote_log_path = self.player_db.get_app_setting('ftp_remote_log_path')
        
        # Override config with database values if they exist
        if server_host:
            self.config['host'] = server_host
            logger.debug(f"Using server host from database: {server_host}")
        
        if server_port:
            try:
                self.config['telnet_port'] = int(server_port)
                logger.debug(f"Using server port from database: {server_port}")
            except:
                pass
        
        if ftp_host:
            self.config['ftp_host'] = ftp_host
            
        if ftp_remote_log_path:
            self.config['remote_log_path'] = ftp_remote_log_path
    
    def get(self, key: str, default=None):
        """
        Get a configuration value, with secure credential lookup if needed.

        Args:
            key (str): Configuration key to retrieve.
            default: Default value if key is not found.

        Returns:
            The configuration value, or credential if requested.
        """
        # Handle credential requests
        if key == 'telnet_password':
            if self.player_db:
                creds = self.player_db.get_rcon_credentials()
                if creds and creds.get('password'):
                    return creds['password']
            return os.environ.get('EMPYRION_RCON_PASSWORD', default)
        
        elif key == 'ftp_password':
            if self.player_db:
                creds = self.player_db.get_ftp_credentials()
                if creds and creds.get('password'):
                    return creds['password']
            return os.environ.get('EMPYRION_FTP_PASSWORD', default)
        
        elif key == 'ftp_user':
            if self.player_db:
                creds = self.player_db.get_ftp_credentials()
                if creds and creds.get('username'):
                    return creds['username']
            return os.environ.get('EMPYRION_FTP_USER', default)
        
        # Regular config values
        return self.config.get(key, default)
    
    def get_all(self) -> dict:
        """
        Get all configuration values, with credentials marked as stored securely.
        NOW RETURNS REAL VALUES from database for header display.

        Returns:
            dict: Dictionary of all configuration values, with credential fields replaced by status markers.
        """
        # Start with current config (which now includes database overrides)
        config_copy = self.config.copy()
        
        # Add credential status indicators
        if self.player_db:
            stored_creds = self.player_db.list_stored_credentials()
            
            if 'rcon' in stored_creds:
                config_copy['telnet_password'] = '[STORED SECURELY]'
                config_copy['rcon_status'] = 'Configured'
            else:
                config_copy['telnet_password'] = '[NOT CONFIGURED]'
                config_copy['rcon_status'] = 'Not configured'
            
            if 'ftp' in stored_creds:
                config_copy['ftp_password'] = '[STORED SECURELY]'
                config_copy['ftp_user'] = '[STORED SECURELY]'
                config_copy['ftp_status'] = 'Configured'
            else:
                config_copy['ftp_password'] = '[NOT CONFIGURED]'
                config_copy['ftp_user'] = '[NOT CONFIGURED]'
                config_copy['ftp_status'] = 'Not configured'
        else:
            config_copy['telnet_password'] = '[DATABASE NOT AVAILABLE]'
            config_copy['ftp_password'] = '[DATABASE NOT AVAILABLE]'
            config_copy['ftp_user'] = '[DATABASE NOT AVAILABLE]'
            config_copy['rcon_status'] = 'Database error'
            config_copy['ftp_status'] = 'Database error'
        
        return config_copy
    
    def set(self, key: str, value):
        """
        Set a configuration value at runtime. Credentials must be set via database methods.

        Args:
            key (str): Configuration key to set.
            value: Value to assign to the key.

        Returns:
            bool: True if value set, False otherwise (for credential keys).
        """
        # Credentials must be set via database methods
        if key in ['telnet_password', 'ftp_password', 'ftp_user']:
            logger.warning(f"Cannot set {key} via config - use database credential methods")
            return False
        
        self.config[key] = value
        return True
    
    def save_config(self) -> bool:
        """
        Save the current configuration to file, excluding sensitive data.

        Returns:
            bool: True if configuration saved successfully, False otherwise.
        """
        try:
            parser = configparser.ConfigParser()
            
            # Create sections and populate them (no sensitive data)
            parser.add_section('server')
            parser.set('server', 'host', str(self.config['host']))
            
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            return False
    
    def validate_config(self) -> dict:
        """
        Validate the current configuration and check for missing or invalid settings.

        Returns:
            dict: Validation result with 'valid', 'issues', and 'warnings' keys.
        """
        issues = []
        warnings = []
        
        # Check required server settings
        if not self.config['host'] or self.config['host'] == '192.168.1.100':
            warnings.append("Server host is set to default value")
        
        # Check credential availability (but don't validate actual credentials)
        if self.player_db:
            stored_creds = self.player_db.list_stored_credentials()
            
            if 'rcon' not in stored_creds:
                # Check environment variable as fallback
                if not os.environ.get('EMPYRION_RCON_PASSWORD'):
                    issues.append("RCON credentials are not configured (database or environment)")
                    
        else:
            issues.append("Database not available for credential validation")
        
        if self.config['telnet_port'] < 1 or self.config['telnet_port'] > 65535:
            issues.append("Invalid telnet port number")
        
        if self.config['update_interval'] < 5:
            warnings.append("Update interval below 5 seconds may cause performance issues")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings
        }
    
    def get_server_info(self) -> dict:
        """
        Get server connection information (host, port, update interval).

        Returns:
            dict: Server connection info.
        """
        return {
            'host': self.config['host'],
            'port': self.config['telnet_port'],
            'update_interval': self.config['update_interval']
        }
    
    def setup_credentials_interactive(self):
        """
        Interactively prompt the user to set up all required credentials (RCON, FTP).

        Returns:
            bool: True if setup completed successfully, False otherwise.
        """
        if not self.player_db:
            logger.error("Database not available for credential setup")
            return False
        
        print("\n🔐 Empyrion Web Helper - Credential Setup")
        print("=" * 50)
        
        # Check current status
        stored_creds = self.player_db.list_stored_credentials()
        
        # RCON Setup
        if 'rcon' not in stored_creds and not os.environ.get('EMPYRION_RCON_PASSWORD'):
            print("\n1️⃣ RCON Server Connection Required")
            rcon_creds = self.player_db.get_rcon_credentials()  # This will prompt if needed
            if not rcon_creds:
                print("❌ RCON setup failed - application cannot connect to server")
                return False
        else:
            print("\n✅ RCON credentials are configured")
        
        # FTP Setup (optional)
        setup_ftp = input("\n2️⃣ Set up FTP credentials for future features? (y/N): ").lower().strip()
        if setup_ftp == 'y':
            if 'ftp' not in stored_creds:
                ftp_creds = self.player_db.get_ftp_credentials()  # This will prompt if needed
                if ftp_creds:
                    print("✅ FTP credentials configured")
                else:
                    print("⚠️ FTP setup skipped")
            else:
                print("✅ FTP credentials already configured")
        
        print("\n🎉 Credential setup complete!")
        print("💡 Credentials are stored encrypted in the database")
        print("💡 You can also use environment variables: EMPYRION_RCON_PASSWORD, EMPYRION_FTP_PASSWORD")
        
        return True
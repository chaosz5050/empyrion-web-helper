#!/usr/bin/env python3
"""
Configuration Manager for Empyrion Web Helper
Handles loading and managing configuration from empyrion_helper.conf
"""

import configparser
import os
import logging

logger = logging.getLogger(__name__)

class ConfigManager:
    """Manages application configuration from empyrion_helper.conf"""
    
    def __init__(self, config_file: str = 'empyrion_helper.conf'):
        self.config_file = config_file
        self.config = {}
        self._set_defaults()
    
    def _set_defaults(self):
        """Set default configuration values"""
        self.config = {
            # Server settings
            'host': '192.168.1.100',
            'telnet_port': 30004,
            'telnet_password': 'your_rcon_password_here',
            
            # Monitoring settings
            'update_interval': 20,
            'log_file': 'empyrion_helper.log',
            
            # FTP settings (for future use)
            'ftp_host': '192.168.1.100:21',
            'ftp_user': 'your_ftp_username',
            'ftp_password': 'your_ftp_password',
            'remote_log_path': '/path/to/your/scenario/Content/Configuration',
            
            # Message settings (for future use)
            'welcome_message': 'Welcome to Space Cowboys, <playername>!',
            'goodbye_message': 'Player <playername> has left our galaxy',
            
            # General settings
            'autoconnect': False
        }
    
    def load_config(self) -> bool:
        """
        Load configuration from file
        Returns True if file was loaded, False if using defaults
        """
        if not os.path.exists(self.config_file):
            logger.warning(f"Config file {self.config_file} not found, using defaults")
            return False
        
        try:
            parser = configparser.ConfigParser()
            parser.read(self.config_file)
            
            # Load server settings
            if parser.has_section('server'):
                self.config.update({
                    'host': parser.get('server', 'host', fallback=self.config['host']),
                    'telnet_port': parser.getint('server', 'telnet_port', fallback=self.config['telnet_port']),
                    'telnet_password': parser.get('server', 'telnet_password', fallback=self.config['telnet_password'])
                })
            
            # Load monitoring settings
            if parser.has_section('monitoring'):
                self.config.update({
                    'update_interval': parser.getint('monitoring', 'update_interval', fallback=self.config['update_interval']),
                    'log_file': parser.get('monitoring', 'log_file', fallback=self.config['log_file'])
                })
            
            # Load FTP settings (for future phases)
            if parser.has_section('ftp'):
                self.config.update({
                    'ftp_host': parser.get('ftp', 'host', fallback=self.config['ftp_host']),
                    'ftp_user': parser.get('ftp', 'user', fallback=self.config['ftp_user']),
                    'ftp_password': parser.get('ftp', 'password', fallback=self.config['ftp_password']),
                    'remote_log_path': parser.get('ftp', 'remote_log_path', fallback=self.config['remote_log_path'])
                })
            
            # Load message settings (for future phases)
            if parser.has_section('messages'):
                self.config.update({
                    'welcome_message': parser.get('messages', 'welcome_message', fallback=self.config['welcome_message']),
                    'goodbye_message': parser.get('messages', 'goodbye_message', fallback=self.config['goodbye_message'])
                })
            
            # Load general settings
            if parser.has_section('general'):
                self.config.update({
                    'autoconnect': parser.getboolean('general', 'autoconnect', fallback=self.config['autoconnect'])
                })
            
            logger.info(f"Configuration loaded from {self.config_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return False
    
    def get(self, key: str, default=None):
        """Get a configuration value"""
        return self.config.get(key, default)
    
    def get_all(self) -> dict:
        """Get all configuration values"""
        return self.config.copy()
    
    def set(self, key: str, value):
        """Set a configuration value (runtime only)"""
        self.config[key] = value
    
    def save_config(self) -> bool:
        """
        Save current configuration to file
        Returns True if successful, False otherwise
        """
        try:
            parser = configparser.ConfigParser()
            
            # Create sections and populate them
            parser.add_section('server')
            parser.set('server', 'host', str(self.config['host']))
            parser.set('server', 'telnet_port', str(self.config['telnet_port']))
            parser.set('server', 'telnet_password', str(self.config['telnet_password']))
            
            parser.add_section('monitoring')
            parser.set('monitoring', 'update_interval', str(self.config['update_interval']))
            parser.set('monitoring', 'log_file', str(self.config['log_file']))
            
            parser.add_section('ftp')
            parser.set('ftp', 'host', str(self.config['ftp_host']))
            parser.set('ftp', 'user', str(self.config['ftp_user']))
            parser.set('ftp', 'password', str(self.config['ftp_password']))
            parser.set('ftp', 'remote_log_path', str(self.config['remote_log_path']))
            
            parser.add_section('messages')
            parser.set('messages', 'welcome_message', str(self.config['welcome_message']))
            parser.set('messages', 'goodbye_message', str(self.config['goodbye_message']))
            
            parser.add_section('general')
            parser.set('general', 'autoconnect', str(self.config['autoconnect']))
            
            # Write to file
            with open(self.config_file, 'w') as f:
                parser.write(f)
            
            logger.info(f"Configuration saved to {self.config_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            return False
    
    def validate_config(self) -> dict:
        """
        Validate current configuration
        Returns dict with validation results
        """
        issues = []
        warnings = []
        
        # Check required server settings
        if not self.config['host'] or self.config['host'] == '192.168.1.100':
            warnings.append("Server host is set to default value")
        
        if not self.config['telnet_password'] or self.config['telnet_password'] == 'your_rcon_password_here':
            issues.append("RCON password is not configured")
        
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
        """Get server connection information"""
        return {
            'host': self.config['host'],
            'port': self.config['telnet_port'],
            'update_interval': self.config['update_interval']
        }

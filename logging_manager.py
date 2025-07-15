# FILE LOCATION: /logging_manager.py (root directory)
#!/usr/bin/env python3
"""
Logging Manager for Empyrion Web Helper
Handles log rotation, cleanup, and management
"""

import logging
import logging.handlers
import os
import glob
import configparser
from datetime import datetime, timedelta
from typing import List, Dict, Optional

class LoggingManager:
    """Manages logging configuration and rotation for the application"""
    
    def __init__(self, config_file: str = "empyrion_helper.conf"):
        self.config_file = config_file
        self.logger = logging.getLogger(__name__)
        
        # Default settings
        self.log_file = "empyrion_helper.log"
        self.max_bytes = 1 * 1024 * 1024  # 1MB
        self.backup_count = 3  # Keep 3 backup files
        self.max_age_days = 7  # Delete logs older than 7 days
        
        # Load settings from config
        self._load_config()
    
    def _load_config(self):
        """Load logging configuration from empyrion_helper.conf"""
        try:
            config = configparser.ConfigParser()
            
            if os.path.exists(self.config_file):
                config.read(self.config_file)
                
                if config.has_section('logging'):
                    self.log_file = config.get('logging', 'log_file', fallback=self.log_file)
                    self.max_bytes = config.getint('logging', 'max_size_mb', fallback=1) * 1024 * 1024
                    self.backup_count = config.getint('logging', 'backup_count', fallback=3)
                    self.max_age_days = config.getint('logging', 'max_age_days', fallback=7)
                    
                    self.logger.info(f"Loaded logging config: {self.log_file}, max={self.max_bytes/1024/1024:.1f}MB, backups={self.backup_count}, max_age={self.max_age_days}d")
                else:
                    self.logger.info("No [logging] section in config, using defaults")
            else:
                self.logger.warning(f"Config file {self.config_file} not found, using defaults")
                
        except Exception as e:
            self.logger.error(f"Error loading logging config: {e}")
    
    def _save_config(self):
        """Save logging configuration to empyrion_helper.conf"""
        try:
            config = configparser.ConfigParser()
            
            # Read existing config
            if os.path.exists(self.config_file):
                config.read(self.config_file)
            
            # Ensure logging section exists
            if not config.has_section('logging'):
                config.add_section('logging')
            
            # Save logging settings
            config.set('logging', 'log_file', self.log_file)
            config.set('logging', 'max_size_mb', str(self.max_bytes // (1024 * 1024)))
            config.set('logging', 'backup_count', str(self.backup_count))
            config.set('logging', 'max_age_days', str(self.max_age_days))
            
            # Write back to file
            with open(self.config_file, 'w', encoding='utf-8') as f:
                config.write(f)
            
            self.logger.info("Logging configuration saved to empyrion_helper.conf")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving logging config: {e}")
            return False
    
    def setup_rotating_logger(self, logger_name: str = None, level: int = logging.INFO) -> logging.Logger:
        """Set up rotating file handler for the application logger"""
        try:
            # Get the root logger if no specific logger requested
            if logger_name:
                logger = logging.getLogger(logger_name)
            else:
                logger = logging.getLogger()
            
            # Remove existing handlers to avoid duplicates
            for handler in logger.handlers[:]:
                logger.removeHandler(handler)
            
            # Create rotating file handler
            file_handler = logging.handlers.RotatingFileHandler(
                self.log_file,
                maxBytes=self.max_bytes,
                backupCount=self.backup_count,
                encoding='utf-8'
            )
            
            # Create console handler
            console_handler = logging.StreamHandler()
            
            # Create formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            
            # Set formatters
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)
            
            # Add handlers to logger
            logger.addHandler(file_handler)
            logger.addHandler(console_handler)
            
            # Set level
            logger.setLevel(level)
            
            # Prevent propagation to avoid duplicate logs
            logger.propagate = False
            
            self.logger.info(f"Rotating logger configured: {self.log_file} (max {self.max_bytes/1024/1024:.1f}MB, {self.backup_count} backups)")
            
            return logger
            
        except Exception as e:
            print(f"Error setting up rotating logger: {e}")
            # Fallback to basic logging
            logging.basicConfig(level=level, format='%(asctime)s - %(levelname)s - %(message)s')
            return logging.getLogger()
    
    def cleanup_old_logs(self) -> Dict[str, int]:
        """Clean up old log files based on age"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.max_age_days)
            
            # Find all log files (including rotated ones)
            log_pattern = f"{self.log_file}*"
            log_files = glob.glob(log_pattern)
            
            deleted_count = 0
            deleted_size = 0
            
            for log_file in log_files:
                try:
                    # Skip the current log file
                    if log_file == self.log_file:
                        continue
                    
                    # Check file age
                    file_time = datetime.fromtimestamp(os.path.getmtime(log_file))
                    
                    if file_time < cutoff_date:
                        file_size = os.path.getsize(log_file)
                        os.remove(log_file)
                        deleted_count += 1
                        deleted_size += file_size
                        self.logger.info(f"Deleted old log file: {log_file} ({file_size} bytes)")
                        
                except Exception as e:
                    self.logger.warning(f"Could not delete log file {log_file}: {e}")
            
            if deleted_count > 0:
                self.logger.info(f"Cleaned up {deleted_count} old log files ({deleted_size} bytes)")
            
            return {
                'deleted_files': deleted_count,
                'deleted_bytes': deleted_size
            }
            
        except Exception as e:
            self.logger.error(f"Error cleaning up old logs: {e}")
            return {'deleted_files': 0, 'deleted_bytes': 0}
    
    def get_log_stats(self) -> Dict[str, any]:
        """Get statistics about log files"""
        try:
            stats = {
                'current_log': {
                    'file': self.log_file,
                    'exists': False,
                    'size': 0,
                    'size_mb': 0.0,
                    'modified': None
                },
                'backup_logs': [],
                'total_size': 0,
                'total_files': 0
            }
            
            # Check current log file
            if os.path.exists(self.log_file):
                size = os.path.getsize(self.log_file)
                modified = datetime.fromtimestamp(os.path.getmtime(self.log_file))
                
                stats['current_log'].update({
                    'exists': True,
                    'size': size,
                    'size_mb': size / (1024 * 1024),
                    'modified': modified.isoformat()
                })
                
                stats['total_size'] += size
                stats['total_files'] += 1
            
            # Check backup log files
            log_pattern = f"{self.log_file}.*"
            backup_files = glob.glob(log_pattern)
            
            for backup_file in sorted(backup_files):
                if os.path.exists(backup_file):
                    size = os.path.getsize(backup_file)
                    modified = datetime.fromtimestamp(os.path.getmtime(backup_file))
                    
                    stats['backup_logs'].append({
                        'file': backup_file,
                        'size': size,
                        'size_mb': size / (1024 * 1024),
                        'modified': modified.isoformat()
                    })
                    
                    stats['total_size'] += size
                    stats['total_files'] += 1
            
            stats['total_size_mb'] = stats['total_size'] / (1024 * 1024)
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting log stats: {e}")
            return {}
    
    def clear_all_logs(self) -> bool:
        """Clear all log files (current and backups)"""
        try:
            # Find all log files
            log_pattern = f"{self.log_file}*"
            log_files = glob.glob(log_pattern)
            
            deleted_count = 0
            
            for log_file in log_files:
                try:
                    if os.path.exists(log_file):
                        os.remove(log_file)
                        deleted_count += 1
                        print(f"Deleted log file: {log_file}")  # Use print since we're clearing logs
                        
                except Exception as e:
                    print(f"Could not delete log file {log_file}: {e}")
            
            if deleted_count > 0:
                print(f"Cleared {deleted_count} log files")
                
                # Restart logging
                self.setup_rotating_logger()
                self.logger.info("Log files cleared and logging restarted")
            
            return deleted_count > 0
            
        except Exception as e:
            print(f"Error clearing logs: {e}")
            return False
    
    def get_recent_logs(self, lines: int = 100) -> List[str]:
        """Get recent log entries from the current log file"""
        try:
            if not os.path.exists(self.log_file):
                return []
            
            with open(self.log_file, 'r', encoding='utf-8') as f:
                # Read all lines and return the last N lines
                all_lines = f.readlines()
                return [line.strip() for line in all_lines[-lines:]]
                
        except Exception as e:
            self.logger.error(f"Error reading recent logs: {e}")
            return []
    
    def update_settings(self, max_size_mb: int = None, backup_count: int = None, max_age_days: int = None) -> bool:
        """Update logging settings"""
        try:
            if max_size_mb is not None:
                self.max_bytes = max_size_mb * 1024 * 1024
            if backup_count is not None:
                self.backup_count = backup_count
            if max_age_days is not None:
                self.max_age_days = max_age_days
            
            # Save to config
            success = self._save_config()
            
            if success:
                # Restart logging with new settings
                self.setup_rotating_logger()
                self.logger.info(f"Updated logging settings: max={self.max_bytes/1024/1024:.1f}MB, backups={self.backup_count}, max_age={self.max_age_days}d")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error updating logging settings: {e}")
            return False
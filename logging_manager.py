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
    """
    Manages logging configuration, rotation, cleanup, and statistics for the Empyrion Web Helper application.

    Provides methods for loading and saving logging settings, setting up rotating loggers, cleaning up old logs, retrieving log statistics, and managing log files.
    """
    
    def __init__(self, config_file: str = "empyrion_helper.conf"):
        """
        Initialize the LoggingManager.

        Args:
            config_file (str, optional): Path to the configuration file. Defaults to 'empyrion_helper.conf'.
        """
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
        """
        Load logging configuration from the empyrion_helper.conf file.
        """
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
        """
        Save logging configuration to the empyrion_helper.conf file.

        Returns:
            bool: True if saved successfully, False otherwise.
        """
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
        """
        Set up a rotating file handler for the application logger.

        Args:
            logger_name (str, optional): Name of the logger to configure. Defaults to root logger.
            level (int, optional): Logging level. Defaults to logging.INFO.

        Returns:
            logging.Logger: Configured logger instance.
        """
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
        """
        Clean up old log files based on their age.

        Returns:
            Dict[str, int]: Dictionary with number of deleted files and total bytes deleted.
        """
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
        """
        Get statistics about the current and backup log files.

        Returns:
            Dict[str, any]: Dictionary with log file statistics.
        """
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
                
                self.logger.info(f"DEBUG: Current log file {self.log_file} - size: {size} bytes ({size/(1024*1024):.3f} MB)")
            else:
                self.logger.warning(f"DEBUG: Current log file {self.log_file} does not exist")
            
            # Check backup log files
            log_pattern = f"{self.log_file}.*"
            backup_files = glob.glob(log_pattern)
            
            self.logger.info(f"DEBUG: Found backup files with pattern '{log_pattern}': {backup_files}")
            
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
                    
                    self.logger.info(f"DEBUG: Backup log {backup_file} - size: {size} bytes")
            
            stats['total_size_mb'] = stats['total_size'] / (1024 * 1024)
            
            self.logger.info(f"DEBUG: Final stats - total files: {stats['total_files']}, total size: {stats['total_size']} bytes ({stats['total_size_mb']:.3f} MB)")
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting log stats: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return {}
    
    def clear_all_logs(self) -> bool:
        """
        Clear all log files, including current and backup files.

        Returns:
            bool: True if any log files were deleted, False otherwise.
        """
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
        """
        Get recent log entries from the current log file.

        Args:
            lines (int, optional): Number of recent lines to retrieve. Defaults to 100.

        Returns:
            List[str]: List of recent log lines.
        """
        try:
            self.logger.info(f"DEBUG: Getting recent logs from {self.log_file}, requesting {lines} lines")
            
            if not os.path.exists(self.log_file):
                self.logger.warning(f"DEBUG: Log file {self.log_file} does not exist")
                return []
            
            file_size = os.path.getsize(self.log_file)
            self.logger.info(f"DEBUG: Log file size: {file_size} bytes")
            
            with open(self.log_file, 'r', encoding='utf-8') as f:
                # Read all lines and return the last N lines
                all_lines = f.readlines()
                self.logger.info(f"DEBUG: Read {len(all_lines)} total lines from log file")
                
                recent_lines = [line.strip() for line in all_lines[-lines:]]
                self.logger.info(f"DEBUG: Returning {len(recent_lines)} recent lines")
                
                return recent_lines
                
        except Exception as e:
            self.logger.error(f"Error reading recent logs: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return []
    
    def update_settings(self, max_size_mb: int = None, backup_count: int = None, max_age_days: int = None) -> bool:
        """
        Update logging settings and save them to the configuration file.

        Args:
            max_size_mb (int, optional): Maximum log file size in MB. Defaults to None.
            backup_count (int, optional): Number of backup log files to keep. Defaults to None.
            max_age_days (int, optional): Maximum age for log files in days. Defaults to None.

        Returns:
            bool: True if settings updated successfully, False otherwise.
        """
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
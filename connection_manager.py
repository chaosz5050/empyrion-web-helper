"""
Enhanced Connection Manager for Empyrion Web Helper
Supports both FTP and SFTP with automatic detection and certificate handling
"""

import ftplib
import paramiko
import socket
import ssl
import logging
import tempfile
import os
from io import BytesIO
from typing import Dict, Any, Optional, Tuple, List
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class ConnectionResult:
    """Result object for connection attempts"""
    def __init__(self, success: bool, connection_type: str = None, message: str = None, details: Dict = None):
        self.success = success
        self.connection_type = connection_type  # 'ftp', 'ftps', 'sftp'
        self.message = message
        self.details = details or {}

class EnhancedConnectionManager:
    """
    Enhanced connection manager supporting FTP, FTPS, and SFTP with automatic detection
    """
    
    def __init__(self):
        self.connection_types = ['sftp', 'ftps', 'ftp']  # Try in order of preference
        
    def detect_and_connect(self, host: str, port: int, username: str, password: str, timeout: int = 10) -> ConnectionResult:
        """
        Automatically detect connection type and establish connection
        
        Args:
            host: Server hostname or IP
            port: Server port
            username: Username for authentication
            password: Password for authentication
            timeout: Connection timeout in seconds
            
        Returns:
            ConnectionResult with connection details
        """
        logger.info(f"🔍 Auto-detecting connection type for {host}:{port}")
        
        # Try connection types in order of preference
        last_error = None
        
        for conn_type in self.connection_types:
            logger.info(f"🔌 Trying {conn_type.upper()} connection to {host}:{port}")
            
            try:
                if conn_type == 'sftp':
                    result = self._try_sftp_connection(host, port, username, password, timeout)
                elif conn_type == 'ftps':
                    result = self._try_ftps_connection(host, port, username, password, timeout)
                else:  # ftp
                    result = self._try_ftp_connection(host, port, username, password, timeout)
                
                if result.success:
                    logger.info(f"✅ Successfully connected using {conn_type.upper()}")
                    return result
                else:
                    last_error = result.message
                    logger.warning(f"❌ {conn_type.upper()} failed: {result.message}")
                    
            except Exception as e:
                last_error = str(e)
                logger.warning(f"❌ {conn_type.upper()} failed with exception: {e}")
                
        return ConnectionResult(
            success=False, 
            message=f"All connection types failed. Last error: {last_error}"
        )
    
    def _try_sftp_connection(self, host: str, port: int, username: str, password: str, timeout: int) -> ConnectionResult:
        """Try SFTP connection with certificate handling"""
        try:
            # Create SSH client with automatic host key acceptance
            ssh_client = paramiko.SSHClient()
            
            # Accept unknown host keys (handles certificate issues)
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Try connecting with password authentication
            ssh_client.connect(
                hostname=host,
                port=port,
                username=username,
                password=password,
                timeout=timeout,
                allow_agent=False,
                look_for_keys=False
            )
            
            # Test SFTP functionality
            sftp_client = ssh_client.open_sftp()
            
            # Try to list remote directory to verify connection
            try:
                file_list = sftp_client.listdir('.')
                sftp_client.close()
                ssh_client.close()
                
                return ConnectionResult(
                    success=True,
                    connection_type='sftp',
                    message='SFTP connection successful',
                    details={
                        'files_found': len(file_list),
                        'supports_certificates': True,
                        'method': 'password'
                    }
                )
            except Exception as list_error:
                sftp_client.close()
                ssh_client.close()
                return ConnectionResult(
                    success=False,
                    message=f"SFTP connection established but directory listing failed: {list_error}"
                )
                
        except paramiko.AuthenticationException:
            return ConnectionResult(
                success=False,
                message="SFTP authentication failed - invalid username/password"
            )
        except paramiko.SSHException as e:
            return ConnectionResult(
                success=False,
                message=f"SFTP SSH error: {e}"
            )
        except socket.timeout:
            return ConnectionResult(
                success=False,
                message="SFTP connection timeout"
            )
        except Exception as e:
            return ConnectionResult(
                success=False,
                message=f"SFTP connection failed: {e}"
            )
    
    def _try_ftps_connection(self, host: str, port: int, username: str, password: str, timeout: int) -> ConnectionResult:
        """Try FTPS connection with SSL/TLS"""
        try:
            # Try implicit FTPS first (usually port 990)
            if port == 990 or port == 21:
                try:
                    ftp = ftplib.FTP_TLS()
                    ftp.connect(host, port, timeout)
                    ftp.login(username, password)
                    ftp.prot_p()  # Enable encryption for data transfers
                    
                    # Test directory listing
                    files = ftp.nlst()
                    ftp.quit()
                    
                    return ConnectionResult(
                        success=True,
                        connection_type='ftps',
                        message='FTPS connection successful',
                        details={
                            'files_found': len(files),
                            'ssl_enabled': True,
                            'mode': 'implicit' if port == 990 else 'explicit'
                        }
                    )
                except Exception as ftps_error:
                    logger.debug(f"FTPS attempt failed: {ftps_error}")
                    
            return ConnectionResult(
                success=False,
                message="FTPS connection not supported or failed"
            )
            
        except Exception as e:
            return ConnectionResult(
                success=False,
                message=f"FTPS connection failed: {e}"
            )
    
    def _try_ftp_connection(self, host: str, port: int, username: str, password: str, timeout: int) -> ConnectionResult:
        """Try standard FTP connection"""
        try:
            ftp = ftplib.FTP()
            ftp.connect(host, port, timeout)
            ftp.login(username, password)
            
            # Test directory listing
            files = ftp.nlst()
            ftp.quit()
            
            return ConnectionResult(
                success=True,
                connection_type='ftp',
                message='FTP connection successful',
                details={
                    'files_found': len(files),
                    'ssl_enabled': False,
                    'mode': 'standard'
                }
            )
            
        except ftplib.error_perm as e:
            return ConnectionResult(
                success=False,
                message=f"FTP permission error: {e}"
            )
        except socket.timeout:
            return ConnectionResult(
                success=False,
                message="FTP connection timeout"
            )
        except Exception as e:
            return ConnectionResult(
                success=False,
                message=f"FTP connection failed: {e}"
            )

class UniversalFileClient:
    """
    Universal file transfer client that works with FTP, FTPS, and SFTP
    """
    
    def __init__(self, connection_type: str, host: str, port: int, username: str, password: str):
        self.connection_type = connection_type
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self._client = None
        self._sftp_client = None
        
    @contextmanager
    def connect(self):
        """Context manager for connections"""
        try:
            if self.connection_type == 'sftp':
                # SSH/SFTP connection
                self._client = paramiko.SSHClient()
                self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                self._client.connect(
                    hostname=self.host,
                    port=self.port,
                    username=self.username,
                    password=self.password,
                    timeout=10,
                    allow_agent=False,
                    look_for_keys=False
                )
                self._sftp_client = self._client.open_sftp()
                yield self
                
            elif self.connection_type == 'ftps':
                # FTPS connection
                self._client = ftplib.FTP_TLS()
                self._client.connect(self.host, self.port, timeout=10)
                self._client.login(self.username, self.password)
                self._client.prot_p()
                yield self
                
            else:  # ftp
                # Standard FTP connection
                self._client = ftplib.FTP()
                self._client.connect(self.host, self.port, timeout=10)
                self._client.login(self.username, self.password)
                yield self
                
        finally:
            self._cleanup()
    
    def _cleanup(self):
        """Clean up connections"""
        try:
            if self._sftp_client:
                self._sftp_client.close()
            if self._client:
                if hasattr(self._client, 'quit'):
                    self._client.quit()
                elif hasattr(self._client, 'close'):
                    self._client.close()
        except:
            pass
    
    def download_file(self, remote_path: str, local_file_obj):
        """Download a file to a file-like object"""
        if self.connection_type == 'sftp':
            # SFTP download
            with self._sftp_client.open(remote_path, 'rb') as remote_file:
                while True:
                    chunk = remote_file.read(8192)
                    if not chunk:
                        break
                    local_file_obj.write(chunk)
        else:
            # FTP/FTPS download
            self._client.retrbinary(f'RETR {remote_path}', local_file_obj.write)
    
    def upload_file(self, local_file_obj, remote_path: str):
        """Upload a file from a file-like object"""
        if self.connection_type == 'sftp':
            # SFTP upload
            with self._sftp_client.open(remote_path, 'wb') as remote_file:
                local_file_obj.seek(0)
                while True:
                    chunk = local_file_obj.read(8192)
                    if not chunk:
                        break
                    remote_file.write(chunk)
        else:
            # FTP/FTPS upload
            local_file_obj.seek(0)
            self._client.storbinary(f'STOR {remote_path}', local_file_obj)
    
    def list_directory(self, path: str = '.') -> List[str]:
        """List directory contents"""
        if self.connection_type == 'sftp':
            return self._sftp_client.listdir(path)
        else:
            # FTP/FTPS
            if path != '.':
                self._client.cwd(path)
            return self._client.nlst()
    
    def get_file_info(self, remote_path: str) -> Dict[str, Any]:
        """Get file information"""
        try:
            if self.connection_type == 'sftp':
                stat = self._sftp_client.stat(remote_path)
                import stat as stat_module
                return {
                    'size': stat.st_size,
                    'modified': stat.st_mtime,
                    'is_directory': stat_module.S_ISDIR(stat.st_mode),
                    'exists': True
                }
            else:
                # For FTP, we need to use SIZE command
                try:
                    size = self._client.size(remote_path)
                    return {
                        'size': size,
                        'is_directory': False,
                        'exists': True
                    }
                except:
                    # Could be a directory - FTP SIZE command fails on directories
                    return {'exists': True, 'size': 0, 'is_directory': True}
        except:
            return {'exists': False}
    
    def list_directories_only(self, path: str = '.') -> List[str]:
        """List only directories in the given path"""
        try:
            if self.connection_type == 'sftp':
                all_items = self._sftp_client.listdir(path)
                directories = []
                for item in all_items:
                    try:
                        full_path = f"{path}/{item}" if path != '.' else item
                        stat = self._sftp_client.stat(full_path)
                        import stat as stat_module
                        if stat_module.S_ISDIR(stat.st_mode):
                            directories.append(item)
                    except:
                        continue
                return directories
            else:
                # For FTP, parse LIST command output to identify directories
                if path != '.':
                    current_dir = self._client.pwd()
                    self._client.cwd(path)
                
                entries = []
                self._client.retrlines('LIST', entries.append)
                
                if path != '.':
                    self._client.cwd(current_dir)
                
                directories = []
                for entry in entries:
                    if entry.startswith('d') and len(entry.split()) >= 9:
                        # Directory entry format: drwxr-xr-x ... filename
                        parts = entry.split()
                        dir_name = ' '.join(parts[8:])  # Handle spaces in names
                        directories.append(dir_name)
                
                return directories
        except Exception as e:
            logger.warning(f"Error listing directories: {e}")
            return []

def test_connection_with_auto_detection(host: str, port: int, username: str, password: str) -> Dict[str, Any]:
    """
    Test connection with automatic detection for backward compatibility
    
    Returns:
        Dictionary with connection test results
    """
    manager = EnhancedConnectionManager()
    result = manager.detect_and_connect(host, port, username, password)
    
    return {
        'success': result.success,
        'connection_type': result.connection_type,
        'message': result.message,
        'details': result.details
    }
#!/usr/bin/env python3
"""
Empyrion Connection Debugger
Enhanced debugging tool for troubleshooting RCON connections with different hosting providers
"""

import socket
import time
import sys
import logging

# Set up detailed logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EmpyrionConnectionDebugger:
    """Debug tool for testing RCON connections with different hosting providers"""
    
    def __init__(self, host, port, password):
        self.host = host
        self.port = port
        self.password = password
        self.socket = None
        
    def debug_connection(self):
        """Comprehensive connection debugging"""
        print(f"\n🔍 DEBUGGING CONNECTION TO {self.host}:{self.port}")
        print("=" * 60)
        
        # Step 1: Basic connectivity test
        print("\n1️⃣ Testing basic socket connection...")
        if not self._test_socket_connection():
            return False
            
        # Step 2: Detailed connection analysis
        print("\n2️⃣ Analyzing connection behavior...")
        self._analyze_connection_behavior()
        
        # Step 3: Test different authentication methods
        print("\n3️⃣ Testing authentication methods...")
        self._test_authentication_methods()
        
        return True
    
    def _test_socket_connection(self):
        """Test basic socket connectivity"""
        try:
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_socket.settimeout(10)
            
            print(f"  Connecting to {self.host}:{self.port}...")
            start_time = time.time()
            test_socket.connect((self.host, self.port))
            connect_time = time.time() - start_time
            
            print(f"  ✅ Socket connection successful ({connect_time:.3f}s)")
            test_socket.close()
            return True
            
        except socket.timeout:
            print(f"  ❌ Connection timeout - server may not be running")
            return False
        except ConnectionRefusedError:
            print(f"  ❌ Connection refused - check if RCON is enabled")
            return False
        except Exception as e:
            print(f"  ❌ Connection failed: {e}")
            return False
    
    def _analyze_connection_behavior(self):
        """Analyze how the server behaves on connection"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)
            self.socket.connect((self.host, self.port))
            
            print("  📡 Connected, analyzing server behavior...")
            
            # Check for immediate data (welcome message)
            print("  🔍 Checking for welcome message...")
            try:
                self.socket.settimeout(2.0)  # Short timeout for welcome
                welcome_data = self.socket.recv(1024)
                if welcome_data:
                    decoded = welcome_data.decode('utf-8', errors='ignore')
                    print(f"  📨 Welcome message received: '{decoded.strip()}'")
                    print(f"  📊 Welcome data length: {len(welcome_data)} bytes")
                    print(f"  🔢 Raw bytes: {welcome_data[:50]}...")
                else:
                    print("  📭 No immediate welcome message")
            except socket.timeout:
                print("  📭 No welcome message within 2 seconds")
            except Exception as e:
                print(f"  ⚠️ Error reading welcome: {e}")
            
            # Test server responsiveness
            print("  🔍 Testing server responsiveness...")
            try:
                self.socket.settimeout(5.0)
                test_command = "help\n"
                print(f"  📤 Sending test command: '{test_command.strip()}'")
                self.socket.send(test_command.encode('utf-8'))
                
                time.sleep(1)  # Give server time to process
                
                response = self.socket.recv(2048)
                if response:
                    decoded = response.decode('utf-8', errors='ignore')
                    print(f"  📨 Server response: '{decoded[:100]}...'")
                    if "Available commands" in decoded or "help" in decoded.lower():
                        print("  ✅ Server responds to commands (already authenticated?)")
                    elif "password" in decoded.lower() or "login" in decoded.lower():
                        print("  🔐 Server requesting authentication")
                    else:
                        print("  ❓ Unexpected response format")
                else:
                    print("  📭 No response to test command")
                    
            except socket.timeout:
                print("  ⏰ Server didn't respond within 5 seconds")
            except Exception as e:
                print(f"  ⚠️ Error testing responsiveness: {e}")
                
        except Exception as e:
            print(f"  ❌ Analysis failed: {e}")
        finally:
            if self.socket:
                self.socket.close()
                self.socket = None
    
    def _test_authentication_methods(self):
        """Test different authentication approaches"""
        auth_methods = [
            ("Standard Password", self._test_standard_auth),
            ("Password with \\r\\n", self._test_crlf_auth),
            ("Username + Password", self._test_user_pass_auth),
            ("Direct Command", self._test_direct_command),
        ]
        
        for method_name, method_func in auth_methods:
            print(f"\n  🔐 Testing: {method_name}")
            try:
                success = method_func()
                if success:
                    print(f"  ✅ {method_name} SUCCESS!")
                    return True
                else:
                    print(f"  ❌ {method_name} failed")
            except Exception as e:
                print(f"  ⚠️ {method_name} error: {e}")
                
        print("\n  ❌ All authentication methods failed")
        return False
    
    def _test_standard_auth(self):
        """Test standard password authentication (current method)"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)
            self.socket.connect((self.host, self.port))
            
            # Wait for any welcome message
            time.sleep(1.0)
            try:
                welcome = self.socket.recv(1024)
                print(f"    📨 Welcome: '{welcome.decode('utf-8', errors='ignore').strip()}'")
            except:
                pass
            
            # Send password
            auth_cmd = f"{self.password}\r\n"
            print(f"    📤 Sending: '{self.password}\\r\\n'")
            self.socket.send(auth_cmd.encode('utf-8'))
            
            time.sleep(1.0)
            
            # Check response
            response = self.socket.recv(1024)
            decoded = response.decode('utf-8', errors='ignore')
            print(f"    📨 Auth response: '{decoded.strip()}'")
            
            if "success" in decoded.lower() or "logged in" in decoded.lower():
                # Test with help command
                self.socket.send(b"help\n")
                time.sleep(1)
                help_response = self.socket.recv(2048)
                help_decoded = help_response.decode('utf-8', errors='ignore')
                
                if "Available commands" in help_decoded:
                    return True
                    
            return False
            
        finally:
            if self.socket:
                self.socket.close()
                self.socket = None
    
    def _test_crlf_auth(self):
        """Test with explicit \\r\\n line endings"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)
            self.socket.connect((self.host, self.port))
            
            time.sleep(1.0)
            try:
                self.socket.recv(1024)  # Clear welcome
            except:
                pass
            
            # Try different line ending combinations
            for ending in ["\r\n", "\n", "\r"]:
                auth_cmd = f"{self.password}{ending}"
                print(f"    📤 Trying ending: {repr(ending)}")
                self.socket.send(auth_cmd.encode('utf-8'))
                
                time.sleep(0.5)
                try:
                    response = self.socket.recv(1024)
                    decoded = response.decode('utf-8', errors='ignore')
                    if "success" in decoded.lower() or "logged in" in decoded.lower():
                        print(f"    ✅ Success with ending: {repr(ending)}")
                        return True
                except:
                    pass
                    
            return False
            
        finally:
            if self.socket:
                self.socket.close()
                self.socket = None
    
    def _test_user_pass_auth(self):
        """Test username + password authentication"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)
            self.socket.connect((self.host, self.port))
            
            time.sleep(1.0)
            try:
                self.socket.recv(1024)  # Clear welcome
            except:
                pass
            
            # Try common username formats
            usernames = ["admin", "rcon", "server", "empyrion"]
            
            for username in usernames:
                print(f"    📤 Trying username: {username}")
                
                # Send username first
                self.socket.send(f"{username}\n".encode('utf-8'))
                time.sleep(0.5)
                
                # Send password
                self.socket.send(f"{self.password}\n".encode('utf-8'))
                time.sleep(1.0)
                
                try:
                    response = self.socket.recv(1024)
                    decoded = response.decode('utf-8', errors='ignore')
                    if "success" in decoded.lower() or "logged in" in decoded.lower():
                        print(f"    ✅ Success with username: {username}")
                        return True
                except:
                    pass
                    
            return False
            
        finally:
            if self.socket:
                self.socket.close()
                self.socket = None
    
    def _test_direct_command(self):
        """Test sending commands without explicit authentication"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)
            self.socket.connect((self.host, self.port))
            
            time.sleep(1.0)
            try:
                self.socket.recv(1024)  # Clear welcome
            except:
                pass
            
            # Try sending help command directly
            print(f"    📤 Sending help command directly")
            self.socket.send(b"help\n")
            time.sleep(2.0)
            
            response = self.socket.recv(2048)
            decoded = response.decode('utf-8', errors='ignore')
            
            if "Available commands" in decoded:
                print(f"    ✅ Server doesn't require authentication!")
                return True
                
            return False
            
        finally:
            if self.socket:
                self.socket.close()
                self.socket = None

def main():
    """Main debugging function"""
    if len(sys.argv) != 4:
        print("Usage: python debug_connection.py <host> <port> <password>")
        print("Example: python debug_connection.py 192.168.1.100 30004 mypassword")
        sys.exit(1)
    
    host = sys.argv[1]
    port = int(sys.argv[2])
    password = sys.argv[3]
    
    debugger = EmpyrionConnectionDebugger(host, port, password)
    debugger.debug_connection()

if __name__ == "__main__":
    main()
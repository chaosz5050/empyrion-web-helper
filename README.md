# FILE LOCATION: /README.md (root directory)

# 🚀 Empyrion Web Helper v0.4.1

[![Platform](https://img.shields.io/badge/Platform-Linux-blue?style=for-the-badge&logo=linux)](https://www.linux.org/)
[![Python](https://img.shields.io/badge/Python-3.8%2B-green?style=for-the-badge&logo=python)](https://www.python.org/)
[![Version](https://img.shields.io/badge/Version-0.4.1-orange?style=for-the-badge)](https://github.com/your-username/empyrion-web-helper)
[![License](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-red?style=for-the-badge)](https://creativecommons.org/licenses/by-nc-sa/4.0/)

> **A modern, web-based administration tool for Empyrion Galactic Survival dedicated servers with independent background service architecture**

Empyrion Web Helper is a comprehensive server management solution that provides real-time player monitoring, automated messaging, and professional logging through an intuitive web interface. Built with a revolutionary background service architecture, it operates independently of the web frontend for true 24/7 server management.

## ⚠️ IMPORTANT: First-Time Setup Required

**Before the background service can start automatically, you MUST configure RCON credentials via the web interface:**

1. **Start the application** for the first time:
   ```bash
   python3 app.py
   ```

2. **Open the web interface**: `http://your-server-ip:5001`

3. **Configure RCON credentials**:
   - The app will detect missing credentials
   - Follow the prompts to enter your RCON password
   - Credentials are stored securely in encrypted database

4. **Restart the application**:
   ```bash
   # Stop with Ctrl+C, then restart
   python3 app.py
   ```

5. **Background service starts automatically** - No web browser required for operation!

## 🏗️ New Architecture: Background Service

### What Changed in v0.4.1

**Before (v0.4.0)**: Web UI controlled everything
- ❌ Messaging only worked when browser was open
- ❌ Welcome/goodbye messages required web UI polling
- ❌ Scheduled messages stopped when browser closed
- ❌ Manual connect/disconnect required

**Now (v0.4.1)**: Independent background service
- ✅ **Automatic connection** on startup
- ✅ **Automatic reconnection** when server restarts
- ✅ **Independent messaging** - works without browser
- ✅ **Real-time player monitoring** - 20-second intervals
- ✅ **Web UI is pure frontend** - just for configuration and viewing

### Background Service Features

🔄 **Automatic Operations**:
- Connects to Empyrion server on startup
- Monitors players every 20 seconds
- Sends welcome/goodbye messages automatically
- Runs scheduled messages independently
- Reconnects automatically after server downtime

🌐 **Web Interface**:
- Configure messages and settings
- View real-time player data
- Monitor service status
- View logs and statistics
- **Optional** - service runs without it

## ✨ Features

### 🎮 **Player Management**
- **Real-time Player Tracking** - Monitor all players with live status updates via background service
- **Comprehensive Database** - Persistent storage of all players who ever visited your server
- **Smart Status Detection** - Automatic login/logout tracking with precise timestamps
- **IP Address & Geolocation** - Track player locations with country identification
- **Advanced Filtering** - Search and filter players by name, status, faction, IP, country, and more
- **Player Actions** - Kick, ban, and unban players directly from the web interface

### 🌌 **Entity Management**
- **Galaxy-wide Entity Tracking** - Browse all objects in your galaxy (asteroids, ships, bases, wrecks)
- **Database Persistence** - Entity data survives app restarts
- **Smart Categorization** - Automatically categorizes entities for easy filtering
- **Advanced Search & Filtering** - Find specific entities by ID, type, faction, name, or playfield
- **Entity ID Display** - Prominently shows entity IDs needed for admin destroy/teleport commands
- **Raw Data Export** - Export complete gents output for detailed analysis in Excel

### 📢 **Messaging System (Background Service)**
- **Independent Operation** - Messages work without web browser open
- **Custom Welcome/Goodbye Messages** - Personalized messages with `<playername>` placeholders
- **Scheduled Messages** - Automated recurring announcements (5 minutes to 12 hours intervals)
- **Global Messaging** - Send immediate messages to all online players
- **Message History** - Complete logging with success tracking and statistics
- **Real-time Status Detection** - Welcome/goodbye triggered by actual server events

### 🌍 **IP Geolocation**
- **Automatic Country Detection** - Uses ip-api.com for free geolocation
- **Smart Caching** - Minimizes API calls with intelligent caching
- **Graceful Fallback** - Handles service outages and network issues
- **Privacy Compliant** - No personal data stored, only country names

### 📋 **Log Management**
- **Automatic Log Rotation** - Configurable file size limits (1MB default) with backup retention
- **Smart Cleanup** - Automatic deletion of logs older than specified days
- **Web-based Log Viewer** - View recent log entries directly in the browser
- **Log Statistics** - Real-time monitoring of log file sizes and counts
- **Background Service Logging** - Comprehensive logging of all service activities

### 🌐 **Modern Web Interface**
- **Dark Theme** - Professional, eye-friendly interface
- **Responsive Design** - Works perfectly on desktop and mobile devices
- **Real-time Updates** - WebSocket integration for live data updates
- **Service Monitoring** - Live status of background service and connections
- **Professional Styling** - Polished UI that looks great in any environment

### 🔧 **Technical Excellence**
- **Background Service Architecture** - True 24/7 operation independent of web UI
- **Modular Design** - Clean separation of concerns for easy maintenance and expansion
- **Linux-Optimized** - Built specifically for Linux servers (no deprecated dependencies)
- **Python 3.8+ Compatible** - Modern Python with full async support
- **SQLite Database** - Reliable, serverless database for player and message history
- **Secure Credential Storage** - AES-256 encryption for passwords
- **Automatic Reconnection** - Handles daily server restarts seamlessly

## 🛠️ Installation

### Prerequisites
- **Linux** (tested on CachyOS, but should work on any Linux distro)
- **Python 3.8 or higher**
- **Empyrion Galactic Survival Dedicated Server** with RCON enabled

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/empyrion-web-helper.git
   cd empyrion-web-helper
   ```

2. **Set up Python environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure your server**
   ```bash
   cp config_template.txt empyrion_helper.conf
   nano empyrion_helper.conf  # Edit with your server details
   ```

4. **First-time credential setup**
   ```bash
   python3 app.py
   # Open browser to http://your-server-ip:5001
   # Configure RCON password when prompted
   # Stop with Ctrl+C and restart
   ```

5. **Production operation**
   ```bash
   python3 app.py
   # Background service starts automatically
   # Access web interface: http://your-server-ip:5001
   ```

## ⚙️ Configuration

### Basic Server Configuration

Edit `empyrion_helper.conf` with your Empyrion server details:

```ini
[server]
host = YOUR_SERVER_IP
telnet_port = 30004
# NOTE: Password stored securely in database after first setup

[monitoring]
# Background service hardcoded to 20 seconds (optimal performance)

[messaging]
welcome_message = Welcome to Space Cowboys, <playername>!
goodbye_message = Player <playername> has left our galaxy

[logging]
max_size_mb = 1
backup_count = 3
max_age_days = 7
```

### Secure Credential Storage

**v0.4.1 uses encrypted database storage for all sensitive data:**

- **AES-256 encryption** for all passwords
- **Interactive setup** on first run
- **Environment variable support** for automation
- **No sensitive data in config files**

### Environment Variables (Optional)
```bash
export EMPYRION_RCON_PASSWORD="your_rcon_password"
export EMPYRION_FTP_USER="your_ftp_username"      # For future features
export EMPYRION_FTP_PASSWORD="your_ftp_password"  # For future features
```

## 🎯 Usage

### Background Service Operation
1. **Configure credentials** via web interface (first time only)
2. **Start the application** - background service auto-starts
3. **Monitor via web interface** (optional)
4. **Service runs independently** of browser
5. **Automatic reconnection** handles server restarts

### Player Management
1. **Automatic monitoring** via background service every 20 seconds
2. **View all players** in the comprehensive player table
3. **Filter and search** using the built-in filter system
4. **Take actions** on players (kick, ban, unban) through web interface
5. **Real-time status updates** with automatic geolocation

### Entity Management
1. **Persistent entity storage** - data survives app restarts
2. **Load from database** instantly on startup
3. **Refresh from server** manually when needed (10-30 seconds)
4. **Browse and filter** through all galaxy objects
5. **Export raw data** for detailed analysis

### Messaging System
1. **Configure messages** through web interface
2. **Background service handles delivery** automatically
3. **Welcome/goodbye messages** sent on real player events
4. **Scheduled messages** run independently
5. **View message history** and statistics

### Log Management
1. **Automatic log rotation** with configurable settings
2. **View recent logs** directly in browser
3. **Monitor service activities** in real-time
4. **Clean up old files** with one-click cleanup

## 🎮 Daily Server Operations

### Your Empyrion server restarts daily?
**No problem!** The background service automatically:

1. **Detects disconnection** when server goes down
2. **Logs the downtime** for your records
3. **Automatically reconnects** when server comes back up
4. **Resumes all operations** seamlessly

**Log example**:
```
2025-07-17 03:00:15 - WARNING - ⚠️ Connection lost. Attempt #1. Retrying in 30 seconds...
2025-07-17 03:05:42 - INFO - ✅ Successfully connected to Empyrion server
2025-07-17 03:05:43 - INFO - 👋 Player joined: TestPlayer
```

### Running as a System Service

For production servers, create a systemd service:

```bash
sudo nano /etc/systemd/system/empyrion-helper.service
```

```ini
[Unit]
Description=Empyrion Web Helper Background Service
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/empyrion-web-helper
Environment=PATH=/path/to/empyrion-web-helper/venv/bin
ExecStart=/path/to/empyrion-web-helper/venv/bin/python app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable empyrion-helper
sudo systemctl start empyrion-helper
sudo systemctl status empyrion-helper
```

## 🏗️ Architecture

Empyrion Web Helper v0.4.1 features a revolutionary background service architecture:

```
Background Service (Independent)
├── Automatic Server Connection
├── Player Monitoring (20s intervals)
├── Status Change Detection  
├── Message Scheduling
├── Automatic Reconnection
└── Database Updates

Web Interface (Optional Frontend)
├── Service Status Monitoring
├── Configuration Management
├── Real-time Data Display
├── Message History
└── Log Viewing
```

### Key Design Principles
- **Service Independence** - Core functionality works without web UI
- **Automatic Operation** - Minimal manual intervention required
- **Real-time Monitoring** - Live status updates and data synchronization
- **Professional Logging** - Comprehensive activity tracking
- **Secure Storage** - Encrypted credentials and persistent data

## 📊 Monitoring & Logs

### Service Status
The web interface shows:
- **Service Status**: Running/Stopped
- **Connection Status**: Connected/Connecting/Disconnected
- **Reconnection Attempts**: Track connection stability
- **Last Activity**: When service last performed actions

### Automatic Logging
- **Rotating logs** with size limits
- **Connection events** logged automatically
- **Player join/leave** events tracked
- **Message delivery** status recorded
- **Server downtime** periods logged

### Example Log Output
```
2025-07-17 15:49:20 - INFO - 🚀 Starting Empyrion Web Helper background service
2025-07-17 15:49:25 - INFO - ✅ Successfully connected to Empyrion server
2025-07-17 15:49:26 - INFO - 📊 Retrieved 23 players from server
2025-07-17 15:50:15 - INFO - 👋 Player joined: NewPlayer
2025-07-17 15:50:15 - INFO - 📢 Welcome message sent: Welcome to Space Cowboys, NewPlayer!
```

## 🔒 Security Considerations

- **Automatic Flask Secret Key Management** - On first run, the app generates a secure secret key and stores it in `instance/ewh_secret.key`. This key is used for session security and should not be deleted. The file is automatically ignored by git and does not require user management.
- **Encrypted Credential Storage** - AES-256 encryption for all passwords
- **Secure File Permissions** - Database and key files protected
- **Environment Variable Support** - For automated deployments
- **Network Security** - Consider using reverse proxy for production
- **Regular Updates** - Keep dependencies updated for security patches

## 🔧 Troubleshooting

### Service Won't Start
```bash
# Check logs
tail -f empyrion_helper.log

# Common issues:
# 1. Missing RCON credentials - configure via web UI first
# 2. Wrong server IP/port in empyrion_helper.conf
# 3. Empyrion server not running
# 4. RCON not enabled in adminconfig.yaml
```

### Messages Not Sending
```bash
# Check message history in web interface
# Look for failed message attempts in logs
grep "Failed to send" empyrion_helper.log

# Verify RCON connection
grep "Successfully connected" empyrion_helper.log
```

### Automatic Reconnection Not Working
```bash
# Check reconnection attempts
grep "Connection lost" empyrion_helper.log
grep "Retrying in" empyrion_helper.log

# Verify server is actually accessible
telnet your-server-ip 30004
```

### Web Interface Not Loading
```bash
# Check if service is running
ps aux | grep python | grep app.py

# Check port binding
netstat -tlnp | grep 5001

# Check firewall settings
sudo ufw status
```

## 🔄 Migration from v0.4.0

If upgrading from v0.4.0:

1. **Backup your data**:
   ```bash
   cp empyrion_helper.conf empyrion_helper.conf.backup
   cp -r instance/ instance_backup/
   ```

2. **Update code** and restart application

3. **No configuration changes needed** - existing settings migrate automatically

4. **Background service starts automatically** if credentials are configured

5. **Test messaging** - should now work without browser open

## 🤝 Contributing

We welcome contributions! Whether it's bug reports, feature requests, or code contributions, your input helps make Empyrion Web Helper better for everyone.

### Development Setup
1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes with appropriate tests
4. Submit a pull request with a clear description

### Coding Standards
- Follow PEP 8 Python style guidelines
- Maintain the modular architecture
- Include comprehensive logging for new features
- Update documentation for any user-facing changes

## 📝 License

This project is licensed under the **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License**.

**You are free to:**
- Share — copy and redistribute the material in any medium or format
- Adapt — remix, transform, and build upon the material

**Under the following terms:**
- **Attribution** — You must give appropriate credit, provide a link to the license, and indicate if changes were made
- **NonCommercial** — You may not use the material for commercial purposes
- **ShareAlike** — If you remix, transform, or build upon the material, you must distribute your contributions under the same license

For more details, see the [full license text](https://creativecommons.org/licenses/by-nc-sa/4.0/).

## 🙏 Acknowledgments

- **Empyrion Community** - For the inspiration and feedback that drives this project
- **Flask & Python Communities** - For the excellent frameworks that make this possible
- **Open Source Contributors** - For the libraries and tools that power this application

## 📞 Support

- **Issues**: Report bugs and request features through GitHub Issues
- **Documentation**: Comprehensive setup guides available in the repository
- **Community**: Join discussions about Empyrion server management

---

**Built with ❤️ for the Empyrion Galactic Survival community by Chaosz Software**

*Empyrion Web Helper v0.4.1 - Professional server management with true background service architecture*
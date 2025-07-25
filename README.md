# 🚀 Empyrion Web Helper v0.5.3

[![Platform](https://img.shields.io/badge/Platform-Linux-blue?style=for-the-badge&logo=linux)](https://www.linux.org/)
[![Python](https://img.shields.io/badge/Python-3.8%2B-green?style=for-the-badge&logo=python)](https://www.python.org/)
[![Version](https://img.shields.io/badge/Version-0.5.3-orange?style=for-the-badge)](https://github.com/your-username/empyrion-web-helper)
[![License](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-red?style=for-the-badge)](https://creativecommons.org/licenses/by-nc-sa/4.0/)

> **A professional web-based administration tool for Empyrion Galactic Survival dedicated servers with universal RCON compatibility**

Empyrion Web Helper is a comprehensive server management solution that provides real-time player monitoring, automated messaging, and professional logging through an intuitive web interface. Built with a revolutionary background service architecture, it operates independently for true 24/7 server management and **works with any hosting provider** automatically.

## ✨ Key Features

### 🌐 **Universal Compatibility**
- **Works with ANY hosting provider** - Havoc, Nitrado, self-hosted, and more
- **Automatic RCON detection** - no provider-specific configuration needed
- **Universal authentication** - tries multiple methods to ensure connection success
- **Real-time connection health monitoring** - accurate status reporting

### 🎮 **Advanced Player Management**
- **Real-time Player Tracking** - Live status updates every 20 seconds via background service
- **Comprehensive Database** - Persistent storage of all players who ever visited your server
- **Smart Status Detection** - Automatic login/logout tracking with precise timestamps
- **IP Geolocation** - Automatic country identification with intelligent caching
- **Advanced Filtering** - Search by name, status, faction, IP, country, and more
- **Player Actions** - Kick, ban, and unban players directly from the web interface

### 🌌 **Galaxy-Wide Entity Management**
- **Complete Entity Database** - Browse all objects in your galaxy (asteroids, ships, bases, wrecks)
- **Instant Loading** - Entity data loads from database in <10ms vs 30+ seconds from server
- **Smart Categorization** - Automatically organizes entities for easy filtering
- **Persistent Storage** - Entity data survives app restarts and server downtime
- **Advanced Search** - Find specific entities by ID, type, faction, name, or playfield
- **Admin Integration** - Entity IDs prominently displayed for destroy/teleport commands

### 🛠️ **ItemsConfig.ecf Management**
- **Live Server Integration** - Direct FTP download and parsing of ItemsConfig.ecf from your server
- **Professional Editor Interface** - Browse and edit 1,100+ game items in a responsive table
- **Safe Property Editing** - Modify StackSize, Mass, Volume, and MarketPrice with validation
- **Template System Support** - Automatic resolution of template inheritance and item relationships
- **Advanced ECF Parser** - Handles complex Empyrion Configuration File format with nested properties
- **Comprehensive Pagination** - Configurable display options (50/100/250/500 items per page)
- **Real-time Connection Testing** - Verify FTP connectivity and file availability before editing

### 📢 **Independent Messaging System**
- **24/7 Operation** - Messages work without web browser open (background service)
- **Smart Welcome/Goodbye** - Personalized messages with `<playername>` placeholders
- **Scheduled Announcements** - Automated recurring messages (10 minutes to 24 hours, up to 10 messages)
- **Global Messaging** - Send immediate messages to all online players
- **Message History** - Complete logging with delivery tracking and statistics
- **Real-time Triggers** - Welcome/goodbye sent on actual server events, not polling

### 🔒 **Enterprise-Grade Security**
- **AES-256 Encryption** - All passwords encrypted in database storage
- **Zero Config File Secrets** - No sensitive data in configuration files
- **Secure Web Interface** - Professional credential management via Settings tab
- **Environment Variable Support** - For automated deployments and CI/CD
- **Automatic Secret Key Management** - Flask session security handled automatically

### 📊 **Professional Operations**
- **Background Service Architecture** - True headless operation independent of web UI
- **Automatic Reconnection** - Handles daily server restarts seamlessly
- **Comprehensive Logging** - Rotating logs with configurable size and retention
- **Real-time Web Updates** - WebSocket integration for live data synchronization
- **Service Monitoring** - Live status of background service and connections
- **Database Persistence** - All data survives restarts and system reboots

## 🚀 Quick Start

### Prerequisites
- **Linux** (tested on CachyOS, Ubuntu, Debian, CentOS)
- **Python 3.8+** with pip
- **Empyrion Dedicated Server** with RCON enabled

### Installation

1. **Clone and setup**
   ```bash
   git clone https://github.com/your-username/empyrion-web-helper.git
   cd empyrion-web-helper
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Create configuration**
   ```bash
   cp config_template.txt empyrion_helper.conf
   # Edit messaging settings if desired (optional)
   ```

3. **Start the application**
   ```bash
   python3 app.py
   ```

4. **Configure via web interface**
   - Open http://localhost:5001 (or http://your-server-ip:5001)
   - Go to **Settings** tab
   - Enter your server details:
     - **Server Host**: Your Empyrion server IP
     - **RCON Port**: Usually 30004
     - **RCON Password**: Your server's RCON password
   - Save settings - the app will automatically connect!

### First Run Experience

The app features **intelligent first-time setup**:
- Detects missing credentials and prompts via web interface
- Tests connection with **universal RCON compatibility**
- Automatically starts background service once configured
- No complex configuration files or provider-specific settings needed

## 🏗️ Architecture

Empyrion Web Helper features a revolutionary **dual-architecture design**:

```
┌─────────────────────────────────────┐
│        Background Service           │
│        (Independent Core)           │
├─────────────────────────────────────┤
│ • Automatic Server Connection       │
│ • Player Monitoring (20s intervals) │
│ • Status Change Detection           │
│ • Automated Messaging               │
│ • Entity Data Collection            │
│ • Database Management               │
│ • Automatic Reconnection            │
└─────────────────────────────────────┘
                    ↕️
┌─────────────────────────────────────┐
│         Web Interface               │
│       (Optional Frontend)           │
├─────────────────────────────────────┤
│ • Service Configuration             │
│ • Real-time Data Display            │
│ • Player & Entity Management        │
│ • Message History & Statistics      │
│ • Live Status Monitoring            │
│ • Settings Management               │
└─────────────────────────────────────┘
```

### Key Design Principles
- **Service Independence** - Core functionality works without web UI
- **Universal Compatibility** - Works with any RCON hosting provider
- **Real-time Operations** - Live status updates and data synchronization
- **Secure by Design** - Encrypted credentials, no sensitive config files
- **Professional Reliability** - Automatic reconnection, persistent storage

## 📱 Web Interface

### Multi-Theme Professional UI
- **Three Complete Themes** - Dark (default), Light, and Accessible (WCAG 2.1 AAA compliant)
- **Real-time Theme Switching** - Instant theme changes without page reload
- **Responsive Design** - Works perfectly on desktop, tablet, and mobile
- **Real-time Updates** - WebSocket integration for live data
- **Professional Styling** - Optimized themes for different environments and accessibility needs
- **Mobile Optimized** - Full functionality available on phones and tablets

### Core Tabs
- **📊 Dashboard** - Service status, connection monitoring, quick actions
- **👥 Players** - Real-time player list, actions, filtering, geolocation
- **🌌 Entities** - Galaxy-wide entity browser, search, admin tools
- **🛠️ ItemsConfig** - Live ECF file management, item editing, template resolution
- **💬 Messaging** - Message history, templates, scheduled announcements
- **📋 Logs** - Real-time log viewer, rotation management, statistics
- **⚙️ Settings** - Secure credential management, service configuration, appearance themes

## 🎯 Daily Operations

### Server Restart Handling
Your Empyrion server restarts daily? **No problem!** The background service:

1. **Detects disconnection** when server goes down for restart
2. **Logs the downtime** with precise timestamps
3. **Automatically reconnects** when server comes back online
4. **Resumes all operations** seamlessly without data loss

**Example log output:**
```
2025-07-21 03:00:15 - WARNING - 🔌 Connection lost. Attempt #1. Retrying in 30 seconds...
2025-07-21 03:05:42 - INFO - ✅ Successfully connected to Empyrion server
2025-07-21 03:05:43 - INFO - 👋 Player TestPlayer joined, sending welcome message
```

### Production Deployment

For 24/7 operation, deploy as a system service:

```bash
# Create service file
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

## 🔧 Configuration

### Web Interface Settings
**All server connection settings are configured via the web interface:**
- Go to **Settings** tab for secure credential management
- Server Host, RCON Port, and Password stored encrypted in database
- FTP settings for future file management features
- Real-time connection testing and status validation

### Config File (empyrion_helper.conf)
**Only contains non-sensitive operational settings:**
```ini
[monitoring]
update_interval = 30  # Player monitoring frequency (seconds)

[messaging]
welcome_message = Welcome to Space Cowboys, <playername>!
goodbye_message = Player <playername> has left our galaxy
# Scheduled messages: Configure up to 10 automated recurring messages via web interface
# Available intervals: Every 10/20/30/40/50 minutes, 1/2/3/6/12/24 hours

[logging]
max_size_mb = 1      # Log file size before rotation
backup_count = 3     # Number of backup log files
max_age_days = 7     # Delete logs older than this
```

### Environment Variables (Optional)
For automated deployments:
```bash
export EMPYRION_RCON_PASSWORD="your_rcon_password"
export EMPYRION_FTP_USER="your_ftp_username"
export EMPYRION_FTP_PASSWORD="your_ftp_password"
export EMPYRION_FTP_HOST="192.168.1.100:21"
```

## 🔍 Monitoring & Troubleshooting

### Real-time Service Status
The web interface provides comprehensive monitoring:
- **Service Status**: Running/Stopped with auto-start controls
- **Connection Status**: Live RCON connectivity with provider detection
- **Reconnection Tracking**: Monitor connection stability over time
- **Last Activity**: Track when service last performed operations
- **Message Statistics**: Delivery success rates and history

### Log Management
- **Automatic Rotation** - Configurable file size limits with backup retention
- **Web-based Viewer** - Browse recent log entries directly in browser
- **Smart Cleanup** - Automatic deletion of old log files
- **Real-time Updates** - Live log streaming for active troubleshooting

### Common Solutions

**Connection Issues:**
```bash
# Check service status
systemctl status empyrion-helper

# Check logs
tail -f empyrion_helper.log

# Test RCON manually
telnet your-server-ip 30004
```

**Credential Issues:**
- Use the Settings tab to verify and update credentials
- Check connection status indicators in the top-right
- Review logs for specific authentication method attempts

**Performance Optimization:**
- **Busy servers (50+ players)**: Increase update_interval to 45-60 seconds
- **Quiet servers (<20 players)**: Decrease to 20 seconds
- Monitor system resources and adjust accordingly

## 🔒 Security Features

### Encryption & Storage
- **AES-256 encryption** for all passwords stored in database
- **Automatic key management** - encryption keys generated and secured automatically
- **No plaintext secrets** - config files contain zero sensitive information
- **Secure file permissions** - Database and key files protected (600 permissions)

### Network Security
- **HTTPS-ready** - Use reverse proxy (nginx, Apache) for production HTTPS
- **Configurable binding** - Bind to localhost-only for additional security
- **Session management** - Secure Flask sessions with automatic secret key rotation

### Best Practices
1. **Use strong, unique passwords** for RCON and FTP access
2. **Regularly backup** your `instance/players.db` file (contains encrypted data)
3. **Keep `instance/ewh_secret.key` secure** (Flask session encryption)
4. **Monitor access logs** for suspicious activity
5. **Keep the application updated** for security patches

## 🤝 Sharing With Other Admins

Empyrion Web Helper is designed to be **easily shared** with other server administrators:

### Universal Compatibility
- **Works with any hosting provider** - no provider-specific configuration
- **Automatic RCON detection** - handles different authentication methods
- **Clean setup process** - web-based configuration, no complex config editing

### Sharing Instructions
1. **Share the repository** - Other admins can clone and use immediately
2. **Provide setup guidance** - Point them to this README's Quick Start
3. **No sensitive data** - Config templates contain no passwords or IPs
4. **Provider agnostic** - Works equally well with Havoc, Nitrado, self-hosted, etc.

## 📊 Technical Specifications

### Performance
- **Entity queries**: <10ms from database vs 10-30 seconds from server
- **Player updates**: Real-time every 20 seconds (configurable)
- **Memory usage**: ~50-100MB typical, ~200MB with large player history
- **Database size**: ~1-10MB for typical servers, scales with player count

### Compatibility
- **Python**: 3.8+ (tested up to 3.13)
- **Operating Systems**: Linux (Ubuntu, Debian, CentOS, Arch variants)
- **Hosting Providers**: Universal RCON compatibility (Havoc, Nitrado, self-hosted)
- **Empyrion Versions**: Game Version 1.10+ with Mod API Version 2.4.0+

### Dependencies
- **Flask & Flask-SocketIO**: Web framework and real-time updates
- **SQLite**: Embedded database for persistence (no external DB required)
- **Cryptography**: AES-256 encryption for credential security
- **Requests**: HTTP client for geolocation services

## 🔄 Migration & Updates

### From Previous Versions
The app includes **automatic migration** for smooth upgrades:
- **Credential migration** - Passwords automatically moved from config to encrypted database
- **Database schema updates** - Automatic table creation and structure updates
- **Config file cleanup** - Sensitive data automatically removed from config files
- **Zero downtime** - Background service continues operation during updates

### Backup Recommendations
```bash
# Backup essential data
cp -r instance/ instance_backup_$(date +%Y%m%d)
cp empyrion_helper.conf empyrion_helper.conf.backup
```

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
- **Server Administrators** - Who test, provide feedback, and help improve reliability
- **Flask & Python Communities** - For the excellent frameworks that make this possible
- **Open Source Contributors** - For the libraries and tools that power this application

## 📞 Support

- **Issues**: Report bugs and request features through GitHub Issues
- **Documentation**: Comprehensive guides available in this repository
- **Community**: Join discussions about Empyrion server management and administration

---

**Built with ❤️ for the Empyrion Galactic Survival community by Chaosz Software**

*Empyrion Web Helper v0.5.3 - Professional server management with universal compatibility, enterprise-grade security, and advanced theming system*
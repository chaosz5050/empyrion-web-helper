# FILE LOCATION: /README.md (root directory)

# 🚀 Empyrion Web Helper

[![Platform](https://img.shields.io/badge/Platform-Linux-blue?style=for-the-badge&logo=linux)](https://www.linux.org/)
[![Python](https://img.shields.io/badge/Python-3.8%2B-green?style=for-the-badge&logo=python)](https://www.python.org/)
[![Version](https://img.shields.io/badge/Version-0.4.0-orange?style=for-the-badge)](https://github.com/your-username/empyrion-web-helper)
[![License](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-red?style=for-the-badge)](https://creativecommons.org/licenses/by-nc-sa/4.0/)

> **A modern, web-based administration tool for Empyrion Galactic Survival dedicated servers**

Empyrion Web Helper is a comprehensive server management solution that provides real-time player monitoring, automated messaging, and professional logging through an intuitive web interface. Built with modularity and scalability in mind, it's the perfect tool for hobby server administrators who want professional-grade functionality.

## ✨ Features

### 🎮 **Player Management**
- **Real-time Player Tracking** - Monitor all players with live status updates
- **Comprehensive Database** - Persistent storage of all players who ever visited your server
- **Smart Status Detection** - Automatic login/logout tracking with precise timestamps
- **IP Address Preservation** - Maintains player IP history even when offline
- **Advanced Filtering** - Search and filter players by name, status, faction, IP, and more
- **Player Actions** - Kick, ban, and unban players directly from the web interface

### 🌌 **Entity Management**
- **Galaxy-wide Entity Tracking** - Browse all objects in your galaxy (asteroids, ships, bases, wrecks)
- **Smart Categorization** - Automatically categorizes entities for easy filtering
- **Advanced Search & Filtering** - Find specific entities by ID, type, faction, name, or playfield
- **Entity ID Display** - Prominently shows entity IDs needed for admin destroy/teleport commands
- **Raw Data Export** - Export complete gents output for detailed analysis in Excel
- **Color-coded Interface** - Visual distinction between asteroids, structures, ships, and wrecks

### 📢 **Messaging System**
- **Custom Welcome/Goodbye Messages** - Personalized messages with `<playername>` placeholders
- **Scheduled Messages** - Automated recurring announcements (5 minutes to 12 hours intervals)
- **Global Messaging** - Send immediate messages to all online players
- **Message History** - Complete logging with success tracking and statistics
- **Professional Templates** - Easy-to-use message configuration

### 📋 **Log Management**
- **Automatic Log Rotation** - Configurable file size limits (1MB default) with backup retention
- **Smart Cleanup** - Automatic deletion of logs older than specified days
- **Web-based Log Viewer** - View recent log entries directly in the browser
- **Log Statistics** - Real-time monitoring of log file sizes and counts
- **Configurable Settings** - Adjust rotation settings through the web interface

### 🌐 **Modern Web Interface**
- **Dark Theme** - Professional, eye-friendly interface
- **Responsive Design** - Works perfectly on desktop and mobile devices
- **Real-time Updates** - WebSocket integration for live data updates
- **Intuitive Navigation** - Clean tab-based interface for easy access to all features
- **Professional Styling** - Polished UI that looks great in any environment

### 🔧 **Technical Excellence**
- **Modular Architecture** - Clean separation of concerns for easy maintenance and expansion
- **Linux-Optimized** - Built specifically for Linux servers (no deprecated dependencies)
- **Python 3.8+ Compatible** - Modern Python with full async support
- **SQLite Database** - Reliable, serverless database for player and message history
- **Configuration-Driven** - All settings managed through a single config file
- **Professional Logging** - Rotating logs with configurable retention policies

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

4. **Start the application**
   ```bash
   python3 app.py
   ```

5. **Access the web interface**
   Open your browser and navigate to: `http://your-server-ip:5001`

## ⚙️ Configuration

### Basic Server Configuration

Edit `empyrion_helper.conf` with your Empyrion server details:

```ini
[server]
host = YOUR_SERVER_IP
telnet_port = 30004
telnet_password = YOUR_RCON_PASSWORD

[monitoring]
update_interval = 30

[messaging]
welcome_message = Welcome to Space Cowboys, <playername>!
goodbye_message = Player <playername> has left our galaxy

[logging]
max_size_mb = 1
backup_count = 3
max_age_days = 7
```

### Advanced Configuration

The application supports extensive customization through the config file:

- **Message Templates** - Customize welcome/goodbye messages with player name placeholders
- **Scheduled Messages** - Configure up to 5 recurring messages with flexible timing
- **Log Rotation** - Set file size limits, backup counts, and retention policies
- **Update Intervals** - Adjust how frequently player data is refreshed
- **Auto-connect** - Enable automatic server connection on startup

## 🎯 Usage

### Player Management
1. **Connect to your server** using the dashboard
2. **View all players** in the comprehensive player table
3. **Filter and search** using the built-in filter system
4. **Take actions** on players (kick, ban, unban) with right-click context menu
5. **Monitor in real-time** with automatic status updates

### Entity Management
1. **Connect to your server** and navigate to the Entities tab
2. **Click "Refresh Entities"** to load all galaxy objects (may take 10-30 seconds)
3. **Browse and filter** through asteroids, ships, bases, and wrecks
4. **Find specific entities** using the advanced search filters
5. **Export raw data** for detailed analysis in spreadsheet applications
6. **Copy Entity IDs** for use in admin destroy or teleport commands

### Messaging System
1. **Configure custom messages** in the Messaging tab
2. **Set up scheduled announcements** with flexible timing options
3. **Send global messages** instantly to all online players
4. **Monitor message history** with detailed success tracking
5. **Test messages** before going live

### Log Management
1. **Monitor log statistics** in real-time
2. **Configure rotation settings** through the web interface
3. **View recent logs** directly in the browser
4. **Clean up old files** with one-click cleanup
5. **Download logs** for external analysis

## 🏗️ Architecture

Empyrion Web Helper is built with a modular architecture for maximum maintainability and extensibility:

```
empyrion-web-helper/
├── app.py                 # Main Flask application
├── messaging.py           # Messaging system module
├── logging_manager.py     # Log rotation and management
├── connection.py          # RCON connection handling
├── database.py           # Player database management
├── config_manager.py     # Configuration management
├── templates/
│   └── index.html        # Web interface
├── instance/
│   └── players.db        # SQLite database (auto-created)
└── empyrion_helper.conf  # Configuration file
```

### Key Design Principles
- **Modular Components** - Each feature is self-contained for easy maintenance
- **Configuration-Driven** - Behavior controlled through config files, not code
- **Database Persistence** - All important data stored reliably in SQLite
- **Real-time Updates** - WebSocket integration for live data synchronization
- **Professional Logging** - Comprehensive logging with automatic rotation

## 🔒 Security Considerations

- **RCON Password Protection** - Store your RCON password securely in the config file
- **Network Security** - Consider using a reverse proxy (nginx) for production deployments
- **File Permissions** - Ensure config files have appropriate read/write permissions
- **Firewall Configuration** - Limit access to the web interface port (5001) as needed

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

**Built with ❤️ for the Empyrion Galactic Survival community**

*Empyrion Web Helper - Professional server management made simple*
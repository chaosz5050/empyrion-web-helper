# 🚀 Empyrion Web Helper

A modern web-based administration tool for Empyrion Galactic Survival dedicated servers.

## ✨ Features

- **🔌 Real-time Server Connection** - Connect to your Empyrion server via RCON
- **👥 Player Management** - View online/offline players with comprehensive tracking
- **🗃️ Player Database** - Persistent storage of all players who ever visited
- **⚡ Player Actions** - Kick, ban, and unban players directly from the web interface
- **📊 Smart Status Tracking** - Automatic detection of player login/logout with timestamps
- **🌐 Modern Web UI** - Responsive dark theme that works on desktop and mobile
- **💾 Offline Capability** - View player history even when server is offline
- **🔍 Advanced Filtering** - Search and filter players by various criteria

## 🛠️ Installation

### Prerequisites
- Python 3.8 or higher
- Access to your Empyrion server's RCON interface

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/chaosz5050/empyrion-web-helper.git
   cd empyrion-web-helper
   ```

2. **Set up Python environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure your server**
   ```bash
   cp config_template.txt empyrion_helper.conf
   # Edit empyrion_helper.conf with your server details
   ```

4. **Start the application**
   ```bash
   python3 app.py
   ```

5. **Open your browser**
   Navigate to: `http://localhost:5001`

## ⚙️ Configuration

Edit `empyrion_helper.conf` with your server details:

```ini
[server]
host = YOUR_SERVER_IP
telnet_port = 30004
telnet_password = YOUR_RCON_PASSWORD

[monitoring]
update_interval = 30

[general]
autoconnect = true
```

## 🎮 Usage

1. **Connect to Server** - Click the connect button to establish RCON connection
2. **View Players** - See all online players with real-time updates
3. **Player Actions** - Use kick/ban buttons for player management
4. **Player History** - View comprehensive database of all server visitors
5. **Filter & Search** - Use the filter boxes to find specific players

## 🏗️ Architecture

- **Modular Design** - Clean separation between connection, database, and web layers
- **Flask Backend** - Lightweight Python web framework
- **SQLite Database** - Local storage for player history and tracking
- **WebSocket Support** - Real-time updates without page refresh
- **Responsive UI** - Modern dark theme with mobile support

## 📝 Features in Detail

### Player Tracking
- Automatic detection of login/logout events
- IP address preservation for offline players
- Real-time status updates every 30 seconds
- Comprehensive player history database

### Player Management
- **Kick** - Remove players with custom messages
- **Ban** - Ban players for specified duration (default: 1 day)
- **Unban** - Remove bans from players
- Smart action buttons based on player status

### Data Persistence
- All player data stored in local SQLite database
- IP addresses preserved even when players go offline
- Real logout timestamps using local computer time
- Offline viewing capability when server is down

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🎯 Roadmap

- [ ] Scheduled server messages
- [ ] FTP integration for configuration editing
- [ ] Entity/structure management
- [ ] Advanced reporting and analytics
- [ ] Multi-server support

## 🙏 Acknowledgments

Built for the Empyrion Galactic Survival community with ❤️

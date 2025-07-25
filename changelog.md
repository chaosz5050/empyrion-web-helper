# Changelog

All notable changes to Empyrion Web Helper will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v0.5.2] - 2025-07-25

### Fixed - POI Regeneration System
- **🔧 Bulk Regeneration Data Bug** - Fixed critical issue where system processed only 286 entities instead of expected 475
  - Root cause: Empty database with no entities table caused system to have zero entity data
  - Added automatic fallback to fetch live entity data from server when database is empty
  - System now processes ALL entities including previously missing entity 2015
  - Prevents partial regeneration runs due to incomplete cached data

- **⏱️ Server Command Timing** - Improved RCON command reliability
  - Increased delay between regeneration commands from 100ms to 200ms
  - Prevents server from dropping commands during bulk operations
  - Reduces failed regenerations due to server overload
  - Better stability for large entity counts (475+ entities)

### Technical Improvements
- Enhanced entity data availability checking with comprehensive fallback logic
- Improved error handling for database initialization and entity retrieval
- Better logging for diagnosing entity data sources (cached vs live)
- Optimized bulk regeneration timing for server stability

## [v0.5.1] - 2025-07-23

### Added
- **🗑️ Player Data Cleanup** - Database maintenance for stale player records
  - "Purge old data" button in Players tab for cleaning database
  - Removes players with no activity data or not seen in 14+ days
  - Confirmation dialog prevents accidental deletion
  - Shows count of removed records and refreshes player list
  - Helps maintain database performance and relevance

- **🎛️ Smart UI Improvements** - Enhanced interface clarity and usability
  - Removed confusing background service start/stop buttons from header
  - Smart FTP status display with progressive states (❌ Not configured → 🔧 Test FTP → ✅ Available)
  - Database tracking for successful FTP test status with immediate header updates
  - FTP settings form now allows partial updates without re-entering credentials
  - Improved tooltips and status messages for better user experience
  - Visual consistency with emoji icons matching RCON status display style

### Fixed - Settings Architecture
- **🔧 Configuration Architecture Cleanup** - Proper separation of settings by type
  - Moved `update_interval` from database to config file (`empyrion_helper.conf`)
  - Background service now properly reads update interval from config instead of hardcoded 20s
  - Fixed RCON polling frequency to respect user-configured interval
  - Settings now properly separated: credentials in database, app config in conf file

### Changed
- **⚙️ RCON Polling Behavior** - More predictable timing
  - Player status detection now uses configured interval (default 40s) instead of hardcoded 20s
  - Welcome/goodbye messages timing now respects user setting
  - Admins can now easily adjust polling frequency via config file

- **🌌 Entities UI Cleanup** - Removed instructional content from interface
  - Removed POI regeneration note container with implementation tips
  - Keeps UI focused on functionality, documentation belongs in README

## [v0.5.0] - 2025-07-22

### Added - ItemsConfig Management Feature
- **=� ItemsConfig.ecf Editor** - Complete ECF file management via FTP
  - Live FTP connection testing with detailed error reporting
  - Real-time download and parsing of ItemsConfig.ecf from server
  - Professional table interface with 1,100+ items display
  - Comprehensive pagination (50/100/250/500 items per page)
  - Safe property editing (StackSize, Mass, Volume, MarketPrice)
  - Template inheritance system with proper resolution
  - Advanced ECF parser with template detection and validation

- **= Enhanced FTP Integration**
  - Uses existing FTP settings from database (no hardcoded paths)
  - Secure temporary file handling with automatic cleanup
  - Comprehensive error handling for connection, permission, and file issues
  - File information display (size, download time, item counts)

- **=� ECF Parser Engine**
  - Handles complex ECF format with nested braces and property inheritance
  - Distinguishes between templates (9) and items (1,118+) correctly
  - Resolves template inheritance for complete item data
  - Safe property extraction with fallback handling
  - Support for complex property formats with metadata

### Technical Improvements
- Enhanced settings validation to require FTP remote path configuration
- Improved error messages for missing configuration
- Added comprehensive logging for FTP operations
- Secure file operations with proper temporary file cleanup

### Dependencies
- No new dependencies added - uses existing Flask, ftplib, and parsing libraries

## [v0.4.1] - Previous Release

### Features
- Background Service Architecture with persistent RCON connections
- Real-time Player Monitoring with 20-second update intervals
- Entity Management with database persistence and instant loading
- Automated Messaging System with welcome/goodbye and scheduled messages
- Professional Web Interface with dark theme and responsive design
- Enterprise-grade Security with AES-256 encryption for credentials
- Universal RCON Compatibility with automatic provider detection
- Comprehensive Logging with rotation and web-based viewer
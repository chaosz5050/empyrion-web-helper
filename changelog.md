# Changelog

All notable changes to Empyrion Web Helper will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v0.5.1] - 2025-07-23

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
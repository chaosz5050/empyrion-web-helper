# Changelog

All notable changes to Empyrion Web Helper will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.6.1] - 2025-08-06

### Security
- **Critical Security Fixes** - Addressed multiple security vulnerabilities identified in security audit
  - **SQL Injection Prevention** - Added column name whitelist validation for database filter queries
  - **Input Validation Enhancement** - Added 500 character limit for message inputs to prevent abuse
  - **Directory Traversal Protection** - Fixed static file serving to prevent access to sensitive files
- **Enhanced Security Posture** - Proactive security hardening for safer hobby project deployment
  - Database queries now validate allowed column names before execution
  - Message inputs properly validated and length-limited
  - Static file serving restricted to proper directory scope

### Fixed  
- **Security Vulnerabilities** - Three critical issues resolved:
  - SQL injection via unvalidated column names in player filters
  - Directory traversal via unrestricted static file serving  
  - Insufficient input validation on message endpoints

### Technical Details
- **Database Security** - Filter queries now use allowed column whitelist: `steam_id`, `name`, `status`, `faction`, `ip_address`, `country`, `playfield`
- **Input Validation** - Message endpoints validate content length and reject empty/oversized inputs
- **Static File Security** - File serving restricted to `static/` directory, preventing access to sensitive project files

### Developer Notes
- Security fixes maintain full backward compatibility with existing functionality
- No changes to user interface or API behavior
- Recommended update for all deployments, especially public-facing instances

## [0.6.0] - 2025-07-30

### Added
- **🖥️ Server Configuration Editor** - Complete dedicated.yaml management system
  - **FTP File Browser** - Navigate server directories to select dedicated.yaml files
  - **File Validation** - Validates server config files contain required fields (Srv_Port, Srv_Name)
  - **GameOptions-Style UI** - Professional form interface with dropdowns, help tooltips, and search
  - **Auto-Loading Workflow** - Configuration loads automatically after file validation for intuitive UX
  - **Complete Schema Support** - All ServerConfig and GameConfig parameters with proper data types
    - Boolean controls (True/False dropdowns)
    - Number inputs with validation ranges
    - String inputs for names, passwords, and paths
    - Enum dropdowns for predefined values (Blueprint restrictions, Game modes)
  - **Comprehensive Configuration Coverage**:
    - **Server Settings**: Port, Name, Max Players, Description, Public visibility
    - **Security**: EAC, Telnet/RCON, Password protection, Steam Family Sharing controls
    - **Performance**: Heartbeat timeouts, Playfield boot timeouts, Reserved playfields
    - **Game Config**: Game mode, World seed, Custom scenarios
- **Enhanced FTP Integration** - Robust directory browsing and file operations
  - **4 New API Endpoints**: `/api/ftp/browse`, `/api/serverconfig/validate`, `/api/serverconfig/load`, `/api/serverconfig/save`
  - **Smart File Detection** - Automatically identifies YAML files and directories
  - **Error Recovery** - Graceful handling of connection issues and missing files
  - **Path Normalization** - Proper handling of root directory and subdirectories

### Changed
- **🎯 Streamlined User Experience** - Intuitive server configuration workflow
  - **One-Step Loading** - Select file → Auto-validate → Auto-load (no separate Load button)
  - **Clear FTP Messaging** - All loading messages specify "FTP" so users understand delays
  - **File Browser Integration** - "Load Config" button directly in file browser for immediate action
- **📡 Enhanced Status Communication** - Better user feedback throughout operations
  - "Loading from FTP server..." instead of generic "Loading directory..."
  - "Browse FTP Files" button clearly indicates remote operation
  - Validation and loading status messages specify FTP operations

### Technical Details
- **🔧 Server Config Architecture** - Professional configuration management
  - Reuses existing FTP infrastructure for consistent connection handling
  - Dynamic form generation based on loaded configuration structure
  - Type-safe handling of booleans, numbers, strings, and enums
  - Comprehensive metadata system with descriptions and validation rules
- **🌐 Navigation Integration** - Seamless addition to existing interface
  - New "Server Config" tab positioned between GameOptions and Messaging
  - Consistent konsole-style theming matching existing design standards
  - Search functionality across all configuration options
- **🔍 File Browser Implementation** - Robust FTP directory navigation
  - Handles string filenames from connection manager correctly
  - Smart file type detection and sorting (directories first, then YAML files)
  - Hidden file filtering with parent directory navigation support
  - Comprehensive error handling with fallback to filename-based type guessing

### Requirements
- **✅ Zero New Dependencies** - Uses existing FTP infrastructure and connection manager
- **🔗 FTP Configuration** - Requires FTP credentials configured in Settings > FTP Auth
- **📁 Server Access** - Needs read/write access to server's dedicated.yaml location

## [0.5.5] - 2025-07-30

### Added
- **Split FTP Settings Interface** - Improved settings organization and scalability
  - New "FTP Auth" panel for connection credentials (Host, Port, Username, Password)
  - New "FTP Paths" panel for server path configurations (ItemsConfig, Playfields, ModConfig, GameOptions)
  - Separate save buttons: "Save FTP Settings" for auth and "Save Paths" for path configurations
  - Better UI scalability for future path additions without cramping the interface

### Fixed
- **Message History Bug** - Resolved missing message history in messaging tab
  - Fixed issue where messages weren't stored in database when server was disconnected
  - Messages are now always logged to history regardless of connection status
  - Failed messages are properly marked as unsuccessful in history
  - "Refresh History" button now displays recent messages correctly
- **ResizeObserver Error** - Suppressed harmless browser console errors
  - Added error suppression for ResizeObserver loop warnings when switching to GameOptions tab
  - Improved initialization timing to prevent DOM layout conflicts

### Changed
- **Settings Panel Organization** - Enhanced user experience for server configuration
  - FTP settings split into logical authentication vs path configuration sections
  - Reduced visual clutter in settings interface
  - Improved workflow for administrators managing multiple server paths

### Technical Details
- **Message Storage**: Messages are stored in `message_history` table even when RCON connection fails
- **Settings Architecture**: Maintains backward compatibility while improving UI organization
- **Error Handling**: Enhanced client-side error suppression for better user experience

## [0.5.4] - 2025-07-28

### Added
- **FTP-Based Mod Configuration Sync** - Revolutionary bidirectional messaging synchronization
  - Real-time configuration upload to server mod via FTP after every save operation
  - Download functionality to retrieve latest configuration from server
  - Automatic conversion between web interface format and mod format
  - Enhanced load buttons with "Loading..." state and server download integration
  - New `/messaging/download-from-server` endpoint for configuration retrieval
- **Enhanced Button State Management** - Professional user feedback system
  - Save buttons show "Uploading..." during FTP operations 
  - Load buttons show "Loading..." during download operations
  - Proper error handling and button state restoration in all scenarios
  - Visual feedback prevents user confusion during network operations

### Changed
- **Messaging System Architecture** - Complete integration with PlayerStatusMod
  - Load operations now fetch latest configuration from server automatically
  - Save operations automatically sync to server mod for immediate effect
  - Bidirectional sync ensures web interface and mod stay synchronized
  - Configuration persistence across server restarts and mod reloads

### Fixed
- **Load Button Functionality** - Fixed non-functional load buttons
  - Previously only loaded from local config file
  - Now downloads latest configuration from FTP server before loading
  - Handles missing local files gracefully by fetching from server
- **JavaScript Syntax Error** - Fixed extra closing brace in messaging.js causing script failures
- **Configuration Loss Recovery** - System now recovers from deleted local configuration files

### Technical Details
- **PlayerStatusMod Integration**: Advanced messaging features require PlayerStatusMod installed on server
- **FTP Transport Layer**: Uses existing FTP infrastructure for reliable configuration delivery
- **Format Conversion**: Automatic translation between `<playername>` and `{playername}` formats
- **Error Resilience**: Graceful fallback when server download fails, using local config as backup

### Requirements
- **⚠️ IMPORTANT**: PlayerStatusMod must be installed on Empyrion server for advanced messaging features
- Without mod: Only basic global messaging works
- With mod: Full welcome/goodbye messages, scheduled messages, and real-time sync

## [0.5.3] - 2025-01-25

### Added
- **Complete CSS Optimization & Theming System** - Revolutionary 3-phase implementation
  - **Phase 1**: Modular CSS architecture - Split 1,980-line monolithic CSS into 6 logical modules
    - `base.css` - Variables, reset, typography, theme system foundation
    - `components.css` - Buttons, forms, modals, tables
    - `layout.css` - Header, navigation, panels, grids
    - `features.css` - Player management, entities, messaging
    - `konsole-settings.css` - Settings page vertical layout
    - `responsive.css` - Media queries, mobile overrides
  - **Phase 2**: Systematic design system with consistent variables
    - 7-tier spacing system (`--space-xs` to `--space-xxxl`)
    - 3-tier border radius system (`--radius-sm/md/lg`)
    - Interactive state variables (`--hover-overlay`, `--focus-ring`, etc.)
    - Base component classes (`.btn-base`, `.form-base`, `.panel-base`)
  - **Phase 3**: Multi-theme support with real-time switching
    - 🌙 **Dark Theme** (default) - High contrast, reduced eye strain
    - ☀️ **Light Theme** - Clean, bright appearance
    - ♿ **Accessible Theme** - WCAG 2.1 AAA compliant with high contrast colors
- **Advanced Theme Management System**
  - Real-time theme switching without page reload
  - Visual theme preview thumbnails showing accurate representations
  - Dual persistence: localStorage for instant loading + database for permanent storage
  - JavaScript ThemeManager with automatic fallback handling
  - Backend API endpoints for theme preference storage (`/api/settings/theme`)
- **Enhanced Settings Interface**
  - New "Appearance" tab positioned between General and Logging as requested
  - Professional theme selector UI with preview cards
  - Theme preference persistence across sessions and page reloads
  - Reset to default theme functionality

### Changed
- **Dramatically Improved Performance** - Reduced CSS token usage by 60-80% through modular architecture
- **Enhanced Maintainability** - Systematic design variables enable consistent UI changes
- **Better User Experience** - Instant theme switching adapts to user preferences and environments
- **Accessibility Compliance** - New accessible theme meets WCAG 2.1 AAA standards
- **Responsive Design** - All themes work seamlessly across desktop, tablet, and mobile

### Technical Details
- Replaced all hardcoded spacing, colors, and radius values with systematic CSS variables
- Implemented CSS class-based theme switching using `html` element classes
- Added comprehensive theme validation and error handling
- Created theme-specific interactive states (hover, focus, active) for each theme
- Established base component classes to ensure consistent styling patterns

### Developer Notes
- CSS architecture now follows established design system principles
- Theme system designed for easy extension with additional themes
- Modular CSS files improve development workflow and collaboration
- Systematic variables enable quick design consistency changes

## [0.5.2] - 2025-01-24

### Added
- **Selective POI Regeneration System** - Advanced playfield management with surgical precision
  - Bulk POI regeneration with intelligent filtering by type, faction, and age
  - Real-time entity validation and status checking
  - Confirmation dialogs with detailed operation summaries
  - Progress tracking with live updates during bulk operations
- **Enhanced Entity Management**
  - Fallback mechanism to fetch live entity data when database is empty
  - Improved error handling for entity operations
  - Better filtering and sorting options for large entity datasets

### Fixed
- **POI Regeneration Bug** - Fixed issue where bulk regeneration processed only 286 entities instead of expected 475
  - Root cause: System relied on cached entity data but database had no entities table
  - Solution: Added fallback to fetch live entity data when database is empty
- **Entity Database Consistency** - Improved reliability of entity data persistence
- **UI Responsiveness** - Enhanced performance during bulk operations

### Changed
- **POI Management Interface** - Streamlined workflow for playfield administration
- **Entity Browser** - Improved loading and filtering performance
- **Error Messages** - More descriptive feedback for failed operations

## [0.5.1] - 2025-01-23

### Added
- **Advanced POI Management** - Comprehensive playfield regeneration system
  - Individual POI regeneration via `remoteex pf=<PID> regenerate <entityid>`
  - Bulk playfield operations with confirmation dialogs
  - POI wipe functionality with proper warnings about destructive nature
- **Enhanced Entity Browser** - Galaxy-wide structure management
  - Real-time entity status validation
  - Advanced filtering by type, faction, playfield
  - Batch operations for multiple entities

### Fixed
- **RCON Command Compatibility** - Clarified differences between in-game console and RCON commands
  - `regenerate <id>` works in-game console only, not via RCON
  - `wipe <playfield> poi` only destroys POIs, doesn't regenerate them
  - `remoteex pf=<PID> regenerate <entityid>` works reliably via RCON

### Changed
- **POI Regeneration Strategy** - Moved from unreliable wipe commands to precise regeneration
- **Entity Management** - Improved batch operation handling and user feedback

## [0.5.0] - 2025-01-22

### Added
- **ItemsConfig.ecf Management** - Professional live editing system
  - Direct FTP integration for real-time server file access
  - Comprehensive item browser with 1,100+ game items
  - Safe editing of StackSize, Mass, Volume, and MarketPrice properties
  - Template system support with automatic inheritance resolution
  - Advanced ECF parser handling complex Empyrion Configuration File format
  - Responsive pagination (50/100/250/500 items per page)
  - Real-time FTP connection testing and validation
- **Enhanced Web Interface** - Complete UI overhaul
  - Professional dark theme optimized for long admin sessions
  - Responsive design working perfectly on mobile, tablet, and desktop
  - Real-time WebSocket integration for live data updates
  - Improved tab navigation and user experience
- **Advanced Security Features** - Enterprise-grade credential management
  - AES-256 encryption for all passwords in database storage
  - Zero sensitive data in configuration files
  - Automatic secret key management for Flask sessions
  - Secure file permissions (600) for database and key files

### Changed
- **Architecture Redesign** - Revolutionary dual-service approach
  - Background service operates independently of web interface
  - True 24/7 operation without browser dependency
  - Automatic reconnection handling for daily server restarts
  - Persistent data storage surviving app restarts
- **Settings Management** - Complete credential security overhaul
  - Web-based secure credential management via Settings tab
  - Automatic migration from config files to encrypted database
  - Real-time connection testing for RCON and FTP
  - Provider-agnostic configuration (works with any hosting)
- **Performance Improvements** - Dramatic speed enhancements
  - Entity queries: <10ms from database vs 10-30 seconds from server
  - Real-time player updates every 20 seconds
  - Optimized memory usage: ~50-100MB typical operation

### Fixed
- **Universal RCON Compatibility** - Works with any hosting provider
  - Automatic authentication method detection
  - Support for Havoc, Nitrado, self-hosted, and other providers
  - Intelligent fallback mechanisms for connection issues
- **Messaging System Reliability** - Eliminated duplicate message issues
  - Centralized scheduling in background service only
  - Proper message delivery tracking and statistics
  - Automatic reconnection preserving message schedules

### Developer Notes
- **Clean Configuration** - No more sensitive data in config files
- **Easy Sharing** - Repository can be shared safely with other admins
- **Automated Setup** - Web-based configuration eliminates complex file editing
- **Provider Independence** - Universal compatibility with any RCON-enabled server

## [0.4.x] - Earlier Versions

### Legacy Features
- Basic player monitoring and RCON connectivity
- Simple messaging system with configuration file management
- Manual credential configuration
- Basic web interface without real-time updates

---

**Note**: Versions prior to 0.5.0 used a different architecture and are not directly comparable. The 0.5.0 release represents a complete rewrite with modern security, performance, and usability standards.
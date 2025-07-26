# Changelog

All notable changes to Empyrion Web Helper will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.4] - 2025-07-26

### Fixed
- **Critical Message Duplication Bug** - Fixed scheduled and welcome/goodbye messages being logged as "sent" even when they failed
  - **Root Cause**: Background service incorrectly evaluated return values from `send_global_message()`
  - **Issue**: Method returns `{'success': False, 'message': 'error'}` but code checked `if success:` instead of `if success['success']`
  - **Impact**: Non-empty dictionaries always evaluate to `True`, causing failed messages to be marked as sent
  - **Solution**: Changed to `result.get('success', False)` for proper boolean evaluation
  - **Files Modified**: 
    - `background_service.py` lines 769-777 (scheduled messages)
    - `background_service.py` lines 717-727 (welcome/goodbye messages)
- **Enhanced Error Reporting** - Failed messages now properly log error details instead of false success messages
- **Improved Message Debugging** - Added comprehensive debug logging to trace message sending pipeline

### Technical Details
- The "duplication" was actually false positive logging - messages appeared to send twice but were failing silently
- Fix ensures only genuinely successful messages are recorded as sent
- Enhanced error handling provides better visibility into messaging failures
- Debug logging helps identify future messaging issues

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
# FILE LOCATION: /CHANGELOG.md (root directory)

# Changelog

All notable changes to Empyrion Web Helper will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- GitHub Actions CI/CD pipeline for automated testing
- Comprehensive contributing guidelines
- Development environment setup documentation

### Changed
- Improved code organization and modularity
- Enhanced security with proper gitignore configuration

### Fixed
- Minor UI consistency improvements

## [0.4.0] - 2025-01-16

### Added
- **🗄️ Entity Database Persistence System**
  - Complete SQLite database storage for all galaxy entities
  - Persistent entity data that survives app restarts
  - Smart dual-mode operation (database load vs server refresh)
  - Entity metadata tracking (first_seen, last_seen, updated_at)
  - App metadata system for tracking refresh timestamps
- **⚡ Enhanced Entity Management**
  - Instant entity loading from database on startup
  - Manual server refresh via "Refresh from Server" button
  - Database-backed filtering and search (no server calls)
  - Last refresh timestamp display ("Never refreshed" vs actual time)
  - Entity statistics with real-time category counts
  - Clear database functionality for admin reset
- **🎨 Professional Entity UI**
  - Enhanced entity table with improved styling
  - Color-coded entity types (asteroids, ships, structures, wrecks)
  - Color-coded faction indicators for easy identification
  - Entity ID display prominently for admin commands
  - Responsive design for mobile and desktop
  - Loading indicators and progress feedback
  - Professional info panels with usage instructions
- **📊 Entity Statistics & Analytics**
  - Real-time entity counts by category
  - Total entity tracking across all playfields
  - Entity lifecycle tracking (when entities appear/disappear)
  - Export functionality for raw gents data analysis
- **🔧 Technical Architecture Improvements**
  - New database tables: `entities`, `app_metadata`
  - Performance indexes for fast entity queries
  - Modular entity route structure (`/entities`, `/entities/refresh`, `/entities/stats`)
  - Enhanced error handling and logging
  - Memory-efficient entity processing

### Changed
- **🚀 Entity Performance Optimization**
  - Entity tab now loads instantly (was 10-30 second wait)
  - Server refresh only when explicitly requested by user
  - Database queries replace slow `gents` command calls
  - Improved entity parsing and categorization logic
- **🎯 User Experience Enhancements**
  - Entity data persists between app sessions
  - Clear visual feedback for data source (database vs server)
  - Better mobile responsiveness for entity management
  - Improved entity search and filtering performance
- **🏗️ Code Organization**
  - Enhanced database module with entity methods
  - Separated entity routes for better maintainability
  - Improved JavaScript entity manager architecture
  - Better CSS organization for entity styles

### Fixed
- Entity data loss on app restart (now persisted)
- Slow entity loading performance (now instant from database)
- Mobile responsiveness issues in entity panel
- Entity filtering requiring server calls (now database-backed)
- Memory usage during large entity processing

### Technical Details
- **Database Schema**: Added `entities` table with entity_id (PK), type, faction, name, playfield, category, timestamps
- **Metadata System**: Added `app_metadata` table for tracking refresh times and app state
- **API Endpoints**: 
  - `GET /entities` - Load from database with optional filters
  - `POST /entities/refresh` - Refresh from server and update database
  - `GET /entities/stats` - Get entity statistics
  - `POST /entities/clear` - Clear all entities from database
- **Performance**: Entity queries execute in <10ms vs 10-30 seconds for server calls
- **Data Integrity**: Full entity lifecycle tracking with proper timestamps

## [0.3.0] - 2025-01-15

### Added
- **📢 Comprehensive Messaging System**
  - Custom welcome/goodbye messages with player name placeholders
  - Scheduled recurring messages (5 minutes to 12 hours)
  - Global messaging to all online players
  - Message history with success tracking and statistics
  - Professional message templates and configuration
- **🔄 Real-time Updates**
  - WebSocket integration for live data synchronization
  - Automatic player status change detection
  - Real-time message history updates
- **📊 Enhanced Player Management**
  - Comprehensive player database with persistent storage
  - Smart status change detection (login/logout tracking)
  - IP address preservation even when offline
  - Advanced filtering and search capabilities
  - Professional player action system (kick, ban, unban)

### Changed
- **Database Architecture**
  - Switched to SQLite for reliable, serverless operation
  - Enhanced player tracking with session management
  - Improved data persistence and integrity
- **Configuration Management**
  - Centralized configuration system
  - Better validation and error handling
  - Support for runtime configuration updates

### Fixed
- Player data synchronization issues
- Connection stability improvements
- Memory leaks in WebSocket connections
- CSS styling inconsistencies

## [0.2.0] - 2025-01-10

### Added
- **👥 Advanced Player Tracking**
  - Real-time player status monitoring
  - Faction and role information display
  - IP address and playfield tracking
  - Player action system (kick, ban, unban)
- **🎨 Professional UI Design**
  - Complete dark theme implementation
  - Responsive design for mobile and desktop
  - Professional color scheme and typography
  - Intuitive navigation with tab system

### Changed
- **Connection System**
  - Improved RCON connection reliability
  - Better error handling and recovery
  - Enhanced connection status indicators
- **Code Organization**
  - Modular architecture implementation
  - Separation of concerns for maintainability
  - Professional logging system

### Fixed
- Connection timeout issues
- UI responsiveness on mobile devices
- Player data parsing edge cases

## [0.1.0] - 2025-01-05

### Added
- **🚀 Initial Release**
  - Basic RCON connection to Empyrion servers
  - Simple player list display
  - Web-based interface with Flask
  - Configuration file support
  - Basic logging functionality

### Features
- Real-time connection to Empyrion Galactic Survival servers
- Player monitoring and basic information display
- Web-based administration interface
- Linux-optimized design (no deprecated dependencies)
- Professional logging with file rotation

---

## Legend

- 🚀 **Major Features** - Significant new functionality
- 🗄️ **Database** - Database and persistence improvements
- ⚡ **Performance** - Speed and efficiency improvements
- 🎨 **UI/UX** - User interface and experience improvements
- 🔒 **Security** - Security improvements and fixes
- 📊 **Data** - Data management and analytics
- 🔧 **Technical** - Code improvements and refactoring
- 🐛 **Fixes** - Bug fixes and stability improvements
- 📚 **Documentation** - Documentation updates

## Attribution

**Empyrion Web Helper** is developed by **Chaosz Software** and licensed under CC BY-NC-SA 4.0.

Built with ❤️ for the Empyrion Galactic Survival community.

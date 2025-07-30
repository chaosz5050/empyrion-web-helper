/**
 * Server Config Manager - Interactive form for editing Empyrion dedicated.yaml files
 * FTP file browser, validation, and GameOptions-style UI
 */

class ServerConfigManager {
    constructor() {
        this.currentServerConfig = {};
        this.selectedFilePath = null;
        this.currentDirectory = '/';
        this.isOperationRunning = false;
        this.fileBrowserOpen = false;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.renderConfigForm();
    }

    setupEventListeners() {
        // File browser controls
        const browseBtn = document.getElementById('browseServerConfigBtn');
        if (browseBtn) {
            browseBtn.addEventListener('click', () => {
                this.openFileBrowser();
            });
        }

        const closeBtn = document.getElementById('closeFileBrowserBtn');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                this.closeFileBrowser();
            });
        }

        const selectBtn = document.getElementById('selectFileBtn');
        if (selectBtn) {
            selectBtn.addEventListener('click', () => {
                this.selectFile();
            });
        }

        // Note: Load button removed - auto-load after file validation
        
        const saveBtn = document.getElementById('saveServerConfigBtn');
        if (saveBtn) {
            saveBtn.addEventListener('click', () => {
                this.saveServerConfig();
            });
        }

        // Search functionality
        const searchInput = document.getElementById('server-config-search');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                clearTimeout(this.searchTimeout);
                this.searchTimeout = setTimeout(() => {
                    this.filterOptions(e.target.value);
                }, 300);
            });
        }

        // Close tooltips when clicking outside
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.help-btn') && !e.target.closest('.option-tooltip')) {
                document.querySelectorAll('.option-tooltip').forEach(tooltip => {
                    tooltip.style.display = 'none';
                });
            }
        });
    }

    async openFileBrowser() {
        if (this.isOperationRunning) {
            showToast('Operation already in progress', 'warning');
            return;
        }

        this.setServerConfigStatus('Opening FTP file browser...', true);
        this.isOperationRunning = true;

        try {
            // Show the file browser
            const browserSection = document.getElementById('serverConfigFileBrowser');
            browserSection.style.display = 'block';
            this.fileBrowserOpen = true;

            // Load root directory
            await this.loadDirectory('/');

        } catch (error) {
            console.error('Error opening file browser:', error);
            showToast('Error opening file browser: ' + error, 'error');
            this.setServerConfigStatus('Error opening FTP file browser', false);
        } finally {
            this.isOperationRunning = false;
        }
    }

    closeFileBrowser() {
        const browserSection = document.getElementById('serverConfigFileBrowser');
        browserSection.style.display = 'none';
        this.fileBrowserOpen = false;
        this.setServerConfigStatus('Ready', false);
    }

    async loadDirectory(path) {
        const contentDiv = document.getElementById('fileBrowserContent');
        const pathSpan = document.getElementById('currentFilePath');
        
        contentDiv.innerHTML = '<div class="loading-spinner">🔄 Loading from FTP server...</div>';
        pathSpan.textContent = path;
        this.currentDirectory = path;

        try {
            const data = await apiCall('/api/ftp/browse', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path: path })
            });

            if (data.success) {
                this.renderFileList(data.files, path);
            } else {
                throw new Error(data.message || 'Failed to browse directory');
            }
        } catch (error) {
            console.error('Error loading directory:', error);
            contentDiv.innerHTML = `<div class="loading-spinner">❌ Error: ${error.message}</div>`;
        }
    }

    renderFileList(files, currentPath) {
        const contentDiv = document.getElementById('fileBrowserContent');
        contentDiv.innerHTML = '';

        // Add parent directory if not at root
        if (currentPath !== '/') {
            const parentPath = currentPath.split('/').slice(0, -1).join('/') || '/';
            const parentItem = this.createFileItem('..', 'directory', 0, parentPath);
            contentDiv.appendChild(parentItem);
        }

        // Sort files: directories first, then YAML files, then others
        const sortedFiles = files.sort((a, b) => {
            if (a.type !== b.type) {
                if (a.type === 'directory') return -1;
                if (b.type === 'directory') return 1;
                if (a.name.endsWith('.yaml') || a.name.endsWith('.yml')) return -1;
                if (b.name.endsWith('.yaml') || b.name.endsWith('.yml')) return 1;
            }
            return a.name.localeCompare(b.name);
        });

        sortedFiles.forEach(file => {
            const fullPath = currentPath === '/' ? `/${file.name}` : `${currentPath}/${file.name}`;
            const fileItem = this.createFileItem(file.name, file.type, file.size, fullPath);
            contentDiv.appendChild(fileItem);
        });
    }

    createFileItem(name, type, size, fullPath) {
        const item = document.createElement('div');
        item.className = 'file-item';
        
        const isYamlFile = name.endsWith('.yaml') || name.endsWith('.yml');
        const isDirectory = type === 'directory';
        const isParent = name === '..';

        if (isDirectory) {
            item.classList.add('directory');
        } else if (isYamlFile) {
            item.classList.add('yaml-file');
        }

        const icon = isParent ? '↩️' : (isDirectory ? '📁' : (isYamlFile ? '📄' : '📎'));
        const sizeStr = isDirectory ? '' : this.formatFileSize(size);

        item.innerHTML = `
            <span class="file-icon">${icon}</span>
            <span class="file-name">${escapeHtml(name)}</span>
            <span class="file-size">${sizeStr}</span>
        `;

        item.addEventListener('click', () => {
            if (isDirectory) {
                this.loadDirectory(fullPath);
            } else if (isYamlFile) {
                this.selectFileInBrowser(fullPath, name);
            }
        });

        return item;
    }

    selectFileInBrowser(filePath, fileName) {
        // Clear previous selections
        document.querySelectorAll('.file-item').forEach(item => {
            item.classList.remove('selected');
        });

        // Select this item
        event.currentTarget.classList.add('selected');

        // Update selected file display
        const selectedSpan = document.getElementById('selectedFileName');
        selectedSpan.textContent = fileName;

        // Enable select button
        const selectBtn = document.getElementById('selectFileBtn');
        selectBtn.disabled = false;

        this.selectedFilePath = filePath;
    }

    async selectFile() {
        if (!this.selectedFilePath) {
            showToast('No file selected', 'warning');
            return;
        }

        this.setServerConfigStatus('Validating server config file via FTP...', true);

        try {
            // Validate the file
            const validation = await apiCall('/api/serverconfig/validate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ file_path: this.selectedFilePath })
            });

            if (validation.success) {
                // File is valid, update UI
                const fileDisplay = document.getElementById('configFileDisplay');
                fileDisplay.textContent = this.selectedFilePath;

                // Close file browser
                this.closeFileBrowser();

                showToast('Valid server config file found - loading configuration...', 'success');
                
                // Auto-load the configuration immediately after validation
                await this.loadServerConfig();

            } else {
                throw new Error(validation.message || 'Invalid server config file');
            }

        } catch (error) {
            console.error('Error validating file:', error);
            showToast('File validation failed: ' + error.message, 'error');
            this.setServerConfigStatus('File validation failed', false);
        }
    }

    async loadServerConfig() {
        if (this.isOperationRunning) {
            showToast('Operation already in progress', 'warning');
            return;
        }

        if (!this.selectedFilePath) {
            showToast('No file selected', 'warning');
            return;
        }

        debugLog('loadServerConfig() called for:', this.selectedFilePath);
        this.setServerConfigStatus('Loading server configuration from FTP...', true);
        this.isOperationRunning = true;
        
        // Note: No load button anymore - loading happens automatically after validation

        try {
            const data = await apiCall('/api/serverconfig/load', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ file_path: this.selectedFilePath })
            });

            if (data.success) {
                this.currentServerConfig = data.config;
                this.renderConfigForm();
                
                // Enable save button and search
                const saveBtn = document.getElementById('saveServerConfigBtn');
                saveBtn.disabled = false;
                
                const searchInput = document.getElementById('server-config-search');
                searchInput.disabled = false;

                showToast('Server configuration loaded successfully', 'success');
                this.setServerConfigStatus('Configuration loaded and ready for editing', false);
                
            } else {
                throw new Error(data.message || 'Failed to load server configuration');
            }
        } catch (error) {
            console.error('Error loading server config:', error);
            showToast('Error loading configuration: ' + error.message, 'error');
            this.setServerConfigStatus('Error loading configuration', false);
        } finally {
            this.isOperationRunning = false;
        }
    }

    async saveServerConfig() {
        if (this.isOperationRunning) {
            showToast('Operation already in progress', 'warning');
            return;
        }

        if (!this.selectedFilePath || Object.keys(this.currentServerConfig).length === 0) {
            showToast('No configuration loaded to save', 'warning');
            return;
        }

        debugLog('saveServerConfig() called');
        this.setServerConfigStatus('Saving server configuration to FTP...', true);
        this.isOperationRunning = true;
        
        const saveBtn = document.getElementById('saveServerConfigBtn');
        const originalText = saveBtn.textContent;
        saveBtn.disabled = true;
        saveBtn.textContent = '💾 Saving...';

        try {
            const data = await apiCall('/api/serverconfig/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    file_path: this.selectedFilePath,
                    config_data: this.currentServerConfig
                })
            });

            if (data.success) {
                showToast('Server configuration saved successfully!', 'success');
                this.setServerConfigStatus('Configuration saved to server', false);
            } else {
                throw new Error(data.message || 'Failed to save server configuration');
            }
        } catch (error) {
            console.error('Error saving server config:', error);
            showToast('Error saving configuration: ' + error.message, 'error');
            this.setServerConfigStatus('Error saving configuration', false);
        } finally {
            this.isOperationRunning = false;
            saveBtn.disabled = false;
            saveBtn.textContent = originalText;
        }
    }

    renderConfigForm() {
        const container = document.getElementById('server-config-content');
        if (!container) return;

        // If no config loaded, show help message
        if (Object.keys(this.currentServerConfig).length === 0) {
            container.innerHTML = `
                <div class="no-config-message">
                    <h3>📄 No configuration loaded</h3>
                    <p>Click "Browse Files" to select a dedicated.yaml file from your server</p>
                    <div class="config-help">
                        <h4>What is dedicated.yaml?</h4>
                        <ul>
                            <li>Main server configuration file for Empyrion dedicated servers</li>
                            <li>Contains ServerConfig and GameConfig sections</li>
                            <li>Controls server name, port, max players, security settings, and more</li>
                            <li>Usually located in your server's root directory</li>
                        </ul>
                    </div>
                </div>
            `;
            return;
        }

        container.innerHTML = '';

        // Create configuration categories
        this.createServerConfigSection(container);
        this.createGameConfigSection(container);
    }

    createServerConfigSection(container) {
        if (!this.currentServerConfig.ServerConfig) return;

        const section = document.createElement('div');
        section.className = 'server-config-category';
        section.dataset.category = 'serverconfig';

        const serverConfig = this.currentServerConfig.ServerConfig;
        const optionCount = Object.keys(serverConfig).length;

        section.innerHTML = `
            <div class="category-header">
                <div class="category-title">
                    <h3><span class="category-icon">🖥️</span>Server Configuration<span class="category-count">${optionCount} options</span></h3>
                    <button class="category-toggle" data-category="serverconfig">
                        <span class="toggle-icon">▼</span>
                    </button>
                </div>
            </div>
            <div class="category-content" id="serverconfig-content"></div>
        `;

        const content = section.querySelector('.category-content');
        
        // Create form controls for each server config option
        Object.entries(serverConfig).forEach(([key, value]) => {
            const optionElement = this.createServerConfigOption(key, value, 'ServerConfig');
            content.appendChild(optionElement);
        });

        // Add toggle functionality
        section.querySelector('.category-toggle').addEventListener('click', () => {
            const isExpanded = content.style.display !== 'none';
            content.style.display = isExpanded ? 'none' : 'block';
            section.querySelector('.toggle-icon').textContent = isExpanded ? '▶' : '▼';
            section.classList.toggle('collapsed', isExpanded);
        });

        container.appendChild(section);
    }

    createGameConfigSection(container) {
        if (!this.currentServerConfig.GameConfig) return;

        const section = document.createElement('div');
        section.className = 'server-config-category';
        section.dataset.category = 'gameconfig';

        const gameConfig = this.currentServerConfig.GameConfig;
        const optionCount = Object.keys(gameConfig).length;

        section.innerHTML = `
            <div class="category-header">
                <div class="category-title">
                    <h3><span class="category-icon">🎮</span>Game Configuration<span class="category-count">${optionCount} options</span></h3>
                    <button class="category-toggle" data-category="gameconfig">
                        <span class="toggle-icon">▼</span>
                    </button>
                </div>
            </div>
            <div class="category-content" id="gameconfig-content"></div>
        `;

        const content = section.querySelector('.category-content');
        
        // Create form controls for each game config option
        Object.entries(gameConfig).forEach(([key, value]) => {
            const optionElement = this.createServerConfigOption(key, value, 'GameConfig');
            content.appendChild(optionElement);
        });

        // Add toggle functionality
        section.querySelector('.category-toggle').addEventListener('click', () => {
            const isExpanded = content.style.display !== 'none';
            content.style.display = isExpanded ? 'none' : 'block';
            section.querySelector('.toggle-icon').textContent = isExpanded ? '▶' : '▼';
            section.classList.toggle('collapsed', isExpanded);
        });

        container.appendChild(section);
    }

    createServerConfigOption(key, value, section) {
        const optionDiv = document.createElement('div');
        optionDiv.className = 'server-config-option';
        optionDiv.dataset.option = key;
        optionDiv.dataset.section = section;

        const optionMeta = this.getServerConfigOptionMeta(key);
        const control = this.createServerConfigControl(key, value, optionMeta);

        optionDiv.innerHTML = `
            <div class="option-header">
                <label class="option-label" for="${section}_${key}">
                    ${optionMeta.displayName}
                    ${optionMeta.unit ? `<span class="option-unit">(${optionMeta.unit})</span>` : ''}
                </label>
                <div class="option-control">
                    ${control}
                </div>
                <div class="option-meta">
                    <span class="value-source custom" title="Custom value">📋</span>
                    <button class="help-btn" data-option="${key}" title="Show help">?</button>
                </div>
            </div>
            <div class="option-tooltip" style="display: none;">
                <div class="tooltip-content">
                    ${optionMeta.description}
                    ${optionMeta.examples ? `<div class="tooltip-meta"><strong>Examples:</strong> ${optionMeta.examples}</div>` : ''}
                </div>
            </div>
        `;

        this.setupServerConfigOptionEventListeners(optionDiv, key, section);
        return optionDiv;
    }

    createServerConfigControl(key, value, meta) {
        const inputId = `${meta.section}_${key}`;

        if (meta.type === 'boolean') {
            return `
                <select id="${inputId}" class="option-select custom-value">
                    <option value="true" ${value === true || value === 'true' ? 'selected' : ''}>True</option>
                    <option value="false" ${value === false || value === 'false' ? 'selected' : ''}>False</option>
                </select>
            `;
        } else if (meta.type === 'number') {
            return `
                <input type="number" 
                       id="${inputId}" 
                       class="option-input custom-value"
                       value="${value}"
                       ${meta.min !== undefined ? `min="${meta.min}"` : ''}
                       ${meta.max !== undefined ? `max="${meta.max}"` : ''}
                >
            `;
        } else if (meta.allowedValues && Array.isArray(meta.allowedValues)) {
            let selectHtml = `<select id="${inputId}" class="option-select custom-value">`;
            meta.allowedValues.forEach(allowed => {
                const selected = value == allowed ? 'selected' : '';
                selectHtml += `<option value="${allowed}" ${selected}>${allowed}</option>`;
            });
            selectHtml += '</select>';
            return selectHtml;
        } else {
            return `
                <input type="text" 
                       id="${inputId}" 
                       class="option-input custom-value"
                       value="${escapeHtml(value)}"
                >
            `;
        }
    }

    getServerConfigOptionMeta(key) {
        // Basic metadata for common server config options
        const metadata = {
            // Server Config
            'Srv_Port': { displayName: 'Server Port', type: 'number', min: 1024, max: 65535, description: 'Port number for the game server' },
            'Srv_Name': { displayName: 'Server Name', type: 'string', description: 'Display name shown in server browser' },
            'Srv_Password': { displayName: 'Server Password', type: 'string', description: 'Password required to join server (optional)' },
            'Srv_MaxPlayers': { displayName: 'Max Players', type: 'number', min: 1, max: 100, description: 'Maximum number of concurrent players' },
            'Srv_Description': { displayName: 'Description', type: 'string', description: 'Server description shown in browser (max 127 chars)' },
            'Srv_Public': { displayName: 'Public Server', type: 'boolean', description: 'Show server in public browser listing' },
            'Srv_StopPeriod': { displayName: 'Auto Restart Period', type: 'number', unit: 'hours', description: 'Automatically restart server every N hours' },
            'Tel_Enabled': { displayName: 'Telnet Enabled', type: 'boolean', description: 'Enable telnet/RCON server' },
            'Tel_Port': { displayName: 'Telnet Port', type: 'number', min: 1024, max: 65535, description: 'Port for telnet/RCON connection' },
            'Tel_Pwd': { displayName: 'Telnet Password', type: 'string', description: 'Password for telnet/RCON access' },
            'EACActive': { displayName: 'EAC Active', type: 'boolean', description: 'Enable Easy Anti-Cheat protection' },
            'SaveDirectory': { displayName: 'Save Directory', type: 'string', description: 'Directory path for save games' },
            'MaxAllowedSizeClass': { displayName: 'Max Blueprint Size', type: 'number', min: 0, max: 100, description: 'Maximum allowed blueprint size class (0 = no limit)' },
            'AllowedBlueprints': { displayName: 'Allowed Blueprints', type: 'string', allowedValues: ['None', 'StockOnly', 'All'], description: 'Blueprint production restrictions' },
            'HeartbeatServer': { displayName: 'Server Heartbeat', type: 'number', unit: 'seconds', description: 'Playfield server heartbeat timeout (0 = disabled)' },
            'HeartbeatClient': { displayName: 'Client Heartbeat', type: 'number', unit: 'seconds', description: 'Client heartbeat timeout (0 = disabled)' },
            'DisableSteamFamilySharing': { displayName: 'Disable Family Sharing', type: 'boolean', description: 'Block Steam Family Sharing users' },
            'KickPlayerWithPing': { displayName: 'Max Ping', type: 'number', unit: 'ms', description: 'Kick players with ping higher than this value' },
            'TimeoutBootingPfServer': { displayName: 'Playfield Boot Timeout', type: 'number', unit: 'seconds', description: 'Timeout for playfield server startup' },
            'Srv_ReservePlayfields': { displayName: 'Reserve Playfields', type: 'number', min: 0, max: 10, description: 'Idle playfield servers held in reserve' },
            
            // Game Config
            'GameName': { displayName: 'Game Name', type: 'string', description: 'Internal game/save name identifier' },
            'Mode': { displayName: 'Game Mode', type: 'string', allowedValues: ['Survival', 'Creative', 'Freedom'], description: 'Primary gameplay mode' },
            'Seed': { displayName: 'World Seed', type: 'number', description: 'Random seed for world generation' },
            'CustomScenario': { displayName: 'Custom Scenario', type: 'string', description: 'Name of custom scenario to use' }
        };

        return metadata[key] || { 
            displayName: key, 
            type: 'string', 
            description: `Configuration option: ${key}`,
            section: 'Unknown'
        };
    }

    setupServerConfigOptionEventListeners(optionDiv, key, section) {
        // Help button toggle
        const helpBtn = optionDiv.querySelector('.help-btn');
        const tooltip = optionDiv.querySelector('.option-tooltip');
        
        helpBtn.addEventListener('click', (e) => {
            e.preventDefault();
            const isVisible = tooltip.style.display === 'block';
            
            // Hide all other tooltips
            document.querySelectorAll('.option-tooltip').forEach(t => t.style.display = 'none');
            
            // Toggle current tooltip
            tooltip.style.display = isVisible ? 'none' : 'block';
        });

        // Value change handler
        const control = optionDiv.querySelector(`#${section}_${key}`);
        if (control) {
            control.addEventListener('change', (e) => {
                this.onServerConfigOptionChanged(key, e.target.value, section);
            });
        }
    }

    onServerConfigOptionChanged(key, newValue, section) {
        // Convert value to appropriate type
        const meta = this.getServerConfigOptionMeta(key);
        let convertedValue = newValue;

        if (meta.type === 'boolean') {
            convertedValue = newValue === 'true';
        } else if (meta.type === 'number') {
            convertedValue = parseInt(newValue, 10);
            if (isNaN(convertedValue)) convertedValue = 0;
        }

        // Update the configuration
        if (!this.currentServerConfig[section]) {
            this.currentServerConfig[section] = {};
        }
        this.currentServerConfig[section][key] = convertedValue;

        console.log(`Server config ${section}.${key} changed to:`, convertedValue);
    }

    filterOptions(searchTerm) {
        const categories = document.querySelectorAll('.server-config-category');
        const lowerSearch = searchTerm.toLowerCase();

        categories.forEach(category => {
            const options = category.querySelectorAll('.server-config-option');
            let visibleCount = 0;

            options.forEach(option => {
                const optionName = option.querySelector('.option-label').textContent.toLowerCase();
                const optionKey = option.dataset.option.toLowerCase();
                const tooltipContent = option.querySelector('.tooltip-content');
                const optionDescription = tooltipContent ? tooltipContent.textContent.toLowerCase() : '';

                const matches = optionName.includes(lowerSearch) || 
                              optionKey.includes(lowerSearch) ||
                              optionDescription.includes(lowerSearch);

                option.style.display = matches ? 'block' : 'none';
                if (matches) visibleCount++;
            });

            // Hide category if no visible options
            category.style.display = visibleCount > 0 ? 'block' : 'none';
            
            // Update category count
            const countSpan = category.querySelector('.category-count');
            if (countSpan) {
                const totalOptions = category.querySelectorAll('.server-config-option').length;
                countSpan.textContent = searchTerm ? `${visibleCount}/${totalOptions} options` : `${totalOptions} options`;
            }
        });
    }

    setServerConfigStatus(message, isLoading = false) {
        const statusElement = document.getElementById('serverconfigStatus');
        const statusText = document.getElementById('serverconfigStatusText');
        
        if (statusElement && statusText) {
            statusText.textContent = message;
            statusElement.style.display = 'block';
            
            if (isLoading) {
                statusElement.className = 'konsole-status-bar loading';
            } else {
                statusElement.className = 'konsole-status-bar';
            }
        }
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }
}

// Global instance
let serverConfigManager = null;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(() => {
        try {
            serverConfigManager = new ServerConfigManager();
            window.serverConfigManager = serverConfigManager;
        } catch (error) {
            console.error('Error initializing ServerConfigManager:', error);
        }
    }, 100);
});
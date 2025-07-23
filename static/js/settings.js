// FILE LOCATION: /static/js/settings.js
/**
 * Settings management functionality for Empyrion Web Helper
 * Konsole-style interface with real data loading
 * Copyright (c) 2025 Chaosz Software
 */

// Settings Manager
window.SettingsManager = {
    currentPanel: 'rcon-settings',
    settingsData: {},

    init() {
        debugLog('Settings manager initialized - Konsole style');
        this.setupNavigation();
        this.setupSearch();
        this.loadAllSettings();
    },

    setupNavigation() {
        // Add click handlers to navigation items
        document.querySelectorAll('.konsole-nav-item').forEach(item => {
            item.addEventListener('click', (e) => {
                const target = item.getAttribute('data-target');
                this.switchPanel(target);
            });
        });
    },

    setupSearch() {
        const searchInput = document.getElementById('settingsSearch');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.filterSettings(e.target.value);
            });
        }
    },

    switchPanel(panelId) {
        // Remove active class from all nav items and panels
        document.querySelectorAll('.konsole-nav-item').forEach(item => {
            item.classList.remove('active');
        });
        document.querySelectorAll('.konsole-content-panel').forEach(panel => {
            panel.classList.remove('active');
        });

        // Add active class to selected nav item and panel
        const navItem = document.querySelector(`[data-target="${panelId}"]`);
        const panel = document.getElementById(panelId);
        
        if (navItem) navItem.classList.add('active');
        if (panel) panel.classList.add('active');
        
        this.currentPanel = panelId;
        debugLog(`Switched to panel: ${panelId}`);
    },

    filterSettings(searchTerm) {
        const term = searchTerm.toLowerCase();
        
        // Show/hide nav items based on search
        document.querySelectorAll('.konsole-nav-item').forEach(item => {
            const label = item.querySelector('.konsole-nav-label').textContent.toLowerCase();
            if (label.includes(term) || term === '') {
                item.style.display = 'flex';
            } else {
                item.style.display = 'none';
            }
        });

        // If current panel is hidden, switch to first visible panel
        if (term !== '') {
            const currentNavItem = document.querySelector(`[data-target="${this.currentPanel}"]`);
            if (currentNavItem && currentNavItem.style.display === 'none') {
                const firstVisible = document.querySelector('.konsole-nav-item[style=""] , .konsole-nav-item:not([style*="none"])');
                if (firstVisible) {
                    const target = firstVisible.getAttribute('data-target');
                    this.switchPanel(target);
                }
            }
        }
    },

    async loadAllSettings() {
        try {
            // Load RCON status
            await this.loadRconStatus();
            
            // Load FTP status  
            await this.loadFtpStatus();
            
            // Load general settings
            await this.loadGeneralSettings();
            
            // Load logging settings
            await this.loadLoggingSettings();
            
            // Update status display
            this.updateStatusDisplay();
            
        } catch (error) {
            console.error('Error loading settings:', error);
            showToast('Error loading settings', 'error');
        }
    },

    async loadRconStatus() {
        try {
            const data = await apiCall('/api/credentials/status');
            
            if (data.rcon) {
                document.getElementById('rconPassword').placeholder = '••••••••••••';
                this.settingsData.rcon = { configured: true };
            } else {
                this.settingsData.rcon = { configured: false };
            }

            // Load server settings
            const serverHost = await this.getAppSetting('server_host');
            const serverPort = await this.getAppSetting('server_port');
            
            if (serverHost) document.getElementById('rconHost').value = serverHost;
            if (serverPort) document.getElementById('rconPort').value = serverPort;
            
        } catch (error) {
            debugLog('Error loading RCON status:', error);
        }
    },

    async loadFtpStatus() {
        try {
            const data = await apiCall('/api/credentials/status');
            
            if (data.ftp) {
                document.getElementById('ftpPassword').placeholder = '••••••••••••';
                document.getElementById('ftpUsername').placeholder = '••••••••••••';
                this.settingsData.ftp = { configured: true };
            } else {
                this.settingsData.ftp = { configured: false };
            }

            // Load FTP settings
            const ftpHost = await this.getAppSetting('ftp_host');
            const ftpRemotePath = await this.getAppSetting('ftp_remote_log_path');
            
            if (ftpHost) {
                // Parse host:port format
                const [host, port] = ftpHost.split(':');
                document.getElementById('ftpHost').value = host;
                document.getElementById('ftpPort').value = port || '21';
            }
            if (ftpRemotePath) document.getElementById('ftpRemotePath').value = ftpRemotePath;
            
        } catch (error) {
            debugLog('Error loading FTP status:', error);
        }
    },

    async loadGeneralSettings() {
        try {
            const monitoringData = await apiCall('/api/settings/monitoring');
            
            if (monitoringData.update_interval) {
                document.getElementById('updateInterval').value = monitoringData.update_interval;
            }

            // Load geolocation setting
            const enableGeo = await this.getAppSetting('enable_geolocation');
            
            if (enableGeo !== 'false') {
                document.getElementById('enableGeoLocation').checked = true;
            }
            
        } catch (error) {
            debugLog('Error loading general settings:', error);
        }
    },

    async loadLoggingSettings() {
        try {
            const data = await apiCall('/logging/settings');
            
            if (data.success && data.settings) {
                document.getElementById('maxLogSize').value = data.settings.max_size_mb || 1;
                document.getElementById('backupCount').value = data.settings.backup_count || 3;
                document.getElementById('maxLogAge').value = data.settings.max_age_days || 7;
            }
            
        } catch (error) {
            debugLog('Error loading logging settings:', error);
        }
    },

    async getAppSetting(key) {
        try {
            const response = await fetch(`/api/settings/${key}`);
            if (response.ok) {
                const data = await response.json();
                return data.value;
            }
        } catch (error) {
            debugLog(`Error getting app setting ${key}:`, error);
        }
        return null;
    },

    updateStatusDisplay() {
        const rconStatus = document.getElementById('rconStatus');
        const ftpStatus = document.getElementById('ftpStatus');
        const lastSaved = document.getElementById('lastSaved');

        if (rconStatus) {
            rconStatus.textContent = this.settingsData.rcon?.configured ? '✅ Configured' : '❌ Not configured';
            rconStatus.style.color = this.settingsData.rcon?.configured ? 'var(--accent-green)' : 'var(--accent-red)';
        }

        // DON'T update FTP status here - let header.html handle connection status
        // The header shows actual connection status, not just configuration status

        if (lastSaved) {
            lastSaved.textContent = new Date().toLocaleString();
        }
    },

    // Password visibility toggle
    togglePassword(inputId) {
        const input = document.getElementById(inputId);
        const button = input.nextElementSibling;
        
        if (input.type === 'password') {
            input.type = 'text';
            button.textContent = '🙈';
        } else {
            input.type = 'password';
            button.textContent = '👁️';
        }
    },

    // RCON Settings
    async saveRconSettings() {
        const host = document.getElementById('rconHost').value.trim();
        const port = document.getElementById('rconPort').value.trim();
        const password = document.getElementById('rconPassword').value.trim();

        if (!host || !port || !password) {
            showToast('Please fill in all RCON fields', 'error');
            return;
        }

        if (parseInt(port) < 1 || parseInt(port) > 65535) {
            showToast('Port must be between 1 and 65535', 'error');
            return;
        }

        try {
            // Save server settings
            await this.setAppSetting('server_host', host);
            await this.setAppSetting('server_port', port);

            // Save RCON credentials
            const credData = await apiCall('/api/credentials/set', {
                method: 'POST',
                body: JSON.stringify({
                    rcon_password: password
                })
            });

            if (credData.success) {
                showToast('RCON settings saved successfully', 'success');
                this.settingsData.rcon = { configured: true };
                document.getElementById('rconPassword').placeholder = '••••••••••••';
                document.getElementById('rconPassword').value = '';
                this.updateStatusDisplay();
            } else {
                showToast('Failed to save RCON credentials', 'error');
            }

        } catch (error) {
            console.error('Error saving RCON settings:', error);
            showToast('Error saving RCON settings', 'error');
        }
    },

    async testRconConnection() {
        showToast('Loading RCON test...', 'info');
        
        try {
            // Get saved credentials from database
            const credData = await apiCall('/api/credentials/get/rcon');
            
            if (!credData.success) {
                showToast('Error loading RCON credentials', 'error');
                return;
            }

            const { host, port, password } = credData;

            if (!host || !port) {
                showToast('Please save server host and port first', 'error');
                return;
            }

            if (!password) {
                showToast('Please save RCON password first', 'error');
                return;
            }

            showToast('Testing RCON connection...', 'info');
            
            const testData = await apiCall('/api/test/rcon', {
                method: 'POST',
                body: JSON.stringify({ host, port, password })
            });

            if (testData.success) {
                showToast(testData.message || 'RCON connection test successful', 'success');
            } else {
                showToast(testData.message || 'RCON connection test failed', 'error');
            }
        } catch (error) {
            showToast('RCON connection test failed', 'error');
        }
    },

    // FTP Settings
    async saveFtpSettings() {
        const host = document.getElementById('ftpHost').value.trim();
        const port = document.getElementById('ftpPort').value.trim() || '21';
        const username = document.getElementById('ftpUsername').value.trim();
        const password = document.getElementById('ftpPassword').value.trim();
        const remotePath = document.getElementById('ftpRemotePath').value.trim();

        // Check if host and path are provided (always required)
        if (!host || !remotePath) {
            showToast('Please provide FTP host and remote path', 'error');
            return;
        }

        // Check if credentials are already configured
        const credentialsConfigured = this.settingsData.ftp?.configured;
        
        // Only require credentials if not already configured
        if (!credentialsConfigured && (!username || !password)) {
            showToast('Please provide FTP username and password for first-time setup', 'error');
            return;
        }

        try {
            // Always save FTP settings (host and path)
            await this.setAppSetting('ftp_host', `${host}:${port}`);
            await this.setAppSetting('ftp_remote_log_path', remotePath);

            // Only update credentials if new ones are provided
            if (username && password) {
                const credData = await apiCall('/api/credentials/set', {
                    method: 'POST',
                    body: JSON.stringify({
                        ftp_user: username,
                        ftp_password: password
                    })
                });

                if (!credData.success) {
                    showToast('Failed to save FTP credentials', 'error');
                    return;
                }
                
                // Update UI to show credentials are configured
                this.settingsData.ftp = { configured: true };
                document.getElementById('ftpUsername').placeholder = '••••••••••••';
                document.getElementById('ftpPassword').placeholder = '••••••••••••';
                document.getElementById('ftpUsername').value = '';
                document.getElementById('ftpPassword').value = '';
                
                showToast('FTP settings and credentials saved successfully', 'success');
            } else {
                showToast('FTP settings saved successfully (credentials unchanged)', 'success');
            }
            
            // Clear FTP test status when settings change (need to retest)
            await apiCall('/api/settings/ftp_test_status', {
                method: 'POST',
                body: JSON.stringify({ value: '' })
            });
            
            this.updateStatusDisplay();
            
            // Immediately update FTP status in header to reflect changes
            if (typeof updateFtpConnectionStatus === 'function') {
                updateFtpConnectionStatus();
            }

        } catch (error) {
            console.error('Error saving FTP settings:', error);
            showToast('Error saving FTP settings', 'error');
        }
    },

    async testFtpConnection() {
        showToast('Loading FTP test...', 'info');
        
        try {
            // Get saved credentials from database
            const credData = await apiCall('/api/credentials/get/ftp');
            
            if (!credData.success) {
                showToast('Error loading FTP credentials', 'error');
                return;
            }

            const { host, username, password } = credData;

            if (!host) {
                showToast('Please save FTP host settings first', 'error');
                return;
            }

            if (!username || !password) {
                showToast('Please save FTP credentials first', 'error');
                return;
            }

            // Extract port from host if present (host:port format)
            let testHost = host;
            let port = '21';
            if (host.includes(':')) {
                const parts = host.split(':');
                testHost = parts[0];
                port = parts[1] || '21';
            }

            showToast('Testing FTP connection...', 'info');
            
            const testData = await apiCall('/api/test/ftp', {
                method: 'POST',
                body: JSON.stringify({ 
                    host: `${testHost}:${port}`, 
                    username, 
                    password 
                })
            });

            if (testData.success) {
                showToast(testData.message || 'FTP connection test successful', 'success');
                
                // Immediately update FTP status in header (don't wait for periodic refresh)
                if (typeof updateFtpConnectionStatus === 'function') {
                    updateFtpConnectionStatus();
                }
            } else {
                showToast(testData.message || 'FTP connection test failed', 'error');
            }
        } catch (error) {
            showToast('FTP connection test failed', 'error');
        }
    },

    // General Settings
    async saveGeneralSettings() {
        const updateInterval = document.getElementById('updateInterval').value.trim();
        const enableGeoLocation = document.getElementById('enableGeoLocation').checked;

        if (!updateInterval || parseInt(updateInterval) < 10) {
            showToast('Update interval must be at least 10 seconds', 'error');
            return;
        }

        try {
            // Save monitoring settings
            const monitoringData = await apiCall('/api/settings/monitoring', {
                method: 'POST',
                body: JSON.stringify({
                    update_interval: parseInt(updateInterval)
                })
            });

            if (!monitoringData.success) {
                throw new Error('Failed to save monitoring settings');
            }

            // Save geolocation setting
            await this.setAppSetting('enable_geolocation', enableGeoLocation.toString());

            showToast('General settings saved successfully', 'success');
            this.updateStatusDisplay();

        } catch (error) {
            console.error('Error saving general settings:', error);
            showToast('Error saving general settings', 'error');
        }
    },

    async resetToDefaults() {
        if (!confirm('Are you sure you want to reset all settings to defaults? This will not affect saved credentials.')) {
            return;
        }

        try {
            // Reset form values to defaults
            document.getElementById('updateInterval').value = '20';
            document.getElementById('enableGeoLocation').checked = true;

            // Save the defaults
            await this.saveGeneralSettings();
            
            showToast('Settings reset to defaults', 'success');

        } catch (error) {
            console.error('Error resetting settings:', error);
            showToast('Error resetting settings', 'error');
        }
    },

    // Logging Settings
    async saveLoggingSettings() {
        const maxSize = document.getElementById('maxLogSize').value.trim();
        const backupCount = document.getElementById('backupCount').value.trim();
        const maxAge = document.getElementById('maxLogAge').value.trim();

        if (!maxSize || !backupCount || !maxAge) {
            showToast('Please fill in all logging fields', 'error');
            return;
        }

        const maxSizeNum = parseInt(maxSize);
        const backupCountNum = parseInt(backupCount);
        const maxAgeNum = parseInt(maxAge);

        if (maxSizeNum < 1 || maxSizeNum > 50) {
            showToast('Max log size must be between 1-50 MB', 'error');
            return;
        }

        if (backupCountNum < 1 || backupCountNum > 10) {
            showToast('Backup count must be between 1-10', 'error');
            return;
        }

        if (maxAgeNum < 1 || maxAgeNum > 30) {
            showToast('Max age must be between 1-30 days', 'error');
            return;
        }

        try {
            const data = await apiCall('/logging/settings', {
                method: 'POST',
                body: JSON.stringify({
                    max_size_mb: maxSizeNum,
                    backup_count: backupCountNum,
                    max_age_days: maxAgeNum
                })
            });

            if (data.success) {
                showToast('Logging settings saved successfully', 'success');
                this.updateStatusDisplay();
            } else {
                showToast('Failed to save logging settings', 'error');
            }

        } catch (error) {
            console.error('Error saving logging settings:', error);
            showToast('Error saving logging settings', 'error');
        }
    },

    async cleanupOldLogs() {
        if (!confirm('Are you sure you want to cleanup old log files? This will delete logs older than the configured age.')) {
            return;
        }

        try {
            const data = await apiCall('/logging/cleanup', { method: 'POST' });

            if (data.success) {
                showToast(data.message || 'Old logs cleaned up successfully', 'success');
            } else {
                showToast('Failed to cleanup old logs', 'error');
            }

        } catch (error) {
            console.error('Error cleaning up logs:', error);
            showToast('Error cleaning up logs', 'error');
        }
    },

    // Add missing loadCurrentSettings function for utils.js compatibility
    loadCurrentSettings() {
        // This function is called by utils.js showTab function
        // Just reload all settings
        this.loadAllSettings();
    },

    // Helper methods
    async setAppSetting(key, value) {
        try {
            const response = await fetch(`/api/settings/${key}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ value })
            });
            return response.ok;
        } catch (error) {
            debugLog(`Error setting app setting ${key}:`, error);
            return false;
        }
    }
};

// Global functions for HTML onclick handlers
function switchSettingsPanel(panelId) {
    if (window.SettingsManager) {
        window.SettingsManager.switchPanel(panelId);
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    if (window.SettingsManager) {
        window.SettingsManager.init();
    }
});
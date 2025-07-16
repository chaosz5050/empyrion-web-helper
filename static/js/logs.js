// FILE LOCATION: /static/js/logs.js
/**
 * Log management functionality for Empyrion Web Helper
 * Enhanced with geolocation management
 * Copyright (c) 2025 Chaosz Software
 */

// Logs Manager
window.LogsManager = {
    init() {
        debugLog('Logs manager initialized');
    },

    async refreshLogStats() {
        debugLog('DEBUG: refreshLogStats() called');
        
        try {
            const data = await apiCall('/logging/stats');
            debugLog('DEBUG: Response data:', data);
            
            if (data.success && data.stats) {
                debugLog('DEBUG: Stats received:', data.stats);
                this.updateLogStatsDisplay(data.stats);
            } else {
                debugLog('DEBUG: No stats in response or success=false');
                showToast(data.message || 'Failed to load log statistics', 'error');
            }
        } catch (error) {
            console.error('Error loading log stats:', error);
            showToast('Error loading log statistics: ' + error, 'error');
        }
    },

    updateLogStatsDisplay(stats) {
        // Current log size - show KiB for small files, MB for larger ones
        let currentSizeText = '0 MB';
        if (stats.current_log && stats.current_log.exists) {
            const sizeBytes = stats.current_log.size;
            if (sizeBytes < 1024 * 1024) {
                // Less than 1MB, show in KiB
                currentSizeText = `${(sizeBytes / 1024).toFixed(1)} KiB`;
            } else {
                // 1MB or larger, show in MB
                currentSizeText = `${stats.current_log.size_mb.toFixed(2)} MB`;
            }
        }
        
        const currentLogSize = document.getElementById('currentLogSize');
        const totalLogFiles = document.getElementById('totalLogFiles');
        const totalLogSize = document.getElementById('totalLogSize');
        
        if (currentLogSize) currentLogSize.textContent = currentSizeText;
        if (totalLogFiles) totalLogFiles.textContent = stats.total_files || 0;
        
        // Total size - show KiB for small totals, MB for larger ones
        let totalSizeText = '0 MB';
        if (stats.total_size_mb) {
            if (stats.total_size_mb < 1) {
                // Less than 1MB total, show in KiB
                const totalKiB = (stats.total_size_mb * 1024);
                totalSizeText = `${totalKiB.toFixed(1)} KiB`;
            } else {
                // 1MB or larger total, show in MB
                totalSizeText = `${stats.total_size_mb.toFixed(2)} MB`;
            }
        }
        
        if (totalLogSize) totalLogSize.textContent = totalSizeText;
        
        debugLog('DEBUG: Updated log stats display:', {
            currentSize: currentSizeText,
            totalFiles: stats.total_files,
            totalSize: totalSizeText,
            rawStats: stats
        });
    },

    async loadLogSettings() {
        try {
            const data = await apiCall('/logging/settings');
            
            if (data.success && data.settings) {
                const maxSizeInput = document.getElementById('maxSizeInput');
                const backupCountInput = document.getElementById('backupCountInput');
                const maxAgeInput = document.getElementById('maxAgeInput');
                const maxLogSize = document.getElementById('maxLogSize');
                
                if (maxSizeInput) maxSizeInput.value = data.settings.max_size_mb;
                if (backupCountInput) backupCountInput.value = data.settings.backup_count;
                if (maxAgeInput) maxAgeInput.value = data.settings.max_age_days;
                if (maxLogSize) maxLogSize.textContent = `${data.settings.max_size_mb} MB`;
            }
        } catch (error) {
            console.error('Error loading log settings:', error);
        }
    },

    async saveLogSettings() {
        const maxSizeInput = document.getElementById('maxSizeInput');
        const backupCountInput = document.getElementById('backupCountInput');
        const maxAgeInput = document.getElementById('maxAgeInput');

        const maxSizeMb = parseInt(maxSizeInput.value);
        const backupCount = parseInt(backupCountInput.value);
        const maxAgeDays = parseInt(maxAgeInput.value);

        if (maxSizeMb < 1 || maxSizeMb > 50) {
            showToast('Max size must be between 1-50 MB', 'error');
            return;
        }

        if (backupCount < 1 || backupCount > 10) {
            showToast('Backup count must be between 1-10 files', 'error');
            return;
        }

        if (maxAgeDays < 1 || maxAgeDays > 30) {
            showToast('Max age must be between 1-30 days', 'error');
            return;
        }

        try {
            const data = await apiCall('/logging/settings', {
                method: 'POST',
                body: JSON.stringify({
                    max_size_mb: maxSizeMb,
                    backup_count: backupCount,
                    max_age_days: maxAgeDays
                })
            });
            
            if (data.success) {
                showToast('Log settings saved successfully', 'success');
                const maxLogSize = document.getElementById('maxLogSize');
                if (maxLogSize) maxLogSize.textContent = `${maxSizeMb} MB`;
                this.refreshLogStats();
            } else {
                showToast(data.message || 'Failed to save log settings', 'error');
            }
        } catch (error) {
            console.error('Error saving log settings:', error);
            showToast('Error saving log settings: ' + error, 'error');
        }
    },

    async loadRecentLogs() {
        debugLog('DEBUG: loadRecentLogs() called');
        
        const logLinesSelect = document.getElementById('logLinesSelect');
        const lines = logLinesSelect ? logLinesSelect.value : '100';
        debugLog('DEBUG: Requesting', lines, 'lines');
        
        try {
            const data = await apiCall(`/logging/recent?lines=${lines}`);
            debugLog('DEBUG: Recent logs response data:', data);
            
            if (data.success && data.logs) {
                debugLog('DEBUG: Received', data.logs.length, 'log lines');
                
                const logsContent = document.getElementById('recentLogsContent');
                if (logsContent) {
                    if (data.logs.length > 0) {
                        logsContent.textContent = data.logs.join('\n');
                        // Scroll to bottom
                        logsContent.scrollTop = logsContent.scrollHeight;
                        debugLog('DEBUG: Updated logs content');
                    } else {
                        logsContent.textContent = 'No log entries found.';
                        debugLog('DEBUG: No log entries found');
                    }
                }
            } else {
                debugLog('DEBUG: Failed to load recent logs:', data.message);
                showToast(data.message || 'Failed to load recent logs', 'error');
            }
        } catch (error) {
            console.error('Error loading recent logs:', error);
            showToast('Error loading recent logs: ' + error, 'error');
        }
    },

    async cleanupOldLogs() {
        if (!confirm('Are you sure you want to clean up old log files? This will delete logs older than the configured age.')) {
            return;
        }

        try {
            const data = await apiCall('/logging/cleanup', { method: 'POST' });
            
            if (data.success) {
                showToast(data.message, 'success');
                this.refreshLogStats();
            } else {
                showToast(data.message || 'Failed to cleanup old logs', 'error');
            }
        } catch (error) {
            console.error('Error cleaning up logs:', error);
            showToast('Error cleaning up logs: ' + error, 'error');
        }
    },

    async clearAllLogs() {
        if (!confirm('Are you sure you want to clear ALL log files? This action cannot be undone and will delete all logging history.')) {
            return;
        }

        try {
            const data = await apiCall('/logging/clear', { method: 'POST' });
            
            if (data.success) {
                showToast(data.message, 'success');
                this.refreshLogStats();
                // Clear the logs display
                const recentLogsContent = document.getElementById('recentLogsContent');
                if (recentLogsContent) {
                    recentLogsContent.textContent = 'Logs cleared. Click "Refresh Logs" to load new entries.';
                }
            } else {
                showToast(data.message || 'Failed to clear logs', 'error');
            }
        } catch (error) {
            console.error('Error clearing logs:', error);
            showToast('Error clearing logs: ' + error, 'error');
        }
    },

    downloadCurrentLog() {
        // Simple download by opening the log file
        // For a better download experience, we could add a dedicated download endpoint
        showToast('Log download feature - use "Refresh Logs" and copy the content for now', 'info');
    },

    // ============================================================================
    // GEOLOCATION MANAGEMENT METHODS
    // ============================================================================

    async refreshGeoStats() {
        debugLog('DEBUG: refreshGeoStats() called');
        
        try {
            const data = await apiCall('/geolocation/stats');
            debugLog('DEBUG: Geolocation stats response:', data);
            
            if (data.success && data.stats) {
                this.updateGeoStatsDisplay(data.stats);
            } else {
                showToast(data.message || 'Failed to load geolocation statistics', 'error');
            }
        } catch (error) {
            console.error('Error loading geolocation stats:', error);
            showToast('Error loading geolocation statistics: ' + error, 'error');
        }
    },

    updateGeoStatsDisplay(stats) {
        debugLog('DEBUG: Updating geolocation stats display:', stats);
        
        const playersWithGeo = document.getElementById('playersWithGeo');
        const playersWithoutGeo = document.getElementById('playersWithoutGeo');
        const geoCacheSize = document.getElementById('geoCacheSize');
        const topCountry = document.getElementById('topCountry');
        const countryList = document.getElementById('countryList');
        
        if (playersWithGeo) playersWithGeo.textContent = stats.with_geolocation || 0;
        if (playersWithoutGeo) playersWithoutGeo.textContent = stats.without_geolocation || 0;
        if (geoCacheSize) geoCacheSize.textContent = stats.cache_size || 0;
        
        // Find top country
        let topCountryName = 'None';
        let maxCount = 0;
        
        if (stats.country_breakdown && Object.keys(stats.country_breakdown).length > 0) {
            for (const [country, count] of Object.entries(stats.country_breakdown)) {
                if (count > maxCount) {
                    maxCount = count;
                    topCountryName = country;
                }
            }
            
            if (topCountry) {
                topCountry.textContent = `${topCountryName} (${maxCount})`;
            }
            
            // Update country breakdown list
            if (countryList) {
                let html = '';
                const sortedCountries = Object.entries(stats.country_breakdown)
                    .sort(([,a], [,b]) => b - a) // Sort by count descending
                    .slice(0, 10); // Show top 10
                
                sortedCountries.forEach(([country, count]) => {
                    const percentage = ((count / (stats.with_geolocation + stats.without_geolocation)) * 100).toFixed(1);
                    html += `
                        <div class="country-item">
                            <span class="country-name">${escapeHtml(country)}</span>
                            <span class="country-count">${count} players (${percentage}%)</span>
                        </div>
                    `;
                });
                
                countryList.innerHTML = html || '<p class="empty-state">No country data available</p>';
            }
        } else {
            if (topCountry) topCountry.textContent = 'None';
            if (countryList) countryList.innerHTML = '<p class="empty-state">No country data available</p>';
        }
    },

    async clearGeoCache() {
        if (!confirm('Are you sure you want to clear the geolocation cache? This will cause IP addresses to be re-looked up on next player update.')) {
            return;
        }
        
        try {
            const data = await apiCall('/geolocation/clear_cache', { method: 'POST' });
            
            if (data.success) {
                showToast('Geolocation cache cleared successfully', 'success');
                this.refreshGeoStats();
            } else {
                showToast(data.message || 'Failed to clear geolocation cache', 'error');
            }
        } catch (error) {
            console.error('Error clearing geolocation cache:', error);
            showToast('Error clearing geolocation cache: ' + error, 'error');
        }
    },

    async forceUpdateGeolocations() {
        if (!confirm('Are you sure you want to force update all player geolocations? This will make many API calls and may take several minutes. Use sparingly to respect API limits.')) {
            return;
        }
        
        const button = event.target;
        const originalText = button.textContent;
        button.disabled = true;
        button.textContent = '🔄 Updating...';
        
        try {
            showToast('Starting geolocation update... This may take several minutes.', 'info');
            
            const data = await apiCall('/geolocation/force_update', { method: 'POST' });
            
            if (data.success) {
                showToast(`Geolocation update completed: ${data.updated_count} players updated`, 'success');
                this.refreshGeoStats();
                
                // Also refresh player data if we're on the players tab
                if (window.PlayersManager) {
                    window.PlayersManager.loadPlayersFromDatabase();
                }
            } else {
                showToast(data.message || 'Failed to update geolocations', 'error');
            }
        } catch (error) {
            console.error('Error updating geolocations:', error);
            showToast('Error updating geolocations: ' + error, 'error');
        } finally {
            button.disabled = false;
            button.textContent = originalText;
        }
    }
};

// Global functions for HTML onclick handlers
function refreshLogStats() {
    window.LogsManager.refreshLogStats();
}

function loadLogSettings() {
    window.LogsManager.loadLogSettings();
}

function saveLogSettings() {
    window.LogsManager.saveLogSettings();
}

function loadRecentLogs() {
    window.LogsManager.loadRecentLogs();
}

function cleanupOldLogs() {
    window.LogsManager.cleanupOldLogs();
}

function clearAllLogs() {
    window.LogsManager.clearAllLogs();
}

function downloadCurrentLog() {
    window.LogsManager.downloadCurrentLog();
}

// Geolocation management functions
function refreshGeoStats() {
    window.LogsManager.refreshGeoStats();
}

function clearGeoCache() {
    window.LogsManager.clearGeoCache();
}

function forceUpdateGeolocations() {
    window.LogsManager.forceUpdateGeolocations();
}
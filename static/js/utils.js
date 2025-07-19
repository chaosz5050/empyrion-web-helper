// FILE LOCATION: /static/js/utils.js
/**
 * Utility functions for Empyrion Web Helper
 * Copyright (c) 2025 Chaosz Software
 */

// Toast notification system
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => toast.classList.add('show'), 100);
    
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => {
            if (document.body.contains(toast)) {
                document.body.removeChild(toast);
            }
        }, 300);
    }, 3000);
}

// Loading indicator control
function showLoading(show) {
    const loadingIndicator = document.getElementById('loadingIndicator');
    if (loadingIndicator) {
        if (show) {
            loadingIndicator.classList.add('show');
        } else {
            loadingIndicator.classList.remove('show');
        }
    }
}

// HTML escaping for security
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Tab navigation system
function showTab(tabName) {
    // Hide all panels
    const panels = ['playersPanel', 'entitiesPanel', 'messagingPanel', 'logsPanel', 'settingsPanel'];
    panels.forEach(panelId => {
        const panel = document.getElementById(panelId);
        if (panel) {
            panel.style.display = 'none';
        }
    });
    
    // Show selected panel
    const selectedPanel = document.getElementById(tabName + 'Panel');
    if (selectedPanel) {
        selectedPanel.style.display = 'block';
    }
    
    // Update tab buttons
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('active');
    });
    
    const activeBtn = document.querySelector(`[onclick="showTab('${tabName}')"]`);
    if (activeBtn) {
        activeBtn.classList.add('active');
    }
    
    // Special initialization for different tabs
    if (tabName === 'messaging') {
        if (window.MessagingManager) {
            window.MessagingManager.loadMessageHistory();
        }
    } else if (tabName === 'logs') {
        if (window.LogsManager) {
            window.LogsManager.refreshLogStats();
            window.LogsManager.loadLogSettings();
            window.LogsManager.loadRecentLogs();
        }
    } else if (tabName === 'entities') {
        // Just enable the refresh button if connected
        if (window.EntitiesManager && isConnected) {
            window.EntitiesManager.enableEntitiesFeatures(true);
        }
    } else if (tabName === 'settings') {
        // Initialize settings manager if it exists
        if (window.SettingsManager && typeof window.SettingsManager.loadCurrentSettings === 'function') {
            window.SettingsManager.loadCurrentSettings();
        } else if (window.SettingsManager && typeof window.SettingsManager.loadAllSettings === 'function') {
            window.SettingsManager.loadAllSettings();
        }
    }
}

// Format timestamps for display
function formatTimestamp(timestamp) {
    try {
        const date = new Date(timestamp);
        return date.toLocaleString();
    } catch (e) {
        return timestamp;
    }
}

// Format "last seen" relative time
function formatLastSeen(lastSeenStr, status) {
    if (status === 'Online') {
        return 'Currently Online';
    }
    
    if (!lastSeenStr) {
        return '';
    }
    
    try {
        const lastSeen = new Date(lastSeenStr);
        const now = new Date();
        const diffMs = now - lastSeen;
        const diffMins = Math.floor(diffMs / (1000 * 60));
        
        if (diffMins < 1) {
            return 'Just now';
        }
        
        const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
        const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
        
        if (diffMins < 60) {
            return `${diffMins} min${diffMins !== 1 ? 's' : ''} ago`;
        } else if (diffHours < 24) {
            return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
        } else if (diffDays < 7) {
            return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;
        } else {
            return lastSeen.toLocaleDateString();
        }
    } catch (e) {
        return '';
    }
}

// Debug logging with timestamp
function debugLog(message, data = null) {
    const timestamp = new Date().toISOString();
    if (data) {
        console.log(`[${timestamp}] ${message}:`, data);
    } else {
        console.log(`[${timestamp}] ${message}`);
    }
}

// API helper functions
async function apiCall(url, options = {}) {
    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        const data = await response.json();
        return data;
    } catch (error) {
        console.error(`API call failed to ${url}:`, error);
        throw error;
    }
}

// Export for ES6 modules compatibility
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        showToast,
        showLoading,
        escapeHtml,
        showTab,
        formatTimestamp,
        formatLastSeen,
        debugLog,
        apiCall
    };
}
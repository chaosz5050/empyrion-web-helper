// FILE LOCATION: /static/js/connection.js
/**
 * Connection management for Empyrion Web Helper v0.4.1
 * Frontend is now a pure database viewer - background service handles all server communication
 * Copyright (c) 2025 Chaosz Software
 */

// Connection state (for UI display only)
let isConnected = false;
let serviceRunning = false;
let socket = null;

// Connection Manager
window.ConnectionManager = {
    init() {
        // Initialize Socket.IO connection
        socket = io();
        this.setupSocketHandlers();
        
        // Initial status check (less frequent)
        this.checkServiceStatus();
        
        // Start slow status monitoring (every 30 seconds)
        this.startSlowStatusMonitoring();
        
        // Start lazy data refresh (every 60 seconds)
        this.startLazyDataRefresh();
        
        debugLog('Frontend initialized - database-only mode');
    },

    setupSocketHandlers() {
        socket.on('connect', () => {
            debugLog('WebSocket connected');
        });

        socket.on('disconnect', () => {
            debugLog('WebSocket disconnected');
        });

        socket.on('connection_status', (data) => {
            this.updateConnectionStatus(data.connected);
        });

        socket.on('message_history_update', (data) => {
            if (data.history && window.MessagingManager) {
                window.MessagingManager.messageHistoryData = data.history;
                window.MessagingManager.updateMessageHistoryTable();
                debugLog('Received message history update via WebSocket');
            }
        });
    },

    async checkServiceStatus() {
        try {
            const data = await apiCall('/status');
            
            if (data.success) {
                serviceRunning = data.service_running;
                isConnected = data.connected;
                
                this.updateServiceStatus({ service_running: serviceRunning });
                this.updateConnectionStatus(isConnected);
            }
        } catch (error) {
            debugLog('Error checking service status:', error);
            // Don't spam on errors
            serviceRunning = false;
            isConnected = false;
            this.updateServiceStatus({ service_running: false });
            this.updateConnectionStatus(false);
        }
    },

    async startService() {
        showLoading(true);
        const startBtn = document.getElementById('startServiceBtn');
        
        if (startBtn) startBtn.disabled = true;
        
        try {
            const data = await apiCall('/service/start', { method: 'POST' });
            
            if (data.success) {
                showToast(data.message, 'success');
                serviceRunning = true;
                this.updateServiceStatus({ service_running: true });
                
                // Check status again in a few seconds
                setTimeout(() => this.checkServiceStatus(), 3000);
            } else {
                showToast(data.message, 'error');
            }
        } catch (error) {
            showToast('Failed to start service: ' + error, 'error');
        } finally {
            showLoading(false);
            if (startBtn) startBtn.disabled = false;
        }
    },

    async stopService() {
        const stopBtn = document.getElementById('stopServiceBtn');
        
        if (stopBtn) stopBtn.disabled = true;
        
        try {
            const data = await apiCall('/service/stop', { method: 'POST' });
            
            if (data.success) {
                showToast(data.message, 'info');
                serviceRunning = false;
                isConnected = false;
                
                this.updateServiceStatus({ service_running: false });
                this.updateConnectionStatus(false);
            } else {
                showToast(data.message, 'error');
            }
        } catch (error) {
            showToast('Failed to stop service: ' + error, 'error');
        } finally {
            if (stopBtn) stopBtn.disabled = false;
        }
    },

    updateServiceStatus(status) {
        const startBtn = document.getElementById('startServiceBtn');
        const stopBtn = document.getElementById('stopServiceBtn');
        const serviceStatusText = document.getElementById('serviceStatusText');
        
        if (status.service_running) {
            if (startBtn) startBtn.style.display = 'none';
            if (stopBtn) stopBtn.style.display = 'inline-block';
            if (serviceStatusText) {
                serviceStatusText.textContent = 'Running';
                serviceStatusText.style.color = 'var(--accent-green)';
            }
        } else {
            if (startBtn) startBtn.style.display = 'inline-block';
            if (stopBtn) stopBtn.style.display = 'none';
            if (serviceStatusText) {
                serviceStatusText.textContent = 'Stopped';
                serviceStatusText.style.color = 'var(--accent-red)';
            }
        }
    },

    updateConnectionStatus(connected) {
        isConnected = connected;
        
        // DO NOT update DOM here - let header.html be the single source of truth
        // This prevents race conditions between multiple status updaters
        debugLog(`Connection status updated: ${connected ? 'Connected' : 'Disconnected'}`);
        
        // Only update the refresh button state
        const refreshDataBtn = document.getElementById('refreshDataBtn');
        
        if (refreshDataBtn && serviceRunning) {
            // Enable/disable refresh button based on connection status
            refreshDataBtn.disabled = !connected;
        }
    },

    startSlowStatusMonitoring() {
        // Check status every 30 seconds (much less frequent)
        this.statusInterval = setInterval(() => {
            this.checkServiceStatus();
        }, 30000); // 30 seconds
        
        debugLog('Started slow status monitoring (30s intervals)');
    },

    stopStatusMonitoring() {
        if (this.statusInterval) {
            clearInterval(this.statusInterval);
            this.statusInterval = null;
        }
        
        this.stopLazyDataRefresh();
        
        debugLog('Stopped status monitoring');
    },

    startLazyDataRefresh() {
        // Load initial data from database immediately
        if (window.PlayersManager) {
            window.PlayersManager.loadPlayersFromDatabase();
        }
        
        // Set up lazy refresh - only every 60 seconds
        this.refreshInterval = setInterval(() => {
            // Always refresh from database, regardless of connection status
            if (window.PlayersManager) {
                window.PlayersManager.loadPlayersFromDatabase();
            }
        }, 60000); // 60 seconds - very lazy
        
        debugLog('Started lazy data refresh (60s intervals, database only)');
    },

    stopLazyDataRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
            debugLog('Stopped lazy data refresh');
        }
    },

    refreshAllData() {
        // Manual refresh - always from database
        if (window.PlayersManager) {
            window.PlayersManager.loadPlayersFromDatabase();
        }
        
        if (window.EntitiesManager) {
            window.EntitiesManager.loadEntitiesFromDatabase();
        }
        
        showToast('Data refreshed from database', 'info');
    },

    requestMessageHistoryUpdate() {
        if (socket) {
            socket.emit('request_message_history');
        }
    }
};

// Global functions for HTML onclick handlers
function startService() {
    window.ConnectionManager.startService();
}

function stopService() {
    window.ConnectionManager.stopService();
}

function refreshAllData() {
    window.ConnectionManager.refreshAllData();
}

// Legacy functions for backward compatibility - now just database operations
function toggleConnection() {
    if (serviceRunning) {
        stopService();
    } else {
        startService();
    }
}

function refreshPlayers() {
    if (window.PlayersManager) {
        window.PlayersManager.loadPlayersFromDatabase();
    }
}
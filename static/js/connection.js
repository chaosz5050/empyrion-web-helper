// FILE LOCATION: /static/js/connection.js
/**
 * Connection management for Empyrion Web Helper v0.4.1
 * Updated for background service architecture
 * Copyright (c) 2025 Chaosz Software
 */

// Connection state
let isConnected = false;
let serviceRunning = false;
let socket = null;

// Connection Manager
window.ConnectionManager = {
    init() {
        // Initialize Socket.IO connection
        socket = io();
        this.setupSocketHandlers();
        
        // Initial status check
        this.checkServiceStatus();
        
        debugLog('Connection manager initialized for background service architecture');
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
                
                if (serviceRunning) {
                    this.startStatusMonitoring();
                }
            }
        } catch (error) {
            debugLog('Error checking service status:', error);
        }
    },

    async startService() {
        showLoading(true);
        const startBtn = document.getElementById('startServiceBtn');
        const stopBtn = document.getElementById('stopServiceBtn');
        
        if (startBtn) startBtn.disabled = true;
        
        try {
            const data = await apiCall('/service/start', { method: 'POST' });
            
            if (data.success) {
                showToast(data.message, 'success');
                serviceRunning = true;
                this.updateServiceStatus({ service_running: true });
                this.startStatusMonitoring();
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
        const startBtn = document.getElementById('startServiceBtn');
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
                this.stopStatusMonitoring();
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
        
        const connectionStatus = document.getElementById('connectionStatus');
        const refreshDataBtn = document.getElementById('refreshDataBtn');
        
        if (connected) {
            if (connectionStatus) {
                connectionStatus.textContent = 'Connected';
                connectionStatus.style.color = 'var(--accent-green)';
            }
            if (refreshDataBtn) refreshDataBtn.disabled = false;
            
            // Enable features
            this.enableFeatures(true);
            
        } else {
            if (connectionStatus) {
                connectionStatus.textContent = serviceRunning ? 'Connecting...' : 'Disconnected';
                connectionStatus.style.color = serviceRunning ? 'var(--accent-orange)' : 'var(--accent-red)';
            }
            if (refreshDataBtn) refreshDataBtn.disabled = true;
            
            // Disable features
            this.enableFeatures(false);
        }
    },

    enableFeatures(enabled) {
        // Enable messaging features
        const messagingInputs = document.querySelectorAll('#globalMessageInput, .scheduled-message-text');
        const messagingButtons = document.querySelectorAll('#sendGlobalBtn, .btn-test');
        
        messagingInputs.forEach(input => {
            input.disabled = !enabled;
        });
        
        messagingButtons.forEach(button => {
            button.disabled = !enabled;
        });
        
        // Enable entities features
        if (window.EntitiesManager) {
            window.EntitiesManager.enableEntitiesFeatures(enabled);
        }
        
        // Enable player features
        if (window.PlayersManager) {
            window.PlayersManager.enablePlayerFeatures(enabled);
        }
    },

    startStatusMonitoring() {
        // Check status every 10 seconds while service is running
        this.statusInterval = setInterval(() => {
            this.checkServiceStatus();
        }, 10000);
        
        // Start auto-refresh for player data
        this.startAutoRefresh();
        
        debugLog('Started status monitoring');
    },

    stopStatusMonitoring() {
        if (this.statusInterval) {
            clearInterval(this.statusInterval);
            this.statusInterval = null;
        }
        
        this.stopAutoRefresh();
        
        debugLog('Stopped status monitoring');
    },

    startAutoRefresh() {
        // Load initial data from database
        if (window.PlayersManager) {
            window.PlayersManager.loadPlayersFromDatabase();
            
            // Set up interval for UI updates (background service handles server polling)
            this.refreshInterval = setInterval(() => {
                window.PlayersManager.loadPlayersFromDatabase();
            }, 30000); // Every 30 seconds - just UI refresh
            
            debugLog('Auto-refresh started (UI updates every 30s)');
        }
    },

    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
            debugLog('Auto-refresh stopped');
        }
    },

    refreshAllData() {
        // Refresh all data from database
        if (window.PlayersManager) {
            window.PlayersManager.loadPlayersFromDatabase();
        }
        
        if (window.EntitiesManager) {
            window.EntitiesManager.loadEntitiesFromDatabase();
        }
        
        showToast('Data refreshed from database', 'info');
    },

    requestMessageHistoryUpdate() {
        if (socket && isConnected) {
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

// Legacy functions for backward compatibility
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
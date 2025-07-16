// FILE LOCATION: /static/js/connection.js
/**
 * Connection management for Empyrion Web Helper
 * Copyright (c) 2025 Chaosz Software
 */

// Connection state
let isConnected = false;
let socket = null;

// Connection Manager
window.ConnectionManager = {
    init() {
        // Initialize Socket.IO connection
        socket = io();
        this.setupSocketHandlers();
        
        debugLog('Connection manager initialized');
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

    async connect() {
        showLoading(true);
        const connectBtn = document.getElementById('connectBtn');
        connectBtn.disabled = true;
        
        try {
            const data = await apiCall('/connect', { method: 'POST' });
            
            if (data.success) {
                showToast(data.message, 'success');
                this.startAutoRefresh();
            } else {
                showToast(data.message, 'error');
            }
        } catch (error) {
            showToast('Connection failed: ' + error, 'error');
        } finally {
            showLoading(false);
            connectBtn.disabled = false;
        }
    },

    async disconnect() {
        const connectBtn = document.getElementById('connectBtn');
        connectBtn.disabled = true;
        
        try {
            const data = await apiCall('/disconnect', { method: 'POST' });
            
            if (data.success) {
                showToast(data.message, 'info');
                this.stopAutoRefresh();
            } else {
                showToast(data.message, 'error');
            }
        } catch (error) {
            showToast('Disconnect failed: ' + error, 'error');
        } finally {
            connectBtn.disabled = false;
        }
    },

    toggleConnection() {
        if (isConnected) {
            this.disconnect();
        } else {
            this.connect();
        }
    },

    updateConnectionStatus(connected) {
        isConnected = connected;
        
        const statusIndicator = document.getElementById('statusIndicator');
        const statusText = document.getElementById('statusText');
        const connectBtn = document.getElementById('connectBtn');
        const refreshBtn = document.getElementById('refreshBtn');
        
        if (connected) {
            statusIndicator.classList.add('connected');
            statusText.classList.add('connected');
            statusText.textContent = 'Connected';
            connectBtn.textContent = 'Disconnect';
            connectBtn.className = 'btn-danger';
            refreshBtn.disabled = false;
            
            // Enable messaging features
            this.enableMessagingFeatures(true);
            
            // Enable entities features
            if (window.EntitiesManager) {
                window.EntitiesManager.enableEntitiesFeatures(true);
            }
            
            if (window.MessagingManager) {
                window.MessagingManager.loadMessageHistory();
            }
        } else {
            statusIndicator.classList.remove('connected');
            statusText.classList.remove('connected');
            statusText.textContent = 'Disconnected';
            connectBtn.textContent = 'Connect';
            connectBtn.className = '';
            refreshBtn.disabled = true;
            
            // Clear player data
            if (window.PlayersManager) {
                window.PlayersManager.allPlayers = [];
                window.PlayersManager.updatePlayersTable();
            }
            
            // Disable messaging features
            this.enableMessagingFeatures(false);
            
            // Disable entities features
            if (window.EntitiesManager) {
                window.EntitiesManager.enableEntitiesFeatures(false);
            }
        }
    },

    enableMessagingFeatures(enabled) {
        const messagingInputs = document.querySelectorAll('#globalMessageInput, .scheduled-message-text');
        const messagingButtons = document.querySelectorAll('#sendGlobalBtn, .btn-test');
        
        messagingInputs.forEach(input => {
            input.disabled = !enabled;
        });
        
        messagingButtons.forEach(button => {
            button.disabled = !enabled;
        });
    },

    startAutoRefresh() {
        // Initial load from database
        if (window.PlayersManager) {
            window.PlayersManager.loadPlayersFromDatabase();
            
            // If connected, also refresh from server
            if (isConnected) {
                window.PlayersManager.refreshPlayers();
            }
            
            // Set up interval for ongoing refreshes
            this.refreshInterval = setInterval(() => {
                window.PlayersManager.refreshPlayers();
            }, window.CONFIG.update_interval * 1000);
            
            debugLog(`Auto-refresh started (${window.CONFIG.update_interval}s intervals)`);
        }
    },

    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
            debugLog('Auto-refresh stopped');
        }
    },

    requestMessageHistoryUpdate() {
        if (socket && isConnected) {
            socket.emit('request_message_history');
        }
    }
};

// Global functions for HTML onclick handlers
function toggleConnection() {
    window.ConnectionManager.toggleConnection();
}
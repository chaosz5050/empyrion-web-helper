// FILE LOCATION: /static/js/messaging.js
/**
 * Messaging system functionality for Empyrion Web Helper
 * Copyright (c) 2025 Chaosz Software
 */

// Messaging Manager
window.MessagingManager = {
    scheduledMessagesData: [],
    messageHistoryData: [],

    init() {
        debugLog('Initializing messaging system...');
        
        // Load custom messages on page load
        this.loadCustomMessages();
        
        // Load scheduled messages on page load
        this.loadScheduledMessages();
        
        // Load message history
        this.loadMessageHistory();
        
        // Set up Enter key for global message input
        const globalInput = document.getElementById('globalMessageInput');
        if (globalInput) {
            globalInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.sendGlobalMessage();
                }
            });
        }
        
        debugLog('Messaging system initialized');
    },

    // Global Messages
    async sendGlobalMessage() {
        const messageInput = document.getElementById('globalMessageInput');
        const message = messageInput.value.trim();
        
        if (!message) {
            showToast('Please enter a message', 'error');
            return;
        }
        
        if (!isConnected) {
            showToast('Not connected to server', 'error');
            return;
        }
        
        // Disable button to prevent spam
        const sendBtn = document.getElementById('sendGlobalBtn');
        const originalText = sendBtn.textContent;
        sendBtn.disabled = true;
        sendBtn.textContent = 'Sending...';
        
        try {
            const data = await apiCall('/messaging/send', {
                method: 'POST',
                body: JSON.stringify({ message: message })
            });
            
            if (data.success) {
                showToast('Global message sent successfully', 'success');
                messageInput.value = '';
                this.loadMessageHistory(); // Refresh history
            } else {
                showToast(data.message || 'Failed to send message', 'error');
            }
        } catch (error) {
            console.error('Error sending global message:', error);
            showToast('Error sending message: ' + error, 'error');
        } finally {
            sendBtn.disabled = false;
            sendBtn.textContent = originalText;
        }
    },

    // Custom Player Status Messages
    async loadCustomMessages() {
        const loadButton = document.querySelector('button[onclick="loadCustomMessages()"]');
        const originalText = loadButton ? loadButton.textContent : 'Load Saved Messages';
        
        // Update button state to show loading
        if (loadButton) {
            loadButton.textContent = 'Loading...';
            loadButton.disabled = true;
        }

        try {
            // First try to download from server to get latest config
            try {
                const downloadResult = await apiCall('/messaging/download-from-server', { method: 'POST' });
                if (downloadResult.success) {
                    showToast('Downloaded latest configuration from server', 'success');
                } else {
                    console.warn('Could not download from server, using local config:', downloadResult.message);
                }
            } catch (downloadError) {
                console.warn('Could not download from server, using local config:', downloadError);
            }
            
            // Load the configuration (now updated from server if successful)
            const data = await apiCall('/messaging/custom');
            
            if (data.success && data.messages) {
                const welcomeInput = document.getElementById('welcomeMessageInput');
                const goodbyeInput = document.getElementById('goodbyeMessageInput');
                const welcomeEnabled = document.getElementById('welcomeMessageEnabled');
                const goodbyeEnabled = document.getElementById('goodbyeMessageEnabled');
                
                if (welcomeInput) {
                    welcomeInput.value = data.messages.welcome_message || 'Welcome to Space Cowboys, <playername>!';
                }
                if (goodbyeInput) {
                    goodbyeInput.value = data.messages.goodbye_message || 'Player <playername> has left our galaxy';
                }
                if (welcomeEnabled) {
                    welcomeEnabled.checked = data.messages.welcome_enabled !== false; // Default to true
                }
                if (goodbyeEnabled) {
                    goodbyeEnabled.checked = data.messages.goodbye_enabled !== false; // Default to true
                }
                
                debugLog('Custom messages loaded');
                showToast('Custom messages loaded successfully', 'success');
            }
        } catch (error) {
            console.error('Error loading custom messages:', error);
            showToast('Error loading custom messages: ' + error, 'error');
        } finally {
            // Restore button state
            if (loadButton) {
                loadButton.textContent = originalText;
                loadButton.disabled = false;
            }
        }
    },

    async saveCustomMessages() {
        const welcomeInput = document.getElementById('welcomeMessageInput');
        const goodbyeInput = document.getElementById('goodbyeMessageInput');
        const welcomeEnabled = document.getElementById('welcomeMessageEnabled');
        const goodbyeEnabled = document.getElementById('goodbyeMessageEnabled');
        
        const welcomeMessage = welcomeInput ? welcomeInput.value.trim() : '';
        const goodbyeMessage = goodbyeInput ? goodbyeInput.value.trim() : '';
        const welcomeIsEnabled = welcomeEnabled ? welcomeEnabled.checked : true;
        const goodbyeIsEnabled = goodbyeEnabled ? goodbyeEnabled.checked : true;
        
        // Only require messages if they're enabled
        if (welcomeIsEnabled && !welcomeMessage) {
            showToast('Welcome message is required when enabled', 'error');
            return;
        }
        if (goodbyeIsEnabled && !goodbyeMessage) {
            showToast('Goodbye message is required when enabled', 'error');
            return;
        }
        
        // Update button state to show uploading
        const saveButton = document.querySelector('button[onclick="saveCustomMessages()"]');
        const originalText = saveButton ? saveButton.textContent : 'Save Custom Messages';
        if (saveButton) {
            saveButton.textContent = 'Uploading...';
            saveButton.disabled = true;
        }

        try {
            const data = await apiCall('/messaging/custom', {
                method: 'POST',
                body: JSON.stringify({
                    welcome_message: welcomeMessage,
                    goodbye_message: goodbyeMessage,
                    welcome_enabled: welcomeIsEnabled,
                    goodbye_enabled: goodbyeIsEnabled
                })
            });
            
            if (data.success) {
                showToast('Custom messages saved and uploaded successfully', 'success');
            } else {
                showToast(data.message || 'Failed to save custom messages', 'error');
            }
        } catch (error) {
            console.error('Error saving custom messages:', error);
            showToast('Error saving custom messages: ' + error, 'error');
        } finally {
            // Restore button state
            if (saveButton) {
                saveButton.textContent = originalText;
                saveButton.disabled = false;
            }
        }
    },

    async testMessage(type) {
        if (!isConnected) {
            showToast('Not connected to server', 'error');
            return;
        }
        
        const testPlayerName = 'TestPlayer';
        
        try {
            const data = await apiCall('/messaging/test', {
                method: 'POST',
                body: JSON.stringify({
                    type: type,
                    player_name: testPlayerName
                })
            });
            
            if (data.success) {
                showToast(`Test ${type} message sent`, 'success');
                this.loadMessageHistory(); // Refresh history
            } else {
                showToast(data.message || `Failed to send test ${type} message`, 'error');
            }
        } catch (error) {
            console.error(`Error sending test ${type} message:`, error);
            showToast(`Error sending test ${type} message: ` + error, 'error');
        }
    },

    // Scheduled Messages
    async loadScheduledMessages() {
        const loadButton = document.querySelector('button[onclick="loadScheduledMessages()"]');
        const originalText = loadButton ? loadButton.textContent : 'Load Schedule';
        
        // Update button state to show loading  
        if (loadButton) {
            loadButton.textContent = 'Loading...';
            loadButton.disabled = true;
        }

        try {
            // First try to download from server to get latest config
            try {
                const downloadResult = await apiCall('/messaging/download-from-server', { method: 'POST' });
                if (downloadResult.success) {
                    showToast('Downloaded latest configuration from server', 'success');
                } else {
                    console.warn('Could not download from server, using local config:', downloadResult.message);
                }
            } catch (downloadError) {
                console.warn('Could not download from server, using local config:', downloadError);
            }
            
            // Load the configuration (now updated from server if successful)
            const data = await apiCall('/messaging/scheduled');
            
            if (data.success && data.messages) {
                // Filter out empty/disabled messages that have no text
                this.scheduledMessagesData = data.messages.filter(msg => 
                    msg.enabled || (msg.text && msg.text.trim() !== '')
                );
                this.renderScheduledMessages();
                debugLog('Scheduled messages loaded:', this.scheduledMessagesData.length);
                showToast('Scheduled messages loaded successfully', 'success');
            }
        } catch (error) {
            console.error('Error loading scheduled messages:', error);
            showToast('Error loading scheduled messages: ' + error, 'error');
            // Initialize with empty data - just one empty message
            this.scheduledMessagesData = [];
            this.renderScheduledMessages();
        } finally {
            // Restore button state
            if (loadButton) {
                loadButton.textContent = originalText;
                loadButton.disabled = false;
            }
        }
    },

    async saveScheduledMessages() {
        // Collect data from UI
        const messages = [];
        const messageItems = document.querySelectorAll('.scheduled-message-item');
        
        messageItems.forEach((item, index) => {
            const checkbox = item.querySelector('input[type="checkbox"]');
            const textInput = item.querySelector('.scheduled-message-text');
            const scheduleSelect = item.querySelector('.schedule-select');
            
            messages.push({
                id: index + 1,
                enabled: checkbox ? checkbox.checked : false,
                text: textInput ? textInput.value.trim() : '',
                schedule: scheduleSelect ? scheduleSelect.value : 'Every 10 minutes'
            });
        });
        
        // Update button state to show uploading
        const saveButton = document.querySelector('button[onclick="saveScheduledMessages()"]');
        const originalText = saveButton ? saveButton.textContent : 'Save Scheduled Messages';
        if (saveButton) {
            saveButton.textContent = 'Uploading...';
            saveButton.disabled = true;
        }

        try {
            const data = await apiCall('/messaging/scheduled', {
                method: 'POST',
                body: JSON.stringify({ messages: messages })
            });
            
            if (data.success) {
                showToast('Scheduled messages saved and uploaded successfully', 'success');
                this.scheduledMessagesData = messages;
            } else {
                showToast(data.message || 'Failed to save scheduled messages', 'error');
            }
        } catch (error) {
            console.error('Error saving scheduled messages:', error);
            showToast('Error saving scheduled messages: ' + error, 'error');
        } finally {
            // Restore button state
            if (saveButton) {
                saveButton.textContent = originalText;
                saveButton.disabled = false;
            }
        }
    },

    renderScheduledMessages() {
        const container = document.getElementById('scheduledMessagesList');
        if (!container) return;
        
        // Create display array: use configured messages as-is
        const displayMessages = [...this.scheduledMessagesData];
        
        // Only add 1 empty message if there are NO configured messages at all
        if (displayMessages.length === 0) {
            displayMessages.push({
                id: 1,
                enabled: false,
                text: '',
                schedule: 'Every 10 minutes'
            });
        }
        
        container.innerHTML = '';
        
        displayMessages.forEach((message, index) => {
            const messageDiv = document.createElement('div');
            messageDiv.className = 'scheduled-message-item';
            
            messageDiv.innerHTML = `
                <div class="scheduled-message-header">
                    <input type="checkbox" id="scheduleEnabled${index}" ${message.enabled ? 'checked' : ''}>
                    <label for="scheduleEnabled${index}">Message ${index + 1}</label>
                    <button onclick="MessagingManager.removeScheduledMessage(${index})" class="btn-danger" style="padding: 4px 8px; font-size: 12px;">Remove</button>
                </div>
                <div class="scheduled-message-body">
                    <div class="message-input-container">
                        <input type="text" class="scheduled-message-text message-input" 
                               value="${escapeHtml(message.text)}" 
                               placeholder="Enter scheduled message..." maxlength="200">
                    </div>
                    <div class="schedule-input-row">
                        <label>Send:</label>
                        <select class="schedule-select">
                            <option value="Every 10 minutes" ${message.schedule === 'Every 10 minutes' ? 'selected' : ''}>Every 10 minutes</option>
                            <option value="Every 20 minutes" ${message.schedule === 'Every 20 minutes' ? 'selected' : ''}>Every 20 minutes</option>
                            <option value="Every 30 minutes" ${message.schedule === 'Every 30 minutes' ? 'selected' : ''}>Every 30 minutes</option>
                            <option value="Every 40 minutes" ${message.schedule === 'Every 40 minutes' ? 'selected' : ''}>Every 40 minutes</option>
                            <option value="Every 50 minutes" ${message.schedule === 'Every 50 minutes' ? 'selected' : ''}>Every 50 minutes</option>
                            <option value="Every 1 hour" ${message.schedule === 'Every 1 hour' ? 'selected' : ''}>Every 1 hour</option>
                            <option value="Every 2 hours" ${message.schedule === 'Every 2 hours' ? 'selected' : ''}>Every 2 hours</option>
                            <option value="Every 3 hours" ${message.schedule === 'Every 3 hours' ? 'selected' : ''}>Every 3 hours</option>
                            <option value="Every 6 hours" ${message.schedule === 'Every 6 hours' ? 'selected' : ''}>Every 6 hours</option>
                            <option value="Every 12 hours" ${message.schedule === 'Every 12 hours' ? 'selected' : ''}>Every 12 hours</option>
                            <option value="Every 24 hours" ${message.schedule === 'Every 24 hours' ? 'selected' : ''}>Every 24 hours</option>
                        </select>
                    </div>
                </div>
            `;
            
            container.appendChild(messageDiv);
        });
    },

    addScheduledMessage() {
        if (this.scheduledMessagesData.length >= 10) {
            showToast('Maximum of 10 scheduled messages allowed', 'error');
            return;
        }
        
        this.scheduledMessagesData.push({
            id: this.scheduledMessagesData.length + 1,
            enabled: false,
            text: '',
            schedule: 'Every 5 minutes'
        });
        this.renderScheduledMessages();
    },

    removeScheduledMessage(index) {
        if (index >= 0 && index < this.scheduledMessagesData.length) {
            this.scheduledMessagesData.splice(index, 1);
            // Reassign IDs
            this.scheduledMessagesData.forEach((msg, i) => {
                msg.id = i + 1;
            });
            this.renderScheduledMessages();
        }
    },

    // Message History
    async loadMessageHistory() {
        try {
            const data = await apiCall('/messaging/history?limit=50');
            
            if (data.success) {
                this.messageHistoryData = data.history || [];
                this.updateMessageHistoryTable();
                this.updateMessageStats(data.stats || {});
                debugLog('Message history loaded:', this.messageHistoryData.length, 'messages');
            } else {
                console.error('Failed to load message history:', data.message);
            }
        } catch (error) {
            console.error('Error loading message history:', error);
            this.messageHistoryData = [];
            this.updateMessageHistoryTable();
        }
    },

    updateMessageHistoryTable() {
        const tbody = document.getElementById('messageHistoryBody');
        if (!tbody) return;
        
        if (this.messageHistoryData.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="5" class="empty-state">No message history available</td>
                </tr>
            `;
            return;
        }
        
        tbody.innerHTML = '';
        
        this.messageHistoryData.forEach(message => {
            const row = document.createElement('tr');
            
            // Format timestamp
            const timestamp = formatTimestamp(message.timestamp);
            
            // Format message type with styling
            const typeClass = message.type.toLowerCase();
            const typeDisplay = message.type.charAt(0).toUpperCase() + message.type.slice(1);
            
            // Truncate long messages
            const messageText = message.message.length > 100 
                ? message.message.substring(0, 100) + '...' 
                : message.message;
            
            // Player name or empty
            const playerName = message.player || '';
            
            // Success status
            const statusClass = message.success ? 'success' : 'failed';
            const statusText = message.success ? 'Success' : 'Failed';
            
            row.innerHTML = `
                <td class="message-timestamp">${timestamp}</td>
                <td><span class="message-type ${typeClass}">${typeDisplay}</span></td>
                <td class="message-text">${escapeHtml(messageText)}</td>
                <td>${escapeHtml(playerName)}</td>
                <td class="message-status ${statusClass}">${statusText}</td>
            `;
            
            tbody.appendChild(row);
        });
    },

    updateMessageStats(stats) {
        const totalMessages = document.getElementById('totalMessages');
        const successfulMessages = document.getElementById('successfulMessages');
        const failedMessages = document.getElementById('failedMessages');
        
        if (totalMessages) totalMessages.textContent = stats.total || 0;
        if (successfulMessages) successfulMessages.textContent = stats.successful || 0;
        if (failedMessages) failedMessages.textContent = stats.failed || 0;
    },

    async clearMessageHistory() {
        if (!confirm('Are you sure you want to clear all message history? This action cannot be undone.')) {
            return;
        }
        
        try {
            const data = await apiCall('/messaging/history/clear', { method: 'POST' });
            
            if (data.success) {
                showToast('Message history cleared successfully', 'success');
                this.messageHistoryData = [];
                this.updateMessageHistoryTable();
                this.updateMessageStats({ total: 0, successful: 0, failed: 0 });
            } else {
                showToast(data.message || 'Failed to clear message history', 'error');
            }
        } catch (error) {
            console.error('Error clearing message history:', error);
            showToast('Error clearing message history: ' + error, 'error');
        }
    }
};

// Global functions for HTML onclick handlers
function sendGlobalMessage() {
    window.MessagingManager.sendGlobalMessage();
}

function saveCustomMessages() {
    window.MessagingManager.saveCustomMessages();
}

function loadCustomMessages() {
    window.MessagingManager.loadCustomMessages();
}

function testMessage(type) {
    window.MessagingManager.testMessage(type);
}

function saveScheduledMessages() {
    window.MessagingManager.saveScheduledMessages();
}

function loadScheduledMessages() {
    window.MessagingManager.loadScheduledMessages();
}

function addScheduledMessage() {
    window.MessagingManager.addScheduledMessage();
}

function loadMessageHistory() {
    window.MessagingManager.loadMessageHistory();
}

function clearMessageHistory() {
    window.MessagingManager.clearMessageHistory();
}
// FILE LOCATION: /static/js/players.js
/**
 * Player management functionality for Empyrion Web Helper
 * Copyright (c) 2025 Chaosz Software
 */

// Players Manager
window.PlayersManager = {
    allPlayers: [],
    filterElements: {},

    init() {
        // Get filter elements
        this.filterElements = {
            steam_id: document.getElementById('filterSteamId'),
            name: document.getElementById('filterName'),
            status: document.getElementById('filterStatus'),
            faction: document.getElementById('filterFaction'),
            ip_address: document.getElementById('filterIp'),
            playfield: document.getElementById('filterPlayfield'),
            last_seen: document.getElementById('filterLastSeen')
        };

        // Set up filter event listeners
        for (const element of Object.values(this.filterElements)) {
            if (element) {
                element.addEventListener('input', () => this.applyFilters());
            }
        }

        debugLog('Players manager initialized');
    },

    async refreshPlayers() {
        debugLog('refreshPlayers() called, isConnected:', isConnected);
        
        if (isConnected) {
            debugLog('Connected - updating server data then loading from database');
            showLoading(true);
            
            try {
                // First: Update database with fresh server data
                const serverData = await apiCall('/players');
                debugLog('Server update response:', serverData);
                
                if (serverData.success) {
                    // Second: Load from database (which now has the updated data)
                    const dbData = await apiCall('/players/all?' + this.getFilterParams());
                    debugLog('Database response:', dbData);
                    
                    if (dbData.success) {
                        this.allPlayers = dbData.players;
                        this.updatePlayersTable();
                        this.updatePlayerStats(dbData.stats);
                    } else {
                        showToast(dbData.message, 'error');
                    }
                } else {
                    throw new Error(serverData.message);
                }
            } catch (error) {
                console.error('Refresh error:', error);
                showToast('Failed to refresh: ' + error, 'error');
            } finally {
                showLoading(false);
            }
        } else {
            // Not connected - load from database only
            this.loadPlayersFromDatabase();
        }
        
        // Also refresh message history when players are refreshed
        if (document.getElementById('messagingPanel').style.display !== 'none' && window.MessagingManager) {
            window.MessagingManager.loadMessageHistory();
        }
    },

    async loadPlayersFromDatabase() {
        debugLog('loadPlayersFromDatabase() called');
        
        try {
            const data = await apiCall('/players/all?' + this.getFilterParams());
            debugLog('Database load response:', data);
            
            if (data.success) {
                this.allPlayers = data.players;
                this.updatePlayersTable();
                this.updatePlayerStats(data.stats);
            } else {
                debugLog('Database load failed:', data.message);
            }
        } catch (error) {
            debugLog('Database load error:', error);
        }
    },

    getFilterParams() {
        const params = new URLSearchParams();
        for (const [key, element] of Object.entries(this.filterElements)) {
            if (element && element.value.trim()) {
                params.append(key, element.value.trim());
            }
        }
        return params.toString();
    },

    async applyFilters() {
        if (!isConnected) return;
        
        showLoading(true);
        
        try {
            const data = await apiCall('/players/all?' + this.getFilterParams());
            
            if (data.success) {
                this.allPlayers = data.players;
                this.updatePlayersTable();
                this.updatePlayerStats(data.stats);
            } else {
                showToast(data.message, 'error');
            }
        } catch (error) {
            showToast('Failed to apply filters: ' + error, 'error');
        } finally {
            showLoading(false);
        }
    },

    clearFilters() {
        for (const element of Object.values(this.filterElements)) {
            if (element) {
                element.value = '';
            }
        }
        if (isConnected) {
            this.applyFilters();
        }
    },

    updatePlayersTable() {
        const playersTableBody = document.getElementById('playersTableBody');
        if (!playersTableBody) return;

        if (this.allPlayers.length === 0) {
            const message = isConnected ? 'No players found' : 'Connect to server to view players';
            playersTableBody.innerHTML = `
                <tr>
                    <td colspan="8" class="empty-state">${message}</td>
                </tr>
            `;
            return;
        }

        let html = '';
        this.allPlayers.forEach(player => {
            const lastSeen = formatLastSeen(player.last_seen, player.status);
            const ipDisplay = player.ip_address || '';
            const playfieldDisplay = player.playfield || '';
            const factionDisplay = player.faction || '';
            
            // Generate action buttons based on player status
            let actionButtons = '';
            if (player.status === 'Online') {
                // Online players: can kick and ban
                actionButtons = `
                    <button class="action-btn kick" data-tooltip="Kick Player" onclick="PlayersManager.showKickModal('${escapeHtml(player.name)}', '${player.steam_id}')">🦶</button>
                    <button class="action-btn ban" data-tooltip="Ban Player (1 day)" onclick="PlayersManager.banPlayer('${player.steam_id}', '${escapeHtml(player.name)}')">🚫</button>
                `;
            } else {
                // Offline players: can ban and unban
                actionButtons = `
                    <button class="action-btn ban" data-tooltip="Ban Player (1 day)" onclick="PlayersManager.banPlayer('${player.steam_id}', '${escapeHtml(player.name)}')">🚫</button>
                    <button class="action-btn unban" data-tooltip="Unban Player" onclick="PlayersManager.unbanPlayer('${player.steam_id}', '${escapeHtml(player.name)}')">✅</button>
                `;
            }
            
            html += `
                <tr>
                    <td class="player-steam-id">${escapeHtml(player.steam_id)}</td>
                    <td class="player-name">${escapeHtml(player.name)}</td>
                    <td><span class="player-status ${player.status.toLowerCase()}">${player.status}</span></td>
                    <td class="player-faction">${escapeHtml(factionDisplay)}</td>
                    <td class="player-ip">${escapeHtml(ipDisplay)}</td>
                    <td class="player-playfield">${escapeHtml(playfieldDisplay)}</td>
                    <td class="player-last-seen">${lastSeen}</td>
                    <td class="player-actions">${actionButtons}</td>
                </tr>
            `;
        });
        
        playersTableBody.innerHTML = html;
    },

    updatePlayerStats(stats) {
        if (stats) {
            const totalPlayers = document.getElementById('totalPlayers');
            const onlinePlayers = document.getElementById('onlinePlayers');
            const offlinePlayers = document.getElementById('offlinePlayers');
            
            if (totalPlayers) totalPlayers.textContent = stats.total || 0;
            if (onlinePlayers) onlinePlayers.textContent = stats.online || 0;
            if (offlinePlayers) offlinePlayers.textContent = stats.offline || 0;
        }
    },

    // Player action methods
    currentKickData: null,

    showKickModal(playerName, steamId) {
        this.currentKickData = { name: playerName, steamId: steamId };
        document.getElementById('kickPlayerName').value = playerName;
        document.getElementById('kickMessage').value = 'Kicked by Admin';
        document.getElementById('kickModal').classList.add('show');
        
        // Focus on message input and select all text for quick editing
        const messageInput = document.getElementById('kickMessage');
        messageInput.focus();
        messageInput.select();
    },

    cancelKick() {
        document.getElementById('kickModal').classList.remove('show');
        this.currentKickData = null;
    },

    executeKick() {
        if (!this.currentKickData) return;
        
        const message = document.getElementById('kickMessage').value.trim();
        if (!message) {
            showToast('Please enter a kick message', 'error');
            return;
        }
        
        this.kickPlayer(this.currentKickData.name, message);
        this.cancelKick();
    },

    async kickPlayer(playerName, message) {
        if (!isConnected) {
            showToast('Not connected to server', 'error');
            return;
        }
        
        try {
            const data = await apiCall('/player_action', {
                method: 'POST',
                body: JSON.stringify({
                    action: 'kick',
                    player_name: playerName,
                    message: message
                })
            });
            
            if (data.success) {
                showToast(`${playerName} has been kicked`, 'success');
                this.refreshPlayers();
            } else {
                showToast(data.message, 'error');
            }
        } catch (error) {
            showToast('Kick failed: ' + error, 'error');
        }
    },

    async banPlayer(steamId, playerName) {
        if (!isConnected) {
            showToast('Not connected to server', 'error');
            return;
        }
        
        try {
            const data = await apiCall('/player_action', {
                method: 'POST',
                body: JSON.stringify({
                    action: 'ban',
                    steam_id: steamId,
                    duration: '1d'
                })
            });
            
            if (data.success) {
                showToast(`${playerName} has been banned for 1 day`, 'success');
                this.refreshPlayers();
            } else {
                showToast(data.message, 'error');
            }
        } catch (error) {
            showToast('Ban failed: ' + error, 'error');
        }
    },

    async unbanPlayer(steamId, playerName) {
        if (!isConnected) {
            showToast('Not connected to server', 'error');
            return;
        }
        
        try {
            const data = await apiCall('/player_action', {
                method: 'POST',
                body: JSON.stringify({
                    action: 'unban',
                    steam_id: steamId
                })
            });
            
            if (data.success) {
                showToast(`${playerName} has been unbanned`, 'success');
                this.refreshPlayers();
            } else {
                showToast(data.message, 'error');
            }
        } catch (error) {
            showToast('Unban failed: ' + error, 'error');
        }
    }
};

// Global functions for HTML onclick handlers
function refreshPlayers() {
    window.PlayersManager.refreshPlayers();
}

function clearFilters() {
    window.PlayersManager.clearFilters();
}

function showKickModal(playerName, steamId) {
    window.PlayersManager.showKickModal(playerName, steamId);
}

function cancelKick() {
    window.PlayersManager.cancelKick();
}

function executeKick() {
    window.PlayersManager.executeKick();
}
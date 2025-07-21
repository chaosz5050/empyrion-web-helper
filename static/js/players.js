// FILE LOCATION: /static/js/players.js
/**
 * Player management functionality for Empyrion Web Helper
 * Frontend now only reads from database - background service handles server communication
 * Copyright (c) 2025 Chaosz Software
 */

// Players Manager
window.PlayersManager = {
    allPlayers: [],
    filterElements: {},

    init() {
        // Get filter elements - now includes country filter
        this.filterElements = {
            steam_id: document.getElementById('filterSteamId'),
            name: document.getElementById('filterName'),
            status: document.getElementById('filterStatus'),
            faction: document.getElementById('filterFaction'),
            ip_address: document.getElementById('filterIp'),
            country: document.getElementById('filterCountry'),
            playfield: document.getElementById('filterPlayfield'),
            last_seen: document.getElementById('filterLastSeen')
        };

        // Set up filter event listeners
        for (const element of Object.values(this.filterElements)) {
            if (element) {
                element.addEventListener('input', () => this.applyFilters());
            }
        }

        debugLog('Players manager initialized - database-only mode');
    },

    async refreshPlayers() {
        // ALWAYS load from database - background service handles server updates
        debugLog('refreshPlayers() called - loading from database only');
        this.loadPlayersFromDatabase();
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
                showToast('Failed to load player data', 'error');
            }
        } catch (error) {
            debugLog('Database load error:', error);
            showToast('Error loading player data', 'error');
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
        // Filters always work on database data
        showLoading(true);
        
        try {
            const data = await apiCall('/players/all?' + this.getFilterParams());
            
            if (data.success) {
                this.allPlayers = data.players;
                this.updatePlayersTable();
                this.updatePlayerStats(data.stats);
            } else {
                showToast('Failed to apply filters', 'error');
            }
        } catch (error) {
            showToast('Error applying filters: ' + error, 'error');
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
        // Reload all players from database
        this.loadPlayersFromDatabase();
    },

    updatePlayersTable() {
        const playersTableBody = document.getElementById('playersTableBody');
        if (!playersTableBody) return;

        if (this.allPlayers.length === 0) {
            const message = 'No players found in database';
            playersTableBody.innerHTML = `
                <tr>
                    <td colspan="9" class="empty-state">${message}</td>
                </tr>
            `;
            return;
        }

        let html = '';
        this.allPlayers.forEach(player => {
            const lastSeen = formatLastSeen(player.last_seen, player.status);
            const ipDisplay = player.ip_address || '';
            const countryDisplay = this.formatCountry(player.country);
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
                    <td class="player-country">${countryDisplay}</td>
                    <td class="player-playfield">${escapeHtml(playfieldDisplay)}</td>
                    <td class="player-last-seen">${lastSeen}</td>
                    <td class="player-actions">${actionButtons}</td>
                </tr>
            `;
        });
        
        playersTableBody.innerHTML = html;
    },

    formatCountry(country) {
        if (!country || country.trim() === '') {
            return '<span class="country-unknown">Unknown location</span>';
        }
        
        // Different styling for different states
        const countryLower = country.toLowerCase();
        let cssClass = 'country-normal';
        let displayText = escapeHtml(country);
        
        if (countryLower === 'unknown location') {
            cssClass = 'country-unknown';
        } else if (countryLower === 'service down') {
            cssClass = 'country-error';
        } else if (countryLower === 'no internet') {
            cssClass = 'country-error';
        } else if (countryLower === 'local network') {
            cssClass = 'country-local';
        } else {
            cssClass = 'country-normal';
            // Add flag emoji for known countries if desired
            displayText = this.addCountryFlag(country);
        }
        
        return `<span class="${cssClass}">${displayText}</span>`;
    },

    addCountryFlag(country) {
        // Simple country to flag emoji mapping for popular countries
        const countryFlags = {
            'United States': '🇺🇸',
            'Germany': '🇩🇪',
            'Netherlands': '🇳🇱',
            'United Kingdom': '🇬🇧',
            'France': '🇫🇷',
            'Canada': '🇨🇦',
            'Australia': '🇦🇺',
            'Japan': '🇯🇵',
            'Brazil': '🇧🇷',
            'Russia': '🇷🇺',
            'China': '🇨🇳',
            'India': '🇮🇳',
            'South Korea': '🇰🇷',
            'Mexico': '🇲🇽',
            'Italy': '🇮🇹',
            'Spain': '🇪🇸',
            'Sweden': '🇸🇪',
            'Norway': '🇳🇴',
            'Denmark': '🇩🇰',
            'Finland': '🇫🇮',
            'Poland': '🇵🇱',
            'Czech Republic': '🇨🇿',
            'Austria': '🇦🇹',
            'Switzerland': '🇨🇭',
            'Belgium': '🇧🇪',
            'Ireland': '🇮🇪',
            'Portugal': '🇵🇹',
            'Greece': '🇬🇷',
            'Turkey': '🇹🇷',
            'Ukraine': '🇺🇦',
            'Romania': '🇷🇴',
            'Hungary': '🇭🇺',
            'Bulgaria': '🇧🇬',
            'Croatia': '🇭🇷',
            'Slovakia': '🇸🇰',
            'Slovenia': '🇸🇮',
            'Lithuania': '🇱🇹',
            'Latvia': '🇱🇻',
            'Estonia': '🇪🇪'
        };
        
        const flag = countryFlags[country];
        return flag ? `${flag} ${escapeHtml(country)}` : escapeHtml(country);
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

    // Player action methods - these still need server connection for commands
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
            showToast('Background service not connected to server', 'error');
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
                // Refresh from database after action
                setTimeout(() => this.loadPlayersFromDatabase(), 2000);
            } else {
                showToast(data.message, 'error');
            }
        } catch (error) {
            showToast('Kick failed: ' + error, 'error');
        }
    },

    async banPlayer(steamId, playerName) {
        if (!isConnected) {
            showToast('Background service not connected to server', 'error');
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
                // Refresh from database after action
                setTimeout(() => this.loadPlayersFromDatabase(), 2000);
            } else {
                showToast(data.message, 'error');
            }
        } catch (error) {
            showToast('Ban failed: ' + error, 'error');
        }
    },

    async unbanPlayer(steamId, playerName) {
        if (!isConnected) {
            showToast('Background service not connected to server', 'error');
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
                // Refresh from database after action
                setTimeout(() => this.loadPlayersFromDatabase(), 2000);
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

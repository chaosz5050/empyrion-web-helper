// FILE LOCATION: /static/js/entities.js
/**
 * Entity management functionality for Empyrion Web Helper
 * Enhanced with database persistence and last refresh tracking
 * Copyright (c) 2025 Chaosz Software
 */

// Entities Manager
window.EntitiesManager = {
    allEntities: [],
    rawGentsData: '',
    lastRefresh: null,
    filterElements: {},

    init() {
        // Get filter elements
        this.filterElements = {
            entity_id: document.getElementById('filterEntityId'),
            type: document.getElementById('filterEntityType'),
            faction: document.getElementById('filterEntityFaction'),
            name: document.getElementById('filterEntityName'),
            playfield: document.getElementById('filterEntityPlayfield')
        };

        // Set up filter event listeners
        for (const element of Object.values(this.filterElements)) {
            if (element) {
                element.addEventListener('input', () => this.applyFilters());
            }
        }

        debugLog('Entities manager initialized');
        
        // Load entities from database on startup
        this.loadEntitiesFromDatabase();
    },

    async loadEntitiesFromDatabase() {
        debugLog('loadEntitiesFromDatabase() called');
        
        try {
            const data = await apiCall('/entities');
            debugLog('Database load response:', data);
            
            if (data.success) {
                this.allEntities = data.entities || [];
                this.lastRefresh = data.last_refresh;
                this.updateEntitiesTable();
                this.updateEntityStats(data.stats);
                this.updateLastRefreshDisplay();
                
                if (this.allEntities.length > 0) {
                    showToast(`Loaded ${this.allEntities.length} entities from database`, 'info');
                } else {
                    debugLog('No entities in database - user needs to refresh from server');
                }
            } else {
                debugLog('Database load failed:', data.message);
            }
        } catch (error) {
            debugLog('Database load error:', error);
        }
    },

    async refreshEntitiesFromServer() {
        if (!isConnected) {
            showToast('Not connected to server', 'error');
            return;
        }

        debugLog('refreshEntitiesFromServer() called');
        this.showEntitiesLoading(true);
        
        const refreshBtn = document.getElementById('refreshEntitiesBtn');
        const originalText = refreshBtn.textContent;
        refreshBtn.disabled = true;
        refreshBtn.textContent = '🔄 Refreshing from server...';

        try {
            const data = await apiCall('/entities/refresh', { method: 'POST' });
            debugLog('Server refresh response:', data);

            if (data.success) {
                this.rawGentsData = data.raw_data || '';
                this.allEntities = data.entities || [];
                this.lastRefresh = data.last_refresh;
                this.updateEntitiesTable();
                this.updateEntityStats(data.stats);
                this.updateLastRefreshDisplay();
                
                const updatedCount = data.updated_count || this.allEntities.length;
                showToast(`Refreshed ${updatedCount} entities from server`, 'success');
            } else {
                showToast(data.message || 'Failed to refresh entities from server', 'error');
            }
        } catch (error) {
            console.error('Error refreshing entities from server:', error);
            showToast('Error refreshing entities: ' + error, 'error');
        } finally {
            this.showEntitiesLoading(false);
            refreshBtn.disabled = false;
            refreshBtn.textContent = originalText;
        }
    },

    async applyFilters() {
        debugLog('applyFilters() called');
        
        // Build filter parameters
        const params = new URLSearchParams();
        for (const [key, element] of Object.entries(this.filterElements)) {
            if (element && element.value.trim()) {
                params.append(key, element.value.trim());
            }
        }
        
        try {
            const data = await apiCall('/entities?' + params.toString());
            
            if (data.success) {
                this.allEntities = data.entities || [];
                this.updateEntitiesTable();
                this.updateEntityStats(data.stats);
                debugLog(`Applied filters, showing ${this.allEntities.length} entities`);
            } else {
                showToast(data.message || 'Failed to apply filters', 'error');
            }
        } catch (error) {
            console.error('Error applying filters:', error);
            showToast('Error applying filters: ' + error, 'error');
        }
    },

    clearEntityFilters() {
        for (const element of Object.values(this.filterElements)) {
            if (element) {
                element.value = '';
            }
        }
        // Reload all entities from database
        this.loadEntitiesFromDatabase();
    },

    updateEntitiesTable() {
        const entitiesTableBody = document.getElementById('entitiesTableBody');
        if (!entitiesTableBody) return;

        if (this.allEntities.length === 0) {
            const message = !this.lastRefresh 
                ? 'Connect to server and click "Refresh from Server" to load galaxy objects'
                : 'No entities match the current filters';
            entitiesTableBody.innerHTML = `
                <tr>
                    <td colspan="6" class="empty-state">${message}</td>
                </tr>
            `;
            return;
        }

        let html = '';
        this.allEntities.forEach(entity => {
            const typeClass = entity.type.toLowerCase();
            const factionClass = entity.faction.toLowerCase().replace(/\s+/g, '');
            const categoryClass = entity.category;

            html += `
                <tr>
                    <td class="entity-id">${escapeHtml(entity.entity_id)}</td>
                    <td><span class="entity-type ${typeClass}">${escapeHtml(entity.type)}</span></td>
                    <td><span class="entity-faction ${factionClass}">${escapeHtml(entity.faction)}</span></td>
                    <td class="entity-name">${escapeHtml(entity.name)}</td>
                    <td class="entity-playfield">${escapeHtml(entity.playfield)}</td>
                    <td><span class="entity-category ${categoryClass}">${categoryClass}</span></td>
                </tr>
            `;
        });

        entitiesTableBody.innerHTML = html;
    },

    updateEntityStats(stats = null) {
        // Use provided stats or get them from current entities
        const entityStats = stats || this.calculateStatsFromEntities();
        
        const totalEntities = document.getElementById('totalEntities');
        const asteroidEntities = document.getElementById('asteroidEntities');
        const baseEntities = document.getElementById('baseEntities');
        const shipEntities = document.getElementById('shipEntities');
        const wreckEntities = document.getElementById('wreckEntities');

        if (totalEntities) totalEntities.textContent = entityStats.total || 0;
        if (asteroidEntities) asteroidEntities.textContent = entityStats.asteroids || 0;
        if (baseEntities) baseEntities.textContent = entityStats.structures || 0;
        if (shipEntities) shipEntities.textContent = entityStats.ships || 0;
        if (wreckEntities) wreckEntities.textContent = entityStats.wrecks || 0;
    },

    calculateStatsFromEntities() {
        const asteroids = this.allEntities.filter(e => e.category === 'asteroid').length;
        const structures = this.allEntities.filter(e => e.category === 'structure').length;
        const ships = this.allEntities.filter(e => e.category === 'ship').length;
        const wrecks = this.allEntities.filter(e => e.category === 'wreck').length;
        
        return {
            total: this.allEntities.length,
            asteroids: asteroids,
            structures: structures,
            ships: ships,
            wrecks: wrecks
        };
    },

    updateLastRefreshDisplay() {
        const lastRefreshElement = document.getElementById('entitiesLastRefresh');
        if (lastRefreshElement) {
            if (this.lastRefresh) {
                const refreshTime = formatTimestamp(this.lastRefresh);
                lastRefreshElement.textContent = `Last refreshed: ${refreshTime}`;
                lastRefreshElement.style.color = '#cccccc';
            } else {
                lastRefreshElement.textContent = 'Never refreshed from server';
                lastRefreshElement.style.color = '#ff9900';
            }
        }
    },

    showEntitiesLoading(show) {
        const loadingIndicator = document.getElementById('entitiesLoadingIndicator');
        if (loadingIndicator) {
            if (show) {
                loadingIndicator.classList.add('show');
            } else {
                loadingIndicator.classList.remove('show');
            }
        }
    },

    exportEntitiesData() {
        if (!this.rawGentsData) {
            showToast('No raw entity data available. Refresh from server first.', 'error');
            return;
        }

        try {
            // Create downloadable file
            const blob = new Blob([this.rawGentsData], { type: 'text/plain' });
            const url = window.URL.createObjectURL(blob);
            
            // Create download link
            const a = document.createElement('a');
            a.href = url;
            a.download = `empyrion_entities_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.txt`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            
            showToast('Entity data exported successfully', 'success');
        } catch (error) {
            console.error('Error exporting entity data:', error);
            showToast('Error exporting entity data: ' + error, 'error');
        }
    },

    async clearAllEntities() {
        if (!confirm('Are you sure you want to clear all entities from the database? This will remove all stored entity data.')) {
            return;
        }

        try {
            const data = await apiCall('/entities/clear', { method: 'POST' });
            
            if (data.success) {
                this.allEntities = [];
                this.rawGentsData = '';
                this.lastRefresh = null;
                this.updateEntitiesTable();
                this.updateEntityStats();
                this.updateLastRefreshDisplay();
                showToast('All entities cleared from database', 'success');
            } else {
                showToast(data.message || 'Failed to clear entities', 'error');
            }
        } catch (error) {
            console.error('Error clearing entities:', error);
            showToast('Error clearing entities: ' + error, 'error');
        }
    },

    enableEntitiesFeatures(enabled) {
        const refreshBtn = document.getElementById('refreshEntitiesBtn');
        if (refreshBtn) {
            refreshBtn.disabled = !enabled;
        }
    }
};

// Global functions for HTML onclick handlers
function refreshEntitiesFromServer() {
    window.EntitiesManager.refreshEntitiesFromServer();
}

function loadEntitiesFromDatabase() {
    window.EntitiesManager.loadEntitiesFromDatabase();
}

function clearEntityFilters() {
    window.EntitiesManager.clearEntityFilters();
}

function exportEntitiesData() {
    window.EntitiesManager.exportEntitiesData();
}

function clearAllEntities() {
    window.EntitiesManager.clearAllEntities();
}

// Backward compatibility - keep the old function name
function refreshEntities() {
    window.EntitiesManager.refreshEntitiesFromServer();
}
// FILE LOCATION: /static/js/entities.js
/**
 * Entity management functionality for Empyrion Web Helper
 * Enhanced with database persistence and last refresh tracking
 * Copyright (c) 2025 Chaosz Software
 */

// Entities Manager
window.EntitiesManager = {
    allEntities: [],
    filteredEntities: [],
    rawGentsData: '',
    lastRefresh: null,
    filterElements: {},
    
    // Pagination state
    currentPage: 1,
    pageSize: 50,
    totalPages: 1,

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
        
        // Initialize pagination display
        this.updatePagination();
        
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
                this.filteredEntities = [...this.allEntities];
                this.lastRefresh = data.last_refresh;
                this.currentPage = 1;
                this.updatePagination();
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
                this.filteredEntities = [...this.allEntities];
                this.lastRefresh = data.last_refresh;
                this.currentPage = 1;
                this.updatePagination();
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

    applyFilters() {
        debugLog('applyFilters() called');
        
        // Start with all entities
        let filtered = [...this.allEntities];
        
        // Apply each filter
        for (const [key, element] of Object.entries(this.filterElements)) {
            if (element && element.value.trim()) {
                const filterValue = element.value.trim().toLowerCase();
                
                filtered = filtered.filter(entity => {
                    let entityValue = '';
                    
                    // Map filter keys to entity properties
                    switch (key) {
                        case 'entity_id':
                            entityValue = entity.id || '';
                            break;
                        case 'type':
                            entityValue = entity.type || '';
                            break;
                        case 'faction':
                            entityValue = entity.faction || '';
                            break;
                        case 'name':
                            entityValue = entity.name || '';
                            break;
                        case 'playfield':
                            entityValue = entity.playfield || '';
                            break;
                        default:
                            return true;
                    }
                    
                    return entityValue.toLowerCase().includes(filterValue);
                });
            }
        }
        
        this.filteredEntities = filtered;
        this.currentPage = 1;
        this.updatePagination();
        this.updateEntitiesTable();
        
        debugLog(`Applied filters, showing ${this.filteredEntities.length} of ${this.allEntities.length} entities`);
        
        // Update stats for filtered results
        this.updateEntityStats(this.calculateFilteredStats());
    },

    calculateFilteredStats() {
        const stats = {
            total: this.filteredEntities.length,
            asteroids: 0,
            bases: 0,
            ships: 0,
            wrecks: 0
        };
        
        this.filteredEntities.forEach(entity => {
            const type = (entity.type || '').toLowerCase();
            if (type.includes('astvoxel') || type.includes('asteroid')) {
                stats.asteroids++;
            } else if (type === 'ba') {
                stats.bases++;
            } else if (type === 'cv' || type === 'sv') {
                stats.ships++;
            } else if (entity.name && entity.name.toLowerCase().includes('wreck')) {
                stats.wrecks++;
            }
        });
        
        return stats;
    },

    clearEntityFilters() {
        for (const element of Object.values(this.filterElements)) {
            if (element) {
                element.value = '';
            }
        }
        // Reset pagination and reload all entities
        this.filteredEntities = [...this.allEntities];
        this.currentPage = 1;
        this.updatePagination();
        this.updateEntitiesTable();
        
        // Reset stats to show all entities
        this.updateEntityStats(this.calculateFilteredStats());
    },

    updateEntitiesTable() {
        const entitiesTableBody = document.getElementById('entitiesTableBody');
        if (!entitiesTableBody) return;

        if (this.filteredEntities.length === 0) {
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

        // Calculate pagination
        const startIndex = (this.currentPage - 1) * this.pageSize;
        const endIndex = startIndex + this.pageSize;
        const pageEntities = this.filteredEntities.slice(startIndex, endIndex);

        let html = '';
        pageEntities.forEach(entity => {
            const typeClass = entity.type.toLowerCase();
            const factionClass = entity.faction.toLowerCase().replace(/\s+/g, '');
            const categoryClass = entity.category;

            html += `
                <tr>
                    <td class="entity-id">${escapeHtml(entity.id)}</td>
                    <td><span class="entity-type ${typeClass}">${escapeHtml(entity.type)}</span></td>
                    <td><span class="entity-faction ${factionClass}">${escapeHtml(entity.faction)}</span></td>
                    <td class="entity-name">${escapeHtml(entity.name)}</td>
                    <td class="entity-playfield">${escapeHtml(entity.playfield)}</td>
                    <td><span class="entity-category ${typeClass}">${escapeHtml(entity.type)}</span></td>
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
        const asteroids = this.filteredEntities.filter(e => e.category === 'asteroid').length;
        const structures = this.filteredEntities.filter(e => e.category === 'structure').length;
        const ships = this.filteredEntities.filter(e => e.category === 'ship').length;
        const wrecks = this.filteredEntities.filter(e => e.category === 'wreck').length;
        
        return {
            total: this.filteredEntities.length,
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
                this.filteredEntities = [];
                this.rawGentsData = '';
                this.lastRefresh = null;
                this.currentPage = 1;
                this.updatePagination();
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

    // Pagination methods
    updatePagination() {
        this.totalPages = Math.ceil(this.filteredEntities.length / this.pageSize);
        this.updatePaginationInfo();
        this.updatePaginationButtons();
    },

    updatePaginationInfo() {
        const startItem = this.filteredEntities.length > 0 ? (this.currentPage - 1) * this.pageSize + 1 : 0;
        const endItem = Math.min(this.currentPage * this.pageSize, this.filteredEntities.length);
        const infoText = `Page ${this.currentPage} of ${this.totalPages} (${this.filteredEntities.length} entities)`;
        
        const pageInfo = document.getElementById('entitiesPageInfo');
        const pageInfoBottom = document.getElementById('entitiesPageInfoBottom');
        
        if (pageInfo) pageInfo.textContent = infoText;
        if (pageInfoBottom) pageInfoBottom.textContent = infoText;
    },

    updatePaginationButtons() {
        const buttons = [
            ['entitiesFirstBtn', 'entitiesFirstBtnBottom'],
            ['entitiesPrevBtn', 'entitiesPrevBtnBottom'],
            ['entitiesNextBtn', 'entitiesNextBtnBottom'],
            ['entitiesLastBtn', 'entitiesLastBtnBottom']
        ];

        const isFirstPage = this.currentPage === 1;
        const isLastPage = this.currentPage >= this.totalPages;

        // Update first and previous buttons
        buttons[0].forEach(id => {
            const btn = document.getElementById(id);
            if (btn) btn.disabled = isFirstPage;
        });
        
        buttons[1].forEach(id => {
            const btn = document.getElementById(id);
            if (btn) btn.disabled = isFirstPage;
        });

        // Update next and last buttons  
        buttons[2].forEach(id => {
            const btn = document.getElementById(id);
            if (btn) btn.disabled = isLastPage;
        });
        
        buttons[3].forEach(id => {
            const btn = document.getElementById(id);
            if (btn) btn.disabled = isLastPage;
        });
    },

    goToPage(page) {
        if (page < 1) page = 1;
        if (page > this.totalPages) page = this.totalPages;
        
        this.currentPage = page;
        this.updatePagination();
        this.updateEntitiesTable();
    },

    previousPage() {
        this.goToPage(this.currentPage - 1);
    },

    nextPage() {
        this.goToPage(this.currentPage + 1);
    },

    goToLastPage() {
        this.goToPage(this.totalPages);
    },

    changePageSize() {
        const pageSizeSelect = document.getElementById('entitiesPageSize');
        if (pageSizeSelect) {
            this.pageSize = parseInt(pageSizeSelect.value);
            this.currentPage = 1;
            this.updatePagination();
            this.updateEntitiesTable();
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

// POI Management Note: 
// The 'wipe poi' command only destroys POIs without regenerating them.
// For POI regeneration, use 'regenerate <entityid>' in-game console or
// manually delete playfield files (World.dat, Plantlife.dat, Decoration.dat)

// Backward compatibility - keep the old function name
function refreshEntities() {
    window.EntitiesManager.refreshEntitiesFromServer();
}
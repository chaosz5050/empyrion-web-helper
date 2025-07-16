// FILE LOCATION: /static/js/entities.js
/**
 * Entity management functionality for Empyrion Web Helper
 * Copyright (c) 2025 Chaosz Software
 */

// Entities Manager
window.EntitiesManager = {
    allEntities: [],
    rawGentsData: '',
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
    },

    async refreshEntities() {
        if (!isConnected) {
            showToast('Not connected to server', 'error');
            return;
        }

        debugLog('refreshEntities() called');
        this.showEntitiesLoading(true);
        
        const refreshBtn = document.getElementById('refreshEntitiesBtn');
        const originalText = refreshBtn.textContent;
        refreshBtn.disabled = true;
        refreshBtn.textContent = '🔄 Loading...';

        try {
            const data = await apiCall('/entities');
            debugLog('Entities response:', data);

            if (data.success) {
                this.rawGentsData = data.raw_data || '';
                this.allEntities = data.entities || [];
                this.updateEntitiesTable();
                this.updateEntityStats();
                showToast(`Loaded ${this.allEntities.length} entities`, 'success');
            } else {
                showToast(data.message || 'Failed to load entities', 'error');
            }
        } catch (error) {
            console.error('Error refreshing entities:', error);
            showToast('Error loading entities: ' + error, 'error');
        } finally {
            this.showEntitiesLoading(false);
            refreshBtn.disabled = false;
            refreshBtn.textContent = originalText;
        }
    },

    parseGentsOutput(gentsData) {
        const entities = [];
        const lines = gentsData.split('\n');
        let currentPlayfield = '';

        for (let line of lines) {
            line = line.trim();
            if (!line) continue;

            // Check if this is a playfield header
            if (!line.match(/^\s*\d+\./)) {
                currentPlayfield = line;
                continue;
            }

            // Parse entity line
            const entity = this.parseEntityLine(line, currentPlayfield);
            if (entity) {
                entities.push(entity);
            }
        }

        return entities;
    },

    parseEntityLine(line, playfield) {
        try {
            // Remove leading number and dot
            const cleanLine = line.replace(/^\s*\d+\.\s*/, '');
            
            // Parse: "050043 AstVoxel [NoF] False False 'Copper Asteroid' (-)"
            const match = cleanLine.match(/^(\d+)\s+(\w+)\s+\[([^\]]+)\]\s+\w+\s+\w+\s+'([^']+)'/);
            
            if (!match) {
                debugLog('Failed to parse entity line:', line);
                return null;
            }

            const [, entityId, type, faction, name] = match;

            return {
                entity_id: entityId,
                type: type,
                faction: faction,
                name: name,
                playfield: playfield,
                category: this.categorizeEntity(type, faction, name)
            };
        } catch (error) {
            debugLog('Error parsing entity line:', line, error);
            return null;
        }
    },

    categorizeEntity(type, faction, name) {
        if (type === 'AstVoxel') {
            return 'asteroid';
        }
        
        if (faction === 'Wreck' || name.toLowerCase().includes('wreck') || 
            name.toLowerCase().includes('debris') || name.toLowerCase().includes('abandoned')) {
            return 'wreck';
        }
        
        if (type === 'BA') {
            return 'structure';
        }
        
        if (type === 'CV' || type === 'SV') {
            return 'ship';
        }
        
        return 'other';
    },

    applyFilters() {
        const filteredEntities = this.allEntities.filter(entity => {
            // Entity ID filter
            if (this.filterElements.entity_id.value.trim() && 
                !entity.entity_id.includes(this.filterElements.entity_id.value.trim())) {
                return false;
            }

            // Type filter
            if (this.filterElements.type.value && 
                entity.type !== this.filterElements.type.value) {
                return false;
            }

            // Faction filter
            if (this.filterElements.faction.value.trim() && 
                !entity.faction.toLowerCase().includes(this.filterElements.faction.value.trim().toLowerCase())) {
                return false;
            }

            // Name filter
            if (this.filterElements.name.value.trim() && 
                !entity.name.toLowerCase().includes(this.filterElements.name.value.trim().toLowerCase())) {
                return false;
            }

            // Playfield filter
            if (this.filterElements.playfield.value.trim() && 
                !entity.playfield.toLowerCase().includes(this.filterElements.playfield.value.trim().toLowerCase())) {
                return false;
            }

            return true;
        });

        this.updateEntitiesTable(filteredEntities);
        this.updateEntityStats(filteredEntities);
    },

    clearEntityFilters() {
        for (const element of Object.values(this.filterElements)) {
            if (element) {
                element.value = '';
            }
        }
        this.updateEntitiesTable();
        this.updateEntityStats();
    },

    updateEntitiesTable(entitiesToShow = null) {
        const entitiesTableBody = document.getElementById('entitiesTableBody');
        if (!entitiesTableBody) return;

        const entities = entitiesToShow || this.allEntities;

        if (entities.length === 0) {
            const message = this.allEntities.length === 0 
                ? 'Connect to server and click "Refresh Entities" to view galaxy objects'
                : 'No entities match the current filters';
            entitiesTableBody.innerHTML = `
                <tr>
                    <td colspan="6" class="empty-state">${message}</td>
                </tr>
            `;
            return;
        }

        let html = '';
        entities.forEach(entity => {
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

    updateEntityStats(entitiesToCount = null) {
        const entities = entitiesToCount || this.allEntities;
        
        const totalEntities = document.getElementById('totalEntities');
        const asteroidEntities = document.getElementById('asteroidEntities');
        const baseEntities = document.getElementById('baseEntities');
        const shipEntities = document.getElementById('shipEntities');
        const wreckEntities = document.getElementById('wreckEntities');

        if (totalEntities) totalEntities.textContent = entities.length;

        // Count by category
        const asteroids = entities.filter(e => e.category === 'asteroid').length;
        const bases = entities.filter(e => e.category === 'structure').length;
        const ships = entities.filter(e => e.category === 'ship').length;
        const wrecks = entities.filter(e => e.category === 'wreck').length;

        if (asteroidEntities) asteroidEntities.textContent = asteroids;
        if (baseEntities) baseEntities.textContent = bases;
        if (shipEntities) shipEntities.textContent = ships;
        if (wreckEntities) wreckEntities.textContent = wrecks;
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
            showToast('No entity data to export. Refresh entities first.', 'error');
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

    enableEntitiesFeatures(enabled) {
        const refreshBtn = document.getElementById('refreshEntitiesBtn');
        if (refreshBtn) {
            refreshBtn.disabled = !enabled;
        }
    }
};

// Global functions for HTML onclick handlers
function refreshEntities() {
    window.EntitiesManager.refreshEntities();
}

function clearEntityFilters() {
    window.EntitiesManager.clearEntityFilters();
}

function exportEntitiesData() {
    window.EntitiesManager.exportEntitiesData();
}
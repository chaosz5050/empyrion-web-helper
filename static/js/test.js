// FILE LOCATION: /static/js/test.js
/**
 * Test functionality for player structure detection and faction classification
 * Tests selective POI regeneration system theory
 * Copyright (c) 2025 Chaosz Software
 */

// Test Manager
window.TestManager = {
    playerStructures: [],
    activePlayfields: [],
    selectedPlayfields: new Set(),
    lastTestRun: null,
    isTestRunning: false,
    
    init() {
        debugLog('Test manager initialized');
        this.updateLastTestDisplay();
    },

    async pullPlayerStructures() {
        if (this.isTestRunning) {
            showToast('Test already in progress', 'warning');
            return;
        }

        debugLog('pullPlayerStructures() called');
        this.setTestStatus('Analyzing entity factions...', true);
        this.isTestRunning = true;
        
        const pullBtn = document.getElementById('pullPlayerStructuresBtn');
        const originalText = pullBtn.textContent;
        pullBtn.disabled = true;
        pullBtn.textContent = '🔄 Analyzing Factions...';

        try {
            const data = await apiCall('/api/test/player-structures');
            debugLog('Player structures response:', data);

            if (data.success) {
                this.playerStructures = data.player_entities || [];
                this.lastTestRun = data.analysis_time;
                
                // Update results display
                this.updatePlayerStructuresTable();
                this.updateTestStatistics(data.statistics);
                this.updateFactionBreakdown(data.faction_breakdown);
                this.updateLastTestDisplay();
                
                // Show/hide sections
                this.showSection('resultsSection', true);
                this.showSection('technicalSection', true);
                
                // Success message
                const playerCount = this.playerStructures.length;
                const totalCount = data.statistics.total_entities || 0;
                showToast(`Analysis complete: Found ${playerCount} player structures out of ${totalCount} total entities`, 'success');
                
            } else {
                showToast(data.message || 'Failed to analyze player structures', 'error');
                debugLog('Player structures analysis failed:', data.message);
            }
        } catch (error) {
            console.error('Error analyzing player structures:', error);
            showToast('Error analyzing player structures: ' + error, 'error');
        } finally {
            this.setTestStatus('Ready for testing', false);
            this.isTestRunning = false;
            pullBtn.disabled = false;
            pullBtn.textContent = originalText;
        }
    },

    async refreshEntityData() {
        if (!isConnected) {
            showToast('Not connected to server', 'error');
            return;
        }

        if (this.isTestRunning) {
            showToast('Test already in progress', 'warning');
            return;
        }

        debugLog('refreshEntityData() called');
        this.setTestStatus('Refreshing entity data from server...', true);
        this.isTestRunning = true;
        
        const refreshBtn = document.getElementById('refreshEntitiesBtn');
        const originalText = refreshBtn.textContent;
        refreshBtn.disabled = true;
        refreshBtn.textContent = '📡 Refreshing...';

        try {
            // Use the same endpoint as the Entities tab
            const data = await apiCall('/entities/refresh', { method: 'POST' });
            debugLog('Entity refresh response:', data);

            if (data.success) {
                const updatedCount = data.updated_count || 0;
                showToast(`Refreshed ${updatedCount} entities from server`, 'success');
                
                // Clear previous test results since entity data has changed
                this.clearTestResults();
                this.setTestStatus('Entity data refreshed - ready to run new test', false);
                
            } else {
                showToast(data.message || 'Failed to refresh entity data', 'error');
                this.setTestStatus('Failed to refresh entity data', false);
            }
        } catch (error) {
            console.error('Error refreshing entity data:', error);
            showToast('Error refreshing entity data: ' + error, 'error');
            this.setTestStatus('Error during refresh', false);
        } finally {
            this.isTestRunning = false;
            refreshBtn.disabled = false;
            refreshBtn.textContent = originalText;
        }
    },

    async loadActivePlayfields() {
        if (!isConnected) {
            showToast('Not connected to server', 'error');
            return;
        }

        if (this.isTestRunning) {
            showToast('Operation already in progress', 'warning');
            return;
        }

        debugLog('loadActivePlayfields() called');
        this.setTestStatus('Loading active playfields...', true);
        this.isTestRunning = true;
        
        const loadBtn = document.getElementById('loadPlayfieldsBtn');
        const originalText = loadBtn.textContent;
        loadBtn.disabled = true;
        loadBtn.textContent = '🌍 Loading...';

        try {
            const data = await apiCall('/api/test/active-playfields');
            debugLog('Active playfields response:', data);

            if (data.success) {
                this.activePlayfields = data.playfields || [];
                this.selectedPlayfields.clear();
                
                this.displayPlayfields();
                showToast(`Loaded ${this.activePlayfields.length} active playfields`, 'success');
                this.setTestStatus(`Found ${this.activePlayfields.length} active playfields`, false);
                
            } else {
                showToast(data.message || 'Failed to load playfields', 'error');
                this.setTestStatus('Failed to load playfields', false);
            }
        } catch (error) {
            console.error('Error loading playfields:', error);
            showToast('Error loading playfields: ' + error, 'error');
            this.setTestStatus('Error loading playfields', false);
        } finally {
            this.isTestRunning = false;
            loadBtn.disabled = false;
            loadBtn.textContent = originalText;
        }
    },

    displayPlayfields() {
        const playfieldSelection = document.getElementById('playfieldSelection');
        const playfieldList = document.getElementById('playfieldList');
        
        if (!playfieldList) return;

        if (this.activePlayfields.length === 0) {
            playfieldSelection.style.display = 'none';
            return;
        }

        // Show playfield selection section
        playfieldSelection.style.display = 'block';
        
        let html = '';
        this.activePlayfields.forEach(playfield => {
            const isSelected = this.selectedPlayfields.has(playfield.name);
            
            html += `
                <div class="konsole-playfield-item ${isSelected ? 'selected' : ''}" 
                     onclick="TestManager.togglePlayfield('${playfield.name}')" 
                     data-playfield="${playfield.name}">
                    <div class="konsole-playfield-header">
                        <input type="checkbox" class="konsole-playfield-checkbox" ${isSelected ? 'checked' : ''} 
                               onclick="event.stopPropagation();" 
                               onchange="TestManager.togglePlayfield('${playfield.name}')">
                        <span class="konsole-playfield-name">${escapeHtml(playfield.name)}</span>
                    </div>
                    <div class="konsole-playfield-stats">
                        <div class="konsole-playfield-stat">
                            <span class="konsole-playfield-stat-label">NPC Entities:</span>
                            <span class="konsole-playfield-stat-value npc">${playfield.npc_count}</span>
                        </div>
                        <div class="konsole-playfield-stat">
                            <span class="konsole-playfield-stat-label">Player Entities:</span>
                            <span class="konsole-playfield-stat-value player">${playfield.player_count}</span>
                        </div>
                        <div class="konsole-playfield-stat">
                            <span class="konsole-playfield-stat-label">Neutral Entities:</span>
                            <span class="konsole-playfield-stat-value">${playfield.neutral_count}</span>
                        </div>
                        <div class="konsole-playfield-stat">
                            <span class="konsole-playfield-stat-label">Total Entities:</span>
                            <span class="konsole-playfield-stat-value">${playfield.total_count}</span>
                        </div>
                    </div>
                </div>
            `;
        });

        playfieldList.innerHTML = html;
        this.updateRegenerationButton();
    },

    togglePlayfield(playfieldName) {
        debugLog(`Toggling playfield: ${playfieldName}`);
        
        if (this.selectedPlayfields.has(playfieldName)) {
            this.selectedPlayfields.delete(playfieldName);
            debugLog(`Removed ${playfieldName} from selection`);
        } else {
            this.selectedPlayfields.add(playfieldName);
            debugLog(`Added ${playfieldName} to selection`);
        }
        
        // Update visual state
        const item = document.querySelector(`[data-playfield="${playfieldName}"]`);
        const checkbox = item?.querySelector('.konsole-playfield-checkbox');
        
        if (!item || !checkbox) {
            debugLog(`Could not find UI elements for ${playfieldName}`);
            return;
        }
        
        const isSelected = this.selectedPlayfields.has(playfieldName);
        
        if (isSelected) {
            item.classList.add('selected');
            checkbox.checked = true;
        } else {
            item.classList.remove('selected');
            checkbox.checked = false;
        }
        
        debugLog(`${playfieldName} is now ${isSelected ? 'selected' : 'unselected'}`);
        debugLog(`Current selection:`, Array.from(this.selectedPlayfields));
        
        this.updateRegenerationButton();
    },

    selectAllPlayfields() {
        this.activePlayfields.forEach(pf => this.selectedPlayfields.add(pf.name));
        this.displayPlayfields();
    },

    clearPlayfieldSelection() {
        this.selectedPlayfields.clear();
        this.displayPlayfields();
    },

    updateRegenerationButton() {
        const regenBtn = document.getElementById('startRegenerationBtn');
        if (regenBtn) {
            const hasSelection = this.selectedPlayfields.size > 0;
            regenBtn.disabled = !hasSelection;
            
            if (hasSelection) {
                const totalRegenerableEntities = this.activePlayfields
                    .filter(pf => this.selectedPlayfields.has(pf.name))
                    .reduce((sum, pf) => sum + pf.npc_count + pf.neutral_count, 0);
                regenBtn.textContent = `⚡ Regenerate ${totalRegenerableEntities} Entities`;
            } else {
                regenBtn.textContent = '⚡ Start Selective Regeneration';
            }
        }
    },

    async startRegeneration() {
        if (this.selectedPlayfields.size === 0) {
            showToast('No playfields selected', 'warning');
            return;
        }

        // Calculate totals
        const selectedPlayfieldData = this.activePlayfields.filter(pf => this.selectedPlayfields.has(pf.name));
        const totalRegenerableEntities = selectedPlayfieldData.reduce((sum, pf) => sum + pf.npc_count + pf.neutral_count, 0);
        const totalPlayerEntities = selectedPlayfieldData.reduce((sum, pf) => sum + pf.player_count, 0);

        const confirmMessage = `
🚨 SELECTIVE POI REGENERATION CONFIRMATION 🚨

Selected Playfields: ${this.selectedPlayfields.size}
Entities to Regenerate: ${totalRegenerableEntities} (NPC + Neutral)
Player Entities to Preserve: ${totalPlayerEntities}

This will regenerate ALL NPC and Neutral POIs on the selected playfields while preserving all player-owned structures.

Are you sure you want to proceed?
        `.trim();

        if (!confirm(confirmMessage)) {
            return;
        }

        // Execute bulk regeneration
        await this.executeBulkRegeneration();
    },

    async executeBulkRegeneration() {
        if (!isConnected) {
            showToast('Not connected to server', 'error');
            return;
        }

        this.setTestStatus('Executing bulk regeneration...', true);
        this.isTestRunning = true;
        
        // Disable all buttons during regeneration
        const regenBtn = document.getElementById('startRegenerationBtn');
        const loadBtn = document.getElementById('loadPlayfieldsBtn');
        const refreshBtn = document.getElementById('refreshEntitiesBtn');
        
        regenBtn.disabled = true;
        loadBtn.disabled = true;
        refreshBtn.disabled = true;
        
        const originalRegenText = regenBtn.textContent;
        regenBtn.textContent = '⚡ Regenerating...';

        // Show progress bar
        this.showProgressBar(true);

        try {
            const selectedPlayfieldsArray = Array.from(this.selectedPlayfields);
            
            // Use Server-Sent Events for real-time progress if supported
            if (typeof EventSource !== 'undefined') {
                debugLog('Using Server-Sent Events for progress tracking');
                await this.executeBulkRegenerationWithProgress(selectedPlayfieldsArray);
            } else {
                debugLog('EventSource not supported, using fallback method');
                // Fallback to regular API call for older browsers
                await this.executeBulkRegenerationFallback(selectedPlayfieldsArray);
            }
            
        } catch (error) {
            console.error('Error executing bulk regeneration:', error);
            showToast('Error executing bulk regeneration: ' + error, 'error');
            this.setTestStatus('Error during bulk regeneration', false);
        } finally {
            this.showProgressBar(false);
            this.isTestRunning = false;
            regenBtn.disabled = false;
            loadBtn.disabled = false;
            refreshBtn.disabled = false;
            regenBtn.textContent = originalRegenText;
        }
    },

    async executeBulkRegenerationWithProgress(selectedPlayfieldsArray) {
        return new Promise((resolve, reject) => {
            const url = `/api/test/bulk-regenerate-stream?playfields=${encodeURIComponent(JSON.stringify(selectedPlayfieldsArray))}`;
            debugLog('Creating EventSource connection to:', url);
            
            const eventSource = new EventSource(url);
            
            let startTime = Date.now();
            
            debugLog('EventSource created, waiting for events...');
            
            // Show progress bar immediately and initialize it
            this.showProgressBar(true);
            this.updateProgress(0, 1, 0, startTime); // Show 0/1 to indicate starting
            
            eventSource.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    debugLog('Progress event received:', data);
                    
                    switch (data.type) {
                        case 'start':
                            this.showProgressBar(true); // Ensure progress bar is visible
                            this.updateProgress(0, data.total, 0, startTime);
                            this.setTestStatus(`Starting regeneration of ${data.total} entities...`, true);
                            break;
                            
                        case 'progress':
                            this.updateProgress(data.processed, data.total, data.successful, startTime);
                            this.setTestStatus(`Regenerating entities... ${data.processed}/${data.total}`, true);
                            break;
                            
                        case 'complete':
                            this.updateProgress(data.total_processed, data.total_processed, data.regenerated_count, startTime);
                            
                            const message = `✅ Regeneration Complete! Successful: ${data.regenerated_count} | Failed: ${data.failed_count} | Total: ${data.total_processed}`;
                            this.setTestStatus(message, false);
                            showToast(`Successfully regenerated ${data.regenerated_count} entities!`, 'success');
                            
                            if (data.failed_count > 0) {
                                console.log('Failed regenerations:', data.failed_regenerations);
                                showToast(`Warning: ${data.failed_count} entities failed to regenerate - check console for details`, 'warning');
                            }
                            
                            // Clear selection after successful regeneration
                            this.selectedPlayfields.clear();
                            this.displayPlayfields();
                            
                            eventSource.close();
                            resolve(data);
                            break;
                            
                        case 'error':
                            this.setTestStatus('Bulk regeneration failed', false);
                            showToast(data.message || 'Bulk regeneration failed', 'error');
                            eventSource.close();
                            reject(new Error(data.message || 'Bulk regeneration failed'));
                            break;
                    }
                } catch (parseError) {
                    console.error('Error parsing progress event:', parseError);
                }
            };
            
            eventSource.onopen = (event) => {
                debugLog('EventSource connection opened successfully');
            };
            
            eventSource.onerror = (error) => {
                console.error('EventSource error:', error);
                debugLog('EventSource readyState:', eventSource.readyState);
                this.setTestStatus('Connection error during regeneration', false);
                showToast('Connection error during regeneration', 'error');
                eventSource.close();
                reject(error);
            };
        });
    },

    async executeBulkRegenerationFallback(selectedPlayfieldsArray) {
        const data = await apiCall('/api/test/bulk-regenerate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                playfields: selectedPlayfieldsArray
            })
        });
        
        debugLog('Bulk regeneration response:', data);

        if (data.success) {
            const message = `✅ Regeneration Complete! Successful: ${data.regenerated_count} | Failed: ${data.failed_count} | Total: ${data.total_processed}`;
            
            showToast(`Successfully regenerated ${data.regenerated_count} entities!`, 'success');
            this.setTestStatus(message, false);
            
            // Show detailed results
            if (data.failed_count > 0) {
                console.log('Failed regenerations:', data.failed_regenerations);
                showToast(`Warning: ${data.failed_count} entities failed to regenerate - check console for details`, 'warning');
            }
            
            // Clear selection after successful regeneration
            this.selectedPlayfields.clear();
            this.displayPlayfields();
            
        } else {
            showToast(data.message || 'Bulk regeneration failed', 'error');
            this.setTestStatus('Bulk regeneration failed', false);
            throw new Error(data.message || 'Bulk regeneration failed');
        }
    },

    updatePlayerStructuresTable() {
        const tableBody = document.getElementById('playerStructuresTableBody');
        const emptyState = document.getElementById('noPlayerStructures');
        
        if (!tableBody || !emptyState) return;

        if (this.playerStructures.length === 0) {
            tableBody.innerHTML = '';
            emptyState.style.display = 'block';
            return;
        }

        emptyState.style.display = 'none';
        
        let html = '';
        this.playerStructures.forEach(structure => {
            const typeClass = (structure.type || '').toLowerCase();
            const factionClass = (structure.faction || '').toLowerCase().replace(/\s+/g, '');
            const statusClass = structure.category === 'player' ? 'player-owned' : 'neutral';
            
            html += `
                <tr>
                    <td class="entity-id">${escapeHtml(structure.id)}</td>
                    <td><span class="entity-type ${typeClass}">${escapeHtml(structure.type)}</span></td>
                    <td><span class="entity-faction ${factionClass}">${escapeHtml(structure.faction)}</span></td>
                    <td class="entity-name">${escapeHtml(structure.name)}</td>
                    <td class="entity-playfield">${escapeHtml(structure.playfield)}</td>
                    <td><span class="entity-status ${statusClass}">${structure.category === 'player' ? 'Player-Owned' : 'Neutral'}</span></td>
                </tr>
            `;
        });

        tableBody.innerHTML = html;
    },

    updateTestStatistics(stats) {
        if (!stats) return;
        
        const elements = {
            'totalPlayerStructures': stats.player_entities || 0,
            'totalNpcStructures': stats.npc_entities || 0,
            'totalNeutralStructures': stats.neutral_entities || 0
        };

        for (const [id, value] of Object.entries(elements)) {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = value;
            }
        }
    },

    updateFactionBreakdown(factionBreakdown) {
        const container = document.getElementById('factionBreakdown');
        if (!container || !factionBreakdown) return;

        let html = '';
        
        // Group factions by category
        const categories = {
            'Player Factions': [],
            'NPC Factions': [],
            'Neutral': []
        };

        for (const [faction, data] of Object.entries(factionBreakdown)) {
            const item = {
                code: faction,
                name: data.name,
                count: data.count,
                category: data.category
            };

            if (data.category === 'Player') {
                categories['Player Factions'].push(item);
            } else if (data.category === 'NPC') {
                categories['NPC Factions'].push(item);
            } else {
                categories['Neutral'].push(item);
            }
        }

        // Render each category
        for (const [categoryName, factions] of Object.entries(categories)) {
            if (factions.length === 0) continue;
            
            html += `<div class="konsole-faction-category"><h4>${categoryName}</h4>`;
            
            factions.forEach(faction => {
                const color = faction.category === 'Player' ? 'var(--accent-green)' : 
                             faction.category === 'NPC' ? 'var(--accent-blue)' : 'var(--text-muted)';
                
                html += `
                    <div class="konsole-faction-item" style="border-left-color: ${color}">
                        <span class="konsole-faction-code">[${escapeHtml(faction.code)}]</span>
                        ${escapeHtml(faction.name)} 
                        (<span class="konsole-faction-count">${faction.count}</span>)
                    </div>
                `;
            });
            
            html += '</div>';
        }

        container.innerHTML = html;
    },

    updateLastTestDisplay() {
        // This would update a display showing when the test was last run
        debugLog('Last test run:', this.lastTestRun);
    },

    setTestStatus(message, isLoading = false) {
        const statusElement = document.getElementById('testStatus');
        const statusText = document.getElementById('testStatusText');
        
        if (statusElement && statusText) {
            statusText.textContent = message;
            statusElement.style.display = 'block';
            
            if (isLoading) {
                statusElement.className = 'konsole-status-bar loading';
            } else {
                statusElement.className = 'konsole-status-bar';
            }
        }
    },

    showSection(sectionId, show = true) {
        const section = document.getElementById(sectionId);
        if (section) {
            section.style.display = show ? 'block' : 'none';
        }
    },

    clearTestResults() {
        this.playerStructures = [];
        this.lastTestRun = null;
        
        // Hide results sections
        this.showSection('resultsSection', false);
        this.showSection('technicalSection', false);
        
        // Clear status
        const statusElement = document.getElementById('testStatus');
        if (statusElement) {
            statusElement.style.display = 'none';
        }
        
        debugLog('Test results cleared');
    },

    showProgressBar(show = true) {
        const progressContainer = document.getElementById('progressContainer');
        const statusElement = document.getElementById('testStatus');
        
        if (progressContainer) {
            progressContainer.style.display = show ? 'block' : 'none';
            
            if (!show) {
                // Reset progress when hiding
                this.updateProgress(0, 0, 0, Date.now());
            }
        }
        
        // Ensure status section is visible when showing progress
        if (show && statusElement) {
            statusElement.style.display = 'block';
        }
    },

    updateProgress(processed, total, successful, startTime) {
        const progressFill = document.getElementById('progressFill');
        const progressText = document.getElementById('progressText');
        const progressEta = document.getElementById('progressEta');
        
        if (!progressFill || !progressText || !progressEta) return;
        
        const percentage = total > 0 ? Math.round((processed / total) * 100) : 0;
        
        // Update progress bar
        progressFill.style.width = `${percentage}%`;
        
        // Update progress text
        progressText.textContent = `${processed}/${total} (${percentage}%)`;
        
        // Calculate and update ETA
        if (processed > 0 && processed < total) {
            const elapsed = Date.now() - startTime;
            const rate = processed / elapsed; // entities per ms
            const remaining = total - processed;
            const etaMs = remaining / rate;
            
            const etaSeconds = Math.round(etaMs / 1000);
            if (etaSeconds > 60) {
                const minutes = Math.floor(etaSeconds / 60);
                const seconds = etaSeconds % 60;
                progressEta.textContent = `ETA: ${minutes}m ${seconds}s`;
            } else {
                progressEta.textContent = `ETA: ${etaSeconds}s`;
            }
        } else {
            progressEta.textContent = '';
        }
    }
};

// Global functions for HTML onclick handlers
function pullPlayerStructures() {
    window.TestManager.pullPlayerStructures();
}

function refreshEntityData() {
    window.TestManager.refreshEntityData();
}

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    if (window.TestManager) {
        window.TestManager.init();
    }
});
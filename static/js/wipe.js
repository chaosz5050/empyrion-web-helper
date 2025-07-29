// FILE LOCATION: /static/js/wipe.js
/**
 * Wipe Manager for Playfield Wipe System
 * Handles deployment of wipeinfo.txt files for playfield resets
 * Copyright (c) 2025 Chaosz Software
 */

// Wipe Manager
window.WipeManager = {
    activePlayfields: [],
    selectedPlayfields: new Set(),
    isOperationRunning: false,
    
    init() {
        debugLog('Wipe manager initialized');
        this.setupWipeTypeHandlers();
    },

    setupWipeTypeHandlers() {
        // Handle mutual exclusivity of "All" option with others
        const wipeAll = document.getElementById('wipeAll');
        const otherCheckboxes = ['wipePOI', 'wipeDeposit', 'wipeTerrain'];
        
        if (wipeAll) {
            wipeAll.addEventListener('change', (e) => {
                if (e.target.checked) {
                    // If "All" is checked, uncheck others
                    otherCheckboxes.forEach(id => {
                        const checkbox = document.getElementById(id);
                        if (checkbox) checkbox.checked = false;
                    });
                }
                this.updateDeployButton();
            });
        }
        
        // Handle other checkboxes unchecking "All"
        otherCheckboxes.forEach(id => {
            const checkbox = document.getElementById(id);
            if (checkbox) {
                checkbox.addEventListener('change', (e) => {
                    if (e.target.checked && wipeAll) {
                        wipeAll.checked = false;
                    }
                    this.updateDeployButton();
                });
            }
        });
    },

    async loadActivePlayfields() {
        if (this.isOperationRunning) {
            showToast('Operation already in progress', 'warning');
            return;
        }

        debugLog('loadActivePlayfields() called');
        this.setWipeStatus('Loading available playfields via FTP...', true);
        this.isOperationRunning = true;
        
        const loadBtn = document.getElementById('loadPlayfieldsBtn');
        const originalText = loadBtn.textContent;
        loadBtn.disabled = true;
        loadBtn.textContent = '🌍 Loading...';

        try {
            // First get the FTP playfields path from settings
            const settingsData = await apiCall('/api/settings/playfields_path');
            if (!settingsData.success || !settingsData.value) {
                throw new Error('FTP playfields path not configured in Settings > FTP section');
            }
            
            const playfieldsPath = settingsData.value;
            debugLog('Using FTP playfields path:', playfieldsPath);
            
            // Use FTP endpoint to list all playfields from server directory
            const data = await apiCall('/api/ftp/list-playfields', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    playfields_path: playfieldsPath
                })
            });
            debugLog('FTP playfields response:', data);

            if (data.success) {
                this.activePlayfields = data.playfields || [];
                this.selectedPlayfields.clear();
                
                this.displayPlayfields();
                showToast(`Loaded ${this.activePlayfields.length} playfields from server directory`, 'success');
                this.setWipeStatus(`Found ${this.activePlayfields.length} playfields available for wiping`, false);
                
            } else {
                showToast(data.message || 'Failed to load playfields via FTP', 'error');
                this.setWipeStatus('Failed to load playfields via FTP', false);
            }
        } catch (error) {
            console.error('Error loading playfields:', error);
            showToast('Error loading playfields: ' + error, 'error');
            this.setWipeStatus('Error loading playfields', false);
        } finally {
            this.isOperationRunning = false;
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
                     onclick="WipeManager.togglePlayfield('${playfield.name}')" 
                     data-playfield="${playfield.name}">
                    <div class="konsole-playfield-header">
                        <input type="checkbox" class="konsole-playfield-checkbox" ${isSelected ? 'checked' : ''} 
                               onclick="event.stopPropagation();" 
                               onchange="WipeManager.togglePlayfield('${playfield.name}')">
                        <span class="konsole-playfield-name">${escapeHtml(playfield.display_name || playfield.name)}</span>
                    </div>
                    <div class="konsole-playfield-info">
                        <small style="color: var(--text-muted);">Type: ${escapeHtml(playfield.type || 'Unknown')}</small>
                    </div>
                </div>
            `;
        });

        playfieldList.innerHTML = html;
        this.updateDeployButton();
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
        
        this.updateDeployButton();
    },

    selectAllPlayfields() {
        this.activePlayfields.forEach(pf => this.selectedPlayfields.add(pf.name));
        this.displayPlayfields();
    },

    clearPlayfieldSelection() {
        this.selectedPlayfields.clear();
        this.displayPlayfields();
    },

    updateDeployButton() {
        const deployBtn = document.getElementById('deployWipeBtn');
        if (deployBtn) {
            const hasSelection = this.selectedPlayfields.size > 0;
            const hasWipeType = this.getSelectedWipeTypes().length > 0;
            
            deployBtn.disabled = !hasSelection || !hasWipeType;
        }
    },

    getSelectedWipeTypes() {
        const types = [];
        const checkboxes = [
            { id: 'wipePOI', type: 'poi' },
            { id: 'wipeDeposit', type: 'deposit' },
            { id: 'wipeTerrain', type: 'terrain' },
            { id: 'wipeAll', type: 'all' }
        ];
        
        checkboxes.forEach(({ id, type }) => {
            const checkbox = document.getElementById(id);
            if (checkbox && checkbox.checked) {
                types.push(type);
            }
        });
        
        return types;
    },

    async deployWipeFiles() {
        if (this.selectedPlayfields.size === 0) {
            showToast('No playfields selected', 'warning');
            return;
        }

        const wipeTypes = this.getSelectedWipeTypes();
        if (wipeTypes.length === 0) {
            showToast('No wipe types selected', 'warning');
            return;
        }

        // Create confirmation message
        const wipeTypeNames = {
            'poi': 'POI (Points of Interest)',
            'deposit': 'Deposits (Resource nodes)',
            'terrain': 'Terrain (Voxel changes)', 
            'all': 'All (Complete playfield reset)'
        };
        
        const selectedTypeText = wipeTypes.map(type => wipeTypeNames[type]).join(', ');
        const confirmMessage = `
🚨 PLAYFIELD WIPE CONFIRMATION 🚨

Selected Playfields: ${this.selectedPlayfields.size}
Wipe Types: ${selectedTypeText}

This will deploy wipeinfo.txt files that will reset the selected content on next server restart or playfield reload.

⚠️ WARNING: This action cannot be undone!

Are you sure you want to proceed?
        `.trim();

        if (!confirm(confirmMessage)) {
            return;
        }

        await this.executeWipeDeployment();
    },

    async executeWipeDeployment() {
        this.setWipeStatus('Deploying wipe files...', true);
        this.isOperationRunning = true;
        
        // Disable all buttons during deployment
        const deployBtn = document.getElementById('deployWipeBtn');
        const loadBtn = document.getElementById('loadPlayfieldsBtn');
        
        deployBtn.disabled = true;
        loadBtn.disabled = true;
        
        const originalDeployText = deployBtn.textContent;
        deployBtn.textContent = '🗑️ Deploying...';

        try {
            // Get the FTP playfields path from settings
            const settingsData = await apiCall('/api/settings/playfields_path');
            if (!settingsData.success || !settingsData.value) {
                throw new Error('FTP playfields path not configured in Settings > FTP section');
            }
            
            const playfieldsPath = settingsData.value;
            const selectedPlayfieldsArray = Array.from(this.selectedPlayfields);
            const wipeTypes = this.getSelectedWipeTypes();
            
            // Generate wipe files
            const generateData = await apiCall('/api/wipe/generate-file', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    playfields: selectedPlayfieldsArray,
                    wipe_types: wipeTypes
                })
            });
            
            debugLog('Wipe file generation response:', generateData);

            if (!generateData.success) {
                throw new Error(generateData.message || 'Failed to generate wipe files');
            }
            
            // Deploy the generated files with playfields path
            const deployData = await apiCall('/api/wipe/deploy-files', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    playfields_path: playfieldsPath,
                    playfields: selectedPlayfieldsArray,
                    wipe_types: wipeTypes
                })
            });
            
            debugLog('Wipe file deployment response:', deployData);

            if (deployData.success) {
                const message = `✅ Wipe files deployed successfully! ${selectedPlayfieldsArray.length} playfields will be wiped on next restart/reload.`;
                this.setWipeStatus(message, false);
                showToast('Wipe files deployed successfully!', 'success');
                
                // Clear selection after successful deployment
                this.selectedPlayfields.clear();
                this.displayPlayfields();
                
            } else {
                throw new Error(deployData.message || 'Failed to deploy wipe files');
            }
            
        } catch (error) {
            console.error('Error deploying wipe files:', error);
            showToast('Error deploying wipe files: ' + error, 'error');
            this.setWipeStatus('Error during wipe deployment', false);
        } finally {
            this.isOperationRunning = false;
            deployBtn.disabled = false;
            loadBtn.disabled = false;
            deployBtn.textContent = originalDeployText;
        }
    },

    setWipeStatus(message, isLoading = false) {
        const statusElement = document.getElementById('wipeStatus');
        const statusText = document.getElementById('wipeStatusText');
        
        if (statusElement && statusText) {
            statusText.textContent = message;
            statusElement.style.display = 'block';
            
            if (isLoading) {
                statusElement.className = 'konsole-status-bar loading';
            } else {
                statusElement.className = 'konsole-status-bar';
            }
        }
    }
};

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    if (window.WipeManager) {
        window.WipeManager.init();
    }
});
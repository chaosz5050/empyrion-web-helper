// FILE LOCATION: /static/js/itemsconfig.js
/**
 * Items Config management functionality for Empyrion Web Helper
 * Handles ItemsConfig.ecf file editing with safety features
 * Copyright (c) 2025 Chaosz Software
 */

// Items Config Manager
window.ItemsConfigManager = {
    allItems: [],
    filteredItems: [],
    modifiedItems: {},
    isConnected: false,
    fileExists: false,
    fileInfo: null,
    
    // Pagination state
    currentPage: 1,
    pageSize: 50,
    totalPages: 1,
    
    init() {
        debugLog('ItemsConfig manager initialized');
        
        // Initialize pagination display
        this.updatePagination();
        this.updateUI();
    },
    
    async testConnection() {
        debugLog('Testing FTP connection and checking for ItemsConfig.ecf');
        
        const testBtn = document.getElementById('testConnectionBtn');
        const originalText = testBtn.textContent;
        testBtn.disabled = true;
        testBtn.textContent = '🔍 Checking...';
        
        try {
            const data = await apiCall('/itemsconfig/test', { method: 'POST' });
            debugLog('Connection test response:', data);
            
            if (data.success) {
                this.isConnected = data.connected;
                this.fileExists = data.file_exists;
                this.fileInfo = data.file_info;
                
                this.updateConnectionStatus();
                this.updateFileInfo();
                this.updateUI();
                
                if (this.isConnected && this.fileExists) {
                    showToast('✅ Connection successful! ItemsConfig.ecf found', 'success');
                } else if (this.isConnected && !this.fileExists) {
                    showToast('⚠️ Connected but ItemsConfig.ecf not found in config directory', 'error');
                } else {
                    showToast('❌ FTP connection failed. Check settings.', 'error');
                }
            } else {
                showToast(data.message || 'Connection test failed', 'error');
            }
        } catch (error) {
            console.error('Error testing connection:', error);
            showToast('Error testing connection: ' + error, 'error');
        } finally {
            testBtn.disabled = false;
            testBtn.textContent = originalText;
        }
    },
    
    async downloadFile() {
        if (!this.isConnected || !this.fileExists) {
            showToast('Cannot download: connection failed or file not found', 'error');
            return;
        }
        
        debugLog('Downloading ItemsConfig.ecf file');
        this.showLoading(true);
        
        const downloadBtn = document.getElementById('downloadFileBtn');
        const originalText = downloadBtn.textContent;
        downloadBtn.disabled = true;
        downloadBtn.textContent = '📥 Downloading...';
        
        try {
            const data = await apiCall('/itemsconfig/download', { method: 'POST' });
            debugLog('Download response:', data);
            
            if (data.success) {
                this.allItems = data.items || [];
                this.filteredItems = [...this.allItems];
                this.modifiedItems = {};
                this.currentPage = 1;
                
                this.updatePagination();
                this.updateTable();
                this.updateUI();
                
                showToast(`Downloaded ${this.allItems.length} items from ItemsConfig.ecf`, 'success');
            } else {
                showToast(data.message || 'Failed to download file', 'error');
            }
        } catch (error) {
            console.error('Error downloading file:', error);
            showToast('Error downloading file: ' + error, 'error');
        } finally {
            this.showLoading(false);
            downloadBtn.disabled = false;
            downloadBtn.textContent = originalText;
        }
    },

    async exportRawFile() {
        if (!this.isConnected || !this.fileExists) {
            showToast('Cannot export: connection failed or file not found', 'error');
            return;
        }
        
        debugLog('Exporting raw ItemsConfig.ecf file');
        
        const exportBtn = document.getElementById('exportRawFileBtn');
        const originalText = exportBtn.textContent;
        exportBtn.disabled = true;
        exportBtn.textContent = '📥 Exporting...';
        
        try {
            const data = await apiCall('/itemsconfig/export-raw', { method: 'POST' });
            debugLog('Export response:', data);
            
            if (data.success) {
                // Create download link and trigger download
                const blob = new Blob([data.content], { type: 'text/plain' });
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = data.filename || 'ItemsConfig.ecf';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
                
                showToast('Raw ItemsConfig.ecf file exported successfully', 'success');
            } else {
                showToast(data.message || 'Failed to export raw file', 'error');
            }
        } catch (error) {
            console.error('Error exporting raw file:', error);
            showToast('Error exporting raw file: ' + error, 'error');
        } finally {
            exportBtn.disabled = false;
            exportBtn.textContent = originalText;
        }
    },
    
    updateConnectionStatus() {
        const statusElement = document.getElementById('itemsconfigConnectionStatus');
        if (statusElement) {
            if (this.isConnected) {
                statusElement.textContent = '✅ Connected';
                statusElement.style.color = '#00cc66';
            } else {
                statusElement.textContent = '❌ Disconnected';
                statusElement.style.color = '#cc0000';
            }
        }
    },
    
    updateFileStatus() {
        const statusElement = document.getElementById('itemsconfigFileStatus');
        if (statusElement) {
            if (this.fileExists) {
                statusElement.textContent = '📄 ItemsConfig.ecf found';
                statusElement.style.color = '#00cc66';
            } else {
                statusElement.textContent = '❌ File not found';
                statusElement.style.color = '#cc0000';
            }
        }
    },
    
    updateFileInfo() {
        const fileInfoDiv = document.getElementById('itemsconfigFileInfo');
        if (!fileInfoDiv) return;
        
        if (this.fileInfo && this.fileExists) {
            fileInfoDiv.style.display = 'block';
            
            const sizeElement = document.getElementById('fileSize');
            const modifiedElement = document.getElementById('fileModified');
            const itemCountElement = document.getElementById('itemCount');
            
            if (sizeElement) sizeElement.textContent = `Size: ${this.fileInfo.size || 'Unknown'}`;
            if (modifiedElement) modifiedElement.textContent = `Modified: ${this.fileInfo.modified || 'Unknown'}`;
            if (itemCountElement) itemCountElement.textContent = `Items: ${this.allItems.length || 'Unknown'}`;
        } else {
            fileInfoDiv.style.display = 'none';
        }
    },
    
    updateUI() {
        // Update button states
        const downloadBtn = document.getElementById('downloadFileBtn');
        const exportBtn = document.getElementById('exportRawFileBtn');
        const saveBtn = document.getElementById('saveChangesBtn');
        const uploadBtn = document.getElementById('uploadFileBtn');
        
        if (downloadBtn) downloadBtn.disabled = !this.isConnected || !this.fileExists;
        if (exportBtn) exportBtn.disabled = !this.isConnected || !this.fileExists;
        if (saveBtn) saveBtn.disabled = Object.keys(this.modifiedItems).length === 0;
        if (uploadBtn) uploadBtn.disabled = Object.keys(this.modifiedItems).length === 0;
        
        // Show/hide panels
        const filtersPanel = document.getElementById('itemsconfigFilters');
        const actionsPanel = document.getElementById('itemsconfigActions');
        const tableContainer = document.getElementById('itemsconfigTableContainer');
        
        const showPanels = this.allItems.length > 0;
        if (filtersPanel) filtersPanel.style.display = showPanels ? 'block' : 'none';
        if (actionsPanel) actionsPanel.style.display = showPanels ? 'block' : 'none';
        if (tableContainer) tableContainer.style.display = showPanels ? 'block' : 'none';
        
        this.updateConnectionStatus();
        this.updateFileStatus();
        this.updateFileInfo();
    },
    
    updateTable() {
        const tableBody = document.getElementById('itemsconfigTableBody');
        if (!tableBody) return;
        
        if (this.filteredItems.length === 0) {
            const message = this.allItems.length === 0 
                ? 'Connect to server and download ItemsConfig.ecf to start editing'
                : 'No items match the current filters';
            tableBody.innerHTML = `
                <tr>
                    <td colspan="9" class="empty-state">${message}</td>
                </tr>
            `;
            return;
        }
        
        // Calculate pagination
        const startIndex = (this.currentPage - 1) * this.pageSize;
        const endIndex = startIndex + this.pageSize;
        const pageItems = this.filteredItems.slice(startIndex, endIndex);
        
        let html = '';
        pageItems.forEach(item => {
            const isTemplate = item.type === 'template';
            const isModified = this.modifiedItems[item.id];
            const rowClass = isModified ? 'modified-row' : '';
            
            html += `
                <tr class="${rowClass}">
                    <td><span class="item-type ${item.type}">${item.type}</span></td>
                    <td class="item-id">${escapeHtml(item.id)}</td>
                    <td class="item-name">${escapeHtml(item.name)}</td>
                    <td class="editable-cell" data-field="stacksize" data-id="${item.id}">${item.stacksize || '-'}</td>
                    <td class="editable-cell" data-field="mass" data-id="${item.id}">${item.mass || '-'}</td>
                    <td class="editable-cell" data-field="volume" data-id="${item.id}">${item.volume || '-'}</td>
                    <td class="editable-cell" data-field="marketprice" data-id="${item.id}">${item.marketprice || '-'}</td>
                    <td class="item-template">${escapeHtml(item.template || '-')}</td>
                    <td class="item-status">${isModified ? '📝 Modified' : '✅ Original'}</td>
                </tr>
            `;
        });
        
        tableBody.innerHTML = html;
        
        // Add click handlers for editable cells
        this.attachEditHandlers();
    },
    
    attachEditHandlers() {
        const editableCells = document.querySelectorAll('.editable-cell');
        editableCells.forEach(cell => {
            cell.addEventListener('click', (e) => this.editCell(e.target));
        });
    },
    
    editCell(cell) {
        if (cell.querySelector('input')) return; // Already editing
        
        const field = cell.dataset.field;
        const itemId = cell.dataset.id;
        const currentValue = cell.textContent.trim();
        
        // Create input element
        const input = document.createElement('input');
        input.type = field === 'stacksize' || field === 'marketprice' ? 'number' : 'text';
        input.value = currentValue === '-' ? '' : currentValue;
        input.className = 'cell-editor';
        
        // Replace cell content with input
        cell.innerHTML = '';
        cell.appendChild(input);
        input.focus();
        input.select();
        
        // Handle save on blur or enter
        const saveValue = () => {
            const newValue = input.value.trim();
            this.updateItemValue(itemId, field, newValue);
            this.updateTable(); // Refresh the table
        };
        
        input.addEventListener('blur', saveValue);
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                saveValue();
            }
        });
    },
    
    updateItemValue(itemId, field, value) {
        // Find the item
        const item = this.allItems.find(i => i.id === itemId);
        if (!item) return;
        
        // Track modification
        if (!this.modifiedItems[itemId]) {
            this.modifiedItems[itemId] = { ...item };
        }
        
        // Update the value
        this.modifiedItems[itemId][field] = value;
        
        // Update in main array too
        item[field] = value;
        
        debugLog(`Updated ${itemId}.${field} = ${value}`);
        this.updateUI();
    },
    
    // Pagination methods (similar to entities)
    updatePagination() {
        this.totalPages = Math.ceil(this.filteredItems.length / this.pageSize);
        this.updatePaginationInfo();
        this.updatePaginationButtons();
    },
    
    updatePaginationInfo() {
        const infoText = `Page ${this.currentPage} of ${this.totalPages} (${this.filteredItems.length} items)`;
        
        const pageInfo = document.getElementById('itemsconfigPageInfo');
        const pageInfoBottom = document.getElementById('itemsconfigPageInfoBottom');
        
        if (pageInfo) pageInfo.textContent = infoText;
        if (pageInfoBottom) pageInfoBottom.textContent = infoText;
    },
    
    updatePaginationButtons() {
        const buttons = [
            ['itemsconfigFirstBtn', 'itemsconfigFirstBtnBottom'],
            ['itemsconfigPrevBtn', 'itemsconfigPrevBtnBottom'],
            ['itemsconfigNextBtn', 'itemsconfigNextBtnBottom'],
            ['itemsconfigLastBtn', 'itemsconfigLastBtnBottom']
        ];
        
        const isFirstPage = this.currentPage === 1;
        const isLastPage = this.currentPage >= this.totalPages;
        
        buttons[0].forEach(id => {
            const btn = document.getElementById(id);
            if (btn) btn.disabled = isFirstPage;
        });
        
        buttons[1].forEach(id => {
            const btn = document.getElementById(id);
            if (btn) btn.disabled = isFirstPage;
        });
        
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
        this.updateTable();
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
        const pageSizeSelect = document.getElementById('itemsconfigPageSize');
        if (pageSizeSelect) {
            this.pageSize = parseInt(pageSizeSelect.value);
            this.currentPage = 1;
            this.updatePagination();
            this.updateTable();
        }
    },
    
    clearFilters() {
        // Reset all filter inputs
        const filterIds = ['filterItemId', 'filterItemName', 'filterItemTemplate', 'filterItemType'];
        filterIds.forEach(id => {
            const element = document.getElementById(id);
            if (element) element.value = '';
        });
        
        // Reset filtered items
        this.filteredItems = [...this.allItems];
        this.currentPage = 1;
        this.updatePagination();
        this.updateTable();
    },
    
    showLoading(show) {
        const loadingIndicator = document.getElementById('itemsconfigLoadingIndicator');
        if (loadingIndicator) {
            if (show) {
                loadingIndicator.classList.add('show');
            } else {
                loadingIndicator.classList.remove('show');
            }
        }
    },
    
    // Placeholder methods for future implementation
    saveChanges() {
        showToast('Save changes functionality coming soon!', 'info');
    },
    
    uploadFile() {
        showToast('Upload to server functionality coming soon!', 'info');
    },
    
    restoreFromBackup() {
        showToast('Restore from backup functionality coming soon!', 'info');
    },
    
    restoreOriginal() {
        showToast('Restore original functionality coming soon!', 'info');
    }
};

// Global functions for HTML onclick handlers
function testItemsConfigConnection() {
    window.ItemsConfigManager.testConnection();
}

function downloadItemsConfig() {
    window.ItemsConfigManager.downloadFile();
}
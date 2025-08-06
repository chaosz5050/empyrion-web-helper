/**
 * FTP Browser Modal - Reusable FTP directory browser component
 * Copyright (c) 2025 Chaosz Software
 */

class FtpBrowserModal {
    constructor() {
        this.isOpen = false;
        this.currentDirectory = '/';
        this.onPathSelected = null;
        this.modal = null;
        
        this.createModal();
        this.bindEvents();
    }

    createModal() {
        // Create modal HTML structure
        const modalHTML = `
            <div id="ftpBrowserModal" class="ftp-modal" style="display: none;">
                <div class="ftp-modal-dialog">
                    <div class="ftp-modal-content">
                        <div class="ftp-modal-header">
                            <h4 class="ftp-modal-title">📁 Browse FTP Directory</h4>
                            <button type="button" class="ftp-close-btn" aria-label="Close">&times;</button>
                        </div>
                        <div class="ftp-modal-body">
                            <div class="ftp-path-display">
                                <span class="ftp-path-label">Path:</span>
                                <span id="ftpCurrentPath">/</span>
                            </div>
                            <div id="ftpBrowserContent" class="ftp-browser-content">
                                <div class="ftp-loading">🔄 Connecting to FTP server...</div>
                            </div>
                        </div>
                        <div class="ftp-modal-footer">
                            <div class="ftp-selected-path">
                                <span class="ftp-selected-label">Selected:</span>
                                <span id="ftpSelectedPath">None</span>
                            </div>
                            <div class="ftp-modal-buttons">
                                <button type="button" class="konsole-btn konsole-btn-secondary" id="ftpCancelBtn">Cancel</button>
                                <button type="button" class="konsole-btn konsole-btn-primary" id="ftpSelectBtn" disabled>Select Path</button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Add modal to body
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        this.modal = document.getElementById('ftpBrowserModal');
        
        // Add CSS styles
        this.addStyles();
    }

    addStyles() {
        const styles = `
            <style id="ftp-browser-modal-styles">
                .ftp-modal {
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: rgba(0, 0, 0, 0.7);
                    z-index: 2000;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }
                
                .ftp-modal-dialog {
                    width: 600px;
                    max-width: 95vw;
                    max-height: 90vh;
                    background: #23272e;
                    border-radius: 10px;
                    box-shadow: 0 0 32px rgba(0, 0, 0, 0.7);
                    display: flex;
                    flex-direction: column;
                }
                
                .ftp-modal-content {
                    display: flex;
                    flex-direction: column;
                    height: 100%;
                    max-height: 90vh;
                }
                
                .ftp-modal-header {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    padding: 1.5rem 2rem 1rem 2rem;
                    border-bottom: 1px solid #444b5a;
                }
                
                .ftp-modal-title {
                    color: #2196f3;
                    font-weight: 700;
                    margin: 0;
                    font-size: 1.2em;
                }
                
                .ftp-close-btn {
                    background: none;
                    border: none;
                    color: #e2e6ee;
                    font-size: 1.8em;
                    cursor: pointer;
                    padding: 0;
                    width: 30px;
                    height: 30px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    border-radius: 4px;
                    transition: background 0.2s;
                }
                
                .ftp-close-btn:hover {
                    background: #444b5a;
                }
                
                .ftp-modal-body {
                    flex: 1;
                    padding: 1.5rem 2rem;
                    display: flex;
                    flex-direction: column;
                    min-height: 0;
                }
                
                .ftp-path-display {
                    display: flex;
                    align-items: center;
                    gap: 0.5rem;
                    margin-bottom: 1rem;
                    padding: 0.75rem;
                    background: #181a20;
                    border-radius: 4px;
                    border: 1px solid #444b5a;
                }
                
                .ftp-path-label {
                    color: #90caf9;
                    font-weight: 600;
                }
                
                #ftpCurrentPath {
                    color: #e2e6ee;
                    font-family: monospace;
                    word-break: break-all;
                }
                
                .ftp-browser-content {
                    flex: 1;
                    border: 1px solid #444b5a;
                    border-radius: 4px;
                    background: #181a20;
                    overflow-y: auto;
                    min-height: 300px;
                    max-height: 400px;
                }
                
                .ftp-loading {
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    height: 100%;
                    color: #90caf9;
                    font-size: 1.1em;
                }
                
                .ftp-item {
                    display: flex;
                    align-items: center;
                    gap: 0.75rem;
                    padding: 0.75rem 1rem;
                    border-bottom: 1px solid #2a2e37;
                    cursor: pointer;
                    transition: background 0.2s;
                }
                
                .ftp-item:hover {
                    background: #2a2e37;
                }
                
                .ftp-item:last-child {
                    border-bottom: none;
                }
                
                .ftp-item-icon {
                    font-size: 1.2em;
                    width: 20px;
                    text-align: center;
                }
                
                .ftp-item-name {
                    flex: 1;
                    color: #e2e6ee;
                    font-family: monospace;
                    word-break: break-all;
                }
                
                .ftp-item.directory .ftp-item-name {
                    color: #90caf9;
                    font-weight: 500;
                }
                
                .ftp-modal-footer {
                    padding: 1rem 2rem 1.5rem 2rem;
                    border-top: 1px solid #444b5a;
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    gap: 1rem;
                }
                
                .ftp-selected-path {
                    display: flex;
                    align-items: center;
                    gap: 0.5rem;
                    flex: 1;
                    min-width: 0;
                }
                
                .ftp-selected-label {
                    color: #90caf9;
                    font-weight: 600;
                    white-space: nowrap;
                }
                
                #ftpSelectedPath {
                    color: #e2e6ee;
                    font-family: monospace;
                    word-break: break-all;
                }
                
                .ftp-modal-buttons {
                    display: flex;
                    gap: 0.75rem;
                }
                
                /* Mobile responsive */
                @media (max-width: 768px) {
                    .ftp-modal-dialog {
                        width: 100%;
                        height: 100%;
                        max-width: none;
                        max-height: none;
                        border-radius: 0;
                    }
                    
                    .ftp-modal-footer {
                        flex-direction: column;
                        align-items: stretch;
                        gap: 1rem;
                    }
                    
                    .ftp-modal-buttons {
                        justify-content: center;
                    }
                }
            </style>
        `;
        
        document.head.insertAdjacentHTML('beforeend', styles);
    }

    bindEvents() {
        // Close button
        document.addEventListener('click', (e) => {
            if (e.target.matches('.ftp-close-btn') || e.target.matches('#ftpCancelBtn')) {
                this.close();
            }
        });

        // Select button
        document.addEventListener('click', (e) => {
            if (e.target.matches('#ftpSelectBtn')) {
                this.selectCurrentPath();
            }
        });

        // Click outside to close
        document.addEventListener('click', (e) => {
            if (e.target.matches('#ftpBrowserModal')) {
                this.close();
            }
        });

        // Escape key to close
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isOpen) {
                this.close();
            }
        });
    }

    open(callback) {
        this.onPathSelected = callback;
        this.isOpen = true;
        this.modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
        
        // Load initial directory
        this.loadDirectory('/');
    }

    close() {
        this.isOpen = false;
        this.modal.style.display = 'none';
        document.body.style.overflow = '';
        this.onPathSelected = null;
        
        // Reset state
        this.currentDirectory = '/';
        document.getElementById('ftpSelectedPath').textContent = 'None';
        document.getElementById('ftpSelectBtn').disabled = true;
    }

    async loadDirectory(path) {
        const contentDiv = document.getElementById('ftpBrowserContent');
        const pathSpan = document.getElementById('ftpCurrentPath');
        
        contentDiv.innerHTML = '<div class="ftp-loading">🔄 Loading from FTP server...</div>';
        pathSpan.textContent = path;
        this.currentDirectory = path;

        try {
            const data = await this.apiCall('/api/ftp/browse', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path: path })
            });

            if (data.success) {
                this.renderFileList(data.files, path);
            } else {
                throw new Error(data.message || 'Failed to browse directory');
            }
        } catch (error) {
            console.error('Error loading directory:', error);
            contentDiv.innerHTML = `
                <div class="ftp-loading" style="color: var(--accent-red);">
                    ❌ Error: ${error.message || 'Failed to load directory'}
                </div>
            `;
        }
    }

    renderFileList(files, currentPath) {
        const contentDiv = document.getElementById('ftpBrowserContent');
        
        if (!files || files.length === 0) {
            contentDiv.innerHTML = '<div class="ftp-loading">📂 Empty directory</div>';
            return;
        }

        let html = '';

        // Add parent directory link if not at root
        if (currentPath !== '/') {
            const parentPath = currentPath.split('/').slice(0, -1).join('/') || '/';
            html += `
                <div class="ftp-item directory" data-path="${parentPath}" data-type="directory">
                    <span class="ftp-item-icon">📁</span>
                    <span class="ftp-item-name">.. (Parent Directory)</span>
                </div>
            `;
        }

        // Sort files: directories first, then files
        const sorted = files.sort((a, b) => {
            if (a.type === 'directory' && b.type !== 'directory') return -1;
            if (a.type !== 'directory' && b.type === 'directory') return 1;
            return a.name.localeCompare(b.name);
        });

        // Add files and directories
        sorted.forEach(file => {
            const icon = file.type === 'directory' ? '📁' : '📄';
            const fullPath = currentPath === '/' ? `/${file.name}` : `${currentPath}/${file.name}`;
            
            html += `
                <div class="ftp-item ${file.type}" data-path="${fullPath}" data-type="${file.type}">
                    <span class="ftp-item-icon">${icon}</span>
                    <span class="ftp-item-name">${file.name}</span>
                </div>
            `;
        });

        contentDiv.innerHTML = html;

        // Add click handlers
        contentDiv.querySelectorAll('.ftp-item').forEach(item => {
            item.addEventListener('click', () => {
                const path = item.dataset.path;
                const type = item.dataset.type;
                
                if (type === 'directory') {
                    this.loadDirectory(path);
                } else {
                    this.selectPath(path);
                }
            });
        });
    }

    selectPath(path) {
        document.getElementById('ftpSelectedPath').textContent = path;
        document.getElementById('ftpSelectBtn').disabled = false;
        this.selectedPath = path;
    }

    selectCurrentPath() {
        if (this.selectedPath && this.onPathSelected) {
            this.onPathSelected(this.selectedPath);
            this.close();
        }
    }

    // Utility method for API calls
    async apiCall(url, options = {}) {
        try {
            const response = await fetch(url, options);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            return data;
            
        } catch (error) {
            console.error(`API call to ${url} failed:`, error);
            throw error;
        }
    }
}

// Create global instance
window.ftpBrowserModal = new FtpBrowserModal();
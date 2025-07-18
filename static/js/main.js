// FILE LOCATION: /static/js/main.js
/**
 * Main application initialization for Empyrion Web Helper
 * Copyright (c) 2025 Chaosz Software
 */

// Application initialization
document.addEventListener('DOMContentLoaded', function() {
    debugLog('Empyrion Web Helper v0.4.1 - Background Service Architecture');
    checkAndShowCredentialConfigModal();
    // Initialize all managers
    initializeApplication();
    // Auto-connect is now handled by the server-side background service
    // No manual connection needed from frontend
});

function checkAndShowCredentialConfigModal() {
    fetch('/api/credentials/status').then(r => r.json()).then(status => {
        // Also check monitoring setting (update_interval)
        fetch('/api/settings/monitoring').then(r2 => r2.json()).then(settings => {
            let needsModal = false;
            if (!status.rcon || !status.ftp || !status.server_host || !status.server_port) needsModal = true;
            if (!settings.update_interval || settings.update_interval < 10) needsModal = true;
            if (needsModal) showCredentialConfigModal(settings);
        }).catch(() => showCredentialConfigModal({update_interval: 20}));
    }).catch(() => showCredentialConfigModal({update_interval: 20}));
}

function showCredentialConfigModal(settings) {
    const modal = document.getElementById('credentialConfigModal');
    const form = document.getElementById('credentialConfigForm');
    const errorsDiv = document.getElementById('credentialConfigErrors');
    
    // Pre-fill update interval if available
    if (settings && settings.update_interval) {
        form.update_interval.value = settings.update_interval;
    }
    
    // Try to pre-populate existing values
    fetch('/api/credentials/current').then(r => r.json()).then(data => {
        if (data.server_host) form.server_host.value = data.server_host;
        if (data.server_port) form.server_port.value = data.server_port;
        if (data.ftp_host) form.ftp_host.value = data.ftp_host;
        if (data.ftp_remote_log_path) form.ftp_remote_log_path.value = data.ftp_remote_log_path;
        if (data.ftp_user) form.ftp_user.value = data.ftp_user;
    }).catch(() => {
        // Set defaults if no existing values
        form.server_host.value = '';
        form.server_port.value = '30004';
        form.ftp_host.value = '';
        form.ftp_remote_log_path.value = '';
        form.ftp_user.value = '';
    });
    
    modal.style.display = 'block';
    document.body.style.overflow = 'hidden';
    
    form.onsubmit = function(e) {
        e.preventDefault();
        errorsDiv.style.display = 'none';
        errorsDiv.innerHTML = '';
        
        const server_host = form.server_host.value.trim();
        const server_port = form.server_port.value.trim();
        const rcon_password = form.rcon_password.value.trim();
        const ftp_host = form.ftp_host.value.trim();
        const ftp_remote_log_path = form.ftp_remote_log_path.value.trim();
        const ftp_user = form.ftp_user.value.trim();
        const ftp_password = form.ftp_password.value.trim();
        const update_interval = form.update_interval.value.trim();
        
        let errors = [];
        
        // Validate server settings
        if (!server_host || server_host.length < 3) errors.push('Server host is required (minimum 3 characters).');
        if (isNaN(server_port) || parseInt(server_port) < 1 || parseInt(server_port) > 65535) errors.push('Server port must be between 1 and 65535.');
        
        // Validate RCON
        if (rcon_password.length < 4) errors.push('RCON password must be at least 4 characters.');
        
        // Validate FTP
        if (!ftp_host || ftp_host.length < 3) errors.push('FTP host is required (minimum 3 characters).');
        if (!ftp_remote_log_path || ftp_remote_log_path.length < 5) errors.push('FTP remote log path is required (minimum 5 characters).');
        if (ftp_user.length < 3) errors.push('FTP username must be at least 3 characters.');
        if (ftp_password.length < 4) errors.push('FTP password must be at least 4 characters.');
        
        // Validate monitoring
        if (isNaN(update_interval) || parseInt(update_interval) < 10) errors.push('Update interval must be at least 10 seconds.');
        
        if (errors.length) {
            errorsDiv.innerHTML = errors.join('<br>');
            errorsDiv.style.display = 'block';
            return;
        }
        
        // Save all settings
        fetch('/api/credentials/set', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                server_host,
                server_port: parseInt(server_port),
                rcon_password,
                ftp_host,
                ftp_remote_log_path,
                ftp_user,
                ftp_password
            })
        }).then(r => {
            if (!r.ok) return r.json().then(j => {throw j;});
            // Save monitoring setting
            return fetch('/api/settings/monitoring', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({update_interval: parseInt(update_interval)})
            });
        }).then(() => {
            modal.style.display = 'none';
            document.body.style.overflow = '';
            showToast('Settings saved successfully! Background service will connect automatically.', 'success');
            
            // Small delay then reload page to restart background service
            setTimeout(() => {
                window.location.reload();
            }, 2000);
        }).catch(err => {
            let msg = err && err.errors ? Object.values(err.errors).join('<br>') : 'Failed to save settings.';
            errorsDiv.innerHTML = msg;
            errorsDiv.style.display = 'block';
        });
    };
    
    // Prevent closing modal by clicking outside
    modal.onclick = function(e) {
        if (e.target === modal) e.stopPropagation();
    };
}

function initializeApplication() {
    // Initialize connection manager
    if (window.ConnectionManager) {
        window.ConnectionManager.init();
    }
    
    // Initialize players manager
    if (window.PlayersManager) {
        window.PlayersManager.init();
        window.PlayersManager.loadPlayersFromDatabase();
    }
    
    // Initialize entities manager
    if (window.EntitiesManager) {
        window.EntitiesManager.init();
    }
    
    // Initialize messaging manager
    if (window.MessagingManager) {
        window.MessagingManager.init();
    }
    
    // Initialize logs manager
    if (window.LogsManager) {
        window.LogsManager.init();
    }
    
    debugLog('All managers initialized');
}

// Clean up on page unload
window.addEventListener('beforeunload', function() {
    if (window.ConnectionManager) {
        window.ConnectionManager.stopAutoRefresh();
    }
});

// Global error handler
window.addEventListener('error', function(event) {
    console.error('Global error:', event.error);
    showToast('An unexpected error occurred', 'error');
});

// Handle unhandled promise rejections
window.addEventListener('unhandledrejection', function(event) {
    console.error('Unhandled promise rejection:', event.reason);
    showToast('A network error occurred', 'error');
});
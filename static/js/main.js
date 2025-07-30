// FILE LOCATION: /static/js/main.js
/**
 * Main application initialization for Empyrion Web Helper
 * Copyright (c) 2025 Chaosz Software
 */

// Client-side error logging to server
function logClientError(type, errorData) {
    try {
        fetch('/api/log/client-error', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                type: type,
                error: errorData,
                url: window.location.href,
                userAgent: navigator.userAgent,
                timestamp: new Date().toISOString()
            })
        }).catch(() => {}); // Silent fail if logging fails
    } catch (e) {
        // Silent fail - don't create infinite error loops
    }
}

// Capture JavaScript errors
window.addEventListener('error', function(event) {
    logClientError('JavaScript Error', {
        message: event.message,
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno,
        stack: event.error?.stack
    });
});

// Capture unhandled promise rejections
window.addEventListener('unhandledrejection', function(event) {
    logClientError('Unhandled Promise Rejection', {
        reason: event.reason,
        stack: event.reason?.stack
    });
});

// Suppress ResizeObserver errors globally (harmless browser warnings)
let resizeObserverErrorDebounce = null;
const originalConsoleError = console.error;
console.error = function(...args) {
    // Suppress ResizeObserver loop completed errors
    if (args[0] && args[0].includes && args[0].includes('ResizeObserver loop completed')) {
        clearTimeout(resizeObserverErrorDebounce);
        resizeObserverErrorDebounce = setTimeout(() => {
            // Only log once per second to avoid spam
        }, 1000);
        return;
    }
    originalConsoleError.apply(console, args);
};

// Application initialization
document.addEventListener('DOMContentLoaded', function() {
    debugLog('Empyrion Web Helper v0.5.0 - Background Service Architecture');
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
            if (!status.rcon || !status.ftp) needsModal = true;
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
    modal.style.display = 'block';
    document.body.style.overflow = 'hidden';
    form.onsubmit = function(e) {
        e.preventDefault();
        errorsDiv.style.display = 'none';
        errorsDiv.innerHTML = '';
        const rcon_password = form.rcon_password.value.trim();
        const ftp_user = form.ftp_user.value.trim();
        const ftp_password = form.ftp_password.value.trim();
        const ftp_host = form.ftp_host.value.trim();
        const ftp_remote_log_path = form.ftp_remote_log_path.value.trim();
        const ftp_mod_path = form.ftp_mod_path.value.trim();
        const server_host = form.server_host.value.trim();
        const server_port = form.server_port.value.trim();
        const update_interval = form.update_interval.value.trim();
        let errors = [];
        if (rcon_password.length < 4) errors.push('RCON password must be at least 4 characters.');
        if (ftp_user.length < 3) errors.push('FTP username must be at least 3 characters.');
        if (ftp_password.length < 4) errors.push('FTP password must be at least 4 characters.');
        if (!ftp_host) errors.push('FTP host is required.');
        if (!ftp_remote_log_path) errors.push('FTP remote log path is required.');
        if (!server_host) errors.push('Server host is required.');
        if (!server_port || isNaN(server_port)) errors.push('Server port must be a valid number.');
        if (isNaN(update_interval) || parseInt(update_interval) < 10) errors.push('Update interval must be at least 10 seconds.');
        if (errors.length) {
            errorsDiv.innerHTML = errors.join('<br>');
            errorsDiv.style.display = 'block';
            return;
        }
        // Save credentials
        fetch('/api/credentials/set', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                rcon_password,
                ftp_user,
                ftp_password,
                ftp_host,
                ftp_remote_log_path,
                ftp_mod_path,
                server_host,
                server_port
            })
        }).then(r => {
            if (!r.ok) return r.json().then(j => {throw j;});
            // Save monitoring setting
            return fetch('/api/settings/monitoring', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({update_interval})
            });
        }).then(() => {
            modal.style.display = 'none';
            document.body.style.overflow = '';
            showToast('Settings saved successfully', 'success');
            window.location.reload();
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
    
    // Initialize items config manager
    if (window.ItemsConfigManager) {
        window.ItemsConfigManager.init();
    }
    
    // Initialize messaging manager
    if (window.MessagingManager) {
        window.MessagingManager.init();
    }
    
    // Initialize logs manager
    if (window.LogsManager) {
        window.LogsManager.init();
    }
    
    // Initialize settings manager
    if (window.SettingsManager) {
        window.SettingsManager.init();
    }
    
    debugLog('All managers initialized');
}

// ===============================
// Settings Tabs and Dirty State Logic
// ===============================

document.addEventListener("DOMContentLoaded", function () {
  const tabBtns = document.querySelectorAll('.settings-tab-btn');
  const tabPanels = document.querySelectorAll('.settings-tab-panel');
  let currentTab = "server";
  let dirtyTabs = { server: false, ftp: false, misc: false };

  // Mark tab as dirty on any input change
  tabPanels.forEach(panel => {
    panel.addEventListener('input', () => {
      dirtyTabs[panel.dataset.tab] = true;
    });
  });

  // Tab switching logic
  tabBtns.forEach(btn => {
    btn.addEventListener('click', function () {
      const target = btn.dataset.tab;
      if (target === currentTab) return;

      // Warn if leaving dirty tab
      if (dirtyTabs[currentTab]) {
        if (!confirm("You have unsaved changes. Save before switching tabs?")) {
          return;
        }
      }

      // Switch active tab
      tabBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      tabPanels.forEach(panel => {
        if (panel.dataset.tab === target) {
          panel.classList.add('active');
        } else {
          panel.classList.remove('active');
        }
      });
      currentTab = target;
    });
  });

  // Save button logic (reset dirty state)
  tabPanels.forEach(panel => {
    const tab = panel.dataset.tab;
    const saveBtn = document.getElementById(`saveSettingsBtn-${tab}`);
    if (saveBtn) {
      saveBtn.addEventListener('click', function () {
        // You can replace this with your actual save logic
        // Example: saveSettings(tab);
        dirtyTabs[tab] = false;
        alert("Settings saved!");
      });
    }
  });
});

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
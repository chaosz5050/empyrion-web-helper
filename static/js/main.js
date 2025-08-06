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
    // Initialize all managers
    initializeApplication();
    // Auto-connect is now handled by the server-side background service
    // No manual connection needed from frontend
});

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
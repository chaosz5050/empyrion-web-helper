// FILE LOCATION: /static/js/main.js
/**
 * Main application initialization for Empyrion Web Helper
 * Copyright (c) 2025 Chaosz Software
 */

// Application initialization
document.addEventListener('DOMContentLoaded', function() {
    debugLog('Empyrion Web Helper v0.4.1 - Background Service Architecture');
    
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
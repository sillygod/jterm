/**
 * Desktop-specific JavaScript for Tauri integration
 * Handles connection to Python backend and Tauri API initialization
 */

// Tauri API will be available at window.__TAURI__
const { invoke } = window.__TAURI__ || {};

// Backend connection state
let backendPort = null;
let backendReady = false;
let retryCount = 0;
const MAX_RETRIES = 30;
const RETRY_INTERVAL = 1000; // 1 second

/**
 * Update loading status message
 */
function updateLoadingStatus(message) {
    const statusElement = document.getElementById('loading-status');
    if (statusElement) {
        statusElement.textContent = message;
    }
    console.log('[Desktop] ' + message);
}

/**
 * Show error screen with message
 */
function showError(message) {
    const loadingScreen = document.getElementById('loading-screen');
    const errorScreen = document.getElementById('error-screen');
    const errorMessage = document.getElementById('error-message');

    if (loadingScreen) loadingScreen.style.display = 'none';
    if (errorScreen) errorScreen.style.display = 'flex';
    if (errorMessage) errorMessage.textContent = message;

    console.error('[Desktop] ' + message);
}

/**
 * Connect to Python backend
 */
async function connectToBackend() {
    try {
        // Get app info from Tauri backend
        updateLoadingStatus('Getting app info...');
        const appInfo = await invoke('app_ready');

        console.log('[Desktop] App info:', appInfo);
        backendPort = appInfo.backend_port;

        if (!backendPort) {
            throw new Error('Backend port not available');
        }

        // Check backend health
        updateLoadingStatus(`Connecting to backend on port ${backendPort}...`);
        const backendUrl = `http://localhost:${backendPort}`;

        const response = await fetch(`${backendUrl}/health`);
        if (!response.ok) {
            throw new Error(`Backend health check failed: ${response.status}`);
        }

        const healthData = await response.json();
        console.log('[Desktop] Backend health check:', healthData);

        // Backend is ready, load the UI
        backendReady = true;
        loadBackendUI();

    } catch (error) {
        console.error('[Desktop] Connection error:', error);

        retryCount++;
        if (retryCount < MAX_RETRIES) {
            updateLoadingStatus(`Waiting for backend... (attempt ${retryCount}/${MAX_RETRIES})`);
            setTimeout(connectToBackend, RETRY_INTERVAL);
        } else {
            showError('Failed to connect to backend server after multiple attempts. Please try restarting the application.');
        }
    }
}

/**
 * Load the Python backend UI in iframe
 */
function loadBackendUI() {
    const iframe = document.getElementById('main-frame');
    const loadingScreen = document.getElementById('loading-screen');

    if (!iframe || !backendPort) {
        showError('Failed to initialize UI components');
        return;
    }

    updateLoadingStatus('Loading terminal interface...');

    // Set iframe source to backend
    iframe.src = `http://localhost:${backendPort}/`;

    // Wait for iframe to load
    iframe.onload = function() {
        console.log('[Desktop] Backend UI loaded successfully');

        // Hide loading screen, show iframe
        if (loadingScreen) loadingScreen.style.display = 'none';
        iframe.style.display = 'block';

        // Inject desktop-specific enhancements into iframe
        injectDesktopEnhancements();
    };

    iframe.onerror = function() {
        showError('Failed to load backend UI');
    };
}

/**
 * Inject desktop-specific enhancements into the iframe
 */
function injectDesktopEnhancements() {
    try {
        const iframe = document.getElementById('main-frame');
        if (!iframe || !iframe.contentWindow) return;

        // Make Tauri API available to iframe content
        iframe.contentWindow.__TAURI_DESKTOP__ = {
            invoke: invoke,
            isDesktop: true,
            platform: navigator.platform,
        };

        console.log('[Desktop] Desktop enhancements injected');
    } catch (error) {
        console.warn('[Desktop] Could not inject enhancements:', error);
        // Non-critical error, UI should still work
    }
}

/**
 * Handle retry button click
 */
document.getElementById('retry-button')?.addEventListener('click', () => {
    const errorScreen = document.getElementById('error-screen');
    const loadingScreen = document.getElementById('loading-screen');

    if (errorScreen) errorScreen.style.display = 'none';
    if (loadingScreen) loadingScreen.style.display = 'flex';

    retryCount = 0;
    connectToBackend();
});

/**
 * Handle quit button click
 */
document.getElementById('quit-button')?.addEventListener('click', async () => {
    try {
        await invoke('quit_app', { force: true });
    } catch (error) {
        console.error('[Desktop] Failed to quit:', error);
        window.close();
    }
});

/**
 * Initialize desktop application
 */
async function initDesktop() {
    console.log('[Desktop] Initializing jterm desktop application...');

    // Check if Tauri API is available
    if (!window.__TAURI__) {
        showError('Tauri API not available. Please ensure you are running the desktop application.');
        return;
    }

    // Start connecting to backend
    connectToBackend();
}

// Start initialization when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDesktop);
} else {
    initDesktop();
}

// Handle window close - cleanup
window.addEventListener('beforeunload', async () => {
    console.log('[Desktop] Application closing...');
    // Cleanup will be handled by Tauri backend
});

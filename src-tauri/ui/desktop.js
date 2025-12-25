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
 * Handle backend ready event
 */
async function onBackendReady(event) {
    try {
        const { port, url } = event.payload;
        console.log('[Desktop] Backend ready:', { port, url });

        backendPort = port;
        backendReady = true;

        // Load backend UI in iframe
        loadBackendUI();
    } catch (error) {
        console.error('[Desktop] Error handling backend ready:', error);
        showError('Failed to load backend UI: ' + error.message);
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

        // Test postMessage communication
        setTimeout(() => {
            console.log('[Desktop] Testing postMessage to iframe...');
            iframe.contentWindow.postMessage({
                type: 'desktop-menu-event',
                menuId: 'test'
            }, '*');
        }, 1000);
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
            clipboardManager: window.__TAURI__.clipboardManager,
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

    const { listen } = window.__TAURI__.event;

    // Setup menu event listeners
    await setupMenuListeners();

    // Listen for backend ready event
    await listen('backend-ready', onBackendReady);
    console.log('[Desktop] Waiting for backend to start...');

    // Listen for messages from iframe (for copy operation)
    window.addEventListener('message', async (event) => {
        if (event.data?.type === 'clipboard-write' && event.data?.text) {
            try {
                const clipboardManager = window.__TAURI__.clipboardManager;
                await clipboardManager.writeText(event.data.text);
                console.log('[Desktop] Wrote', event.data.text.length, 'chars to clipboard');
            } catch (error) {
                console.error('[Desktop] Failed to write to clipboard:', error);
            }
        } else if (event.data?.type === 'clipboard-write-image' && event.data?.rgba) {
            try {
                const clipboardManager = window.__TAURI__.clipboardManager;
                const { rgba, width, height } = event.data;
                console.log('[Desktop] Writing image to clipboard:', width, 'x', height, 'pixels');

                // Write image to clipboard using Tauri
                // The API expects {rgba: number[], width: number, height: number}
                await clipboardManager.writeImage({
                    rgba: rgba,
                    width: width,
                    height: height
                });

                console.log('[Desktop] Successfully wrote image to clipboard');
            } catch (error) {
                console.error('[Desktop] Failed to write image to clipboard:', error);
                console.error('[Desktop] Error details:', error.message);
            }
        }
    });

    updateLoadingStatus('Starting Python backend...');
}

/**
 * Handle menu events from native menu bar
 */
async function handleMenuEvent(event) {
    console.log('[Desktop] handleMenuEvent called with:', event);
    const { id } = event.payload;
    console.log('[Desktop] Menu event ID:', id);

    // Get iframe for postMessage communication
    const iframe = document.getElementById('main-frame');
    if (!iframe || !iframe.contentWindow) {
        console.warn('[Desktop] Cannot handle menu event - iframe not loaded');
        return;
    }

    // Handle clipboard operations using Tauri's native API
    if (id === 'paste' && window.__TAURI__) {
        try {
            // Tauri 2.x clipboard-manager plugin API
            const clipboardManager = window.__TAURI__.clipboardManager;
            const text = await clipboardManager.readText();
            console.log('[Desktop] Read from native clipboard:', text?.length, 'chars');

            // Send paste command with the text
            iframe.contentWindow.postMessage({
                type: 'desktop-menu-event',
                menuId: 'paste',
                clipboardText: text
            }, '*');
            return;
        } catch (error) {
            console.error('[Desktop] Failed to read from native clipboard:', error);
            console.log('[Desktop] Error details:', error);
        }
    }

    // For other menu items, just forward the event
    iframe.contentWindow.postMessage({
        type: 'desktop-menu-event',
        menuId: id
    }, '*');

    console.log('[Desktop] Posted message to iframe:', id);
}

/**
 * Setup menu event listeners
 */
async function setupMenuListeners() {
    if (!window.__TAURI__) return;

    const { listen } = window.__TAURI__.event;

    // Listen for menu events from Tauri
    await listen('menu-event', handleMenuEvent);

    console.log('[Desktop] Menu event listeners registered');
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

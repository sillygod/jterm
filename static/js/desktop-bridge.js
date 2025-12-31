/**
 * Desktop Bridge - Handles Tauri desktop app integration
 *
 * This script runs in the Python backend UI and integrates with Tauri APIs.
 * No iframe or postMessage needed - direct access to window.__TAURI__
 */

(function() {
    'use strict';

    console.log('[DesktopBridge] Initializing...');

    // Check if running in Tauri desktop environment
    const isDesktop = typeof window.__TAURI__ !== 'undefined';
    console.log('[DesktopBridge] Running in desktop mode:', isDesktop);

    if (!isDesktop) {
        console.log('[DesktopBridge] Not in desktop mode, skipping initialization');
        return;
    }

    /**
     * Listen for menu events from Tauri (via DOM CustomEvent)
     *
     * We use DOM events instead of Tauri's event.listen because
     * event.listen is restricted to local files, not remote URLs
     * like http://localhost:8000
     */
    function initializeMenuListeners() {
        window.addEventListener('tauri-menu-event', async (event) => {
            console.log('[DesktopBridge] Menu event received:', event.detail);
            const menuId = event.detail.id;

            try {
                await handleMenuAction(menuId);
            } catch (error) {
                console.error('[DesktopBridge] Error handling menu action:', error);
            }
        });

        console.log('[DesktopBridge] Menu event listeners registered (DOM events)');
    }

    /**
     * Handle menu actions
     */
    async function handleMenuAction(menuId) {
        // Get terminal instance (assumes WebTerminal is available)
        const terminal = window.webTerminal?.terminal;
        const clipboardManager = window.__TAURI__?.clipboardManager;

        switch (menuId) {
            case 'copy':
                console.log('[DesktopBridge] Copy action');
                if (terminal && clipboardManager) {
                    try {
                        // Get selected text from terminal
                        const selection = terminal.getSelection();
                        if (selection) {
                            console.log('[DesktopBridge] Copying', selection.length, 'chars to clipboard');
                            // Write directly to native clipboard
                            await clipboardManager.writeText(selection);
                            console.log('[DesktopBridge] Copy successful');
                        } else {
                            console.warn('[DesktopBridge] No text selected');
                        }
                    } catch (error) {
                        console.error('[DesktopBridge] Copy failed:', error);
                    }
                } else {
                    console.warn('[DesktopBridge] Terminal or clipboard not available');
                }
                break;

            case 'paste':
                console.log('[DesktopBridge] Paste action');
                if (clipboardManager && window.webTerminal) {
                    try {
                        // Read from native clipboard
                        const clipboardText = await clipboardManager.readText();
                        console.log('[DesktopBridge] Read', clipboardText?.length, 'chars from clipboard');

                        if (clipboardText) {
                            // Send text to terminal websocket with session ID
                            if (window.webTerminal.websocket?.readyState === WebSocket.OPEN && window.webTerminal.sessionId) {
                                window.webTerminal.websocket.send(JSON.stringify({
                                    type: 'input',
                                    sessionId: window.webTerminal.sessionId,
                                    data: clipboardText,
                                    timestamp: new Date().toISOString()
                                }));
                                console.log('[DesktopBridge] Paste executed successfully');
                            } else {
                                console.warn('[DesktopBridge] WebSocket not ready or session not created');
                            }
                        } else {
                            console.warn('[DesktopBridge] Clipboard is empty');
                        }
                    } catch (error) {
                        console.error('[DesktopBridge] Paste failed:', error);
                    }
                } else {
                    console.warn('[DesktopBridge] Clipboard or terminal not available');
                }
                break;

            case 'clear':
                console.log('[DesktopBridge] Clear action');
                if (terminal) {
                    terminal.clear();
                    console.log('[DesktopBridge] Terminal cleared');
                } else {
                    console.warn('[DesktopBridge] Terminal not available for clear');
                }
                break;

            case 'new_tab':
                console.log('[DesktopBridge] New tab action');
                // TODO: Implement tab creation via backend API
                alert('New Tab: Not yet implemented');
                break;

            case 'close_tab':
                console.log('[DesktopBridge] Close tab action');
                // TODO: Implement tab closing via backend API
                alert('Close Tab: Not yet implemented');
                break;

            case 'show_recording_controls':
                console.log('[DesktopBridge] Toggle recording controls');
                toggleElement('recording-controls');
                break;

            case 'show_performance_monitor':
                console.log('[DesktopBridge] Toggle performance monitor');
                toggleElement('performance-metrics');
                break;

            case 'show_ai_assistant':
                console.log('[DesktopBridge] Toggle AI assistant');
                toggleElement('ai-sidebar');
                break;

            case 'preferences':
                console.log('[DesktopBridge] Preferences action');
                // TODO: Implement preferences dialog
                alert('Preferences: Not yet implemented');
                break;

            default:
                console.warn('[DesktopBridge] Unknown menu action:', menuId);
        }
    }

    /**
     * Toggle visibility of an element
     */
    function toggleElement(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            const isHidden = element.style.display === 'none';
            element.style.display = isHidden ? 'block' : 'none';
            console.log(`[DesktopBridge] Toggled ${elementId}: ${isHidden ? 'shown' : 'hidden'}`);
        } else {
            console.warn(`[DesktopBridge] Element not found: ${elementId}`);
        }
    }

    // Initialize menu listeners when running in desktop mode
    if (isDesktop) {
        initializeMenuListeners();
    }

    console.log('[DesktopBridge] Initialized');
})();

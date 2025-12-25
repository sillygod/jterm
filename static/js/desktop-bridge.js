/**
 * Desktop Bridge - Handles communication between Tauri desktop app and web UI
 *
 * This script runs inside the iframe (Python backend UI) and receives
 * postMessage events from the parent window (Tauri desktop wrapper).
 */

(function() {
    'use strict';

    console.log('[DesktopBridge] Initializing...');

    // Always set up the message handler - it's harmless if we're not in an iframe
    // (messages just won't arrive, and there's no performance cost)

    /**
     * Handle messages from the desktop wrapper
     */
    window.addEventListener('message', async (event) => {
        // Log all messages for debugging
        console.log('[DesktopBridge] Received postMessage:', event.data);

        // Verify message structure
        if (!event.data || event.data.type !== 'desktop-menu-event') {
            console.log('[DesktopBridge] Ignoring message - not a desktop menu event');
            return;
        }

        const menuId = event.data.menuId;
        const clipboardText = event.data.clipboardText;
        console.log('[DesktopBridge] Processing menu event:', menuId);

        try {
            await handleMenuAction(menuId, clipboardText);
        } catch (error) {
            console.error('[DesktopBridge] Error handling menu action:', error);
        }
    });

    /**
     * Handle menu actions
     */
    async function handleMenuAction(menuId, clipboardText) {
        // Get terminal instance (assumes WebTerminal is available)
        const terminal = window.webTerminal?.terminal;

        switch (menuId) {
            case 'copy':
                console.log('[DesktopBridge] Copy action');
                if (terminal) {
                    try {
                        // Get selected text from terminal
                        const selection = terminal.getSelection();
                        if (selection) {
                            console.log('[DesktopBridge] Sending', selection.length, 'chars to parent for clipboard');
                            // Send to parent window to use native clipboard
                            window.parent.postMessage({
                                type: 'clipboard-write',
                                text: selection
                            }, '*');
                            console.log('[DesktopBridge] Copy request sent to parent');
                        } else {
                            console.warn('[DesktopBridge] No text selected');
                        }
                    } catch (error) {
                        console.error('[DesktopBridge] Copy failed:', error);
                    }
                } else {
                    console.warn('[DesktopBridge] Terminal not available for copy');
                }
                break;

            case 'paste':
                console.log('[DesktopBridge] Paste action, text length:', clipboardText?.length);
                if (clipboardText && window.webTerminal) {
                    try {
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
                    } catch (error) {
                        console.error('[DesktopBridge] Paste failed:', error);
                    }
                } else if (!clipboardText) {
                    console.warn('[DesktopBridge] No clipboard text provided');
                } else {
                    console.warn('[DesktopBridge] Terminal not available for paste');
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

            case 'test':
                console.log('[DesktopBridge] ✅ TEST MESSAGE RECEIVED! PostMessage is working!');
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

    console.log('[DesktopBridge] Message handler registered');
})();

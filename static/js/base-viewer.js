/**
 * Base Viewer JavaScript
 * Common functionality for all cat command viewers
 * Extracted from base_viewer.html to be loaded independently
 */

class BaseViewer {
    constructor(viewerId, viewerType) {
        this.viewerId = viewerId;
        this.viewerType = viewerType;
        this.overlay = null;
        this.container = null;
    }

    /**
     * Initialize the viewer
     */
    init() {
        this.overlay = document.getElementById(`${this.viewerId}-overlay`);
        this.container = document.getElementById(`${this.viewerId}-container`);

        if (!this.overlay || !this.container) {
            console.error(`Viewer elements not found: ${this.viewerId}`);
            return false;
        }

        this.setupKeyboardShortcuts();
        this.setupCloseHandlers();
        return true;
    }

    /**
     * Show the viewer
     */
    show() {
        if (this.overlay) {
            console.log('show() - overlay element:', this.overlay);
            console.log('show() - overlay computed style before:', window.getComputedStyle(this.overlay).display);
            this.overlay.classList.add('visible');
            console.log('show() - overlay classes:', this.overlay.className);
            console.log('show() - overlay computed style after:', window.getComputedStyle(this.overlay).display);
            document.body.style.overflow = 'hidden'; // Prevent background scrolling
        } else {
            console.error('show() - overlay is null!');
        }
    }

    /**
     * Hide the viewer
     */
    hide() {
        if (this.overlay) {
            this.overlay.classList.remove('visible');
            document.body.style.overflow = ''; // Restore scrolling
        }
    }

    /**
     * Close and cleanup the viewer
     */
    close() {
        this.hide();
        // Allow time for animation before removing
        setTimeout(() => {
            if (this.overlay && this.overlay.parentNode) {
                this.overlay.parentNode.removeChild(this.overlay);
            }
        }, 300);
    }

    /**
     * Setup keyboard shortcuts (common to all viewers)
     * T055: Enhanced keyboard shortcuts for navigation
     */
    setupKeyboardShortcuts() {
        const keyHandler = (e) => {
            // Only handle if this viewer is visible
            if (!this.overlay || !this.overlay.classList.contains('visible')) {
                return;
            }

            // Check for modifier keys
            const isCtrl = e.ctrlKey || e.metaKey; // metaKey for Mac Cmd
            const isShift = e.shiftKey;

            // Handle keyboard shortcuts
            if (e.key === 'Escape') {
                this.close();
                e.preventDefault();
                return;
            }

            // Ctrl+E or Cmd+E: Export
            if (isCtrl && e.key === 'e') {
                const exportBtn = document.getElementById(`${this.viewerId}-export-btn`);
                if (exportBtn) {
                    exportBtn.click();
                    e.preventDefault();
                }
                return;
            }

            // Ctrl+F or Cmd+F: Focus search
            if (isCtrl && e.key === 'f') {
                const searchInput = this.container?.querySelector('.viewer-search-input, input[type="search"]');
                if (searchInput) {
                    searchInput.focus();
                    searchInput.select();
                    e.preventDefault();
                }
                return;
            }

            // Ctrl+R or Cmd+R: Refresh/Reload
            if (isCtrl && e.key === 'r') {
                const refreshBtn = this.container?.querySelector('[id$="-refresh-schema"], [id$="-reload-btn"]');
                if (refreshBtn) {
                    refreshBtn.click();
                    e.preventDefault();
                }
                return;
            }

            // Question mark: Show keyboard shortcuts help
            if (e.key === '?' && !isCtrl && !isShift) {
                this.showKeyboardShortcutsHelp();
                e.preventDefault();
                return;
            }

            // Allow viewer-specific shortcuts
            if (this.handleViewerShortcut) {
                this.handleViewerShortcut(e, isCtrl, isShift);
            }
        };

        document.addEventListener('keydown', keyHandler);

        // Store handler for cleanup
        this._keyHandler = keyHandler;
    }

    /**
     * Show keyboard shortcuts help dialog
     * T055: Help dialog for keyboard shortcuts
     */
    showKeyboardShortcutsHelp() {
        const shortcuts = this.getKeyboardShortcuts();

        const dialogHtml = `
            <div class="keyboard-shortcuts-overlay" id="${this.viewerId}-shortcuts-overlay">
                <div class="keyboard-shortcuts-dialog">
                    <div class="keyboard-shortcuts-header">
                        <h3>Keyboard Shortcuts</h3>
                        <button class="shortcuts-close">✕</button>
                    </div>
                    <div class="keyboard-shortcuts-body">
                        ${shortcuts.map(group => `
                            <div class="shortcuts-group">
                                <h4>${group.title}</h4>
                                <div class="shortcuts-list">
                                    ${group.shortcuts.map(s => `
                                        <div class="shortcut-item">
                                            <kbd class="shortcut-keys">${s.keys}</kbd>
                                            <span class="shortcut-description">${s.description}</span>
                                        </div>
                                    `).join('')}
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', dialogHtml);

        // Close handlers
        const overlay = document.getElementById(`${this.viewerId}-shortcuts-overlay`);
        const closeBtn = overlay.querySelector('.shortcuts-close');

        closeBtn.addEventListener('click', () => overlay.remove());
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) overlay.remove();
        });

        // Close on Escape or ?
        const closeHandler = (e) => {
            if (e.key === 'Escape' || e.key === '?') {
                overlay.remove();
                document.removeEventListener('keydown', closeHandler);
            }
        };
        document.addEventListener('keydown', closeHandler);
    }

    /**
     * Get keyboard shortcuts for this viewer
     * T055: Define available shortcuts (can be overridden by subclasses)
     */
    getKeyboardShortcuts() {
        return [
            {
                title: 'General',
                shortcuts: [
                    { keys: 'Esc', description: 'Close viewer' },
                    { keys: '?', description: 'Show keyboard shortcuts' },
                ]
            },
            {
                title: 'Actions',
                shortcuts: [
                    { keys: 'Ctrl+E', description: 'Export data' },
                    { keys: 'Ctrl+F', description: 'Focus search' },
                    { keys: 'Ctrl+R', description: 'Refresh/Reload' },
                ]
            }
        ];
    }

    /**
     * Setup close handlers (click outside, close button)
     */
    setupCloseHandlers() {
        if (this.overlay) {
            // Close when clicking on overlay background (not container)
            this.overlay.addEventListener('click', (e) => {
                if (e.target === this.overlay) {
                    this.close();
                }
            });
        }

        // Close button handler
        if (this.container) {
            const closeBtn = this.container.querySelector('.viewer-btn-close');
            if (closeBtn) {
                closeBtn.addEventListener('click', () => this.close());
            }
        }
    }

    /**
     * Show loading state with custom message and optional progress
     * T054: Enhanced loading states with progress indicators
     */
    showLoading(message = 'Loading...', showProgress = false, progress = 0) {
        const body = this.container?.querySelector('.viewer-body');
        if (body) {
            body.innerHTML = `
                <div class="viewer-loading">
                    <div class="viewer-spinner"></div>
                    <div class="viewer-loading-message">${this.escapeHtml(message)}</div>
                    ${showProgress ? `
                        <div class="viewer-progress-bar">
                            <div class="viewer-progress-fill" style="width: ${Math.min(100, Math.max(0, progress))}%"></div>
                        </div>
                        <div class="viewer-progress-text">${Math.round(progress)}%</div>
                    ` : ''}
                </div>
            `;
        }
    }

    /**
     * Update loading progress
     * T054: Dynamic progress updates
     */
    updateLoadingProgress(progress, message = null) {
        const progressFill = this.container?.querySelector('.viewer-progress-fill');
        const progressText = this.container?.querySelector('.viewer-progress-text');
        const loadingMessage = this.container?.querySelector('.viewer-loading-message');

        if (progressFill) {
            progressFill.style.width = `${Math.min(100, Math.max(0, progress))}%`;
        }
        if (progressText) {
            progressText.textContent = `${Math.round(progress)}%`;
        }
        if (message && loadingMessage) {
            loadingMessage.textContent = message;
        }
    }

    /**
     * Show inline loading indicator (for buttons, smaller areas)
     * T054: Inline loading states
     */
    showInlineLoading(element, message = '') {
        if (!element) return;

        const originalContent = element.innerHTML;
        element.dataset.originalContent = originalContent;
        element.disabled = true;
        element.classList.add('loading');

        element.innerHTML = `
            <span class="inline-spinner"></span>
            ${message ? `<span>${this.escapeHtml(message)}</span>` : ''}
        `;
    }

    /**
     * Hide inline loading indicator
     * T054: Restore original content after loading
     */
    hideInlineLoading(element) {
        if (!element) return;

        element.disabled = false;
        element.classList.remove('loading');

        if (element.dataset.originalContent) {
            element.innerHTML = element.dataset.originalContent;
            delete element.dataset.originalContent;
        }
    }

    /**
     * Show empty state
     */
    showEmpty() {
        const body = this.container?.querySelector('.viewer-body');
        if (body) {
            body.innerHTML = `
                <div class="viewer-empty">
                    <div class="viewer-empty-icon">📭</div>
                    <div class="viewer-empty-message">No data to display</div>
                    <div class="viewer-empty-hint">Try adjusting your filters or query</div>
                </div>
            `;
        }
    }

    /**
     * Show error state with user-friendly messaging
     * T053: Enhanced error handling with detailed messages
     */
    showError(message, details = null, actionButton = null) {
        const body = this.container?.querySelector('.viewer-body');
        if (body) {
            // Parse error to provide user-friendly message
            const friendlyMessage = this.getFriendlyErrorMessage(message);

            body.innerHTML = `
                <div class="viewer-error">
                    <div class="viewer-error-icon">⚠️</div>
                    <div class="viewer-error-title">Something went wrong</div>
                    <div class="viewer-error-message">${this.escapeHtml(friendlyMessage)}</div>
                    ${details ? `<details class="viewer-error-details">
                        <summary>Technical Details</summary>
                        <pre>${this.escapeHtml(details)}</pre>
                    </details>` : ''}
                    ${actionButton ? `<div class="viewer-error-actions">${actionButton}</div>` : ''}
                </div>
            `;
        }
    }

    /**
     * Convert technical error messages to user-friendly ones
     * T053: User-friendly error message mapping
     */
    getFriendlyErrorMessage(error) {
        const message = typeof error === 'string' ? error : error.message || 'Unknown error';

        // Map common errors to friendly messages
        const errorMappings = {
            'Failed to fetch': 'Unable to connect to the server. Please check your internet connection.',
            'Network request failed': 'Network error occurred. Please try again.',
            'File not found': 'The requested file could not be found. Please check the path.',
            'HTTP 404': 'The requested resource was not found.',
            'HTTP 500': 'Server error occurred. Please try again later.',
            'HTTP 403': 'Access denied. You don\'t have permission to access this resource.',
            'HTTP 401': 'Authentication required. Please log in.',
            'Timeout': 'The request took too long. Please try again.',
            'Parse error': 'Unable to parse the data. The file format may be invalid.',
            'Invalid format': 'The file format is not supported or is invalid.',
            'Connection refused': 'Unable to connect to the database or service.',
            'Permission denied': 'You don\'t have permission to access this file or resource.'
        };

        // Check for mapped error messages
        for (const [key, friendly] of Object.entries(errorMappings)) {
            if (message.toLowerCase().includes(key.toLowerCase())) {
                return friendly;
            }
        }

        // Return original message if no mapping found
        return message;
    }

    /**
     * Clear viewer content
     */
    clearContent() {
        const body = this.container?.querySelector('.viewer-body');
        if (body) {
            body.innerHTML = '';
        }
    }

    /**
     * Make an API request with error handling
     */
    async apiRequest(url, options = {}) {
        try {
            const response = await fetch(url, {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            });

            if (!response.ok) {
                const error = await response.json().catch(() => ({}));
                throw new Error(error.detail || error.message || `HTTP ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`API request failed: ${url}`, error);
            throw error;
        }
    }

    /**
     * Export data (common functionality)
     */
    async exportData(format, data, filename) {
        try {
            let blob;
            let mimeType;

            switch(format.toLowerCase()) {
                case 'json':
                    blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
                    mimeType = 'application/json';
                    filename = filename || 'export.json';
                    break;
                case 'csv':
                    // CSV conversion handled by specific viewers
                    throw new Error('CSV export must be implemented by specific viewer');
                default:
                    throw new Error(`Unsupported export format: ${format}`);
            }

            // Trigger download
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

        } catch (error) {
            console.error('Export failed:', error);
            this.showError(`Export failed: ${error.message}`);
        }
    }

    /**
     * Escape HTML special characters
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Export BaseViewer for use in specific viewers
window.BaseViewer = BaseViewer;

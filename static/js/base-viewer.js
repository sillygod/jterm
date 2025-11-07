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
     */
    setupKeyboardShortcuts() {
        const keyHandler = (e) => {
            // Only handle if this viewer is visible
            if (!this.overlay || !this.overlay.classList.contains('visible')) {
                return;
            }

            switch(e.key) {
                case 'Escape':
                    this.close();
                    e.preventDefault();
                    break;
            }
        };

        document.addEventListener('keydown', keyHandler);

        // Store handler for cleanup
        this._keyHandler = keyHandler;
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
    }

    /**
     * Show loading state
     */
    showLoading() {
        const body = this.container?.querySelector('.viewer-body');
        if (body) {
            body.innerHTML = `
                <div class="viewer-loading">
                    <div class="viewer-spinner"></div>
                    <div>Loading...</div>
                </div>
            `;
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
     * Show error state
     */
    showError(message) {
        const body = this.container?.querySelector('.viewer-body');
        if (body) {
            body.innerHTML = `
                <div class="viewer-error">
                    <div class="viewer-error-title">Error</div>
                    <div class="viewer-error-message">${this.escapeHtml(message)}</div>
                </div>
            `;
        }
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

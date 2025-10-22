/**
 * Ebook Viewer - PDF/EPUB rendering with foliate-js
 * Handles ebook display, navigation, search, and password decryption
 */

class EbookViewer {
    constructor() {
        this.viewers = new Map(); // Map of ebook_id -> viewer instance
        this.viewerStates = new Map(); // Map of ebook_id -> state object
        this.passwordAttempts = new Map(); // Map of ebook_id -> attempt count
        this.maxPasswordAttempts = 3;

        // Configuration
        this.defaultFontSize = 100; // percentage
        this.fontSizeStep = 10;
        this.minFontSize = 50;
        this.maxFontSize = 200;

        this.init();
    }

    init() {
        this.setupEventListeners();
        console.log('EbookViewer initialized');
    }

    setupEventListeners() {
        // Listen for ebook commands from terminal via WebSocket
        document.addEventListener('htmx:wsAfterMessage', (e) => {
            const message = e.detail.message;
            if (message.type === 'ebook_command') {
                this.handleEbookCommand(message.data, message.metadata);
            }
        });

        // Global keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            // Handle shortcuts for any active ebook viewer
            for (const [ebookId, viewer] of this.viewers.entries()) {
                const viewerElement = document.getElementById(`ebook-viewer-${ebookId}`);
                if (viewerElement && !viewerElement.classList.contains('hidden')) {
                    this.handleKeyboardShortcut(e, ebookId);
                    break; // Only handle for the topmost viewer
                }
            }
        });
    }

    handleKeyboardShortcut(e, ebookId) {
        const viewerElement = document.getElementById(`ebook-viewer-${ebookId}`);
        if (!viewerElement) return;

        // Don't handle if user is typing in an input
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
            return;
        }

        switch (e.key) {
            case 'ArrowLeft':
                e.preventDefault();
                this.prevPage(ebookId);
                break;
            case 'ArrowRight':
                e.preventDefault();
                this.nextPage(ebookId);
                break;
            case 'f':
            case 'F':
                if (e.ctrlKey || e.metaKey) {
                    e.preventDefault();
                    this.toggleSearch(ebookId);
                }
                break;
            case '+':
            case '=':
                if (e.ctrlKey || e.metaKey) {
                    e.preventDefault();
                    this.increaseFontSize(ebookId);
                }
                break;
            case '-':
            case '_':
                if (e.ctrlKey || e.metaKey) {
                    e.preventDefault();
                    this.decreaseFontSize(ebookId);
                }
                break;
            case '0':
                if (e.ctrlKey || e.metaKey) {
                    e.preventDefault();
                    this.resetFontSize(ebookId);
                }
                break;
        }
    }

    handleEbookCommand(data, metadata) {
        const { command, filePath, ebookId, options } = data;

        switch (command) {
            case 'open':
                this.openEbook(filePath, ebookId, options);
                break;
            case 'close':
                this.closeEbook(ebookId);
                break;
            default:
                console.log('Unknown ebook command:', command);
        }
    }

    /**
     * Open an ebook file
     * @param {string} filePath - Path to the ebook file
     * @param {string} ebookId - Unique identifier for this ebook
     * @param {object} options - Additional options (title, author, etc.)
     */
    async openEbook(filePath, ebookId, options = {}) {
        try {
            // First, process the ebook via API to get metadata
            const response = await fetch('/api/ebooks/process', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ filePath: filePath })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || 'Failed to process ebook');
            }

            const metadata = await response.json();

            // Check if ebook is encrypted and requires password
            if (metadata.is_encrypted) {
                this.showPasswordPrompt(metadata.id, filePath, options);
                return;
            }

            // Render the ebook viewer
            await this.renderViewer(metadata);

        } catch (error) {
            console.error('Error opening ebook:', error);
            this.showError(ebookId, error.message);
        }
    }

    /**
     * Render the ebook viewer modal
     * @param {object} metadata - Ebook metadata from API
     */
    async renderViewer(metadata) {
        const ebookId = metadata.id;

        // Create viewer container if it doesn't exist
        let container = document.getElementById(`ebook-viewer-${ebookId}`);

        if (!container) {
            // Create viewer from template (HTMX would typically do this)
            // For now, we'll inject it into the body
            container = await this.createViewerElement(metadata);
            document.body.appendChild(container);
        }

        // Show loading state
        this.showLoading(ebookId);

        // Initialize the foliate-js viewer
        await this.initializeFoliateViewer(metadata);
    }

    /**
     * Create the viewer DOM element
     * @param {object} metadata - Ebook metadata
     * @returns {HTMLElement} The viewer element
     */
    async createViewerElement(metadata) {
        // Fetch the template from the server
        const response = await fetch(`/api/ebooks/${metadata.id}/viewer-template`);
        const html = await response.text();

        // Create a temporary container to parse the HTML
        const temp = document.createElement('div');
        temp.innerHTML = html;

        return temp.firstElementChild;
    }

    /**
     * Initialize foliate-js viewer
     * @param {object} metadata - Ebook metadata
     */
    async initializeFoliateViewer(metadata) {
        const ebookId = metadata.id;

        try {
            // Load the ebook content
            const contentUrl = `/api/ebooks/${ebookId}/content`;
            const response = await fetch(contentUrl);

            if (!response.ok) {
                throw new Error('Failed to load ebook content');
            }

            const blob = await response.blob();

            // Update progress
            this.updateProgress(ebookId, 50, 'Loading content...');

            // Get the viewer container
            const viewerContainer = document.getElementById(`foliate-viewer-${ebookId}`);

            if (!viewerContainer) {
                throw new Error('Viewer container not found');
            }

            // Initialize foliate-js
            // Note: This is a simplified version - actual foliate-js API may differ
            const { createReader } = window.foliate || {};

            if (!createReader) {
                throw new Error('foliate-js library not loaded');
            }

            const reader = await createReader(blob, {
                bookType: metadata.file_type, // 'pdf' or 'epub'
                container: viewerContainer,
            });

            // Store the reader instance
            this.viewers.set(ebookId, reader);

            // Initialize viewer state
            this.viewerStates.set(ebookId, {
                currentPage: 1,
                totalPages: metadata.total_pages || 0,
                fontSize: this.defaultFontSize,
                isSearchVisible: false,
                searchResults: [],
                currentSearchIndex: 0,
            });

            // Set up reader event handlers
            this.setupReaderEvents(ebookId, reader);

            // Update UI
            this.updateProgress(ebookId, 100, 'Ready');
            this.hideLoading(ebookId);

            // Update page info
            this.updatePageInfo(ebookId);

            console.log(`Ebook viewer initialized for ${ebookId}`);

        } catch (error) {
            console.error('Error initializing foliate viewer:', error);
            this.showError(ebookId, error.message);
        }
    }

    /**
     * Set up event handlers for the reader
     * @param {string} ebookId - Ebook identifier
     * @param {object} reader - foliate-js reader instance
     */
    setupReaderEvents(ebookId, reader) {
        // Page navigation events
        reader.addEventListener('relocate', (event) => {
            const state = this.viewerStates.get(ebookId);
            if (state) {
                state.currentPage = event.detail.page || 1;
                this.updatePageInfo(ebookId);
                this.updateReadingProgress(ebookId);
            }
        });

        // TOC loaded event
        reader.addEventListener('toc', (event) => {
            this.updateTableOfContents(ebookId, event.detail.toc);
        });

        // Error events
        reader.addEventListener('error', (event) => {
            console.error('Reader error:', event.detail);
            this.showError(ebookId, event.detail.message);
        });
    }

    /**
     * Navigate to previous page
     * @param {string} ebookId - Ebook identifier
     */
    prevPage(ebookId) {
        const reader = this.viewers.get(ebookId);
        if (reader && reader.prev) {
            reader.prev();
        }
    }

    /**
     * Navigate to next page
     * @param {string} ebookId - Ebook identifier
     */
    nextPage(ebookId) {
        const reader = this.viewers.get(ebookId);
        if (reader && reader.next) {
            reader.next();
        }
    }

    /**
     * Navigate to specific page
     * @param {string} ebookId - Ebook identifier
     * @param {number} pageNum - Page number (1-indexed)
     */
    gotoPage(ebookId, pageNum) {
        const reader = this.viewers.get(ebookId);
        const state = this.viewerStates.get(ebookId);

        if (reader && reader.goTo && state) {
            const page = Math.max(1, Math.min(parseInt(pageNum), state.totalPages));
            reader.goTo(page - 1); // foliate-js uses 0-indexed pages

            state.currentPage = page;
            this.updatePageInfo(ebookId);
        }
    }

    /**
     * Update page information display
     * @param {string} ebookId - Ebook identifier
     */
    updatePageInfo(ebookId) {
        const state = this.viewerStates.get(ebookId);
        if (!state) return;

        const pageInput = document.getElementById(`ebook-page-input-${ebookId}`);
        const totalPagesSpan = document.getElementById(`ebook-total-pages-${ebookId}`);
        const prevButton = document.getElementById(`ebook-prev-${ebookId}`);
        const nextButton = document.getElementById(`ebook-next-${ebookId}`);

        if (pageInput) {
            pageInput.value = state.currentPage;
            pageInput.max = state.totalPages;
        }

        if (totalPagesSpan) {
            totalPagesSpan.textContent = state.totalPages || '...';
        }

        // Enable/disable navigation buttons
        if (prevButton) {
            prevButton.disabled = state.currentPage <= 1;
        }

        if (nextButton) {
            nextButton.disabled = state.currentPage >= state.totalPages;
        }
    }

    /**
     * Update reading progress indicator
     * @param {string} ebookId - Ebook identifier
     */
    updateReadingProgress(ebookId) {
        const state = this.viewerStates.get(ebookId);
        if (!state || state.totalPages === 0) return;

        const percentage = Math.round((state.currentPage / state.totalPages) * 100);

        const progressBar = document.getElementById(`ebook-reading-progress-${ebookId}`);
        const progressText = document.getElementById(`ebook-progress-percent-${ebookId}`);

        if (progressBar) {
            progressBar.style.width = `${percentage}%`;
        }

        if (progressText) {
            progressText.textContent = `${percentage}%`;
        }
    }

    /**
     * Update table of contents
     * @param {string} ebookId - Ebook identifier
     * @param {Array} toc - Table of contents array
     */
    updateTableOfContents(ebookId, toc) {
        const tocNav = document.getElementById(`ebook-toc-nav-${ebookId}`);
        if (!tocNav || !toc || toc.length === 0) return;

        // Clear loading message
        tocNav.innerHTML = '';

        // Build TOC links
        toc.forEach((item, index) => {
            const link = document.createElement('a');
            link.className = `toc-link toc-level-${item.level || 1}`;
            link.textContent = item.label || item.title;
            link.href = '#';

            link.addEventListener('click', (e) => {
                e.preventDefault();

                // Navigate to this section
                const reader = this.viewers.get(ebookId);
                if (reader && reader.goTo && item.href) {
                    reader.goTo(item.href);
                }

                // Update active state
                tocNav.querySelectorAll('.toc-link').forEach(l => l.classList.remove('active'));
                link.classList.add('active');
            });

            tocNav.appendChild(link);
        });
    }

    /**
     * Increase font size
     * @param {string} ebookId - Ebook identifier
     */
    increaseFontSize(ebookId) {
        const state = this.viewerStates.get(ebookId);
        if (!state) return;

        state.fontSize = Math.min(state.fontSize + this.fontSizeStep, this.maxFontSize);
        this.applyFontSize(ebookId);
    }

    /**
     * Decrease font size
     * @param {string} ebookId - Ebook identifier
     */
    decreaseFontSize(ebookId) {
        const state = this.viewerStates.get(ebookId);
        if (!state) return;

        state.fontSize = Math.max(state.fontSize - this.fontSizeStep, this.minFontSize);
        this.applyFontSize(ebookId);
    }

    /**
     * Reset font size to default
     * @param {string} ebookId - Ebook identifier
     */
    resetFontSize(ebookId) {
        const state = this.viewerStates.get(ebookId);
        if (!state) return;

        state.fontSize = this.defaultFontSize;
        this.applyFontSize(ebookId);
    }

    /**
     * Apply font size to viewer
     * @param {string} ebookId - Ebook identifier
     */
    applyFontSize(ebookId) {
        const state = this.viewerStates.get(ebookId);
        const reader = this.viewers.get(ebookId);

        if (!state || !reader) return;

        // Update reader font size (API may vary)
        if (reader.setFontSize) {
            reader.setFontSize(state.fontSize);
        }

        // Update UI label
        const fontSizeLabel = document.getElementById(`ebook-font-size-${ebookId}`);
        if (fontSizeLabel) {
            fontSizeLabel.textContent = `${state.fontSize}%`;
        }
    }

    /**
     * Toggle search bar visibility
     * @param {string} ebookId - Ebook identifier
     */
    toggleSearch(ebookId) {
        const viewerElement = document.getElementById(`ebook-viewer-${ebookId}`);
        const searchInput = document.getElementById(`ebook-search-input-${ebookId}`);

        if (viewerElement) {
            viewerElement.classList.toggle('search-visible');

            // Focus search input when opened
            if (viewerElement.classList.contains('search-visible') && searchInput) {
                searchInput.focus();
            }
        }
    }

    /**
     * Search within ebook
     * @param {string} ebookId - Ebook identifier
     * @param {string} query - Search query
     */
    async search(ebookId, query) {
        const reader = this.viewers.get(ebookId);
        const state = this.viewerStates.get(ebookId);

        if (!reader || !state) return;

        if (!query || query.trim() === '') {
            state.searchResults = [];
            state.currentSearchIndex = 0;
            this.updateSearchCount(ebookId);
            return;
        }

        try {
            // Search using foliate-js API
            if (reader.search) {
                const results = await reader.search(query);
                state.searchResults = results || [];
                state.currentSearchIndex = 0;

                this.updateSearchCount(ebookId);

                // Navigate to first result
                if (results && results.length > 0) {
                    this.searchNext(ebookId);
                }
            }
        } catch (error) {
            console.error('Search error:', error);
        }
    }

    /**
     * Navigate to next search result
     * @param {string} ebookId - Ebook identifier
     */
    searchNext(ebookId) {
        const reader = this.viewers.get(ebookId);
        const state = this.viewerStates.get(ebookId);

        if (!state || !state.searchResults || state.searchResults.length === 0) return;

        state.currentSearchIndex = (state.currentSearchIndex + 1) % state.searchResults.length;

        const result = state.searchResults[state.currentSearchIndex];
        if (reader && reader.goTo && result.cfi) {
            reader.goTo(result.cfi);
        }

        this.updateSearchCount(ebookId);
    }

    /**
     * Navigate to previous search result
     * @param {string} ebookId - Ebook identifier
     */
    searchPrev(ebookId) {
        const reader = this.viewers.get(ebookId);
        const state = this.viewerStates.get(ebookId);

        if (!state || !state.searchResults || state.searchResults.length === 0) return;

        state.currentSearchIndex = state.currentSearchIndex - 1;
        if (state.currentSearchIndex < 0) {
            state.currentSearchIndex = state.searchResults.length - 1;
        }

        const result = state.searchResults[state.currentSearchIndex];
        if (reader && reader.goTo && result.cfi) {
            reader.goTo(result.cfi);
        }

        this.updateSearchCount(ebookId);
    }

    /**
     * Update search results count display
     * @param {string} ebookId - Ebook identifier
     */
    updateSearchCount(ebookId) {
        const state = this.viewerStates.get(ebookId);
        const countElement = document.getElementById(`ebook-search-count-${ebookId}`);

        if (!countElement || !state) return;

        if (state.searchResults.length === 0) {
            countElement.textContent = '0 results';
        } else {
            countElement.textContent = `${state.currentSearchIndex + 1} of ${state.searchResults.length}`;
        }
    }

    /**
     * Show password prompt for encrypted PDF
     * @param {string} ebookId - Ebook identifier
     * @param {string} filePath - File path
     * @param {object} options - Additional options
     */
    showPasswordPrompt(ebookId, filePath, options = {}) {
        // Initialize attempt counter
        this.passwordAttempts.set(ebookId, 0);

        // Show the password modal (assuming it exists in the template)
        const modal = document.getElementById(`ebook-password-modal-${ebookId}`);
        if (modal) {
            modal.style.display = 'flex';

            // Focus password input
            const input = document.getElementById(`password-input-${ebookId}`);
            if (input) {
                input.focus();
            }
        }
    }

    /**
     * Handle password decryption response
     * @param {string} ebookId - Ebook identifier
     * @param {boolean} success - Whether decryption succeeded
     * @param {object} error - Error details if failed
     */
    handleDecryptionResponse(ebookId, success, error = null) {
        if (success) {
            // Hide password modal
            const modal = document.getElementById(`ebook-password-modal-${ebookId}`);
            if (modal) {
                modal.style.display = 'none';
            }

            // Reload the ebook viewer
            this.reload(ebookId);

        } else {
            // Increment attempt counter
            const attempts = (this.passwordAttempts.get(ebookId) || 0) + 1;
            this.passwordAttempts.set(ebookId, attempts);

            // Update attempts display
            const attemptsCount = document.getElementById(`password-attempts-count-${ebookId}`);
            if (attemptsCount) {
                attemptsCount.textContent = this.maxPasswordAttempts - attempts;
            }

            // Show error
            const errorElement = document.getElementById(`password-error-${ebookId}`);
            if (errorElement) {
                errorElement.style.display = 'flex';
            }

            // Check if max attempts reached
            if (attempts >= this.maxPasswordAttempts) {
                this.showError(ebookId, 'Maximum password attempts exceeded');

                // Hide password modal
                const modal = document.getElementById(`ebook-password-modal-${ebookId}`);
                if (modal) {
                    modal.style.display = 'none';
                }
            }
        }
    }

    /**
     * Reload ebook viewer (after decryption)
     * @param {string} ebookId - Ebook identifier
     */
    async reload(ebookId) {
        // Get fresh metadata
        try {
            const response = await fetch(`/api/ebooks/${ebookId}/content`);

            if (!response.ok) {
                throw new Error('Failed to reload ebook');
            }

            // Re-initialize viewer
            const metadata = { id: ebookId }; // Simplified - would need full metadata
            await this.initializeFoliateViewer(metadata);

        } catch (error) {
            console.error('Error reloading ebook:', error);
            this.showError(ebookId, error.message);
        }
    }

    /**
     * Retry loading after error
     * @param {string} ebookId - Ebook identifier
     */
    async retry(ebookId) {
        this.hideError(ebookId);
        this.showLoading(ebookId);

        const metadata = { id: ebookId }; // Simplified
        await this.initializeFoliateViewer(metadata);
    }

    /**
     * Close ebook viewer
     * @param {string} ebookId - Ebook identifier
     */
    closeEbook(ebookId) {
        // Clean up viewer instance
        const reader = this.viewers.get(ebookId);
        if (reader && reader.destroy) {
            reader.destroy();
        }

        // Remove from maps
        this.viewers.delete(ebookId);
        this.viewerStates.delete(ebookId);
        this.passwordAttempts.delete(ebookId);

        // Remove viewer element
        const viewerElement = document.getElementById(`ebook-viewer-${ebookId}`);
        if (viewerElement) {
            viewerElement.remove();
        }
    }

    /**
     * Show loading indicator
     * @param {string} ebookId - Ebook identifier
     */
    showLoading(ebookId) {
        const loading = document.getElementById(`ebook-loading-${ebookId}`);
        const viewer = document.getElementById(`foliate-viewer-${ebookId}`);
        const error = document.getElementById(`ebook-error-${ebookId}`);

        if (loading) loading.style.display = 'flex';
        if (viewer) viewer.style.display = 'none';
        if (error) error.style.display = 'none';
    }

    /**
     * Hide loading indicator
     * @param {string} ebookId - Ebook identifier
     */
    hideLoading(ebookId) {
        const loading = document.getElementById(`ebook-loading-${ebookId}`);
        const viewer = document.getElementById(`foliate-viewer-${ebookId}`);

        if (loading) loading.style.display = 'none';
        if (viewer) viewer.style.display = 'block';
    }

    /**
     * Update loading progress
     * @param {string} ebookId - Ebook identifier
     * @param {number} percentage - Progress percentage (0-100)
     * @param {string} text - Progress text
     */
    updateProgress(ebookId, percentage, text = '') {
        const progressBar = document.getElementById(`ebook-progress-${ebookId}`);
        const progressText = document.getElementById(`ebook-progress-text-${ebookId}`);

        if (progressBar) {
            progressBar.style.width = `${percentage}%`;
        }

        if (progressText) {
            progressText.textContent = text || `${percentage}%`;
        }
    }

    /**
     * Show error message
     * @param {string} ebookId - Ebook identifier
     * @param {string} message - Error message
     */
    showError(ebookId, message) {
        const loading = document.getElementById(`ebook-loading-${ebookId}`);
        const viewer = document.getElementById(`foliate-viewer-${ebookId}`);
        const error = document.getElementById(`ebook-error-${ebookId}`);
        const errorMessage = document.getElementById(`ebook-error-message-${ebookId}`);

        if (loading) loading.style.display = 'none';
        if (viewer) viewer.style.display = 'none';
        if (error) error.style.display = 'flex';
        if (errorMessage) errorMessage.textContent = message;
    }

    /**
     * Hide error message
     * @param {string} ebookId - Ebook identifier
     */
    hideError(ebookId) {
        const error = document.getElementById(`ebook-error-${ebookId}`);
        if (error) error.style.display = 'none';
    }
}

// Initialize global instance
window.ebookViewer = new EbookViewer();

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = EbookViewer;
}

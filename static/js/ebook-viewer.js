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

        // Zoom configuration
        this.defaultZoomLevel = 100; // percentage
        this.zoomStep = 10;
        this.minZoom = 50;
        this.maxZoom = 300;

        this.init();
    }

    init() {
        this.injectStyles();
        this.setupEventListeners();
        console.log('EbookViewer initialized');
    }

    /**
     * Inject CSS styles for ebook viewer (only once)
     */
    injectStyles() {
        // Check if styles already injected
        if (document.getElementById('ebook-viewer-styles')) {
            return;
        }

        const styleSheet = document.createElement('style');
        styleSheet.id = 'ebook-viewer-styles';
        styleSheet.textContent = `
/* Ebook Viewer Styles */
.ebook-viewer {
    position: fixed;
    top: 5%;
    left: 5%;
    right: 5%;
    bottom: 5%;
    display: flex;
    flex-direction: column;
    background: var(--secondary-bg, #1a1a1a);
    border-radius: 0.5rem;
    overflow: hidden;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
    z-index: 900;
    animation: slideIn 0.3s ease-out;
}

.ebook-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.75rem 1rem;
    background: var(--accent-bg, #2a2a2a);
    border-bottom: 1px solid var(--border-color, #444);
    flex-shrink: 0;
}

.ebook-info {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    flex: 1;
    min-width: 0;
}

.ebook-title-group {
    display: flex;
    flex-direction: column;
    min-width: 0;
}

.ebook-title {
    font-weight: 600;
    font-size: 1rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.ebook-author {
    font-size: 0.875rem;
    color: var(--secondary-text, #aaa);
    font-style: italic;
}

.ebook-meta {
    font-size: 0.875rem;
    color: var(--secondary-text, #aaa);
    white-space: nowrap;
}

.ebook-controls {
    display: flex;
    gap: 0.25rem;
    flex-shrink: 0;
}

.ebook-container {
    flex: 1;
    display: flex;
    overflow: hidden;
    position: relative;
}

.ebook-content {
    flex: 1;
    position: relative;
    overflow: auto;
    background: var(--terminal-bg, #000);
}

.ebook-content > .foliate-viewer-container {
    width: 100%;
    height: 100%;
    min-width: 100%;
    min-height: 100%;
}

.ebook-loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    color: var(--secondary-text, #aaa);
}

.loading-spinner {
    width: 50px;
    height: 50px;
    border: 4px solid var(--border-color, #444);
    border-top-color: var(--primary-color, #00aaff);
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin-bottom: 1rem;
}

@keyframes spin {
    to { transform: rotate(360deg); }
}

.loading-progress {
    width: 300px;
    margin-top: 1rem;
}

.progress-bar {
    height: 4px;
    background: var(--border-color, #444);
    border-radius: 2px;
    overflow: hidden;
    margin-bottom: 0.5rem;
}

.progress-fill {
    height: 100%;
    background: var(--primary-color, #00aaff);
    transition: width 0.3s ease;
}

.progress-text {
    font-size: 0.875rem;
    color: var(--secondary-text, #aaa);
}

.foliate-viewer-container {
    width: 100%;
    height: 100%;
    background: white;
    color: black;
}

/* PDF canvas container - use flexbox for centering */
.foliate-viewer-container:has(canvas) {
    display: flex;
    align-items: center;
    justify-content: center;
}

.foliate-viewer-container canvas {
    max-width: none;
    max-height: none;
    background: white;
}

foliate-view {
    width: 100% !important;
    height: 100% !important;
}

/* Style the foliate-view custom element for readability */
foliate-view {
    background: white !important;
    color: black !important;
}

/* Force light theme for EPUB content */
foliate-view::part(main) {
    background: white !important;
    color: black !important;
}

/* Additional selectors for foliate-view internal structure */
foliate-view * {
    color: black;
}

foliate-view iframe {
    background: white !important;
}

.ebook-error {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    padding: 2rem;
    text-align: center;
}

.ebook-error .error-icon {
    font-size: 3rem;
    margin-bottom: 1rem;
}

.ebook-error h3 {
    margin: 0 0 0.5rem 0;
    color: var(--error-color, #ff5555);
}

.ebook-error .error-message {
    color: var(--secondary-text, #aaa);
    margin-bottom: 1.5rem;
}

.ebook-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.75rem 1rem;
    background: var(--accent-bg, #2a2a2a);
    border-top: 1px solid var(--border-color, #444);
    flex-shrink: 0;
    gap: 1rem;
}

.ebook-navigation {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.page-controls {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.page-info {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    font-size: 0.875rem;
    color: var(--text-color, #fff);
    font-weight: 400;
}

.page-input {
    width: 60px;
    padding: 0.25rem 0.5rem;
    background: var(--secondary-bg, #1a1a1a);
    border: 1px solid var(--border-color, #444);
    border-radius: 0.25rem;
    color: var(--text-color, #fff) !important;
    text-align: center;
    font-size: 0.875rem !important;
    font-weight: 500;
    line-height: 1.5;
}

.page-input:focus {
    outline: none;
    border-color: var(--primary-color, #00aaff);
    background: var(--secondary-bg, #1a1a1a);
    color: #fff !important;
}

.btn {
    padding: 0.5rem 1rem;
    background: var(--primary-color, #00aaff);
    color: white;
    border: none;
    border-radius: 0.25rem;
    cursor: pointer;
    font-size: 0.875rem;
}

.btn:hover {
    opacity: 0.9;
}

.btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

.btn-icon {
    padding: 0.5rem;
    background: transparent;
    color: var(--text-color, #fff);
}

.btn-icon:hover {
    background: var(--hover-bg, rgba(255, 255, 255, 0.1));
}

.btn-icon .icon {
    font-size: 1.25rem;
}

.btn-primary {
    background: var(--primary-color, #00aaff);
}

.close-btn {
    color: var(--error-color, #ff5555);
}

.ebook-actions {
    display: flex;
    align-items: center;
    gap: 1.5rem;
}

.zoom-controls {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.zoom-label {
    font-size: 0.875rem;
    min-width: 2.5rem;
    text-align: center;
    color: var(--text-color, #fff);
}

.btn-sm {
    padding: 0.375rem 0.75rem;
    font-size: 0.8125rem;
    background: transparent;
    color: var(--text-color, #fff);
    border: 1px solid var(--border-color, #444);
    border-radius: 0.25rem;
    cursor: pointer;
}

.btn-sm:hover {
    background: var(--hover-bg, rgba(255, 255, 255, 0.1));
}

.btn-sm .icon {
    font-size: 1rem;
}

@keyframes slideIn {
    from {
        opacity: 0;
        transform: translateY(-20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}
        `;
        document.head.appendChild(styleSheet);
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
                    if (e.shiftKey) {
                        // Shift + Ctrl + Plus = Zoom in
                        this.zoomIn(ebookId);
                    } else {
                        // Ctrl + Plus = Increase font size
                        this.increaseFontSize(ebookId);
                    }
                }
                break;
            case '-':
            case '_':
                if (e.ctrlKey || e.metaKey) {
                    e.preventDefault();
                    if (e.shiftKey) {
                        // Shift + Ctrl + Minus = Zoom out
                        this.zoomOut(ebookId);
                    } else {
                        // Ctrl + Minus = Decrease font size
                        this.decreaseFontSize(ebookId);
                    }
                }
                break;
            case '0':
                if (e.ctrlKey || e.metaKey) {
                    e.preventDefault();
                    if (e.shiftKey) {
                        // Shift + Ctrl + 0 = Reset zoom
                        this.resetZoom(ebookId);
                    } else {
                        // Ctrl + 0 = Reset font size
                        this.resetFontSize(ebookId);
                    }
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

            console.log('Ebook metadata received:', metadata);

            // Check if ebook is encrypted and requires password
            if (metadata.is_encrypted) {
                console.log('PDF is encrypted, showing password prompt');
                this.showPasswordPrompt(metadata.id, filePath, options);
                return;
            }

            console.log('PDF is not encrypted, rendering viewer');
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
        const ebookId = metadata.id;
        const fileType = metadata.file_type;
        const fileName = metadata.file_path ? metadata.file_path.split('/').pop() : 'file';
        // Use title from metadata, or fall back to filename (not 'Untitled')
        const title = metadata.title || fileName;
        const author = metadata.author || '';
        const totalPages = metadata.total_pages || 0;
        const fileSize = this.formatFileSize(metadata.file_size || 0);

        // Create viewer container with minimal HTML structure
        const container = document.createElement('div');
        container.className = 'ebook-viewer';
        container.id = `ebook-viewer-${ebookId}`;
        container.setAttribute('data-ebook-id', ebookId);
        container.setAttribute('data-file-type', fileType);

        container.innerHTML = `
            <div class="ebook-header">
                <div class="ebook-info">
                    <span class="icon">${fileType === 'pdf' ? '📕' : '📗'}</span>
                    <div class="ebook-title-group">
                        <span class="ebook-title">${this.escapeHtml(title)}</span>
                        ${author ? `<span class="ebook-author">by ${this.escapeHtml(author)}</span>` : ''}
                    </div>
                    <span class="ebook-meta">
                        ${totalPages ? `${totalPages} pages` : ''}
                        ${fileSize ? ` • ${fileSize}` : ''}
                    </span>
                </div>
                <div class="ebook-controls">
                    <button class="btn btn-icon close-btn" onclick="window.ebookViewer.closeEbook('${ebookId}')" title="Close">
                        <span class="icon">✕</span>
                    </button>
                </div>
            </div>

            <div class="ebook-container">
                <div class="ebook-content" id="ebook-content-${ebookId}">
                    <div class="ebook-loading" id="ebook-loading-${ebookId}">
                        <div class="loading-spinner"></div>
                        <p>Loading ebook...</p>
                        <div class="loading-progress">
                            <div class="progress-bar">
                                <div class="progress-fill" id="ebook-progress-${ebookId}" style="width: 0%"></div>
                            </div>
                            <span class="progress-text" id="ebook-progress-text-${ebookId}">0%</span>
                        </div>
                    </div>

                    <div class="foliate-viewer-container"
                         id="foliate-viewer-${ebookId}"
                         data-ebook-url="/api/ebooks/${ebookId}/content"
                         style="display: none;">
                    </div>

                    <div class="ebook-error" id="ebook-error-${ebookId}" style="display: none;">
                        <span class="error-icon">⚠️</span>
                        <h3>Failed to load ebook</h3>
                        <p class="error-message" id="ebook-error-message-${ebookId}"></p>
                        <button class="btn btn-primary" onclick="window.ebookViewer.retry('${ebookId}')">
                            Retry
                        </button>
                    </div>
                </div>
            </div>

            <div class="ebook-footer">
                <div class="ebook-navigation">
                    <button class="btn btn-icon" id="ebook-prev-${ebookId}"
                            onclick="window.ebookViewer.prevPage('${ebookId}')"
                            title="Previous Page" disabled>
                        <span class="icon">◄</span>
                    </button>
                    <div class="page-controls">
                        <span class="page-info" id="ebook-page-info-${ebookId}">
                            Page <input type="number" class="page-input"
                                       id="ebook-page-input-${ebookId}"
                                       value="1" min="1" max="${totalPages || 999}"
                                       style="color: white !important; background: #2a2a2a !important; font-size: 14px !important; font-weight: 500 !important;"
                                       onchange="window.ebookViewer.gotoPage('${ebookId}', this.value)">
                            of <span id="ebook-total-pages-${ebookId}">${totalPages || '...'}</span>
                        </span>
                    </div>
                    <button class="btn btn-icon" id="ebook-next-${ebookId}"
                            onclick="window.ebookViewer.nextPage('${ebookId}')"
                            title="Next Page">
                        <span class="icon">►</span>
                    </button>
                </div>

                <div class="ebook-actions">
                    <!-- Zoom controls -->
                    <div class="zoom-controls">
                        <button class="btn btn-sm"
                                onclick="window.ebookViewer.zoomOut('${ebookId}')"
                                title="Zoom Out (Shift+Ctrl+-)">
                            <span class="icon">🔎−</span>
                        </button>
                        <span class="zoom-label" id="ebook-zoom-${ebookId}">100%</span>
                        <button class="btn btn-sm"
                                onclick="window.ebookViewer.zoomIn('${ebookId}')"
                                title="Zoom In (Shift+Ctrl++)">
                            <span class="icon">🔎+</span>
                        </button>
                        <button class="btn btn-sm"
                                onclick="window.ebookViewer.resetZoom('${ebookId}')"
                                title="Reset Zoom (Shift+Ctrl+0)">
                            <span class="icon">⟲</span>
                        </button>
                    </div>
                </div>
            </div>
        `;

        return container;
    }

    /**
     * Escape HTML to prevent XSS
     * @param {string} text - Text to escape
     * @returns {string} Escaped text
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Format file size in human-readable format
     * @param {number} bytes - File size in bytes
     * @returns {string} Formatted size
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
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

            // Initialize foliate-js based on file type
            let view;

            if (metadata.file_type === 'pdf') {
                // For PDFs, use PDF.js directly since foliate-js PDF support is experimental
                // and not available in the standard view.js module
                try {
                    // Use PDF.js directly
                    if (typeof pdfjsLib === 'undefined') {
                        throw new Error('PDF.js library not loaded');
                    }

                    // Load PDF document
                    const arrayBuffer = await blob.arrayBuffer();
                    const loadingTask = pdfjsLib.getDocument({ data: arrayBuffer });
                    const pdfDoc = await loadingTask.promise;

                    // Create canvas for rendering
                    const canvas = document.createElement('canvas');
                    viewerContainer.appendChild(canvas);

                    // Store PDF document for navigation
                    const viewerInstance = window.ebookViewer; // Reference to update page info
                    view = {
                        _pdfDoc: pdfDoc,
                        _canvas: canvas,
                        _currentPage: 1,
                        _totalPages: pdfDoc.numPages,
                        _ebookId: ebookId,
                        next: async function() {
                            if (this._currentPage < this._totalPages) {
                                this._currentPage++;
                                await this._renderPage(this._currentPage);
                                viewerInstance.updatePageInfo(this._ebookId);
                            }
                        },
                        prev: async function() {
                            if (this._currentPage > 1) {
                                this._currentPage--;
                                await this._renderPage(this._currentPage);
                                viewerInstance.updatePageInfo(this._ebookId);
                            }
                        },
                        goTo: async function(pageNum) {
                            const targetPage = Math.max(1, Math.min(pageNum, this._totalPages));
                            this._currentPage = targetPage;
                            await this._renderPage(this._currentPage);
                            viewerInstance.updatePageInfo(this._ebookId);
                        },
                        _renderPage: async function(pageNum) {
                            const page = await this._pdfDoc.getPage(pageNum);

                            // Calculate scale to fit viewport while maintaining aspect ratio
                            const containerWidth = viewerContainer.clientWidth;
                            const containerHeight = viewerContainer.clientHeight;

                            // Get page dimensions at scale 1.0
                            const viewport = page.getViewport({ scale: 1.0 });

                            // Calculate scale to fit container
                            const scaleX = containerWidth / viewport.width;
                            const scaleY = containerHeight / viewport.height;
                            let scale = Math.min(scaleX, scaleY) * 0.95; // 95% to add some padding

                            // Apply zoom level from viewer state
                            const state = viewerInstance.viewerStates.get(this._ebookId);
                            if (state && state.zoomLevel) {
                                scale *= (state.zoomLevel / 100);
                            }

                            // Get scaled viewport
                            const scaledViewport = page.getViewport({ scale });

                            // Update canvas dimensions
                            this._canvas.width = scaledViewport.width;
                            this._canvas.height = scaledViewport.height;

                            // Center canvas in container (removed max-width/max-height to allow zooming)
                            this._canvas.style.margin = 'auto';
                            this._canvas.style.display = 'block';

                            const ctx = this._canvas.getContext('2d');
                            await page.render({ canvasContext: ctx, viewport: scaledViewport }).promise;
                        }
                    };

                    // Render first page
                    await view._renderPage(1);

                } catch (e) {
                    console.error('Failed to load PDF:', e);
                    throw new Error('PDF rendering failed: ' + e.message);
                }
            } else {
                // For EPUB and other formats, use foliate-js
                try {
                    // Ensure foliate-js module is loaded
                    await import('https://cdn.jsdelivr.net/npm/foliate-js@latest/view.js');
                } catch (e) {
                    console.error('Failed to load foliate-js:', e);
                    throw new Error('foliate-js library not loaded');
                }

                // Create the foliate-view custom element
                view = document.createElement('foliate-view');
                view.style.cssText = `
                    width: 100%;
                    height: 100%;
                    display: block;
                    background: white;
                    overflow: auto;
                `;

                // Set attributes for proper rendering
                view.setAttribute('flow', 'paginated');

                viewerContainer.appendChild(view);
                console.log('Foliate-view appended to container, container dimensions:',
                    viewerContainer.clientWidth, 'x', viewerContainer.clientHeight);

                // Convert blob to File object with proper name and type
                const fileName = metadata.file_path.split('/').pop();
                const fileType = 'application/epub+zip';
                const file = new File([blob], fileName, { type: fileType });

                console.log('Opening EPUB file:', fileName);

                // Open the ebook file
                await view.open(file);

                console.log('EPUB opened, view:', view);
                console.log('View renderer:', view.renderer);

                // Wait for book to be ready and get structure
                await new Promise(resolve => {
                    if (view.book) {
                        resolve();
                    } else {
                        view.addEventListener('load', () => resolve(), { once: true });
                        // Timeout fallback
                        setTimeout(resolve, 2000);
                    }
                });

                // Get the book structure and total sections
                const book = view.book;
                console.log('EPUB book object:', book);
                console.log('EPUB book.sections:', book?.sections);
                console.log('EPUB book.toc:', book?.toc);

                if (book) {
                    // Update total pages based on book structure
                    // For EPUB, we'll use sections/chapters as "pages"
                    const sections = book.sections || book.spine?.items || [];
                    const sectionCount = sections.length || 1;
                    metadata.total_pages = sectionCount;

                    console.log(`EPUB loaded: ${sectionCount} sections`);
                    console.log('First section:', sections[0]);
                    console.log('Section structure:', {
                        id: sections[0]?.id,
                        href: sections[0]?.href,
                        url: sections[0]?.url,
                        linear: sections[0]?.linear,
                        keys: sections[0] ? Object.keys(sections[0]) : []
                    });

                    // Store sections for navigation
                    view._sections = sections;
                    view._currentSection = 0;
                    view._ebookId = ebookId; // Store for callbacks
                } else {
                    console.warn('EPUB book object not available, using default pagination');
                    // Use a simpler navigation model
                    view._useFallbackNav = true;
                }

                // Apply light theme configuration after opening
                if (view.renderer) {
                    console.log('Configuring renderer:', view.renderer.tagName || view.renderer);

                    // For foliate-paginator, we need to set styles via CSS variables
                    try {
                        // Set CSS custom properties for theming
                        view.style.setProperty('--viewer-bg-color', '#ffffff');
                        view.style.setProperty('--viewer-fg-color', '#000000');
                        view.style.setProperty('--viewer-link-color', '#0066cc');

                        // Also try setting on the renderer
                        if (view.renderer.style) {
                            view.renderer.style.setProperty('--bg', '#ffffff');
                            view.renderer.style.setProperty('--fg', '#000000');
                            view.renderer.style.backgroundColor = 'white';
                            view.renderer.style.color = 'black';
                        }

                        console.log('Renderer styles configured via CSS properties');
                    } catch (e) {
                        console.error('Failed to set renderer styles:', e);
                    }

                    // For paginator, try to access and configure the view
                    if (view.renderer.tagName === 'FOLIATE-PAGINATOR') {
                        console.log('Paginator detected, configuring...');

                        // The paginator might need explicit styling
                        view.renderer.style.cssText = `
                            width: 100%;
                            height: 100%;
                            display: block;
                            background: white;
                            color: black;
                        `;

                        // Try to get the book from the view and render first section
                        if (view._sections && view._sections.length > 0) {
                            const firstSection = view._sections[0];
                            console.log('Attempting to render first section:', firstSection);

                            // Try different properties that might contain the navigation target
                            const target = firstSection.href || firstSection.url || firstSection.id || firstSection;

                            console.log('Navigation target:', target);

                            try {
                                // Try multiple navigation methods
                                if (typeof target === 'string') {
                                    await view.goTo(target);
                                    console.log('Successfully navigated to:', target);
                                    view._currentSection = 0;
                                } else if (target && typeof target === 'object') {
                                    // Try navigating by index
                                    await view.goTo({ index: 0 });
                                    console.log('Successfully navigated by index: 0');
                                    view._currentSection = 0;
                                } else {
                                    // Fallback: try to render by fraction
                                    await view.goTo({ fraction: 0 });
                                    console.log('Successfully navigated by fraction: 0');
                                    view._currentSection = 0;
                                }
                            } catch (e) {
                                console.error('Failed to navigate to first section:', e);
                                // Last resort: try without any parameter
                                try {
                                    await view.goTo(0);
                                    console.log('Successfully navigated with index 0');
                                    view._currentSection = 0;
                                } catch (e2) {
                                    console.error('All navigation attempts failed:', e2);
                                }
                            }
                        }
                    }
                } else {
                    console.warn('No renderer available on view object');
                }

                // For paginator-based rendering, we need different approach
                const ensureVisibleContent = () => {
                    console.log('Ensuring content visibility...');

                    // Set CSS variables that foliate-js might use
                    view.style.setProperty('--paginator-bg', 'white');
                    view.style.setProperty('--paginator-fg', 'black');

                    if (view.renderer) {
                        view.renderer.style.setProperty('--paginator-bg', 'white');
                        view.renderer.style.setProperty('--paginator-fg', 'black');

                        // Try to find the container div inside paginator
                        if (view.renderer.shadowRoot) {
                            const container = view.renderer.shadowRoot.querySelector('[style*="container"]') ||
                                            view.renderer.shadowRoot.querySelector('div');
                            if (container) {
                                container.style.backgroundColor = 'white';
                                container.style.color = 'black';
                                console.log('Set container styles in paginator shadow root');
                            }
                        }
                    }
                };

                // Initial style application
                setTimeout(ensureVisibleContent, 500);

                // Re-apply after navigation
                view.addEventListener('relocate', () => {
                    setTimeout(ensureVisibleContent, 100);

                    // Also update page info when content changes
                    const state = this.viewerStates.get(ebookId);
                    if (state) {
                        this.updatePageInfo(ebookId);
                    }
                });
            }

            // Store the view instance
            this.viewers.set(ebookId, view);

            // Initialize viewer state
            this.viewerStates.set(ebookId, {
                currentPage: 1,
                totalPages: metadata.total_pages || 0,
                fontSize: this.defaultFontSize,
                zoomLevel: this.defaultZoomLevel,
                isSearchVisible: false,
                searchResults: [],
                currentSearchIndex: 0,
            });

            // Set up view event handlers
            this.setupReaderEvents(ebookId, view);

            // Update UI
            this.updateProgress(ebookId, 100, 'Ready');
            this.hideLoading(ebookId);

            // Update page info
            this.updatePageInfo(ebookId);

            console.log(`Ebook viewer initialized for ${ebookId}`);

            // Debug: Check what's actually rendered
            setTimeout(() => {
                console.log('=== EPUB Rendering Debug ===');
                console.log('View element:', view);
                console.log('View innerHTML length:', view.innerHTML?.length || 0);
                console.log('View childNodes:', view.childNodes?.length || 0);
                console.log('View shadowRoot:', view.shadowRoot);
                console.log('View renderer:', view.renderer);
                console.log('View offsetWidth/Height:', view.offsetWidth, view.offsetHeight);
                console.log('ViewerContainer display:', viewerContainer.style.display);
                console.log('ViewerContainer offsetWidth/Height:', viewerContainer.offsetWidth, viewerContainer.offsetHeight);

                // Try to find any iframe
                const iframe = view.querySelector('iframe') || view.shadowRoot?.querySelector('iframe');
                console.log('Iframe found:', iframe);
                if (iframe) {
                    console.log('Iframe dimensions:', iframe.offsetWidth, iframe.offsetHeight);
                    console.log('Iframe src:', iframe.src);
                }
            }, 1000);

        } catch (error) {
            console.error('Error initializing foliate viewer:', error);
            this.showError(ebookId, error.message);
        }
    }

    /**
     * Set up event handlers for the view
     * @param {string} ebookId - Ebook identifier
     * @param {HTMLElement|Object} view - foliate-view custom element or PDF.js wrapper object
     */
    setupReaderEvents(ebookId, view) {
        // Only set up event listeners for DOM elements (foliate-view)
        // PDF.js wrapper doesn't need event listeners
        if (view.addEventListener && typeof view.addEventListener === 'function') {
            // Listen for location/page changes (foliate-view only)
            view.addEventListener('relocate', (e) => {
                console.log('EPUB location changed:', e.detail);
                const state = this.viewerStates.get(ebookId);
                if (state && e.detail) {
                    let sectionIndex = -1;

                    // Try to find current section index from various properties
                    if (view._sections) {
                        // 1. Try matching by section object identity or properties (HIGHEST PRIORITY)
                        if (e.detail.section && typeof e.detail.section === 'object') {
                            console.log('Trying to match section object:', {
                                section: e.detail.section,
                                sectionId: e.detail.section.id,
                                sectionHref: e.detail.section.href,
                                firstSectionInArray: view._sections[0]
                            });

                            // e.detail.section is an object - find its index in _sections array
                            sectionIndex = view._sections.findIndex(s => {
                                const matches = s === e.detail.section ||
                                    (s.href && e.detail.section.href && s.href === e.detail.section.href) ||
                                    (s.id && e.detail.section.id && s.id === e.detail.section.id);

                                if (matches) {
                                    console.log('Match found!', { s, detail: e.detail.section });
                                }
                                return matches;
                            });

                            if (sectionIndex >= 0) {
                                console.log(`Found section by object match: ${sectionIndex}`);
                            } else {
                                console.log('Section object matching failed');
                            }
                        }

                        // 2. Try matching by href
                        if (sectionIndex < 0 && e.detail.href) {
                            sectionIndex = view._sections.findIndex(s => s.href === e.detail.href);
                            if (sectionIndex >= 0) {
                                console.log(`Found section by href: ${sectionIndex} (${e.detail.href})`);
                            }
                        }

                        // 3. Try using index property directly (if it's a number)
                        if (sectionIndex < 0 && e.detail.index !== undefined && typeof e.detail.index === 'number') {
                            sectionIndex = e.detail.index;
                            console.log(`Using index property: ${sectionIndex}`);
                        }
                    }

                    // 4. ONLY use fraction if we have no other option (LOWEST PRIORITY - very inaccurate!)
                    // Don't use fraction if we already have _currentSection set (trust manual navigation)
                    if (sectionIndex < 0 && view._currentSection === undefined && e.detail.fraction !== undefined) {
                        sectionIndex = Math.floor(e.detail.fraction * (view._sections?.length || 1));
                        console.log(`Estimated from fraction ${e.detail.fraction}: ${sectionIndex} (FALLBACK - may be inaccurate)`);
                    }

                    // Update state if we found a valid section index
                    if (sectionIndex >= 0) {
                        view._currentSection = sectionIndex;
                        state.currentPage = sectionIndex + 1;
                        console.log(`Set currentPage to ${state.currentPage} of ${state.totalPages}`);
                    } else {
                        console.warn('Could not determine section index from relocate event:', e.detail);
                    }

                    this.updatePageInfo(ebookId);
                    this.updateReadingProgress(ebookId);
                }
            });

            // Also listen for load events
            view.addEventListener('load', (e) => {
                console.log('EPUB loaded event:', e);
                this.updatePageInfo(ebookId);
            });

            console.log('Foliate-view events setup complete');
        } else {
            // PDF.js wrapper - no events needed
            console.log('PDF.js view setup (no events)');
        }
    }

    /**
     * Navigate to previous page
     * @param {string} ebookId - Ebook identifier
     */
    async prevPage(ebookId) {
        const reader = this.viewers.get(ebookId);
        const state = this.viewerStates.get(ebookId);

        console.log('prevPage called for:', ebookId, 'reader:', reader, 'state:', state);

        if (!reader || !state) {
            console.error('Reader or state not found');
            return;
        }

        try {
            // For PDF views with _currentPage
            if (reader._currentPage !== undefined) {
                console.log('PDF navigation: prev');
                await reader.prev?.();
            } else {
                // For EPUB/foliate-view
                console.log('EPUB navigation: prev, currentSection:', reader._currentSection, 'sections:', reader._sections?.length);

                if (reader._sections && reader._currentSection !== undefined && reader._currentSection > 0) {
                    reader._currentSection--;
                    const section = reader._sections[reader._currentSection];
                    console.log('Navigating to section:', reader._currentSection, section);

                    const target = section?.href || section?.url || section?.id || section;

                    if (target) {
                        try {
                            if (typeof target === 'string') {
                                await reader.goTo(target);
                            } else {
                                await reader.goTo({ index: reader._currentSection });
                            }
                            state.currentPage = reader._currentSection + 1;
                            console.log('Set state.currentPage to:', state.currentPage);

                            // Use setTimeout to ensure DOM updates after async navigation completes
                            setTimeout(() => {
                                this.updatePageInfo(ebookId);
                            }, 50);

                            console.log(`Navigate to section ${state.currentPage}/${state.totalPages}`);
                        } catch (e) {
                            console.error('Navigation failed:', e);
                            // Restore section index on failure
                            reader._currentSection++;
                        }
                    }
                } else if (typeof reader.prev === 'function') {
                    // Fallback: use foliate-js native prev
                    console.log('Using fallback prev navigation');
                    await reader.prev();
                    // Manually decrement page if we don't have section tracking
                    if (state.currentPage > 1) {
                        state.currentPage--;
                        this.updatePageInfo(ebookId);
                    }
                } else {
                    console.error('No navigation method available');
                }
            }
        } catch (e) {
            console.error('prevPage error:', e);
        }
    }

    /**
     * Navigate to next page
     * @param {string} ebookId - Ebook identifier
     */
    async nextPage(ebookId) {
        const reader = this.viewers.get(ebookId);
        const state = this.viewerStates.get(ebookId);

        console.log('nextPage called for:', ebookId, 'reader:', reader, 'state:', state);

        if (!reader || !state) {
            console.error('Reader or state not found');
            return;
        }

        try {
            // For PDF views with _currentPage
            if (reader._currentPage !== undefined) {
                console.log('PDF navigation: next');
                await reader.next?.();
            } else {
                // For EPUB/foliate-view
                console.log('EPUB navigation: next, currentSection:', reader._currentSection, 'sections:', reader._sections?.length);

                if (reader._sections && reader._currentSection !== undefined && reader._currentSection < reader._sections.length - 1) {
                    reader._currentSection++;
                    const section = reader._sections[reader._currentSection];
                    console.log('Navigating to section:', reader._currentSection, section);

                    const target = section?.href || section?.url || section?.id || section;

                    if (target) {
                        try {
                            if (typeof target === 'string') {
                                await reader.goTo(target);
                            } else {
                                await reader.goTo({ index: reader._currentSection });
                            }
                            state.currentPage = reader._currentSection + 1;
                            console.log('Set state.currentPage to:', state.currentPage);

                            // Use setTimeout to ensure DOM updates after async navigation completes
                            setTimeout(() => {
                                this.updatePageInfo(ebookId);
                            }, 50);

                            console.log(`Navigate to section ${state.currentPage}/${state.totalPages}`);
                        } catch (e) {
                            console.error('Navigation failed:', e);
                            // Restore section index on failure
                            reader._currentSection--;
                        }
                    }
                } else if (typeof reader.next === 'function') {
                    // Fallback: use foliate-js native next
                    console.log('Using fallback next navigation');
                    await reader.next();
                    // Manually increment page if we don't have section tracking
                    if (state.currentPage < state.totalPages) {
                        state.currentPage++;
                        this.updatePageInfo(ebookId);
                    }
                } else {
                    console.error('No navigation method available');
                }
            }
        } catch (e) {
            console.error('nextPage error:', e);
        }
    }

    /**
     * Navigate to specific page
     * @param {string} ebookId - Ebook identifier
     * @param {number} pageNum - Page number (1-indexed)
     */
    async gotoPage(ebookId, pageNum) {
        console.log('=== gotoPage called ===', { ebookId, pageNum });
        const reader = this.viewers.get(ebookId);
        const state = this.viewerStates.get(ebookId);

        if (reader && state) {
            try {
                const page = Math.max(1, Math.min(parseInt(pageNum), state.totalPages));
                console.log('Validated page number:', page);

                // For PDF views, pass 1-indexed page number
                if (reader._currentPage !== undefined) {
                    await reader.goTo?.(page);
                } else {
                    // For foliate-js views (EPUB)
                    // Navigate to section by index (0-indexed)
                    if (reader._sections && reader._sections[page - 1]) {
                        const section = reader._sections[page - 1];
                        const target = section?.href || section?.url || section?.id || section;

                        console.log('Jumping to page', page, 'section:', section, 'target:', target);

                        try {
                            if (typeof target === 'string') {
                                await reader.goTo(target);
                            } else {
                                await reader.goTo({ index: page - 1 });
                            }
                            reader._currentSection = page - 1;
                            state.currentPage = page;
                            console.log('Set state.currentPage to:', state.currentPage);

                            // Use setTimeout to ensure DOM updates after async navigation completes
                            setTimeout(() => {
                                this.updatePageInfo(ebookId);
                            }, 50);

                            console.log('Successfully jumped to page', page);
                        } catch (e) {
                            console.error('Failed to jump to page:', e);
                        }
                    } else {
                        console.warn('Section not found for page:', page);
                    }
                }
            } catch (e) {
                console.warn('gotoPage not supported:', e);
            }
        }
    }

    /**
     * Update page information display
     * @param {string} ebookId - Ebook identifier
     */
    updatePageInfo(ebookId) {
        console.log('=== updatePageInfo called ===');
        console.trace('Call stack');

        const state = this.viewerStates.get(ebookId);
        const viewer = this.viewers.get(ebookId);
        if (!state) {
            console.warn('No state found for ebookId:', ebookId);
            return;
        }

        console.log('State BEFORE sync:', {
            currentPage: state.currentPage,
            totalPages: state.totalPages
        });

        // For PDF views, sync current page from the view object
        if (viewer && viewer._currentPage !== undefined) {
            state.currentPage = viewer._currentPage;
            state.totalPages = viewer._totalPages || state.totalPages;
            console.log('Synced from PDF view:', state.currentPage);
        }
        // For EPUB views, sync from _currentSection
        else if (viewer && viewer._currentSection !== undefined) {
            state.currentPage = viewer._currentSection + 1;
            state.totalPages = viewer._sections?.length || state.totalPages;
            console.log('Synced from EPUB view:', {
                _currentSection: viewer._currentSection,
                calculatedPage: viewer._currentSection + 1,
                finalCurrentPage: state.currentPage
            });
        }

        const pageInput = document.getElementById(`ebook-page-input-${ebookId}`);
        const totalPagesSpan = document.getElementById(`ebook-total-pages-${ebookId}`);
        const prevButton = document.getElementById(`ebook-prev-${ebookId}`);
        const nextButton = document.getElementById(`ebook-next-${ebookId}`);

        console.log('Updating page info:', {
            ebookId,
            currentPage: state.currentPage,
            totalPages: state.totalPages,
            pageInput: pageInput?.id,
            inputValue: pageInput?.value
        });

        if (pageInput) {
            // Ensure inline styles are set
            pageInput.style.color = 'white';
            pageInput.style.background = '#2a2a2a';
            pageInput.style.fontSize = '14px';
            pageInput.style.fontWeight = '500';

            console.log('BEFORE setting value:', {
                currentValue: pageInput.value,
                newValue: state.currentPage,
                stateCurrentPage: state.currentPage,
                viewerCurrentSection: viewer?._currentSection,
                inputElement: pageInput
            });

            // Update value - ensure it's a valid number
            if (state.currentPage !== undefined && state.currentPage !== null && !isNaN(state.currentPage)) {
                pageInput.value = String(state.currentPage);
                pageInput.setAttribute('value', String(state.currentPage));
            } else {
                console.error('Invalid currentPage value:', state.currentPage);
                pageInput.value = '1';
            }

            pageInput.max = state.totalPages;

            // Force repaint by reading offsetHeight
            void pageInput.offsetHeight;

            console.log('AFTER setting value:', {
                inputValue: pageInput.value,
                inputAttribute: pageInput.getAttribute('value'),
                computedColor: window.getComputedStyle(pageInput).color
            });
        } else {
            console.warn('Page input not found:', `ebook-page-input-${ebookId}`);
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
     * Zoom in (increase zoom level)
     * @param {string} ebookId - Ebook identifier
     */
    zoomIn(ebookId) {
        const state = this.viewerStates.get(ebookId);
        if (!state) return;

        state.zoomLevel = Math.min(state.zoomLevel + this.zoomStep, this.maxZoom);
        this.applyZoom(ebookId);
    }

    /**
     * Zoom out (decrease zoom level)
     * @param {string} ebookId - Ebook identifier
     */
    zoomOut(ebookId) {
        const state = this.viewerStates.get(ebookId);
        if (!state) return;

        state.zoomLevel = Math.max(state.zoomLevel - this.zoomStep, this.minZoom);
        this.applyZoom(ebookId);
    }

    /**
     * Reset zoom to default level
     * @param {string} ebookId - Ebook identifier
     */
    resetZoom(ebookId) {
        const state = this.viewerStates.get(ebookId);
        if (!state) return;

        state.zoomLevel = this.defaultZoomLevel;
        this.applyZoom(ebookId);
    }

    /**
     * Apply zoom level to viewer
     * @param {string} ebookId - Ebook identifier
     */
    async applyZoom(ebookId) {
        const state = this.viewerStates.get(ebookId);
        const reader = this.viewers.get(ebookId);

        if (!state || !reader) return;

        // For PDF viewers, re-render the current page with new zoom
        if (reader._pdfDoc && reader._renderPage) {
            await reader._renderPage(reader._currentPage);
        }

        // Update UI label
        const zoomLabel = document.getElementById(`ebook-zoom-${ebookId}`);
        if (zoomLabel) {
            zoomLabel.textContent = `${state.zoomLevel}%`;
        }

        console.log(`Zoom level updated to ${state.zoomLevel}%`);
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
        console.log('showPasswordPrompt called:', { ebookId, filePath });

        // Initialize attempt counter
        this.passwordAttempts.set(ebookId, 0);

        // Check if modal already exists
        let modal = document.getElementById(`ebook-password-modal-${ebookId}`);
        console.log('Existing modal:', modal);

        if (!modal) {
            // Create password modal dynamically
            console.log('Creating new password modal');
            modal = this.createPasswordModal(ebookId, filePath);
            document.body.appendChild(modal);
            console.log('Modal appended to body:', modal);
        }

        // Show the modal
        modal.style.display = 'flex';
        console.log('Modal displayed, style:', modal.style.display);

        // Focus password input after a short delay to ensure DOM is ready
        setTimeout(() => {
            const input = document.getElementById(`password-input-${ebookId}`);
            if (input) {
                input.focus();
            }
        }, 100);
    }

    /**
     * Create password modal HTML dynamically
     * @param {string} ebookId - Ebook identifier
     * @param {string} filePath - File path
     * @returns {HTMLElement} Modal element
     */
    createPasswordModal(ebookId, filePath) {
        const modal = document.createElement('div');
        modal.className = 'ebook-password-modal';
        modal.id = `ebook-password-modal-${ebookId}`;
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            display: none;
            justify-content: center;
            align-items: center;
            z-index: 10000;
        `;

        modal.innerHTML = `
            <div class="password-modal-content" style="
                background: #1e1e1e;
                border: 1px solid #444;
                border-radius: 8px;
                padding: 24px;
                max-width: 500px;
                width: 90%;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
            ">
                <div class="password-modal-header" style="
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 20px;
                ">
                    <h3 style="margin: 0; color: #fff; font-size: 18px;">🔒 Password Required</h3>
                    <button onclick="window.ebookViewer.closePasswordModal('${ebookId}')" style="
                        background: none;
                        border: none;
                        color: #999;
                        font-size: 24px;
                        cursor: pointer;
                        padding: 0;
                        width: 30px;
                        height: 30px;
                    ">×</button>
                </div>

                <div class="password-modal-body">
                    <p style="color: #ccc; margin-bottom: 16px;">
                        This PDF is password-protected. Please enter the password to view it.
                    </p>

                    <form id="password-form-${ebookId}" onsubmit="window.ebookViewer.submitPassword(event, '${ebookId}'); return false;">
                        <input type="password"
                               id="password-input-${ebookId}"
                               name="password"
                               data-file-path="${filePath}"
                               placeholder="Enter password..."
                               autocomplete="off"
                               required
                               style="
                                   width: 100%;
                                   padding: 10px;
                                   border: 1px solid #444;
                                   border-radius: 4px;
                                   background: #2a2a2a;
                                   color: #fff;
                                   font-size: 14px;
                                   margin-bottom: 12px;
                                   box-sizing: border-box;
                               ">

                        <div id="password-error-${ebookId}" style="
                            display: none;
                            background: #3a1a1a;
                            border: 1px solid #aa3333;
                            border-radius: 4px;
                            padding: 8px 12px;
                            margin-bottom: 12px;
                            color: #ff6666;
                            font-size: 13px;
                        ">
                            <span class="error-text">Incorrect password. Please try again.</span>
                        </div>

                        <div id="password-attempts-${ebookId}" style="
                            color: #999;
                            font-size: 13px;
                            margin-bottom: 16px;
                        ">
                            Attempts remaining: <span id="password-attempts-count-${ebookId}">3</span>
                        </div>

                        <div class="password-actions" style="
                            display: flex;
                            gap: 12px;
                            justify-content: flex-end;
                        ">
                            <button type="button"
                                    onclick="window.ebookViewer.closePasswordModal('${ebookId}')"
                                    style="
                                        padding: 8px 16px;
                                        background: #2a2a2a;
                                        border: 1px solid #444;
                                        border-radius: 4px;
                                        color: #ccc;
                                        cursor: pointer;
                                        font-size: 14px;
                                    ">
                                Cancel
                            </button>
                            <button type="submit"
                                    id="password-submit-${ebookId}"
                                    style="
                                        padding: 8px 16px;
                                        background: #0066cc;
                                        border: none;
                                        border-radius: 4px;
                                        color: white;
                                        cursor: pointer;
                                        font-size: 14px;
                                    ">
                                Unlock
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        `;

        return modal;
    }

    /**
     * Close password modal
     * @param {string} ebookId - Ebook identifier
     */
    closePasswordModal(ebookId) {
        const modal = document.getElementById(`ebook-password-modal-${ebookId}`);
        if (modal) {
            modal.style.display = 'none';
            modal.remove();
        }
        this.passwordAttempts.delete(ebookId);
    }

    /**
     * Submit password for decryption
     * @param {Event} event - Form submit event
     * @param {string} ebookId - Ebook identifier
     */
    async submitPassword(event, ebookId) {
        event.preventDefault();

        const input = document.getElementById(`password-input-${ebookId}`);
        const submitBtn = document.getElementById(`password-submit-${ebookId}`);
        const errorDiv = document.getElementById(`password-error-${ebookId}`);

        if (!input || !input.value) {
            return;
        }

        const password = input.value;

        // Disable submit button
        submitBtn.disabled = true;
        submitBtn.textContent = 'Unlocking...';

        // Hide previous error
        if (errorDiv) {
            errorDiv.style.display = 'none';
        }

        try {
            const response = await fetch(`/api/ebooks/${ebookId}/decrypt`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ password })
            });

            if (response.ok) {
                console.log('Decryption successful!');

                // Success - close modal and reload viewer
                const filePath = input.dataset.filePath || '';
                this.closePasswordModal(ebookId);

                // Get the updated metadata after decryption
                // The decrypted content is now cached on the server
                try {
                    const metadataResponse = await fetch('/api/ebooks/process', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ filePath: filePath })
                    });

                    if (metadataResponse.ok) {
                        const metadata = await metadataResponse.json();
                        console.log('Rendering viewer with decrypted content:', metadata);
                        // Now render the viewer - it will use the cached decrypted content
                        await this.renderViewer(metadata);
                    } else {
                        throw new Error('Failed to get metadata after decryption');
                    }
                } catch (error) {
                    console.error('Error loading decrypted ebook:', error);
                    this.showError(ebookId, 'Failed to load decrypted content');
                }
            } else {
                // Failed - show error
                const error = await response.json();
                this.handleDecryptionResponse(ebookId, false, error);

                // Re-enable submit button
                submitBtn.disabled = false;
                submitBtn.textContent = 'Unlock';

                // Clear password input
                input.value = '';
                input.focus();
            }
        } catch (error) {
            console.error('Error submitting password:', error);
            this.handleDecryptionResponse(ebookId, false, { message: error.message });

            // Re-enable submit button
            submitBtn.disabled = false;
            submitBtn.textContent = 'Unlock';
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

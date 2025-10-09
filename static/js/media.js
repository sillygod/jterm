/**
 * Media.js - Media handling for Web Terminal
 */

class MediaHandler {
    constructor() {
        this.supportedImageTypes = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'svg'];
        this.supportedVideoTypes = ['mp4', 'webm', 'ogg', 'mov', 'avi'];
        this.maxImageSize = 10 * 1024 * 1024; // 10MB
        this.maxVideoSize = 50 * 1024 * 1024; // 50MB

        this.init();
    }

    init() {
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Close media overlay on escape or click outside
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeMediaOverlay();
            }
        });

        // Media overlay click handler
        document.addEventListener('click', (e) => {
            if (e.target.id === 'media-overlay') {
                this.closeMediaOverlay();
            }
        });

        // Handle media commands from terminal
        document.addEventListener('htmx:wsAfterMessage', (e) => {
            const message = e.detail.message;
            if (message.type === 'media_command') {
                this.handleMediaCommand(message.data, message.metadata);
            }
        });
    }

    handleMediaCommand(data, metadata) {
        const { command, filePath, options } = data;

        switch (command) {
            case 'view':
                this.viewFile(filePath, options);
                break;
            case 'play':
                this.playVideo(filePath, options);
                break;
            case 'htmlview':
                this.previewHTML(filePath, options);
                break;
            case 'mdview':
                this.renderMarkdown(filePath, options);
                break;
            default:
                console.log('Unknown media command:', command);
        }
    }

    async viewFile(filePath, options = {}) {
        try {
            const fileExt = this.getFileExtension(filePath);
            const fileType = this.getMediaType(fileExt);

            if (fileType === 'image') {
                await this.displayImage(filePath, options);
            } else if (fileType === 'video') {
                await this.playVideo(filePath, options);
            } else {
                console.log('Unsupported file type for viewing:', fileExt);
                this.showError('Unsupported file type: ' + fileExt);
            }
        } catch (error) {
            console.error('Error viewing file:', error);
            this.showError('Failed to load file: ' + error.message);
        }
    }

    async displayImage(filePath, options = {}) {
        const overlay = document.getElementById('media-overlay');
        if (!overlay) return;

        // Show loading indicator
        overlay.innerHTML = `
            <div class="media-loading">
                <div class="spinner"></div>
                <p>Loading image...</p>
            </div>
        `;
        overlay.classList.add('visible');

        try {
            // Request image processing from server
            const response = await fetch('/api/media/process', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    filePath: filePath,
                    mediaType: 'image',
                    options: options
                })
            });

            if (!response.ok) {
                throw new Error('Failed to process image');
            }

            const result = await response.json();

            // Create image viewer
            overlay.innerHTML = `
                <div class="image-viewer" id="image-viewer">
                    <div class="image-controls">
                        <div class="control-group-left">
                            <button class="btn btn-icon" onclick="mediaHandler.closeMediaOverlay()"
                                    title="Close (Esc)">
                                <span class="icon">✕</span>
                            </button>
                        </div>
                        <div class="control-group-center">
                            <span class="image-info">
                                ${result.fileName} (${result.dimensions.width}×${result.dimensions.height})
                            </span>
                        </div>
                        <div class="control-group-right">
                            <button class="btn btn-icon" onclick="mediaHandler.zoomOut()"
                                    title="Zoom Out (-)">
                                <span class="icon">−</span>
                            </button>
                            <button class="btn btn-icon" onclick="mediaHandler.resetZoom()"
                                    title="Reset Zoom">
                                <span class="icon">⟲</span>
                            </button>
                            <button class="btn btn-icon" onclick="mediaHandler.zoomIn()"
                                    title="Zoom In (+)">
                                <span class="icon">+</span>
                            </button>
                            <button class="btn btn-icon" onclick="mediaHandler.toggleFullscreen()"
                                    title="Toggle Fullscreen">
                                <span class="icon">⛶</span>
                            </button>
                        </div>
                    </div>
                    <div class="image-container" id="image-container">
                        <img src="${result.url}"
                             alt="${result.fileName}"
                             class="media-image fade-in"
                             id="media-image"
                             draggable="false">
                    </div>
                </div>
            `;
        } catch (error) {
            this.showError('Failed to load image: ' + error.message);
        }
    }

    async playVideo(filePath, options = {}) {
        const overlay = document.getElementById('media-overlay');
        if (!overlay) return;

        overlay.innerHTML = `
            <div class="media-loading">
                <div class="spinner"></div>
                <p>Loading video...</p>
            </div>
        `;
        overlay.classList.add('visible');

        try {
            const response = await fetch('/api/media/process', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    filePath: filePath,
                    mediaType: 'video',
                    options: options
                })
            });

            if (!response.ok) {
                throw new Error('Failed to process video');
            }

            const result = await response.json();

            overlay.innerHTML = `
                <div class="video-viewer">
                    <div class="video-controls-top">
                        <button class="btn btn-icon" onclick="mediaHandler.closeMediaOverlay()"
                                title="Close (Esc)">
                            <span class="icon">✕</span>
                        </button>
                        <span class="video-info">
                            ${result.fileName} (${this.formatFileSize(result.fileSize)})
                        </span>
                    </div>
                    <div class="video-container">
                        <video controls
                               class="media-video fade-in"
                               preload="metadata"
                               _="on loadedmetadata remove .loading from #media-overlay">
                            <source src="${result.url}" type="${result.mimeType}">
                            Your browser does not support video playback.
                        </video>
                    </div>
                </div>
            `;
        } catch (error) {
            this.showError('Failed to load video: ' + error.message);
        }
    }

    async previewHTML(filePath, options = {}) {
        const overlay = document.getElementById('media-overlay');
        if (!overlay) return;

        overlay.innerHTML = `
            <div class="media-loading">
                <div class="spinner"></div>
                <p>Loading HTML preview...</p>
            </div>
        `;
        overlay.classList.add('visible');

        try {
            const response = await fetch('/api/media/html-preview', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    filePath: filePath,
                    allowJS: options.allowJS || false,
                    security: options.security || 'strict'
                })
            });

            if (!response.ok) {
                throw new Error('Failed to process HTML');
            }

            const result = await response.json();

            overlay.innerHTML = `
                <div class="html-viewer" id="html-viewer">
                    <div class="html-controls">
                        <div class="control-group-left">
                            <button class="btn btn-icon" onclick="mediaHandler.closeMediaOverlay()"
                                    title="Close (Esc)">
                                <span class="icon">✕</span>
                            </button>
                        </div>
                        <div class="control-group-center">
                            <span class="html-info">${result.fileName}</span>
                            ${!options.allowJS ? '<span class="security-badge">JS Disabled</span>' : ''}
                        </div>
                        <div class="control-group-right">
                            <button class="btn btn-icon" onclick="document.getElementById('html-viewer').classList.toggle('fullscreen')"
                                    title="Toggle Fullscreen">
                                <span class="icon">⛶</span>
                            </button>
                        </div>
                    </div>
                    <iframe src="${result.sandboxUrl}"
                            class="html-preview fade-in"
                            sandbox="${result.sandboxPermissions}">
                    </iframe>
                </div>
            `;
        } catch (error) {
            this.showError('Failed to preview HTML: ' + error.message);
        }
    }

    async renderMarkdown(filePath, options = {}) {
        try {
            // Fetch markdown content
            const response = await fetch('/api/media/markdown', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    filePath: filePath,
                    ...options
                })
            });

            if (!response.ok) {
                throw new Error('Failed to load markdown');
            }

            const html = await response.text();

            // Create overlay container for markdown
            let overlay = document.getElementById('markdown-overlay');
            if (!overlay) {
                overlay = document.createElement('div');
                overlay.id = 'markdown-overlay';
                overlay.className = 'media-overlay';
                document.body.appendChild(overlay);
            }

            // Insert markdown viewer
            overlay.innerHTML = html;
            overlay.classList.add('visible');

            // Add close on escape
            const closeHandler = (e) => {{
                if (e.key === 'Escape') {{
                    overlay.classList.remove('visible');
                    document.removeEventListener('keydown', closeHandler);
                }}
            }};
            document.addEventListener('keydown', closeHandler);
        } catch (error) {
            this.showError('Failed to render markdown: ' + error.message);
        }
    }

    closeMediaOverlay() {
        const overlay = document.getElementById('media-overlay');
        if (overlay) {
            overlay.classList.remove('visible');
            // Clear content after animation
            setTimeout(() => {
                if (!overlay.classList.contains('visible')) {
                    overlay.innerHTML = '';
                }
            }, 300);
        }
    }

    showError(message) {
        const overlay = document.getElementById('media-overlay');
        if (overlay) {
            overlay.innerHTML = `
                <div class="media-error">
                    <div class="error-icon">⚠️</div>
                    <h3>Error</h3>
                    <p>${message}</p>
                    <button class="btn btn-primary" onclick="mediaHandler.closeMediaOverlay()">
                        Close
                    </button>
                </div>
            `;
            overlay.classList.add('visible');
        }
    }

    getFileExtension(filePath) {
        return filePath.split('.').pop().toLowerCase();
    }

    getMediaType(extension) {
        if (this.supportedImageTypes.includes(extension)) {
            return 'image';
        } else if (this.supportedVideoTypes.includes(extension)) {
            return 'video';
        }
        return 'unknown';
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    toggleFullscreen() {
        const viewer = document.getElementById('image-viewer');
        if (viewer) {
            viewer.classList.toggle('fullscreen');
        }
    }

    zoomIn() {
        const img = document.getElementById('media-image');
        if (img) {
            const currentScale = parseFloat(img.dataset.scale || '1');
            const newScale = Math.min(currentScale * 1.2, 5);
            img.dataset.scale = newScale;
            img.style.transform = `scale(${newScale})`;
        }
    }

    zoomOut() {
        const img = document.getElementById('media-image');
        if (img) {
            const currentScale = parseFloat(img.dataset.scale || '1');
            const newScale = Math.max(currentScale / 1.2, 0.1);
            img.dataset.scale = newScale;
            img.style.transform = `scale(${newScale})`;
        }
    }

    resetZoom() {
        const img = document.getElementById('media-image');
        if (img) {
            img.dataset.scale = '1';
            img.style.transform = 'scale(1)';
        }
    }

    // Public API
    static getInstance() {
        if (!MediaHandler.instance) {
            MediaHandler.instance = new MediaHandler();
        }
        return MediaHandler.instance;
    }
}

// Initialize media handler
document.addEventListener('DOMContentLoaded', () => {
    window.mediaHandler = MediaHandler.getInstance();
});

// Add CSS for media components
const mediaStyles = `
<style>
.image-viewer, .video-viewer, .html-viewer {
    background: var(--secondary-bg);
    border-radius: 0.5rem;
    overflow: hidden;
    max-width: 90vw;
    max-height: 90vh;
    display: flex;
    flex-direction: column;
}

.image-controls, .video-controls-top, .html-controls {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.5rem 1rem;
    background: var(--accent-bg);
    border-bottom: 1px solid var(--border-color);
}

.control-group-left,
.control-group-center,
.control-group-right {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.control-group-center {
    flex: 1;
    justify-content: center;
}

.control-group-right {
    gap: 0.25rem;
}

.image-container, .video-container {
    flex: 1;
    display: flex;
    justify-content: center;
    align-items: center;
    overflow: hidden;
    min-height: 300px;
}

.media-image, .media-video {
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
    cursor: pointer;
    transition: transform 0.2s ease-out;
    transform-origin: center center;
}

.image-viewer.fullscreen {
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    right: 0 !important;
    bottom: 0 !important;
    width: 100vw !important;
    height: 100vh !important;
    max-width: 100vw !important;
    max-height: 100vh !important;
    margin: 0 !important;
    border-radius: 0 !important;
    z-index: 10000 !important;
}

.image-viewer.fullscreen .image-container {
    height: calc(100vh - 50px) !important;
}

.image-viewer.fullscreen .image-controls {
    background: rgba(0, 0, 0, 0.8) !important;
}

.html-viewer {
    max-width: 90vw;
    max-height: 90vh;
    width: 1200px;
    height: 800px;
}

.html-preview {
    width: 100%;
    height: 100%;
    border: none;
    background: white;
}

.html-viewer.fullscreen {
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    right: 0 !important;
    bottom: 0 !important;
    width: 100vw !important;
    height: 100vh !important;
    max-width: 100vw !important;
    max-height: 100vh !important;
    margin: 0 !important;
    border-radius: 0 !important;
    z-index: 10000 !important;
}

.html-viewer.fullscreen .html-preview {
    height: calc(100vh - 50px) !important;
}

.media-loading, .media-error {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 2rem;
    color: var(--primary-text);
}

.error-icon {
    font-size: 3rem;
    margin-bottom: 1rem;
}

.security-badge {
    background: var(--success-color);
    color: white;
    padding: 0.25rem 0.5rem;
    border-radius: 0.25rem;
    font-size: 0.75rem;
    font-weight: 500;
}

.zoom-in .media-image {
    transform: scale(1.2);
    transition: transform 0.2s ease;
}

.zoom-out .media-image {
    transform: scale(0.8);
    transition: transform 0.2s ease;
}
</style>
`;

// Inject media styles
document.head.insertAdjacentHTML('beforeend', mediaStyles);
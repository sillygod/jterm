/**
 * Image Editor - Fabric.js-based image annotation editor
 *
 * Handles canvas initialization, tool management, and auto-save functionality.
 */

class ImageEditor {
    constructor(sessionId) {
        this.sessionId = sessionId;
        this.canvas = null;
        this.currentTool = 'pen';
        this.currentColor = '#ff0000';
        this.currentStrokeWidth = 3;
        this.currentFillEnabled = false;
        this.currentFillColor = '#ff000080';
        this.currentFontSize = 18;
        this.currentBold = false;
        this.currentItalic = false;
        this.currentTextBackground = false;
        this.version = 1;
        this.autoSaveTimer = null;
        this.autoSaveDelay = 500; // 500ms debounce
        this.isDirty = false;

        // Undo/redo state
        this.undoStack = [];
        this.redoStack = [];
        this.maxUndoSteps = 50;

        // Drawing tools instance
        this.drawingTools = null;

        this.init();
    }

    async init() {
        try {
            // Wait for Fabric.js to load
            if (typeof fabric === 'undefined') {
                console.error('Fabric.js not loaded');
                this.showError('Canvas library not loaded. Please refresh the page.');
                return;
            }

            // Initialize canvas
            const canvasElement = document.getElementById(`canvas-${this.sessionId}`);
            if (!canvasElement) {
                console.error('Canvas element not found');
                return;
            }

            const imageUrl = canvasElement.dataset.imageUrl;
            this.version = parseInt(canvasElement.dataset.version) || 1;

            // Show loading
            this.showLoading();

            // Load image and create canvas
            await this.loadImage(imageUrl);

            // Setup event listeners
            this.setupEventListeners();
            this.setupToolEventListeners();
            this.setupKeyboardShortcuts();

            // Initialize drawing tools
            if (typeof DrawingTools !== 'undefined') {
                this.drawingTools = new DrawingTools(this.canvas, this);
            }

            // Initialize with pen tool
            this.setTool('pen');

            // Hide loading
            this.hideLoading();

            console.log('Image editor initialized:', this.sessionId);
        } catch (error) {
            console.error('Error initializing image editor:', error);
            this.showError('Failed to initialize editor: ' + error.message);
        }
    }

    async loadImage(imageUrl) {
        return new Promise((resolve, reject) => {
            fabric.Image.fromURL(imageUrl, (img) => {
                if (!img || !img.getElement()) {
                    reject(new Error('Failed to load image'));
                    return;
                }

                // Create canvas with image dimensions
                const canvasElement = document.getElementById(`canvas-${this.sessionId}`);

                // Set canvas dimensions
                this.canvas = new fabric.Canvas(`canvas-${this.sessionId}`, {
                    width: img.width,
                    height: img.height,
                    backgroundColor: '#f0f0f0'
                });

                // Set image as background
                this.canvas.setBackgroundImage(img, this.canvas.renderAll.bind(this.canvas), {
                    scaleX: 1,
                    scaleY: 1,
                });

                // Save initial state
                this.saveState();

                resolve();
            }, {
                crossOrigin: 'anonymous'
            });
        });
    }

    setupEventListeners() {
        const editorElement = document.getElementById(`image-editor-${this.sessionId}`);
        if (!editorElement) return;

        // Canvas events
        this.canvas.on('object:added', () => this.handleCanvasChange());
        this.canvas.on('object:modified', () => this.handleCanvasChange());
        this.canvas.on('object:removed', () => this.handleCanvasChange());

        // Mouse position tracking
        this.canvas.on('mouse:move', (e) => {
            const pointer = this.canvas.getPointer(e.e);
            this.updateMousePosition(pointer.x, pointer.y);
        });

        // Window resize
        window.addEventListener('resize', () => this.handleResize());
    }

    setupToolEventListeners() {
        const editorElement = document.getElementById(`image-editor-${this.sessionId}`);
        if (!editorElement) return;

        // Tool change
        editorElement.addEventListener('toolChange', (e) => {
            this.setTool(e.detail.tool);
        });

        // Color change
        editorElement.addEventListener('colorChange', (e) => {
            this.setColor(e.detail.color);
        });

        // Stroke width change
        editorElement.addEventListener('strokeWidthChange', (e) => {
            this.setStrokeWidth(e.detail.width);
        });

        // Fill toggle
        editorElement.addEventListener('fillToggle', (e) => {
            this.setFillEnabled(e.detail.fill);
        });

        // Fill color change
        editorElement.addEventListener('fillColorChange', (e) => {
            this.setFillColor(e.detail.color);
        });

        // Font size change
        editorElement.addEventListener('fontSizeChange', (e) => {
            this.setFontSize(e.detail.size);
        });

        // Text formatting
        editorElement.addEventListener('textBoldToggle', (e) => {
            this.setTextBold(e.detail.bold);
        });

        editorElement.addEventListener('textItalicToggle', (e) => {
            this.setTextItalic(e.detail.italic);
        });

        editorElement.addEventListener('textBackgroundToggle', (e) => {
            this.setTextBackground(e.detail.background);
        });

        // Undo/redo
        editorElement.addEventListener('undoEdit', () => this.undo());
        editorElement.addEventListener('redoEdit', () => this.redo());

        // Clipboard
        editorElement.addEventListener('copyToClipboard', () => this.copyToClipboard());

        // Clear canvas
        editorElement.addEventListener('clearCanvas', () => this.clearAnnotations());

        // Reset zoom
        editorElement.addEventListener('resetZoom', () => this.resetZoom());
    }

    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Forward to drawing tools for Shift key handling
            if (this.drawingTools && e.key === 'Shift') {
                this.drawingTools.handleKeyDown(e);
            }

            // Only handle shortcuts when editor is focused
            const editorElement = document.getElementById(`image-editor-${this.sessionId}`);
            if (!editorElement || !editorElement.contains(document.activeElement)) {
                return;
            }

            // Cmd/Ctrl + Z: Undo
            if ((e.metaKey || e.ctrlKey) && e.key === 'z' && !e.shiftKey) {
                e.preventDefault();
                this.undo();
            }

            // Cmd/Ctrl + Shift + Z: Redo
            if ((e.metaKey || e.ctrlKey) && e.key === 'z' && e.shiftKey) {
                e.preventDefault();
                this.redo();
            }

            // Tool shortcuts
            if (!e.metaKey && !e.ctrlKey) {
                switch (e.key.toLowerCase()) {
                    case 'v':
                        this.setTool('select');
                        break;
                    case 'p':
                        this.setTool('pen');
                        break;
                    case 'a':
                        this.setTool('arrow');
                        break;
                    case 't':
                        this.setTool('text');
                        break;
                    case 'r':
                        this.setTool('rectangle');
                        break;
                    case 'c':
                        this.setTool('circle');
                        break;
                    case 'l':
                        this.setTool('line');
                        break;
                    case 'e':
                        this.setTool('eraser');
                        break;
                }
            }

            // Delete key
            if (e.key === 'Delete' || e.key === 'Backspace') {
                const activeObject = this.canvas.getActiveObject();
                if (activeObject) {
                    this.canvas.remove(activeObject);
                    this.canvas.renderAll();
                }
            }
        });

        document.addEventListener('keyup', (e) => {
            // Forward to drawing tools for Shift key handling
            if (this.drawingTools && e.key === 'Shift') {
                this.drawingTools.handleKeyUp(e);
            }
        });
    }

    setTool(tool) {
        this.currentTool = tool;

        // Update tool UI
        document.querySelectorAll('.tool-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        const toolBtn = document.getElementById(`tool-${tool}`);
        if (toolBtn) {
            toolBtn.classList.add('active');
        }

        // Configure canvas based on tool
        if (tool === 'select') {
            this.canvas.isDrawingMode = false;
            this.canvas.selection = true;
        } else if (tool === 'pen') {
            this.canvas.isDrawingMode = true;
            this.canvas.freeDrawingBrush.color = this.currentColor;
            this.canvas.freeDrawingBrush.width = this.currentStrokeWidth;
        } else {
            this.canvas.isDrawingMode = false;
            this.canvas.selection = false;
        }

        console.log('Tool changed to:', tool);
    }

    setColor(color) {
        this.currentColor = color;
        if (this.canvas.isDrawingMode) {
            this.canvas.freeDrawingBrush.color = color;
        }

        // Update selected object color
        const activeObject = this.canvas.getActiveObject();
        if (activeObject) {
            activeObject.set('stroke', color);
            this.canvas.renderAll();
        }
    }

    setStrokeWidth(width) {
        this.currentStrokeWidth = width;
        if (this.canvas.isDrawingMode) {
            this.canvas.freeDrawingBrush.width = width;
        }

        // Update selected object stroke width
        const activeObject = this.canvas.getActiveObject();
        if (activeObject) {
            activeObject.set('strokeWidth', width);
            this.canvas.renderAll();
        }
    }

    setFillEnabled(enabled) {
        this.currentFillEnabled = enabled;
    }

    setFillColor(color) {
        this.currentFillColor = color;
    }

    setFontSize(size) {
        this.currentFontSize = size;

        // Update selected text object
        const activeObject = this.canvas.getActiveObject();
        if (activeObject && activeObject.type === 'i-text') {
            activeObject.set('fontSize', size);
            this.canvas.renderAll();
        }
    }

    setTextBold(bold) {
        this.currentBold = bold;

        // Update selected text object
        const activeObject = this.canvas.getActiveObject();
        if (activeObject && activeObject.type === 'i-text') {
            activeObject.set('fontWeight', bold ? 'bold' : 'normal');
            this.canvas.renderAll();
        }
    }

    setTextItalic(italic) {
        this.currentItalic = italic;

        // Update selected text object
        const activeObject = this.canvas.getActiveObject();
        if (activeObject && activeObject.type === 'i-text') {
            activeObject.set('fontStyle', italic ? 'italic' : 'normal');
            this.canvas.renderAll();
        }
    }

    setTextBackground(background) {
        this.currentTextBackground = background;
    }

    handleCanvasChange() {
        this.isDirty = true;
        this.updateSaveStatus('unsaved');
        this.scheduleAutoSave();

        // Save state for undo/redo
        this.saveState();
    }

    scheduleAutoSave() {
        // Clear existing timer
        if (this.autoSaveTimer) {
            clearTimeout(this.autoSaveTimer);
        }

        // Schedule new auto-save
        this.autoSaveTimer = setTimeout(() => {
            this.autoSave();
        }, this.autoSaveDelay);
    }

    async autoSave() {
        if (!this.isDirty) return;

        try {
            const canvasJSON = JSON.stringify(this.canvas.toJSON());

            const response = await fetch(`/api/v1/image-editor/annotation-layer/${this.sessionId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    canvas_json: canvasJSON,
                    version: this.version
                })
            });

            if (!response.ok) {
                throw new Error('Failed to save annotations');
            }

            const data = await response.json();
            this.version = data.new_version;
            this.isDirty = false;
            this.updateSaveStatus('saved');

            console.log('Auto-saved annotations, new version:', this.version);
        } catch (error) {
            console.error('Error auto-saving:', error);
            this.updateSaveStatus('error');
        }
    }

    saveState() {
        const state = JSON.stringify(this.canvas.toJSON());
        this.undoStack.push(state);

        // Limit undo stack size
        if (this.undoStack.length > this.maxUndoSteps) {
            this.undoStack.shift();
        }

        // Clear redo stack on new action
        this.redoStack = [];

        this.updateUndoRedoButtons();
    }

    undo() {
        if (this.undoStack.length <= 1) return; // Keep at least initial state

        const currentState = this.undoStack.pop();
        this.redoStack.push(currentState);

        const previousState = this.undoStack[this.undoStack.length - 1];
        this.loadState(previousState);

        this.updateUndoRedoButtons();
    }

    redo() {
        if (this.redoStack.length === 0) return;

        const nextState = this.redoStack.pop();
        this.undoStack.push(nextState);
        this.loadState(nextState);

        this.updateUndoRedoButtons();
    }

    loadState(stateJSON) {
        this.canvas.loadFromJSON(stateJSON, () => {
            this.canvas.renderAll();
        });
    }

    updateUndoRedoButtons() {
        const undoBtn = document.getElementById(`undo-btn-${this.sessionId}`);
        const redoBtn = document.getElementById(`redo-btn-${this.sessionId}`);

        if (undoBtn) {
            undoBtn.disabled = this.undoStack.length <= 1;
        }

        if (redoBtn) {
            redoBtn.disabled = this.redoStack.length === 0;
        }
    }

    async copyToClipboard() {
        try {
            // Export canvas as PNG blob
            const dataURL = this.canvas.toDataURL('image/png');
            const blob = await (await fetch(dataURL)).blob();

            // Copy to clipboard
            await navigator.clipboard.write([
                new ClipboardItem({
                    'image/png': blob
                })
            ]);

            console.log('Copied to clipboard');
            this.showSuccess('Copied to clipboard!');
        } catch (error) {
            console.error('Error copying to clipboard:', error);
            this.showError('Failed to copy to clipboard. Browser may not support this feature.');
        }
    }

    clearAnnotations() {
        // Remove all objects except background
        const objects = this.canvas.getObjects();
        objects.forEach(obj => {
            if (obj !== this.canvas.backgroundImage) {
                this.canvas.remove(obj);
            }
        });
        this.canvas.renderAll();
        this.handleCanvasChange();
    }

    resetZoom() {
        // TODO: Implement zoom reset when zoom functionality is added
        console.log('Reset zoom');
    }

    handleResize() {
        // TODO: Handle window resize
        // May need to recalculate canvas container dimensions
    }

    updateMousePosition(x, y) {
        const posElement = document.getElementById(`mouse-position-${this.sessionId}`);
        if (posElement) {
            posElement.textContent = `${Math.round(x)}, ${Math.round(y)}`;
        }
    }

    updateSaveStatus(status) {
        const statusElement = document.getElementById(`save-status-${this.sessionId}`);
        if (!statusElement) return;

        const indicator = statusElement.querySelector('.status-indicator');
        const text = statusElement.querySelector('.status-text');

        if (status === 'saved') {
            indicator.classList.remove('unsaved');
            text.textContent = 'Saved';
        } else if (status === 'unsaved') {
            indicator.classList.add('unsaved');
            text.textContent = 'Unsaved';
        } else if (status === 'error') {
            indicator.classList.add('unsaved');
            text.textContent = 'Error';
        }
    }

    showLoading() {
        const loadingElement = document.getElementById(`loading-${this.sessionId}`);
        if (loadingElement) {
            loadingElement.style.display = 'flex';
        }
    }

    hideLoading() {
        const loadingElement = document.getElementById(`loading-${this.sessionId}`);
        if (loadingElement) {
            loadingElement.style.display = 'none';
        }
    }

    showError(message) {
        const errorElement = document.getElementById(`error-${this.sessionId}`);
        if (errorElement) {
            errorElement.querySelector('.error-message').textContent = message;
            errorElement.style.display = 'flex';
        }

        // Hide loading if showing
        this.hideLoading();
    }

    showSuccess(message) {
        // TODO: Implement success notification
        console.log('Success:', message);
    }

    static init(sessionId) {
        return new ImageEditor(sessionId);
    }
}

// Global instance map
window.imageEditors = window.imageEditors || {};

// Export for use in templates
window.ImageEditor = ImageEditor;

/**
 * Drawing Tools for Image Editor
 *
 * Implements various drawing tools: pen, arrow, text, shapes, etc.
 */

class DrawingTools {
    constructor(canvas, editor) {
        this.canvas = canvas;
        this.editor = editor;
        this.isDrawing = false;
        this.startX = 0;
        this.startY = 0;
        this.currentShape = null;

        this.setupTools();
    }

    setupTools() {
        // Listen for mouse events on canvas
        console.log('[DrawingTools] Setting up mouse event listeners on canvas');
        this.canvas.on('mouse:down', (e) => this.handleMouseDown(e));
        this.canvas.on('mouse:move', (e) => this.handleMouseMove(e));
        this.canvas.on('mouse:up', (e) => this.handleMouseUp(e));
        console.log('[DrawingTools] Mouse event listeners registered');
    }

    handleMouseDown(e) {
        const tool = this.editor.currentTool;
        console.log('[DrawingTools] Mouse down, tool:', tool, 'target:', e.target?.type);

        // Skip if pen tool (handled by Fabric's drawing mode) or select tool
        if (tool === 'pen' || tool === 'select') return;

        // Skip if clicking on existing object (except for crop tool and eraser)
        // Allow clicks on background image for drawing
        if (e.target && e.target !== this.canvas.backgroundImage && tool !== 'crop' && tool !== 'eraser') {
            console.log('[DrawingTools] Skipping - clicked on existing object');
            return;
        }

        const pointer = this.canvas.getPointer(e.e);
        this.startX = pointer.x;
        this.startY = pointer.y;
        this.isDrawing = true;

        console.log('[DrawingTools] Starting shape at', pointer.x, pointer.y);

        // Create initial shape based on tool
        switch (tool) {
            case 'arrow':
                this.startArrow();
                break;
            case 'text':
                this.addText(pointer.x, pointer.y);
                break;
            case 'rectangle':
                console.log('[DrawingTools] Creating rectangle');
                this.startRectangle();
                break;
            case 'circle':
                console.log('[DrawingTools] Creating circle');
                this.startCircle();
                break;
            case 'line':
                this.startLine();
                break;
            case 'eraser':
                this.handleEraser(pointer);
                break;
            case 'crop':
                this.startCrop();
                break;
        }
    }

    handleMouseMove(e) {
        if (!this.isDrawing || !this.currentShape) {
            if (!this.isDrawing && this.editor.currentTool === 'rectangle') {
                console.log('[DrawingTools] Not drawing, isDrawing:', this.isDrawing);
            }
            return;
        }

        const tool = this.editor.currentTool;
        if (tool === 'pen' || tool === 'select' || tool === 'text') return;

        const pointer = this.canvas.getPointer(e.e);

        // Update shape based on tool
        switch (tool) {
            case 'arrow':
                this.updateArrow(pointer.x, pointer.y);
                break;
            case 'rectangle':
                this.updateRectangle(pointer.x, pointer.y);
                break;
            case 'circle':
                this.updateCircle(pointer.x, pointer.y);
                break;
            case 'line':
                this.updateLine(pointer.x, pointer.y);
                break;
            case 'crop':
                this.updateCrop(pointer.x, pointer.y);
                break;
        }

        this.canvas.renderAll();
    }

    handleMouseUp(e) {
        if (!this.isDrawing) return;

        this.isDrawing = false;
        this.currentShape = null;
    }

    // ==================== Pen Tool ====================
    // Pen tool is handled by Fabric's free drawing mode in ImageEditor

    // ==================== Arrow Tool ====================

    startArrow() {
        // Create line
        const line = new fabric.Line([this.startX, this.startY, this.startX, this.startY], {
            stroke: this.editor.currentColor,
            strokeWidth: this.editor.currentStrokeWidth,
            selectable: true,
            evented: true,
        });

        // Create arrowhead (triangle)
        const arrowhead = new fabric.Triangle({
            left: this.startX,
            top: this.startY,
            fill: this.editor.currentColor,
            width: this.editor.currentStrokeWidth * 3,
            height: this.editor.currentStrokeWidth * 4,
            angle: 0,
            selectable: false,
            evented: false,
        });

        // Group line and arrowhead
        this.currentShape = new fabric.Group([line, arrowhead], {
            selectable: true,
            evented: true,
        });

        this.canvas.add(this.currentShape);
    }

    updateArrow(x, y) {
        if (!this.currentShape) return;

        // Calculate angle
        const angle = Math.atan2(y - this.startY, x - this.startX) * 180 / Math.PI;

        // Get line and arrowhead from group
        const objects = this.currentShape.getObjects();
        const line = objects[0];
        const arrowhead = objects[1];

        // Update line
        line.set({
            x2: x - this.startX,
            y2: y - this.startY
        });

        // Update arrowhead position and rotation
        arrowhead.set({
            left: x - this.startX,
            top: y - this.startY,
            angle: angle + 90
        });

        this.currentShape.setCoords();
    }

    // ==================== Text Tool ====================

    addText(x, y) {
        // T135: Create editable text object
        // Double-clicking on the text will enable editing mode automatically
        const text = new fabric.IText('Text', {
            left: x,
            top: y,
            fill: this.editor.currentColor,
            fontSize: this.editor.currentFontSize,
            fontWeight: this.editor.currentBold ? 'bold' : 'normal',
            fontStyle: this.editor.currentItalic ? 'italic' : 'normal',
            fontFamily: 'Arial, sans-serif',
            selectable: true,
            editable: true,  // T135: Enables double-click to edit
        });

        // Add text background if enabled
        if (this.editor.currentTextBackground) {
            text.set('backgroundColor', this.editor.currentFillColor);
        }

        this.canvas.add(text);
        this.canvas.setActiveObject(text);
        text.enterEditing();
        text.selectAll();

        // Reset drawing state
        this.isDrawing = false;
        this.currentShape = null;
    }

    // ==================== Rectangle Tool ====================

    startRectangle() {
        console.log('[DrawingTools] startRectangle called', {
            startX: this.startX,
            startY: this.startY,
            fill: this.editor.currentFillEnabled ? this.editor.currentFillColor : 'transparent',
            stroke: this.editor.currentColor,
            strokeWidth: this.editor.currentStrokeWidth
        });

        this.currentShape = new fabric.Rect({
            left: this.startX,
            top: this.startY,
            width: 0,
            height: 0,
            fill: this.editor.currentFillEnabled ? this.editor.currentFillColor : 'transparent',
            stroke: this.editor.currentColor,
            strokeWidth: this.editor.currentStrokeWidth,
            selectable: true,
            evented: true,
        });

        console.log('[DrawingTools] Rectangle created:', this.currentShape);
        this.canvas.add(this.currentShape);
        console.log('[DrawingTools] Rectangle added to canvas');
        this.canvas.renderAll();
    }

    updateRectangle(x, y) {
        if (!this.currentShape) return;

        const width = Math.abs(x - this.startX);
        const height = Math.abs(y - this.startY);

        this.currentShape.set({
            left: Math.min(this.startX, x),
            top: Math.min(this.startY, y),
            width: width,
            height: height
        });

        this.currentShape.setCoords();
    }

    // ==================== Circle Tool ====================

    startCircle() {
        this.currentShape = new fabric.Circle({
            left: this.startX,
            top: this.startY,
            radius: 0,
            fill: this.editor.currentFillEnabled ? this.editor.currentFillColor : 'transparent',
            stroke: this.editor.currentColor,
            strokeWidth: this.editor.currentStrokeWidth,
            selectable: true,
            evented: true,
        });

        this.canvas.add(this.currentShape);
    }

    updateCircle(x, y) {
        if (!this.currentShape) return;

        const radius = Math.sqrt(
            Math.pow(x - this.startX, 2) + Math.pow(y - this.startY, 2)
        );

        this.currentShape.set({
            radius: radius
        });

        this.currentShape.setCoords();
    }

    // ==================== Line Tool ====================

    startLine() {
        this.currentShape = new fabric.Line([this.startX, this.startY, this.startX, this.startY], {
            stroke: this.editor.currentColor,
            strokeWidth: this.editor.currentStrokeWidth,
            selectable: true,
            evented: true,
        });

        this.canvas.add(this.currentShape);
    }

    updateLine(x, y) {
        if (!this.currentShape) return;

        let endX = x;
        let endY = y;

        // Snap to 45-degree angles if Shift is held
        if (this.shiftHeld) {
            const dx = x - this.startX;
            const dy = y - this.startY;
            const angle = Math.atan2(dy, dx);
            const snappedAngle = Math.round(angle / (Math.PI / 4)) * (Math.PI / 4);
            const length = Math.sqrt(dx * dx + dy * dy);

            endX = this.startX + length * Math.cos(snappedAngle);
            endY = this.startY + length * Math.sin(snappedAngle);
        }

        this.currentShape.set({
            x2: endX,
            y2: endY
        });

        this.currentShape.setCoords();
    }

    // ==================== Eraser Tool ====================

    handleEraser(pointer) {
        // Find objects at pointer location
        const target = this.canvas.findTarget(pointer, false);

        if (target && target !== this.canvas.backgroundImage) {
            this.canvas.remove(target);
            this.canvas.renderAll();
        }
    }

    // ==================== Color Picker Integration ====================

    updateColor(color) {
        // Update color of selected object
        const activeObject = this.canvas.getActiveObject();
        if (activeObject) {
            if (activeObject.type === 'i-text') {
                activeObject.set('fill', color);
            } else {
                activeObject.set('stroke', color);
            }
            this.canvas.renderAll();
        }
    }

    updateStrokeWidth(width) {
        // Update stroke width of selected object
        const activeObject = this.canvas.getActiveObject();
        if (activeObject && activeObject.strokeWidth !== undefined) {
            activeObject.set('strokeWidth', width);
            this.canvas.renderAll();
        }
    }

    updateFill(fillEnabled, fillColor) {
        // Update fill of selected object
        const activeObject = this.canvas.getActiveObject();
        if (activeObject && (activeObject.type === 'rect' || activeObject.type === 'circle')) {
            activeObject.set('fill', fillEnabled ? fillColor : 'transparent');
            this.canvas.renderAll();
        }
    }

    // ==================== Text Formatting (T131-T134) ====================

    updateTextFormatting(property, value) {
        // Update formatting of selected text object
        const activeObject = this.canvas.getActiveObject();
        if (activeObject && activeObject.type === 'i-text') {
            activeObject.set(property, value);
            this.canvas.renderAll();
            // Trigger auto-save
            if (this.editor.handleCanvasChange) {
                this.editor.handleCanvasChange();
            }
        }
    }

    updateFontSize(size) {
        // T131: Update font size of selected text
        this.updateTextFormatting('fontSize', size);
    }

    toggleBold(enabled) {
        // T132: Toggle bold formatting
        const activeObject = this.canvas.getActiveObject();
        if (activeObject && activeObject.type === 'i-text') {
            const newWeight = enabled ? 'bold' : 'normal';
            this.updateTextFormatting('fontWeight', newWeight);
        }
    }

    toggleItalic(enabled) {
        // T133: Toggle italic formatting
        const activeObject = this.canvas.getActiveObject();
        if (activeObject && activeObject.type === 'i-text') {
            const newStyle = enabled ? 'italic' : 'normal';
            this.updateTextFormatting('fontStyle', newStyle);
        }
    }

    toggleTextBackground(enabled, backgroundColor) {
        // T134: Toggle text background
        const activeObject = this.canvas.getActiveObject();
        if (activeObject && activeObject.type === 'i-text') {
            if (enabled) {
                this.updateTextFormatting('backgroundColor', backgroundColor);
            } else {
                // Remove background by setting to undefined
                activeObject.set('backgroundColor', undefined);
                this.canvas.renderAll();
                if (this.editor.handleCanvasChange) {
                    this.editor.handleCanvasChange();
                }
            }
        }
    }

    // ==================== Crop Tool ====================

    startCrop() {
        // Create crop selection rectangle with semi-transparent overlay
        this.currentShape = new fabric.Rect({
            left: this.startX,
            top: this.startY,
            width: 0,
            height: 0,
            fill: 'rgba(0, 0, 0, 0.4)',
            stroke: '#00ff00',
            strokeWidth: 2,
            strokeDashArray: [5, 5],
            selectable: true,
            evented: true,
            hasControls: true,
            hasBorders: true,
            lockRotation: true,
            cropTool: true  // Mark as crop tool
        });

        this.canvas.add(this.currentShape);
        this.canvas.setActiveObject(this.currentShape);

        // Create dim overlay outside crop area
        this.createCropOverlay();
    }

    updateCrop(x, y) {
        if (!this.currentShape) return;

        const width = Math.abs(x - this.startX);
        const height = Math.abs(y - this.startY);

        this.currentShape.set({
            left: Math.min(this.startX, x),
            top: Math.min(this.startY, y),
            width: width,
            height: height
        });

        this.currentShape.setCoords();
        this.updateCropOverlay();
    }

    createCropOverlay() {
        // Remove existing overlay if any
        this.removeCropOverlay();

        // Create semi-transparent overlay to dim non-crop area
        const canvasWidth = this.canvas.width;
        const canvasHeight = this.canvas.height;

        // Create overlay group
        this.cropOverlay = new fabric.Group([], {
            selectable: false,
            evented: false,
            cropOverlay: true
        });

        // Add four rectangles to cover areas outside crop selection
        const overlayColor = 'rgba(0, 0, 0, 0.5)';

        // Top
        this.cropOverlayTop = new fabric.Rect({
            left: 0,
            top: 0,
            width: canvasWidth,
            height: 0,
            fill: overlayColor,
            selectable: false,
            evented: false
        });

        // Bottom
        this.cropOverlayBottom = new fabric.Rect({
            left: 0,
            top: 0,
            width: canvasWidth,
            height: 0,
            fill: overlayColor,
            selectable: false,
            evented: false
        });

        // Left
        this.cropOverlayLeft = new fabric.Rect({
            left: 0,
            top: 0,
            width: 0,
            height: 0,
            fill: overlayColor,
            selectable: false,
            evented: false
        });

        // Right
        this.cropOverlayRight = new fabric.Rect({
            left: 0,
            top: 0,
            width: 0,
            height: 0,
            fill: overlayColor,
            selectable: false,
            evented: false
        });

        this.canvas.add(this.cropOverlayTop);
        this.canvas.add(this.cropOverlayBottom);
        this.canvas.add(this.cropOverlayLeft);
        this.canvas.add(this.cropOverlayRight);

        // Move crop selection to front
        if (this.currentShape) {
            this.canvas.bringToFront(this.currentShape);
        }
    }

    updateCropOverlay() {
        if (!this.currentShape) return;

        const cropLeft = this.currentShape.left;
        const cropTop = this.currentShape.top;
        const cropWidth = this.currentShape.width * (this.currentShape.scaleX || 1);
        const cropHeight = this.currentShape.height * (this.currentShape.scaleY || 1);
        const cropRight = cropLeft + cropWidth;
        const cropBottom = cropTop + cropHeight;

        const canvasWidth = this.canvas.width;
        const canvasHeight = this.canvas.height;

        // Top rectangle
        if (this.cropOverlayTop) {
            this.cropOverlayTop.set({
                left: 0,
                top: 0,
                width: canvasWidth,
                height: cropTop
            });
        }

        // Bottom rectangle
        if (this.cropOverlayBottom) {
            this.cropOverlayBottom.set({
                left: 0,
                top: cropBottom,
                width: canvasWidth,
                height: canvasHeight - cropBottom
            });
        }

        // Left rectangle
        if (this.cropOverlayLeft) {
            this.cropOverlayLeft.set({
                left: 0,
                top: cropTop,
                width: cropLeft,
                height: cropHeight
            });
        }

        // Right rectangle
        if (this.cropOverlayRight) {
            this.cropOverlayRight.set({
                left: cropRight,
                top: cropTop,
                width: canvasWidth - cropRight,
                height: cropHeight
            });
        }
    }

    removeCropOverlay() {
        const objects = this.canvas.getObjects();
        objects.forEach(obj => {
            if (obj.cropOverlay || obj === this.cropOverlayTop ||
                obj === this.cropOverlayBottom || obj === this.cropOverlayLeft ||
                obj === this.cropOverlayRight) {
                this.canvas.remove(obj);
            }
        });

        this.cropOverlayTop = null;
        this.cropOverlayBottom = null;
        this.cropOverlayLeft = null;
        this.cropOverlayRight = null;
        this.cropOverlay = null;
    }

    getCropBounds() {
        // Get current crop selection bounds
        const cropRect = this.canvas.getObjects().find(obj => obj.cropTool);

        if (!cropRect) {
            return null;
        }

        const left = Math.round(cropRect.left);
        const top = Math.round(cropRect.top);
        const width = Math.round(cropRect.width * (cropRect.scaleX || 1));
        const height = Math.round(cropRect.height * (cropRect.scaleY || 1));

        return { x: left, y: top, width, height };
    }

    applyCrop() {
        const bounds = this.getCropBounds();

        if (!bounds || bounds.width === 0 || bounds.height === 0) {
            this.editor.showError('Please select a crop area first');
            return;
        }

        // Call editor to apply crop
        this.editor.applyCrop(bounds);

        // Clean up crop tool
        this.cancelCrop();
    }

    cancelCrop() {
        // Remove crop selection and overlay
        const objects = this.canvas.getObjects();
        objects.forEach(obj => {
            if (obj.cropTool) {
                this.canvas.remove(obj);
            }
        });

        this.removeCropOverlay();
        this.currentShape = null;

        // Switch back to select tool
        this.editor.setTool('select');
    }

    // ==================== Keyboard Event Handling ====================

    handleKeyDown(e) {
        if (e.key === 'Shift') {
            this.shiftHeld = true;
        }
    }

    handleKeyUp(e) {
        if (e.key === 'Shift') {
            this.shiftHeld = false;
        }
    }
}

// Export for use in ImageEditor
window.DrawingTools = DrawingTools;

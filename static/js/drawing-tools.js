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
        this.canvas.on('mouse:down', (e) => this.handleMouseDown(e));
        this.canvas.on('mouse:move', (e) => this.handleMouseMove(e));
        this.canvas.on('mouse:up', (e) => this.handleMouseUp(e));
    }

    handleMouseDown(e) {
        const tool = this.editor.currentTool;

        // Skip if pen tool (handled by Fabric's drawing mode) or select tool
        if (tool === 'pen' || tool === 'select') return;

        // Skip if clicking on existing object
        if (e.target) return;

        const pointer = this.canvas.getPointer(e.e);
        this.startX = pointer.x;
        this.startY = pointer.y;
        this.isDrawing = true;

        // Create initial shape based on tool
        switch (tool) {
            case 'arrow':
                this.startArrow();
                break;
            case 'text':
                this.addText(pointer.x, pointer.y);
                break;
            case 'rectangle':
                this.startRectangle();
                break;
            case 'circle':
                this.startCircle();
                break;
            case 'line':
                this.startLine();
                break;
            case 'eraser':
                this.handleEraser(pointer);
                break;
        }
    }

    handleMouseMove(e) {
        if (!this.isDrawing || !this.currentShape) return;

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
        const text = new fabric.IText('Text', {
            left: x,
            top: y,
            fill: this.editor.currentColor,
            fontSize: this.editor.currentFontSize,
            fontWeight: this.editor.currentBold ? 'bold' : 'normal',
            fontStyle: this.editor.currentItalic ? 'italic' : 'normal',
            fontFamily: 'Arial, sans-serif',
            selectable: true,
            editable: true,
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

        this.canvas.add(this.currentShape);
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

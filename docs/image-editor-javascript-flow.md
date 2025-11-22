# Image Editor JavaScript Flow Documentation

**Last Updated**: 2025-11-18
**Project**: jterm Terminal Emulator
**Feature**: Image Editor (`imgcat` command)

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Initialization Flow](#initialization-flow)
4. [Event Flow](#event-flow)
5. [Drawing Tools Flow](#drawing-tools-flow)
6. [Tool Switching Flow](#tool-switching-flow)
7. [Auto-Save Flow](#auto-save-flow)
8. [Key Classes](#key-classes)
9. [Troubleshooting Guide](#troubleshooting-guide)

---

## Overview

The jterm image editor is a web-based canvas editor that allows users to annotate, draw shapes, apply filters, and edit images directly in the terminal. The editor uses **Fabric.js** for canvas management and is loaded dynamically when a user runs `imgcat <file>` in the terminal.

### Technology Stack

- **Frontend Framework**: Vanilla JavaScript ES2022 + Fabric.js 5.3.0
- **Canvas Library**: Fabric.js (object-based canvas manipulation)
- **Template Engine**: Jinja2 (server-side) + HTMX (client-side)
- **Event System**: Custom events + Hyperscript (with JavaScript fallbacks)

---

## Architecture

### Component Hierarchy

```
terminal.js (Terminal Manager)
    ↓
    handles `imgcat` OSC sequence
    ↓
    loads dependencies dynamically
    ↓
    fetches image-editor HTML component
    ↓
    initializes ImageEditor class
    ↓
    ┌─────────────────────────────────────────┐
    │         ImageEditor Instance            │
    │  (static/js/image-editor.js)            │
    ├─────────────────────────────────────────┤
    │ - Fabric.js Canvas                      │
    │ - Current Tool State                    │
    │ - Undo/Redo Stacks                      │
    │ - Auto-save Timer                       │
    └─────────────────────────────────────────┘
           ↓                    ↓
    ┌──────────────┐    ┌─────────────────┐
    │ DrawingTools │    │  FilterEngine   │
    │ (shapes,     │    │  (brightness,   │
    │  arrows,     │    │   contrast,     │
    │  text, etc.) │    │   blur, etc.)   │
    └──────────────┘    └─────────────────┘
```

### File Structure

```
static/js/
├── terminal.js              # Main terminal manager
├── image-editor.js          # ImageEditor class (canvas management)
├── drawing-tools.js         # DrawingTools class (shape creation)
└── filter-engine.js         # FilterEngine class (image filters)

templates/components/
├── image_editor.html        # Main editor HTML template
└── toolbar.html             # Toolbar UI component
```

---

## Initialization Flow

### Step 1: User Runs `imgcat` Command

```javascript
// User types in terminal:
$ imgcat /path/to/image.jpg

// Terminal emits OSC sequence
terminal.write('\x1b]1337;ViewImage=/path/to/image.jpg\x07');
```

### Step 2: Terminal.js Handles OSC Sequence

**File**: `static/js/terminal.js`

```javascript
// OSC parser detects image viewer sequence
handleMessage(data) {
    if (data.type === 'image_viewer') {
        this.handleImageViewer(data);
    }
}
```

### Step 3: API Call to Load Image

```javascript
async handleImageViewer(data) {
    // 1. Call backend API to load image
    const response = await fetch('/api/v1/image-editor/load', {
        method: 'POST',
        body: JSON.stringify({
            source_type: 'file',
            source_path: file_path,
            terminal_session_id: session_id
        })
    });

    const result = await response.json();
    // result = { session_id: "abc-123", image_info: {...} }
}
```

### Step 4: Load JavaScript Dependencies

```javascript
async loadImageEditorDependencies() {
    // Dependencies loaded in CORRECT ORDER:

    // 1. Fabric.js (canvas library)
    if (typeof window.fabric === 'undefined') {
        await this.loadScript('/static/js/vendor/fabric.min.js');
    }

    // 2. DrawingTools (MUST be loaded before ImageEditor)
    if (typeof window.DrawingTools === 'undefined') {
        await this.loadScript('/static/js/drawing-tools.js');
    }

    // 3. FilterEngine
    if (typeof window.FilterEngine === 'undefined') {
        await this.loadScript('/static/js/filter-engine.js');
    }

    // 4. ImageEditor (depends on DrawingTools and FilterEngine)
    if (typeof window.ImageEditor === 'undefined') {
        await this.loadScript('/static/js/image-editor.js');
    }
}
```

**⚠️ CRITICAL**: DrawingTools must be loaded BEFORE ImageEditor, otherwise shape tools won't work!

### Step 5: Fetch HTML Component

```javascript
// Fetch pre-rendered editor HTML from server
const componentResponse = await fetch(
    `/api/v1/image-editor/component/${result.session_id}`
);
const componentHTML = await componentResponse.text();

// Inject into overlay
let overlay = document.getElementById('media-overlay');
overlay.innerHTML = componentHTML;
overlay.classList.add('visible');
```

### Step 6: Initialize ImageEditor

```javascript
// Initialize the editor instance
if (window.ImageEditor) {
    window.ImageEditor.init(result.session_id);
}
```

**File**: `static/js/image-editor.js`

```javascript
static init(sessionId) {
    const editor = new ImageEditor(sessionId);
    ImageEditor.instances[sessionId] = editor;
    return editor;
}

async init() {
    // 1. Load image and create Fabric canvas
    await this.loadImage(imageUrl);

    // 2. Setup event listeners
    this.setupEventListeners();
    this.setupToolEventListeners();
    this.setupKeyboardShortcuts();

    // 3. Initialize DrawingTools (registers mouse handlers)
    this.drawingTools = new DrawingTools(this.canvas, this);

    // 4. Initialize FilterEngine
    this.filterEngine = new FilterEngine(this.sessionId, this.canvas);

    // 5. Set default tool (pen)
    this.setTool('pen');

    console.log('Image editor initialized:', this.sessionId);
}
```

### Step 7: Setup Event Listeners (Toolbar Controls)

**File**: `static/js/terminal.js` (lines 601-696)

```javascript
setTimeout(() => {
    const toolButtons = document.querySelectorAll('.tool-btn[data-tool]');
    const editorElement = document.getElementById(`image-editor-${result.session_id}`);

    // Tool buttons
    toolButtons.forEach(btn => {
        btn.addEventListener('click', function(e) {
            const tool = this.getAttribute('data-tool');
            const event = new CustomEvent('toolChange', {
                detail: { tool: tool },
                bubbles: true
            });
            editorElement.dispatchEvent(event);
        });
    });

    // Color picker, stroke width, fill toggle, etc.
    // ... (similar event listeners)
}, 300); // Wait for editor to fully initialize
```

**Why setTimeout?** The editor HTML is injected dynamically, so we need to wait for the DOM to be ready before attaching event listeners.

---

## Event Flow

### Tool Change Event

```
User clicks Rectangle button
    ↓
[Toolbar] Click event fires
    ↓
[Terminal.js] Dispatch 'toolChange' custom event
    ↓
[ImageEditor] Listen for 'toolChange' event
    ↓
[ImageEditor] Call setTool('rectangle')
    ↓
[ImageEditor] Update canvas.isDrawingMode = false
    ↓
[ImageEditor] Update canvas.selection = false
    ↓
[ImageEditor] Update currentTool = 'rectangle'
    ↓
[Toolbar] Highlight active button
```

**Code Flow**:

```javascript
// 1. Toolbar button click (terminal.js)
btn.addEventListener('click', function(e) {
    const event = new CustomEvent('toolChange', {
        detail: { tool: 'rectangle' }
    });
    editorElement.dispatchEvent(event);
});

// 2. ImageEditor listens (image-editor.js)
editorElement.addEventListener('toolChange', (e) => {
    this.setTool(e.detail.tool);
});

// 3. setTool updates canvas state
setTool(tool) {
    this.currentTool = tool;

    if (tool === 'select') {
        this.canvas.isDrawingMode = false;
        this.canvas.selection = true;
    } else if (tool === 'pen') {
        this.canvas.isDrawingMode = true;
    } else {
        this.canvas.isDrawingMode = false;
        this.canvas.selection = false;
    }
}
```

### Color Change Event

```
User picks color #00FF00
    ↓
[Toolbar] Color input change
    ↓
[Terminal.js] Dispatch 'colorChange' event
    ↓
[ImageEditor] Listen for 'colorChange'
    ↓
[ImageEditor] Call setColor('#00FF00')
    ↓
[ImageEditor] Update currentColor
    ↓
[ImageEditor] Update freeDrawingBrush.color (if pen tool)
```

---

## Drawing Tools Flow

### Rectangle Drawing Flow

```
User clicks on canvas (with rectangle tool active)
    ↓
[Fabric.js] Fire 'mouse:down' event
    ↓
[DrawingTools] handleMouseDown()
    ↓
Check: tool !== 'pen' && tool !== 'select'
    ↓
Check: e.target === canvas.backgroundImage (allow drawing on image)
    ↓
[DrawingTools] startRectangle()
    ↓
Create fabric.Rect with width=0, height=0
    ↓
Add rectangle to canvas
    ↓
User drags mouse
    ↓
[Fabric.js] Fire 'mouse:move' event
    ↓
[DrawingTools] handleMouseMove()
    ↓
[DrawingTools] updateRectangle(x, y)
    ↓
Calculate width and height from drag distance
    ↓
Update rectangle.set({ width, height, left, top })
    ↓
canvas.renderAll() (redraw canvas)
    ↓
User releases mouse
    ↓
[Fabric.js] Fire 'mouse:up' event
    ↓
[DrawingTools] handleMouseUp()
    ↓
Set isDrawing = false
    ↓
Rectangle is now selectable and movable
```

**Code Implementation**:

```javascript
// DrawingTools.handleMouseDown (drawing-tools.js:26-73)
handleMouseDown(e) {
    const tool = this.editor.currentTool;

    // Skip pen and select tools
    if (tool === 'pen' || tool === 'select') return;

    // Allow clicks on background image for drawing
    if (e.target && e.target !== this.canvas.backgroundImage &&
        tool !== 'crop' && tool !== 'eraser') {
        return;
    }

    const pointer = this.canvas.getPointer(e.e);
    this.startX = pointer.x;
    this.startY = pointer.y;
    this.isDrawing = true;

    switch (tool) {
        case 'rectangle':
            this.startRectangle();
            break;
        // ... other tools
    }
}

// DrawingTools.startRectangle (drawing-tools.js:206-231)
startRectangle() {
    this.currentShape = new fabric.Rect({
        left: this.startX,
        top: this.startY,
        width: 0,
        height: 0,
        fill: this.editor.currentFillEnabled ?
              this.editor.currentFillColor : 'transparent',
        stroke: this.editor.currentColor,
        strokeWidth: this.editor.currentStrokeWidth,
        selectable: true,
        evented: true,
    });

    this.canvas.add(this.currentShape);
    this.canvas.renderAll();
}

// DrawingTools.updateRectangle (drawing-tools.js:233-244)
updateRectangle(x, y) {
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
```

### Circle Drawing Flow

Similar to rectangle, but uses **radius** instead of width/height:

```javascript
startCircle() {
    this.currentShape = new fabric.Circle({
        left: this.startX,
        top: this.startY,
        radius: 0,  // Starts at 0
        fill: this.editor.currentFillEnabled ?
              this.editor.currentFillColor : 'transparent',
        stroke: this.editor.currentColor,
        strokeWidth: this.editor.currentStrokeWidth,
    });

    this.canvas.add(this.currentShape);
}

updateCircle(x, y) {
    // Calculate radius from center point
    const radius = Math.sqrt(
        Math.pow(x - this.startX, 2) +
        Math.pow(y - this.startY, 2)
    );

    this.currentShape.set({ radius });
    this.currentShape.setCoords();
}
```

### Line Drawing with Shift-Key Snapping

```javascript
updateLine(x, y) {
    let endX = x;
    let endY = y;

    // Snap to 45° angles if Shift is held
    if (this.shiftHeld) {
        const dx = x - this.startX;
        const dy = y - this.startY;
        const angle = Math.atan2(dy, dx);

        // Round to nearest 45° (π/4 radians)
        const snappedAngle = Math.round(angle / (Math.PI / 4)) * (Math.PI / 4);
        const length = Math.sqrt(dx * dx + dy * dy);

        endX = this.startX + length * Math.cos(snappedAngle);
        endY = this.startY + length * Math.sin(snappedAngle);
    }

    this.currentShape.set({ x2: endX, y2: endY });
    this.currentShape.setCoords();
}
```

### Pen (Free Drawing) Flow

The pen tool uses **Fabric.js built-in free drawing mode**:

```javascript
setTool(tool) {
    if (tool === 'pen') {
        this.canvas.isDrawingMode = true;
        this.canvas.freeDrawingBrush.color = this.currentColor;
        this.canvas.freeDrawingBrush.width = this.currentStrokeWidth;
    }
}
```

When `isDrawingMode = true`, Fabric.js handles all mouse events automatically and creates `fabric.Path` objects as the user draws.

---

## Tool Switching Flow

### State Management

```javascript
// ImageEditor maintains current tool state
this.currentTool = 'pen';  // Default tool

// Canvas drawing mode state
this.canvas.isDrawingMode = false;  // false for shape tools, true for pen
this.canvas.selection = false;      // false for drawing, true for select
```

### Tool Modes

| Tool | isDrawingMode | selection | Mouse Handler |
|------|---------------|-----------|---------------|
| **Pen** | `true` | `false` | Fabric.js (automatic) |
| **Select** | `false` | `true` | Fabric.js (automatic) |
| **Rectangle** | `false` | `false` | DrawingTools |
| **Circle** | `false` | `false` | DrawingTools |
| **Line** | `false` | `false` | DrawingTools |
| **Arrow** | `false` | `false` | DrawingTools |
| **Text** | `false` | `false` | DrawingTools |
| **Eraser** | `false` | `false` | DrawingTools |
| **Crop** | `false` | `false` | DrawingTools |

### Switching Between Tools

```javascript
// From Pen → Rectangle
setTool('pen')        // isDrawingMode = true
    ↓
setTool('rectangle')  // isDrawingMode = false
    ↓
handleMouseDown now uses DrawingTools instead of Fabric free drawing
```

**Key Code**:

```javascript
setTool(tool) {
    this.currentTool = tool;

    // Update UI (highlight active button)
    document.querySelectorAll('.tool-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.getElementById(`tool-${tool}`).classList.add('active');

    // Configure canvas mode
    if (tool === 'select') {
        this.canvas.isDrawingMode = false;
        this.canvas.selection = true;
    } else if (tool === 'pen') {
        this.canvas.isDrawingMode = true;
        this.canvas.freeDrawingBrush.color = this.currentColor;
        this.canvas.freeDrawingBrush.width = this.currentStrokeWidth;
    } else {
        // Shape tools: rectangle, circle, line, arrow, etc.
        this.canvas.isDrawingMode = false;
        this.canvas.selection = false;
    }
}
```

---

## Auto-Save Flow

The editor automatically saves canvas state to the backend after each modification.

### Debounced Auto-Save

```javascript
// ImageEditor properties
this.autoSaveTimer = null;
this.autoSaveDelay = 500;  // 500ms debounce
this.isDirty = false;

// Triggered on canvas changes
handleCanvasChange() {
    this.isDirty = true;
    this.scheduleAutoSave();
}

scheduleAutoSave() {
    // Clear existing timer
    if (this.autoSaveTimer) {
        clearTimeout(this.autoSaveTimer);
    }

    // Schedule new save after 500ms
    this.autoSaveTimer = setTimeout(() => {
        this.autoSave();
    }, this.autoSaveDelay);
}
```

### Auto-Save HTTP Request

```javascript
async autoSave() {
    if (!this.isDirty) return;

    try {
        // Serialize canvas to JSON
        const canvasJSON = JSON.stringify(this.canvas.toJSON());

        // POST to backend
        const response = await fetch(
            `/api/v1/image-editor/session/${this.sessionId}/annotation`,
            {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ canvas_json: canvasJSON })
            }
        );

        const result = await response.json();
        this.version = result.version;  // Update version number
        this.isDirty = false;

        // Update UI status
        this.updateSaveStatus('Saved', 'success');

        console.log('Auto-saved annotations, new version:', this.version);
    } catch (error) {
        console.error('Auto-save failed:', error);
        this.updateSaveStatus('Save failed', 'error');
    }
}
```

### Canvas Change Events

```javascript
// Listen for all canvas modifications
setupEventListeners() {
    this.canvas.on('object:added', () => this.handleCanvasChange());
    this.canvas.on('object:modified', () => this.handleCanvasChange());
    this.canvas.on('object:removed', () => this.handleCanvasChange());
    this.canvas.on('path:created', () => this.handleCanvasChange());
}
```

---

## Key Classes

### 1. ImageEditor (`static/js/image-editor.js`)

**Purpose**: Main controller for the image editor instance.

**Responsibilities**:
- Manage Fabric.js canvas
- Handle tool state (currentTool, currentColor, etc.)
- Coordinate DrawingTools and FilterEngine
- Auto-save canvas state
- Undo/redo management
- Keyboard shortcuts

**Key Properties**:
```javascript
class ImageEditor {
    sessionId: string           // Unique editor session ID
    canvas: fabric.Canvas       // Fabric.js canvas instance
    currentTool: string         // Active tool ('pen', 'rectangle', etc.)
    currentColor: string        // Stroke color
    currentStrokeWidth: number  // Stroke width
    currentFillEnabled: boolean // Fill shapes?
    currentFillColor: string    // Fill color (rgba)
    drawingTools: DrawingTools  // Shape drawing handler
    filterEngine: FilterEngine  // Filter management
    undoStack: Array            // Undo history
    redoStack: Array            // Redo history
}
```

**Key Methods**:
- `init()` - Initialize editor
- `setTool(tool)` - Change active tool
- `setColor(color)` - Update stroke color
- `setFillColor(color)` - Update fill color (converts to rgba)
- `autoSave()` - Save canvas to backend
- `undo()` / `redo()` - Navigate history
- `saveState()` - Add canvas state to undo stack

### 2. DrawingTools (`static/js/drawing-tools.js`)

**Purpose**: Handle shape creation and manipulation.

**Responsibilities**:
- Listen for mouse events on canvas
- Create shapes (rectangle, circle, line, arrow, text)
- Handle crop tool
- Handle eraser tool
- Keyboard event handling (Shift key for line snapping)

**Key Properties**:
```javascript
class DrawingTools {
    canvas: fabric.Canvas       // Reference to canvas
    editor: ImageEditor         // Reference to parent editor
    isDrawing: boolean          // Currently drawing?
    startX: number              // Mouse down X coordinate
    startY: number              // Mouse down Y coordinate
    currentShape: fabric.Object // Shape being drawn
    shiftHeld: boolean          // Shift key pressed?
}
```

**Key Methods**:
- `handleMouseDown(e)` - Start drawing
- `handleMouseMove(e)` - Update shape during drag
- `handleMouseUp(e)` - Finish drawing
- `startRectangle()` / `updateRectangle()` - Rectangle tool
- `startCircle()` / `updateCircle()` - Circle tool
- `startLine()` / `updateLine()` - Line tool
- `startArrow()` / `updateArrow()` - Arrow tool
- `addText()` - Text tool
- `handleKeyDown()` / `handleKeyUp()` - Keyboard events

### 3. FilterEngine (`static/js/filter-engine.js`)

**Purpose**: Apply image filters (brightness, contrast, saturation, blur, sharpen).

**Responsibilities**:
- Client-side CSS filters (brightness, contrast, saturation)
- Server-side filters via API (blur, sharpen)
- Live preview for client-side filters
- Apply permanent filters to canvas

**Key Properties**:
```javascript
class FilterEngine {
    sessionId: string
    canvas: fabric.Canvas
    brightness: number          // 0-200 (100 = normal)
    contrast: number            // 0-200 (100 = normal)
    saturation: number          // 0-200 (100 = normal)
    blur: number                // 0-20 pixels
    sharpen: number             // 0-10 intensity
}
```

**Key Methods**:
- `applyPreviewFilters()` - Apply CSS filters for live preview
- `applyFilters()` - Apply filters permanently via API
- `resetFilters()` - Reset all filters to default

---

## Troubleshooting Guide

### Issue: Shape Tools Don't Work (Rectangle, Circle, Line)

**Symptoms**: Clicking on canvas does nothing when rectangle/circle/line tool is selected.

**Root Cause**: DrawingTools.js not loaded.

**Solution**: Ensure `drawing-tools.js` is loaded BEFORE `image-editor.js` in `terminal.js`:

```javascript
// terminal.js - loadImageEditorDependencies()
await this.loadScript('/static/js/drawing-tools.js');  // Load FIRST
await this.loadScript('/static/js/image-editor.js');   // Load SECOND
```

**How to Verify**:
```javascript
// Check console for these logs:
[DrawingTools] Setting up mouse event listeners on canvas
[DrawingTools] Mouse event listeners registered
[ImageEditor] DrawingTools initialized: DrawingTools {...}
```

### Issue: Tool Buttons Don't Change Tool

**Symptoms**: Clicking tool buttons in toolbar doesn't change the active tool.

**Root Cause**: Event listeners not attached (Hyperscript events not firing, JavaScript fallbacks not set up).

**Solution**: Event listeners are set up in `terminal.js` after editor initialization:

```javascript
// terminal.js - handleImageViewer()
setTimeout(() => {
    const toolButtons = document.querySelectorAll('.tool-btn[data-tool]');
    toolButtons.forEach(btn => {
        btn.addEventListener('click', function(e) {
            const event = new CustomEvent('toolChange', {
                detail: { tool: this.getAttribute('data-tool') }
            });
            editorElement.dispatchEvent(event);
        });
    });
}, 300);
```

**How to Verify**:
```javascript
// Check console for:
[ImageViewer] Setting up event listeners, found 9 tool buttons
[ImageViewer] Tool button clicked: rectangle
Tool changed to: rectangle
```

### Issue: Colors Don't Change

**Root Cause**: Color change events not firing or not being handled.

**Solution**: Same as tool buttons - event listeners in `terminal.js`:

```javascript
const colorPicker = document.getElementById(`stroke-color-${sessionId}`);
colorPicker.addEventListener('input', function(e) {
    const event = new CustomEvent('colorChange', {
        detail: { color: this.value }
    });
    editorElement.dispatchEvent(event);
});
```

**How to Verify**:
```javascript
[ImageViewer] Color changed: #00ff00
```

### Issue: Clicking on Background Image Doesn't Start Drawing

**Root Cause**: DrawingTools filtering out clicks on `e.target`.

**Solution**: Allow clicks on `canvas.backgroundImage`:

```javascript
// drawing-tools.js - handleMouseDown()
if (e.target && e.target !== this.canvas.backgroundImage &&
    tool !== 'crop' && tool !== 'eraser') {
    return;  // Skip clicks on other objects
}
```

### Issue: Fill Color Shows Invalid Format Error

**Symptoms**: Console error: "The specified value '#ff000080' does not conform to required format"

**Root Cause**: HTML `<input type="color">` only accepts 6-digit hex (#rrggbb), not 8-digit with alpha.

**Solution**: Store fill color as `rgba()` format internally:

```javascript
// image-editor.js - setFillColor()
setFillColor(color) {
    if (color.startsWith('#') && color.length === 7) {
        const r = parseInt(color.substr(1, 2), 16);
        const g = parseInt(color.substr(3, 2), 16);
        const b = parseInt(color.substr(5, 2), 16);
        this.currentFillColor = `rgba(${r}, ${g}, ${b}, 0.3)`;  // 30% opacity
    }
}
```

### Issue: Auto-Save Not Working

**Symptoms**: Canvas changes don't persist after refresh.

**Root Cause**: Canvas event listeners not registered.

**Solution**: Ensure event listeners are set up in `setupEventListeners()`:

```javascript
setupEventListeners() {
    this.canvas.on('object:added', () => this.handleCanvasChange());
    this.canvas.on('object:modified', () => this.handleCanvasChange());
    this.canvas.on('object:removed', () => this.handleCanvasChange());
    this.canvas.on('path:created', () => this.handleCanvasChange());
}
```

**How to Verify**:
```javascript
// Check console after drawing:
Auto-saved annotations, new version: 2
```

### Issue: Shapes Appear But Don't Update During Drag

**Symptoms**: Rectangle appears as a dot, doesn't expand during drag.

**Root Cause**: `handleMouseMove()` not firing or `isDrawing` is false.

**Solution**: Verify `isDrawing` is set to `true` in `handleMouseDown()`:

```javascript
handleMouseDown(e) {
    this.isDrawing = true;  // Enable mouse move tracking
    this.startRectangle();
}
```

### Debugging Checklist

When shapes don't work, check in order:

1. ✅ **DrawingTools loaded?**
   - Look for `[DrawingTools] Setting up mouse event listeners`

2. ✅ **Tool changed?**
   - Look for `Tool changed to: rectangle`

3. ✅ **Mouse down event?**
   - Look for `[DrawingTools] Mouse down, tool: rectangle`

4. ✅ **Shape created?**
   - Look for `[DrawingTools] Creating rectangle`

5. ✅ **Shape added to canvas?**
   - Look for `[DrawingTools] Rectangle added to canvas`

6. ✅ **Mouse move firing?**
   - Drag should trigger `updateRectangle()` calls

---

## Performance Considerations

### Canvas Rendering

- Use `canvas.renderAll()` sparingly - it's expensive
- Batch updates when possible
- Only call `renderAll()` after final shape position is set

### Auto-Save Debouncing

- 500ms delay prevents excessive API calls
- Saves only when `isDirty` flag is true
- Clears pending save timer on new changes

### Event Listener Cleanup

When closing editor, remove event listeners to prevent memory leaks:

```javascript
closeEditor() {
    // Remove canvas event listeners
    this.canvas.off('object:added');
    this.canvas.off('object:modified');

    // Clear auto-save timer
    if (this.autoSaveTimer) {
        clearTimeout(this.autoSaveTimer);
    }

    // Dispose canvas
    this.canvas.dispose();
}
```

---

## Summary

The jterm image editor follows a **component-based architecture** with clear separation of concerns:

1. **Terminal.js** - Entry point, loads dependencies, manages overlay
2. **ImageEditor** - Canvas controller, tool state, auto-save
3. **DrawingTools** - Shape creation, mouse event handling
4. **FilterEngine** - Image filter management

**Key Flow**: `imgcat` → Load Dependencies → Fetch HTML → Initialize Editor → Setup Event Listeners → User Interaction → Auto-Save

**Critical Dependencies**: DrawingTools MUST load before ImageEditor!

**Event System**: Custom events bridge UI controls to editor logic with JavaScript fallbacks for Hyperscript.

**Common Issues**: Missing dependencies, event listeners not attached, background image click blocking.

---

**For more information**:
- See `static/js/image-editor.js` for canvas management
- See `static/js/drawing-tools.js` for shape implementations
- See `templates/components/toolbar.html` for UI controls
- See `static/js/terminal.js` for initialization flow

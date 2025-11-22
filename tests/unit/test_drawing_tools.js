/**
 * Unit tests for shape drawing tools (T116)
 *
 * Tests rectangle, circle, and line tool creation with Fabric.js
 */

describe('DrawingTools - Shape Tool Logic', () => {
    let mockCanvas;
    let drawingTools;

    beforeEach(() => {
        // Mock Fabric.js canvas
        mockCanvas = {
            add: jest.fn(),
            setActiveObject: jest.fn(),
            renderAll: jest.fn(),
            getObjects: jest.fn(() => []),
            remove: jest.fn(),
            discardActiveObject: jest.fn(),
            selection: true
        };

        // Mock Fabric.js shape constructors
        global.fabric = {
            Rect: jest.fn((options) => ({
                type: 'rect',
                ...options,
                set: jest.fn(function(key, value) {
                    this[key] = value;
                    return this;
                }),
                setCoords: jest.fn()
            })),
            Circle: jest.fn((options) => ({
                type: 'circle',
                ...options,
                set: jest.fn(function(key, value) {
                    this[key] = value;
                    return this;
                }),
                setCoords: jest.fn()
            })),
            Line: jest.fn((coords, options) => ({
                type: 'line',
                coords,
                ...options,
                set: jest.fn(function(key, value) {
                    this[key] = value;
                    return this;
                }),
                setCoords: jest.fn()
            }))
        };

        // Mock DrawingTools class (to be implemented in static/js/drawing-tools.js)
        class MockDrawingTools {
            constructor(canvas) {
                this.canvas = canvas;
                this.activeTool = null;
                this.strokeColor = '#FF0000';
                this.strokeWidth = 2;
                this.fillEnabled = false;
                this.fillColor = 'rgba(255, 0, 0, 0.3)';
                this.isDrawing = false;
                this.currentShape = null;
                this.startX = 0;
                this.startY = 0;
            }

            setTool(toolName) {
                this.activeTool = toolName;
                this.canvas.selection = (toolName === 'select');
            }

            setStrokeColor(color) {
                this.strokeColor = color;
            }

            setStrokeWidth(width) {
                this.strokeWidth = Math.max(1, Math.min(20, width));
            }

            setFillEnabled(enabled) {
                this.fillEnabled = enabled;
            }

            setFillColor(color) {
                this.fillColor = color;
            }

            startDrawing(x, y) {
                if (!this.activeTool || this.activeTool === 'select') return;

                this.isDrawing = true;
                this.startX = x;
                this.startY = y;

                if (this.activeTool === 'rectangle') {
                    this.currentShape = new fabric.Rect({
                        left: x,
                        top: y,
                        width: 0,
                        height: 0,
                        stroke: this.strokeColor,
                        strokeWidth: this.strokeWidth,
                        fill: this.fillEnabled ? this.fillColor : 'transparent',
                        selectable: false
                    });
                } else if (this.activeTool === 'circle') {
                    this.currentShape = new fabric.Circle({
                        left: x,
                        top: y,
                        radius: 0,
                        stroke: this.strokeColor,
                        strokeWidth: this.strokeWidth,
                        fill: this.fillEnabled ? this.fillColor : 'transparent',
                        selectable: false
                    });
                } else if (this.activeTool === 'line') {
                    this.currentShape = new fabric.Line([x, y, x, y], {
                        stroke: this.strokeColor,
                        strokeWidth: this.strokeWidth,
                        selectable: false
                    });
                }

                if (this.currentShape) {
                    this.canvas.add(this.currentShape);
                }
            }

            updateDrawing(x, y, shiftKey = false) {
                if (!this.isDrawing || !this.currentShape) return;

                if (this.activeTool === 'rectangle') {
                    const width = x - this.startX;
                    const height = y - this.startY;

                    this.currentShape.set({
                        width: Math.abs(width),
                        height: Math.abs(height),
                        left: width < 0 ? x : this.startX,
                        top: height < 0 ? y : this.startY
                    });
                } else if (this.activeTool === 'circle') {
                    const radius = Math.sqrt(
                        Math.pow(x - this.startX, 2) + Math.pow(y - this.startY, 2)
                    );
                    this.currentShape.set({ radius });
                } else if (this.activeTool === 'line') {
                    let endX = x;
                    let endY = y;

                    // Snap to 45° angles when Shift is pressed
                    if (shiftKey) {
                        const dx = x - this.startX;
                        const dy = y - this.startY;
                        const angle = Math.atan2(dy, dx);
                        const snapAngle = Math.round(angle / (Math.PI / 4)) * (Math.PI / 4);
                        const distance = Math.sqrt(dx * dx + dy * dy);

                        endX = this.startX + distance * Math.cos(snapAngle);
                        endY = this.startY + distance * Math.sin(snapAngle);
                    }

                    this.currentShape.set({
                        x2: endX,
                        y2: endY
                    });
                }

                this.currentShape.setCoords();
                this.canvas.renderAll();
            }

            finishDrawing() {
                if (!this.isDrawing) return null;

                this.isDrawing = false;
                const shape = this.currentShape;
                this.currentShape = null;

                if (shape) {
                    shape.set({ selectable: true });
                    shape.setCoords();
                }

                return shape;
            }
        }

        drawingTools = new MockDrawingTools(mockCanvas);
    });

    describe('Tool selection', () => {
        test('should set active tool to rectangle', () => {
            drawingTools.setTool('rectangle');

            expect(drawingTools.activeTool).toBe('rectangle');
        });

        test('should set active tool to circle', () => {
            drawingTools.setTool('circle');

            expect(drawingTools.activeTool).toBe('circle');
        });

        test('should set active tool to line', () => {
            drawingTools.setTool('line');

            expect(drawingTools.activeTool).toBe('line');
        });

        test('should enable canvas selection when select tool is active', () => {
            drawingTools.setTool('select');

            expect(mockCanvas.selection).toBe(true);
        });

        test('should disable canvas selection when drawing tool is active', () => {
            drawingTools.setTool('rectangle');

            expect(mockCanvas.selection).toBe(false);
        });
    });

    describe('Rectangle tool', () => {
        test('should create Fabric.Rect on startDrawing', () => {
            drawingTools.setTool('rectangle');
            drawingTools.startDrawing(100, 100);

            expect(fabric.Rect).toHaveBeenCalledWith(
                expect.objectContaining({
                    left: 100,
                    top: 100,
                    width: 0,
                    height: 0,
                    stroke: '#FF0000',
                    strokeWidth: 2
                })
            );

            expect(mockCanvas.add).toHaveBeenCalled();
        });

        test('should use active stroke color and width', () => {
            drawingTools.setTool('rectangle');
            drawingTools.setStrokeColor('#00FF00');
            drawingTools.setStrokeWidth(5);
            drawingTools.startDrawing(50, 50);

            expect(fabric.Rect).toHaveBeenCalledWith(
                expect.objectContaining({
                    stroke: '#00FF00',
                    strokeWidth: 5
                })
            );
        });

        test('should apply fill when fillEnabled is true', () => {
            drawingTools.setTool('rectangle');
            drawingTools.setFillEnabled(true);
            drawingTools.setFillColor('rgba(0, 255, 0, 0.5)');
            drawingTools.startDrawing(50, 50);

            expect(fabric.Rect).toHaveBeenCalledWith(
                expect.objectContaining({
                    fill: 'rgba(0, 255, 0, 0.5)'
                })
            );
        });

        test('should use transparent fill when fillEnabled is false', () => {
            drawingTools.setTool('rectangle');
            drawingTools.setFillEnabled(false);
            drawingTools.startDrawing(50, 50);

            expect(fabric.Rect).toHaveBeenCalledWith(
                expect.objectContaining({
                    fill: 'transparent'
                })
            );
        });

        test('should update rectangle dimensions during drag', () => {
            drawingTools.setTool('rectangle');
            drawingTools.startDrawing(100, 100);
            drawingTools.updateDrawing(200, 150);

            expect(drawingTools.currentShape.set).toHaveBeenCalledWith(
                expect.objectContaining({
                    width: 100,
                    height: 50
                })
            );
        });

        test('should handle negative drag direction', () => {
            drawingTools.setTool('rectangle');
            drawingTools.startDrawing(100, 100);
            drawingTools.updateDrawing(50, 75);

            expect(drawingTools.currentShape.set).toHaveBeenCalledWith(
                expect.objectContaining({
                    width: 50,
                    height: 25,
                    left: 50,
                    top: 75
                })
            );
        });

        test('should make rectangle selectable after finishDrawing', () => {
            drawingTools.setTool('rectangle');
            drawingTools.startDrawing(100, 100);
            drawingTools.updateDrawing(200, 150);
            const shape = drawingTools.finishDrawing();

            expect(shape.set).toHaveBeenCalledWith({ selectable: true });
        });
    });

    describe('Circle tool', () => {
        test('should create Fabric.Circle on startDrawing', () => {
            drawingTools.setTool('circle');
            drawingTools.startDrawing(150, 150);

            expect(fabric.Circle).toHaveBeenCalledWith(
                expect.objectContaining({
                    left: 150,
                    top: 150,
                    radius: 0,
                    stroke: '#FF0000',
                    strokeWidth: 2
                })
            );

            expect(mockCanvas.add).toHaveBeenCalled();
        });

        test('should calculate radius based on distance from center', () => {
            drawingTools.setTool('circle');
            drawingTools.startDrawing(100, 100);
            drawingTools.updateDrawing(140, 130); // Distance: 50px

            const expectedRadius = Math.sqrt(40 * 40 + 30 * 30);

            expect(drawingTools.currentShape.set).toHaveBeenCalledWith({
                radius: expectedRadius
            });
        });

        test('should support fill toggle', () => {
            drawingTools.setTool('circle');
            drawingTools.setFillEnabled(true);
            drawingTools.setFillColor('rgba(0, 0, 255, 0.4)');
            drawingTools.startDrawing(100, 100);

            expect(fabric.Circle).toHaveBeenCalledWith(
                expect.objectContaining({
                    fill: 'rgba(0, 0, 255, 0.4)'
                })
            );
        });

        test('should make circle selectable after finishDrawing', () => {
            drawingTools.setTool('circle');
            drawingTools.startDrawing(100, 100);
            drawingTools.updateDrawing(150, 150);
            const shape = drawingTools.finishDrawing();

            expect(shape.set).toHaveBeenCalledWith({ selectable: true });
        });
    });

    describe('Line tool', () => {
        test('should create Fabric.Line on startDrawing', () => {
            drawingTools.setTool('line');
            drawingTools.startDrawing(50, 50);

            expect(fabric.Line).toHaveBeenCalledWith(
                [50, 50, 50, 50],
                expect.objectContaining({
                    stroke: '#FF0000',
                    strokeWidth: 2
                })
            );

            expect(mockCanvas.add).toHaveBeenCalled();
        });

        test('should update line endpoint during drag', () => {
            drawingTools.setTool('line');
            drawingTools.startDrawing(100, 100);
            drawingTools.updateDrawing(200, 150);

            expect(drawingTools.currentShape.set).toHaveBeenCalledWith({
                x2: 200,
                y2: 150
            });
        });

        test('should snap to 45° angles when Shift key is pressed', () => {
            drawingTools.setTool('line');
            drawingTools.startDrawing(100, 100);

            // Dragging to approximately 30° should snap to 45°
            drawingTools.updateDrawing(200, 120, true);

            // Calculate expected snap coordinates
            const dx = 200 - 100;
            const dy = 120 - 100;
            const angle = Math.atan2(dy, dx);
            const snapAngle = Math.round(angle / (Math.PI / 4)) * (Math.PI / 4);
            const distance = Math.sqrt(dx * dx + dy * dy);

            const expectedX = 100 + distance * Math.cos(snapAngle);
            const expectedY = 100 + distance * Math.sin(snapAngle);

            expect(drawingTools.currentShape.set).toHaveBeenCalledWith({
                x2: expectedX,
                y2: expectedY
            });
        });

        test('should not snap when Shift key is not pressed', () => {
            drawingTools.setTool('line');
            drawingTools.startDrawing(100, 100);
            drawingTools.updateDrawing(200, 150, false);

            expect(drawingTools.currentShape.set).toHaveBeenCalledWith({
                x2: 200,
                y2: 150
            });
        });

        test('should make line selectable after finishDrawing', () => {
            drawingTools.setTool('line');
            drawingTools.startDrawing(100, 100);
            drawingTools.updateDrawing(200, 150);
            const shape = drawingTools.finishDrawing();

            expect(shape.set).toHaveBeenCalledWith({ selectable: true });
        });
    });

    describe('Stroke customization', () => {
        test('should update stroke color for new shapes', () => {
            drawingTools.setStrokeColor('#0000FF');

            expect(drawingTools.strokeColor).toBe('#0000FF');
        });

        test('should clamp stroke width to 1-20 range', () => {
            drawingTools.setStrokeWidth(25);
            expect(drawingTools.strokeWidth).toBe(20);

            drawingTools.setStrokeWidth(0);
            expect(drawingTools.strokeWidth).toBe(1);
        });
    });

    describe('Fill customization', () => {
        test('should toggle fill enabled state', () => {
            drawingTools.setFillEnabled(true);
            expect(drawingTools.fillEnabled).toBe(true);

            drawingTools.setFillEnabled(false);
            expect(drawingTools.fillEnabled).toBe(false);
        });

        test('should update fill color', () => {
            drawingTools.setFillColor('rgba(255, 255, 0, 0.6)');

            expect(drawingTools.fillColor).toBe('rgba(255, 255, 0, 0.6)');
        });
    });

    describe('Drawing state management', () => {
        test('should track drawing state', () => {
            expect(drawingTools.isDrawing).toBe(false);

            drawingTools.setTool('rectangle');
            drawingTools.startDrawing(100, 100);

            expect(drawingTools.isDrawing).toBe(true);

            drawingTools.finishDrawing();

            expect(drawingTools.isDrawing).toBe(false);
        });

        test('should not start drawing when select tool is active', () => {
            drawingTools.setTool('select');
            drawingTools.startDrawing(100, 100);

            expect(drawingTools.isDrawing).toBe(false);
            expect(mockCanvas.add).not.toHaveBeenCalled();
        });

        test('should return shape from finishDrawing', () => {
            drawingTools.setTool('rectangle');
            drawingTools.startDrawing(100, 100);
            drawingTools.updateDrawing(200, 150);

            const shape = drawingTools.finishDrawing();

            expect(shape).toBeDefined();
            expect(shape.type).toBe('rect');
        });

        test('should return null from finishDrawing when not drawing', () => {
            const shape = drawingTools.finishDrawing();

            expect(shape).toBeNull();
        });
    });

    describe('Text formatting (T127)', () => {
        beforeEach(() => {
            // Mock Fabric.IText
            global.fabric.IText = jest.fn((text, options) => ({
                type: 'i-text',
                text,
                ...options,
                set: jest.fn(function(key, value) {
                    if (typeof key === 'object') {
                        Object.assign(this, key);
                    } else {
                        this[key] = value;
                    }
                    return this;
                }),
                setCoords: jest.fn(),
                enterEditing: jest.fn(),
                selectAll: jest.fn()
            }));
        });

        test('should create text with specified font size', () => {
            drawingTools.setTool('text');
            drawingTools.editor.currentFontSize = 24;
            drawingTools.addText(100, 100);

            expect(fabric.IText).toHaveBeenCalledWith(
                'Text',
                expect.objectContaining({
                    fontSize: 24
                })
            );
        });

        test('should create text with bold font weight', () => {
            drawingTools.setTool('text');
            drawingTools.editor.currentBold = true;
            drawingTools.addText(100, 100);

            expect(fabric.IText).toHaveBeenCalledWith(
                'Text',
                expect.objectContaining({
                    fontWeight: 'bold'
                })
            );
        });

        test('should create text with italic font style', () => {
            drawingTools.setTool('text');
            drawingTools.editor.currentItalic = true;
            drawingTools.addText(100, 100);

            expect(fabric.IText).toHaveBeenCalledWith(
                'Text',
                expect.objectContaining({
                    fontStyle: 'italic'
                })
            );
        });

        test('should create text with background color when enabled', () => {
            drawingTools.setTool('text');
            drawingTools.editor.currentTextBackground = true;
            drawingTools.editor.currentFillColor = 'rgba(255, 255, 0, 0.8)';
            drawingTools.addText(100, 100);

            expect(fabric.IText).toHaveBeenCalledWith(
                'Text',
                expect.objectContaining({
                    backgroundColor: 'rgba(255, 255, 0, 0.8)'
                })
            );
        });

        test('should create text without background when disabled', () => {
            drawingTools.setTool('text');
            drawingTools.editor.currentTextBackground = false;
            drawingTools.addText(100, 100);

            const textObject = mockCanvas.add.mock.calls[0][0];
            expect(textObject.backgroundColor).toBeUndefined();
        });

        test('should create text with all formatting combined', () => {
            drawingTools.setTool('text');
            drawingTools.editor.currentFontSize = 32;
            drawingTools.editor.currentBold = true;
            drawingTools.editor.currentItalic = true;
            drawingTools.editor.currentTextBackground = true;
            drawingTools.editor.currentFillColor = 'rgba(255, 0, 0, 0.5)';
            drawingTools.editor.currentColor = '#0000FF';

            drawingTools.addText(150, 200);

            expect(fabric.IText).toHaveBeenCalledWith(
                'Text',
                expect.objectContaining({
                    fontSize: 32,
                    fontWeight: 'bold',
                    fontStyle: 'italic',
                    fill: '#0000FF',
                    backgroundColor: 'rgba(255, 0, 0, 0.5)'
                })
            );
        });

        test('should apply font size to existing selected text', () => {
            const mockText = {
                type: 'i-text',
                fontSize: 18,
                set: jest.fn()
            };

            mockCanvas.getActiveObject = jest.fn(() => mockText);

            drawingTools.updateTextFormatting('fontSize', 28);

            expect(mockText.set).toHaveBeenCalledWith('fontSize', 28);
            expect(mockCanvas.renderAll).toHaveBeenCalled();
        });

        test('should toggle bold on selected text', () => {
            const mockText = {
                type: 'i-text',
                fontWeight: 'normal',
                set: jest.fn()
            };

            mockCanvas.getActiveObject = jest.fn(() => mockText);

            drawingTools.updateTextFormatting('fontWeight', 'bold');

            expect(mockText.set).toHaveBeenCalledWith('fontWeight', 'bold');
        });

        test('should toggle italic on selected text', () => {
            const mockText = {
                type: 'i-text',
                fontStyle: 'normal',
                set: jest.fn()
            };

            mockCanvas.getActiveObject = jest.fn(() => mockText);

            drawingTools.updateTextFormatting('fontStyle', 'italic');

            expect(mockText.set).toHaveBeenCalledWith('fontStyle', 'italic');
        });

        test('should add background color to selected text', () => {
            const mockText = {
                type: 'i-text',
                set: jest.fn()
            };

            mockCanvas.getActiveObject = jest.fn(() => mockText);

            drawingTools.updateTextFormatting('backgroundColor', 'rgba(255, 255, 0, 0.8)');

            expect(mockText.set).toHaveBeenCalledWith('backgroundColor', 'rgba(255, 255, 0, 0.8)');
        });

        test('should not update formatting if no text is selected', () => {
            mockCanvas.getActiveObject = jest.fn(() => null);

            drawingTools.updateTextFormatting('fontSize', 24);

            expect(mockCanvas.renderAll).not.toHaveBeenCalled();
        });

        test('should not update formatting if selected object is not text', () => {
            const mockRect = {
                type: 'rect',
                set: jest.fn()
            };

            mockCanvas.getActiveObject = jest.fn(() => mockRect);

            drawingTools.updateTextFormatting('fontSize', 24);

            expect(mockRect.set).not.toHaveBeenCalled();
        });
    });
});

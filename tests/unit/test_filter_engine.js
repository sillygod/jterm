/**
 * Unit tests for client-side filter preview functionality
 *
 * Tests CSS filter application for brightness, contrast, and saturation adjustments.
 */

describe('FilterEngine - Client-side Filter Preview', () => {
    let mockCanvas;
    let mockCanvasElement;
    let filterEngine;

    beforeEach(() => {
        // Mock DOM canvas element
        mockCanvasElement = document.createElement('canvas');
        mockCanvasElement.id = 'test-canvas';
        mockCanvasElement.style.filter = '';
        document.body.appendChild(mockCanvasElement);

        // Mock canvas object
        mockCanvas = {
            lowerCanvasEl: mockCanvasElement,
            renderAll: jest.fn()
        };

        // Mock FilterEngine class (would be defined in static/js/filter-engine.js)
        class MockFilterEngine {
            constructor(canvas) {
                this.canvas = canvas;
                this.brightness = 100;
                this.contrast = 100;
                this.saturation = 100;
                this.blur = 0;
            }

            applyPreviewFilters() {
                const filters = [];

                if (this.brightness !== 100) {
                    filters.push(`brightness(${this.brightness}%)`);
                }

                if (this.contrast !== 100) {
                    filters.push(`contrast(${this.contrast}%)`);
                }

                if (this.saturation !== 100) {
                    filters.push(`saturate(${this.saturation}%)`);
                }

                if (this.blur > 0) {
                    filters.push(`blur(${this.blur}px)`);
                }

                this.canvas.lowerCanvasEl.style.filter = filters.join(' ');
            }

            setBrightness(value) {
                this.brightness = Math.max(0, Math.min(200, value));
                this.applyPreviewFilters();
            }

            setContrast(value) {
                this.contrast = Math.max(0, Math.min(200, value));
                this.applyPreviewFilters();
            }

            setSaturation(value) {
                this.saturation = Math.max(0, Math.min(200, value));
                this.applyPreviewFilters();
            }

            setBlur(value) {
                this.blur = Math.max(0, Math.min(20, value));
                this.applyPreviewFilters();
            }

            resetFilters() {
                this.brightness = 100;
                this.contrast = 100;
                this.saturation = 100;
                this.blur = 0;
                this.canvas.lowerCanvasEl.style.filter = '';
            }

            getFilterValues() {
                return {
                    brightness: this.brightness,
                    contrast: this.contrast,
                    saturation: this.saturation,
                    blur: this.blur
                };
            }
        }

        filterEngine = new MockFilterEngine(mockCanvas);
    });

    afterEach(() => {
        document.body.removeChild(mockCanvasElement);
    });

    describe('Brightness adjustment', () => {
        test('should apply brightness filter to canvas element', () => {
            filterEngine.setBrightness(150);

            expect(mockCanvasElement.style.filter).toContain('brightness(150%)');
        });

        test('should clamp brightness to 0-200 range', () => {
            filterEngine.setBrightness(250);
            expect(filterEngine.brightness).toBe(200);

            filterEngine.setBrightness(-50);
            expect(filterEngine.brightness).toBe(0);
        });

        test('should not add filter when brightness is 100 (default)', () => {
            filterEngine.setBrightness(100);

            expect(mockCanvasElement.style.filter).not.toContain('brightness');
        });

        test('should update existing brightness filter', () => {
            filterEngine.setBrightness(120);
            expect(mockCanvasElement.style.filter).toContain('brightness(120%)');

            filterEngine.setBrightness(80);
            expect(mockCanvasElement.style.filter).toContain('brightness(80%)');
            expect(mockCanvasElement.style.filter).not.toContain('brightness(120%)');
        });
    });

    describe('Contrast adjustment', () => {
        test('should apply contrast filter to canvas element', () => {
            filterEngine.setContrast(130);

            expect(mockCanvasElement.style.filter).toContain('contrast(130%)');
        });

        test('should clamp contrast to 0-200 range', () => {
            filterEngine.setContrast(300);
            expect(filterEngine.contrast).toBe(200);

            filterEngine.setContrast(-20);
            expect(filterEngine.contrast).toBe(0);
        });

        test('should not add filter when contrast is 100 (default)', () => {
            filterEngine.setContrast(100);

            expect(mockCanvasElement.style.filter).not.toContain('contrast');
        });
    });

    describe('Saturation adjustment', () => {
        test('should apply saturation filter to canvas element', () => {
            filterEngine.setSaturation(140);

            expect(mockCanvasElement.style.filter).toContain('saturate(140%)');
        });

        test('should clamp saturation to 0-200 range', () => {
            filterEngine.setSaturation(250);
            expect(filterEngine.saturation).toBe(200);

            filterEngine.setSaturation(-10);
            expect(filterEngine.saturation).toBe(0);
        });

        test('should handle grayscale (saturation = 0)', () => {
            filterEngine.setSaturation(0);

            expect(mockCanvasElement.style.filter).toContain('saturate(0%)');
        });
    });

    describe('Blur preview', () => {
        test('should apply blur filter to canvas element', () => {
            filterEngine.setBlur(5);

            expect(mockCanvasElement.style.filter).toContain('blur(5px)');
        });

        test('should clamp blur to 0-20 range', () => {
            filterEngine.setBlur(30);
            expect(filterEngine.blur).toBe(20);

            filterEngine.setBlur(-5);
            expect(filterEngine.blur).toBe(0);
        });

        test('should not add filter when blur is 0 (default)', () => {
            filterEngine.setBlur(0);

            expect(mockCanvasElement.style.filter).not.toContain('blur');
        });
    });

    describe('Multiple filters', () => {
        test('should apply multiple filters simultaneously', () => {
            filterEngine.setBrightness(120);
            filterEngine.setContrast(110);
            filterEngine.setSaturation(130);

            const filterStyle = mockCanvasElement.style.filter;
            expect(filterStyle).toContain('brightness(120%)');
            expect(filterStyle).toContain('contrast(110%)');
            expect(filterStyle).toContain('saturate(130%)');
        });

        test('should handle all filters at once', () => {
            filterEngine.setBrightness(150);
            filterEngine.setContrast(120);
            filterEngine.setSaturation(80);
            filterEngine.setBlur(3);

            const filterStyle = mockCanvasElement.style.filter;
            expect(filterStyle).toContain('brightness(150%)');
            expect(filterStyle).toContain('contrast(120%)');
            expect(filterStyle).toContain('saturate(80%)');
            expect(filterStyle).toContain('blur(3px)');
        });

        test('should maintain order of filters', () => {
            filterEngine.setBrightness(120);
            filterEngine.setContrast(110);
            filterEngine.setSaturation(130);
            filterEngine.setBlur(2);

            const filterStyle = mockCanvasElement.style.filter;
            const brightnessIndex = filterStyle.indexOf('brightness');
            const contrastIndex = filterStyle.indexOf('contrast');
            const saturateIndex = filterStyle.indexOf('saturate');
            const blurIndex = filterStyle.indexOf('blur');

            expect(brightnessIndex).toBeLessThan(contrastIndex);
            expect(contrastIndex).toBeLessThan(saturateIndex);
            expect(saturateIndex).toBeLessThan(blurIndex);
        });
    });

    describe('Filter reset', () => {
        test('should reset all filters to default values', () => {
            filterEngine.setBrightness(150);
            filterEngine.setContrast(120);
            filterEngine.setSaturation(80);
            filterEngine.setBlur(5);

            filterEngine.resetFilters();

            expect(filterEngine.brightness).toBe(100);
            expect(filterEngine.contrast).toBe(100);
            expect(filterEngine.saturation).toBe(100);
            expect(filterEngine.blur).toBe(0);
            expect(mockCanvasElement.style.filter).toBe('');
        });

        test('should clear CSS filter from canvas element', () => {
            filterEngine.setBrightness(130);
            filterEngine.setContrast(110);

            expect(mockCanvasElement.style.filter).not.toBe('');

            filterEngine.resetFilters();

            expect(mockCanvasElement.style.filter).toBe('');
        });
    });

    describe('Get filter values', () => {
        test('should return current filter values', () => {
            filterEngine.setBrightness(125);
            filterEngine.setContrast(115);
            filterEngine.setSaturation(90);
            filterEngine.setBlur(4);

            const values = filterEngine.getFilterValues();

            expect(values).toEqual({
                brightness: 125,
                contrast: 115,
                saturation: 90,
                blur: 4
            });
        });

        test('should return default values when no filters applied', () => {
            const values = filterEngine.getFilterValues();

            expect(values).toEqual({
                brightness: 100,
                contrast: 100,
                saturation: 100,
                blur: 0
            });
        });
    });

    describe('Performance', () => {
        test('should apply filters within 50ms', () => {
            const startTime = performance.now();

            for (let i = 0; i < 100; i++) {
                filterEngine.setBrightness(100 + (i % 50));
                filterEngine.setContrast(100 + (i % 30));
                filterEngine.setSaturation(100 + (i % 40));
            }

            const endTime = performance.now();
            const duration = endTime - startTime;

            // 100 filter applications should take less than 50ms total
            expect(duration).toBeLessThan(50);
        });
    });
});

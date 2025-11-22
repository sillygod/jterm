/**
 * FilterEngine - Client-side image filter and adjustment engine
 *
 * Provides real-time preview of CSS-based filters (brightness, contrast, saturation)
 * and manages server-side filter operations (blur, sharpen).
 *
 * Features:
 * - Live preview with <200ms update time
 * - CSS filter manipulation for client-side adjustments
 * - Server-side filter integration for blur/sharpen
 * - Filter state management and reset functionality
 */

class FilterEngine {
    /**
     * Initialize the filter engine for a canvas session
     * @param {string} sessionId - Image editor session ID
     * @param {fabric.Canvas} canvas - Fabric.js canvas instance
     */
    constructor(sessionId, canvas) {
        this.sessionId = sessionId;
        this.canvas = canvas;

        // Filter state
        this.filters = {
            brightness: 100,  // 0-200%
            contrast: 100,    // 0-200%
            saturate: 100,    // 0-200% (saturation)
            blur: 0,          // 0-20px (server-side)
            sharpen: 0        // 0-10 (server-side)
        };

        // Default filter values
        this.defaults = { ...this.filters };

        // Debounce timer for preview updates
        this.previewTimer = null;
        this.previewDelay = 50; // 50ms debounce for smooth updates

        // Initialize event listeners
        this.init();
    }

    /**
     * Initialize filter controls and event listeners
     */
    init() {
        // Client-side filter sliders (live preview)
        this.initClientSideFilter('brightness');
        this.initClientSideFilter('contrast');
        this.initClientSideFilter('saturate', 'saturation');

        // Server-side filter sliders (requires apply)
        this.initServerSideFilter('blur');
        this.initServerSideFilter('sharpen');

        // Apply and Reset buttons
        this.initActionButtons();

        console.log(`[FilterEngine] Initialized for session ${this.sessionId}`);
    }

    /**
     * Initialize a client-side filter slider with live preview
     * @param {string} filterType - Filter type (brightness, contrast, saturate)
     * @param {string} sliderId - Optional custom slider ID prefix
     */
    initClientSideFilter(filterType, sliderId = null) {
        const id = sliderId || filterType;
        const slider = document.getElementById(`${id}-${this.sessionId}`);
        const valueDisplay = document.getElementById(`${id}-value-${this.sessionId}`);

        if (!slider) {
            console.warn(`[FilterEngine] Slider not found: ${id}-${this.sessionId}`);
            return;
        }

        // Update on slider input (real-time preview)
        slider.addEventListener('input', (e) => {
            const value = parseFloat(e.target.value);
            this.filters[filterType] = value;

            // Update value display
            const unit = slider.dataset.unit || '';
            if (valueDisplay) {
                valueDisplay.textContent = `${value}${unit}`;
            }

            // Apply preview with debouncing
            this.schedulePreviewUpdate();
        });

        console.log(`[FilterEngine] Initialized client-side filter: ${filterType}`);
    }

    /**
     * Initialize a server-side filter slider
     * @param {string} filterType - Filter type (blur, sharpen)
     */
    initServerSideFilter(filterType) {
        const slider = document.getElementById(`${filterType}-${this.sessionId}`);
        const valueDisplay = document.getElementById(`${filterType}-value-${this.sessionId}`);
        const applyBtn = document.getElementById(`apply-${filterType}-${this.sessionId}`);

        if (!slider) {
            console.warn(`[FilterEngine] Server-side slider not found: ${filterType}-${this.sessionId}`);
            return;
        }

        // Update value display on slider change
        slider.addEventListener('input', (e) => {
            const value = parseFloat(e.target.value);
            this.filters[filterType] = value;

            // Update value display
            const unit = slider.dataset.unit || '';
            if (valueDisplay) {
                valueDisplay.textContent = `${value}${unit}`;
            }

            // Enable apply button if value changed from default
            if (applyBtn) {
                applyBtn.disabled = (value === 0);
            }
        });

        // Apply button handler
        if (applyBtn) {
            applyBtn.addEventListener('click', () => {
                this.applyServerSideFilter(filterType);
            });
        }

        console.log(`[FilterEngine] Initialized server-side filter: ${filterType}`);
    }

    /**
     * Initialize Apply and Reset All buttons
     */
    initActionButtons() {
        // Apply Adjustments button (commits client-side filters)
        const applyBtn = document.getElementById(`apply-filters-${this.sessionId}`);
        if (applyBtn) {
            applyBtn.addEventListener('click', () => {
                this.applyClientSideFilters();
            });
        }

        // Reset All button
        const resetBtn = document.getElementById(`reset-filters-${this.sessionId}`);
        if (resetBtn) {
            resetBtn.addEventListener('click', () => {
                this.resetAllFilters();
            });
        }
    }

    /**
     * Schedule a preview update with debouncing
     * Ensures updates happen no more frequently than previewDelay ms
     */
    schedulePreviewUpdate() {
        // Clear existing timer
        if (this.previewTimer) {
            clearTimeout(this.previewTimer);
        }

        // Schedule new update
        this.previewTimer = setTimeout(() => {
            this.applyPreviewFilters();
        }, this.previewDelay);
    }

    /**
     * Apply client-side filters as CSS preview (T079, T080, T081)
     * Updates canvas CSS filters for real-time preview
     * Performance target: <200ms
     */
    applyPreviewFilters() {
        const startTime = performance.now();

        // Build CSS filter string from current filter values
        const filterParts = [];

        // Only include filters that differ from default (100%)
        if (this.filters.brightness !== 100) {
            filterParts.push(`brightness(${this.filters.brightness}%)`);
        }
        if (this.filters.contrast !== 100) {
            filterParts.push(`contrast(${this.filters.contrast}%)`);
        }
        if (this.filters.saturate !== 100) {
            filterParts.push(`saturate(${this.filters.saturate}%)`);
        }

        // Apply CSS filter to the canvas element
        const canvasEl = this.canvas.lowerCanvasEl;
        if (canvasEl) {
            canvasEl.style.filter = filterParts.join(' ');
        }

        const elapsed = performance.now() - startTime;
        console.log(`[FilterEngine] Preview updated in ${elapsed.toFixed(2)}ms`);

        // Warn if performance threshold exceeded
        if (elapsed > 200) {
            console.warn(`[FilterEngine] Preview update exceeded 200ms threshold: ${elapsed.toFixed(2)}ms`);
        }
    }

    /**
     * Apply and commit client-side filters (T082 + T089)
     * Converts CSS preview filters to permanent canvas filters
     * Clears CSS preview after committing
     * Saves state for undo/redo
     */
    async applyClientSideFilters() {
        console.log('[FilterEngine] Applying client-side filters permanently');

        try {
            // Show loading indicator
            this.showLoading();

            // Get current CSS filters
            const canvasEl = this.canvas.lowerCanvasEl;
            const currentCSSFilter = canvasEl ? canvasEl.style.filter : '';

            if (!currentCSSFilter) {
                console.log('[FilterEngine] No filters to apply');
                this.hideLoading();
                return;
            }

            // T089: Save state for undo before applying filters
            if (window.ImageEditor && window.ImageEditor.instances) {
                const editor = window.ImageEditor.instances[this.sessionId];
                if (editor && editor.saveStateForUndo) {
                    await editor.saveStateForUndo();
                    console.log('[FilterEngine] Saved state for undo before applying filters');
                }
            }

            // Method 1: Use Fabric.js filters to apply to background image
            // This makes the filters permanent by converting to image data
            const bgImage = this.canvas.backgroundImage;

            if (bgImage) {
                // Apply brightness filter
                if (this.filters.brightness !== 100) {
                    const brightnessValue = (this.filters.brightness - 100) / 100; // Convert to -1 to 1 range
                    bgImage.filters = bgImage.filters || [];
                    bgImage.filters.push(new fabric.Image.filters.Brightness({
                        brightness: brightnessValue
                    }));
                }

                // Apply contrast filter
                if (this.filters.contrast !== 100) {
                    const contrastValue = (this.filters.contrast - 100) / 100; // Convert to -1 to 1 range
                    bgImage.filters = bgImage.filters || [];
                    bgImage.filters.push(new fabric.Image.filters.Contrast({
                        contrast: contrastValue
                    }));
                }

                // Apply saturation filter
                if (this.filters.saturate !== 100) {
                    const saturationValue = (this.filters.saturate - 100) / 100; // Convert to -1 to 1 range
                    bgImage.filters = bgImage.filters || [];
                    bgImage.filters.push(new fabric.Image.filters.Saturation({
                        saturation: saturationValue
                    }));
                }

                // Apply all filters
                bgImage.applyFilters();
                this.canvas.renderAll();
            }

            // Clear CSS preview filters
            if (canvasEl) {
                canvasEl.style.filter = '';
            }

            // Reset filter values to defaults
            this.filters.brightness = 100;
            this.filters.contrast = 100;
            this.filters.saturate = 100;

            // Reset slider positions
            this.resetSlider('brightness');
            this.resetSlider('contrast');
            this.resetSlider('saturation');

            // Mark image as modified
            if (window.ImageEditor && window.ImageEditor.instances) {
                const editor = window.ImageEditor.instances[this.sessionId];
                if (editor) {
                    editor.updateSaveStatus('unsaved');
                }
            }

            console.log('[FilterEngine] Client-side filters applied successfully');

        } catch (error) {
            console.error('[FilterEngine] Error applying filters:', error);
            alert('Failed to apply filters. Please try again.');
        } finally {
            this.hideLoading();
        }
    }

    /**
     * Apply a server-side filter (blur or sharpen) (T087 + T089)
     * Sends request to backend for Pillow processing
     * Saves state for undo before applying
     * @param {string} filterType - Filter type (blur or sharpen)
     */
    async applyServerSideFilter(filterType) {
        const value = this.filters[filterType];

        if (value === 0) {
            console.log(`[FilterEngine] ${filterType} value is 0, nothing to apply`);
            return;
        }

        console.log(`[FilterEngine] Applying server-side filter: ${filterType} = ${value}`);

        try {
            // T089: Save state for undo before applying server-side filter
            if (window.ImageEditor && window.ImageEditor.instances) {
                const editor = window.ImageEditor.instances[this.sessionId];
                if (editor && editor.saveStateForUndo) {
                    await editor.saveStateForUndo();
                    console.log(`[FilterEngine] Saved state for undo before applying ${filterType}`);
                }
            }

            // Show loading indicator
            this.showLoading(`Applying ${filterType}...`);

            // Prepare request payload
            const payload = {
                operation: filterType,
                parameters: {}
            };

            // Add filter-specific parameters
            if (filterType === 'blur') {
                payload.parameters.radius = value;
            } else if (filterType === 'sharpen') {
                payload.parameters.amount = value; // Send as 0-10, backend will handle conversion
            }

            // Send request to backend (T087: Wire to API endpoint)
            const response = await fetch(`/api/v1/image-editor/process/${this.sessionId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                throw new Error(`Server returned ${response.status}: ${response.statusText}`);
            }

            const result = await response.json();
            console.log(`[FilterEngine] ${filterType} applied successfully:`, result);

            // Reload the image to show processed result
            if (window.ImageEditor && window.ImageEditor.instances) {
                const editor = window.ImageEditor.instances[this.sessionId];
                if (editor && editor.reloadImage) {
                    await editor.reloadImage();
                }
            }

            // Reset the filter slider
            this.filters[filterType] = 0;
            this.resetSlider(filterType);

            // Disable apply button
            const applyBtn = document.getElementById(`apply-${filterType}-${this.sessionId}`);
            if (applyBtn) {
                applyBtn.disabled = true;
            }

        } catch (error) {
            console.error(`[FilterEngine] Error applying ${filterType}:`, error);
            alert(`Failed to apply ${filterType} filter. Please try again.`);
        } finally {
            this.hideLoading();
        }
    }

    /**
     * Reset all filters to default values (T088)
     * Clears both CSS preview and slider states, reloads original image
     */
    resetAllFilters() {
        console.log('[FilterEngine] Resetting all filters to defaults');

        try {
            // Reset filter state
            this.filters = { ...this.defaults };

            // Clear CSS preview filters
            const canvasEl = this.canvas.lowerCanvasEl;
            if (canvasEl) {
                canvasEl.style.filter = '';
            }

            // Clear Fabric.js filters from background image
            const bgImage = this.canvas.backgroundImage;
            if (bgImage && bgImage.filters) {
                bgImage.filters = [];
                bgImage.applyFilters();
                this.canvas.renderAll();
            }

            // Reset all sliders to default values
            this.resetSlider('brightness');
            this.resetSlider('contrast');
            this.resetSlider('saturation');
            this.resetSlider('blur');
            this.resetSlider('sharpen');

            // Disable server-side filter apply buttons
            const blurBtn = document.getElementById(`apply-blur-${this.sessionId}`);
            if (blurBtn) blurBtn.disabled = true;

            const sharpenBtn = document.getElementById(`apply-sharpen-${this.sessionId}`);
            if (sharpenBtn) sharpenBtn.disabled = true;

            // Reload original image (removes server-side filters)
            if (window.ImageEditor && window.ImageEditor.instances) {
                const editor = window.ImageEditor.instances[this.sessionId];
                if (editor && editor.reloadImage) {
                    editor.reloadImage();
                }
            }

            console.log('[FilterEngine] All filters reset successfully');
        } catch (error) {
            console.error('[FilterEngine] Error resetting filters:', error);
            // Continue anyway - partial reset is better than none
        }
    }

    /**
     * Reset a specific slider to its default value
     * @param {string} sliderId - Slider ID prefix
     */
    resetSlider(sliderId) {
        const slider = document.getElementById(`${sliderId}-${this.sessionId}`);
        const valueDisplay = document.getElementById(`${sliderId}-value-${this.sessionId}`);

        if (slider) {
            const defaultValue = this.defaults[slider.dataset.filterType] || slider.defaultValue || 100;
            slider.value = defaultValue;

            if (valueDisplay) {
                const unit = slider.dataset.unit || '';
                valueDisplay.textContent = `${defaultValue}${unit}`;
            }
        }
    }

    /**
     * Show loading indicator
     * @param {string} message - Optional loading message
     */
    showLoading(message = 'Processing filter...') {
        const loadingEl = document.getElementById(`filter-loading-${this.sessionId}`);
        if (loadingEl) {
            const textEl = loadingEl.querySelector('.loading-text-sm');
            if (textEl) {
                textEl.textContent = message;
            }
            loadingEl.style.display = 'flex';
        }
    }

    /**
     * Hide loading indicator
     */
    hideLoading() {
        const loadingEl = document.getElementById(`filter-loading-${this.sessionId}`);
        if (loadingEl) {
            loadingEl.style.display = 'none';
        }
    }

    /**
     * Get current filter state
     * @returns {Object} Current filter values
     */
    getFilterState() {
        return { ...this.filters };
    }

    /**
     * Set filter state (for undo/redo)
     * @param {Object} state - Filter state to restore
     */
    setFilterState(state) {
        this.filters = { ...state };

        // Update sliders
        Object.keys(state).forEach(filterType => {
            const slider = document.getElementById(`${filterType}-${this.sessionId}`);
            if (slider) {
                slider.value = state[filterType];

                const valueDisplay = document.getElementById(`${filterType}-value-${this.sessionId}`);
                if (valueDisplay) {
                    const unit = slider.dataset.unit || '';
                    valueDisplay.textContent = `${state[filterType]}${unit}`;
                }
            }
        });

        // Apply preview
        this.applyPreviewFilters();
    }

    /**
     * Cleanup and destroy the filter engine
     */
    destroy() {
        // Clear any pending timers
        if (this.previewTimer) {
            clearTimeout(this.previewTimer);
        }

        // Clear CSS filters
        const canvasEl = this.canvas.lowerCanvasEl;
        if (canvasEl) {
            canvasEl.style.filter = '';
        }

        console.log(`[FilterEngine] Destroyed for session ${this.sessionId}`);
    }
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = FilterEngine;
}

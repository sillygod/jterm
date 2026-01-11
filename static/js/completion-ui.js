/**
 * Completion UI Component
 *
 * Manages the visual completion popup, keyboard navigation,
 * and user interaction for command-line intellisense.
 */

class CompletionUI {
    constructor(terminalElement) {
        this.terminalElement = terminalElement;
        this.popup = null;
        this.completions = [];
        this.selectedIndex = 0;
        this.visible = false;
        this.justShown = false;
        this.onSelectCallback = null;
        this.onCancelCallback = null;

        this._createPopup();
        this._attachEventListeners();
    }

    /**
     * Create the popup DOM element
     * @private
     */
    _createPopup() {
        this.popup = document.createElement('div');
        this.popup.className = 'completion-popup';
        this.popup.style.display = 'none';
        document.body.appendChild(this.popup);
    }

    /**
     * Attach global event listeners
     * @private
     */
    _attachEventListeners() {
        // Click outside to close
        document.addEventListener('click', (e) => {
            if (this.visible && !this.popup.contains(e.target)) {
                this.hide();
            }
        });
    }

    /**
     * Show completion popup with results
     * @param {Array} completions - Array of completion items
     * @param {Object} position - {x, y} screen coordinates
     * @param {Function} onSelect - Callback when item is selected
     * @param {Function} onCancel - Callback when canceled
     */
    show(completions, position, onSelect, onCancel) {
        if (!completions || completions.length === 0) {
            this.hide();
            return;
        }

        this.completions = completions;
        this.selectedIndex = 0;
        this.onSelectCallback = onSelect;
        this.onCancelCallback = onCancel;
        this.justShown = true; // Flag to prevent immediate selection

        this._render();

        // Make popup visible but hidden to measure dimensions
        this.popup.style.visibility = 'hidden';
        this.popup.style.display = 'block';

        // Position after rendering so we have accurate dimensions
        this._position(position);

        // Now make it fully visible
        this.popup.style.visibility = 'visible';
        this.visible = true;

        // Clear the justShown flag after a brief delay
        setTimeout(() => {
            this.justShown = false;
        }, 100);
    }

    /**
     * Hide the completion popup
     */
    hide() {
        if (this.popup) {
            this.popup.style.display = 'none';
        }
        this.visible = false;
        this.justShown = false;
        this.completions = [];
        this.selectedIndex = 0;
    }

    /**
     * Render completion items
     * @private
     */
    _render() {
        const html = this.completions.map((comp, index) => {
            const selected = index === this.selectedIndex ? 'selected' : '';
            const icon = this._getIconForType(comp.type);
            const sourceClass = `source-${comp.source}`;

            return `
                <div class="completion-item ${selected} ${sourceClass}"
                     data-index="${index}">
                    <span class="completion-icon">${icon}</span>
                    <div class="completion-content">
                        <div class="completion-text">${this._escapeHtml(comp.display)}</div>
                        ${comp.description ? `<div class="completion-description">${this._escapeHtml(comp.description)}</div>` : ''}
                    </div>
                    <span class="completion-source">${comp.source}</span>
                </div>
            `;
        }).join('');

        this.popup.innerHTML = html;

        // Attach click handlers
        this.popup.querySelectorAll('.completion-item').forEach(item => {
            item.addEventListener('click', (e) => {
                const index = parseInt(e.currentTarget.dataset.index);
                this.selectItem(index);
            });
        });
    }

    /**
     * Get icon for completion type
     * @private
     */
    _getIconForType(type) {
        const icons = {
            'command': '⚡',
            'file': '📄',
            'directory': '📁',
            'option': '⚙️',
            'variable': '💲',
            'custom': '✨',
            'function': 'ƒ',
            'alias': '↪️',
            'branch': '🌿',
            'remote-branch': '🌐',
            'remote': '📡',
            'tag': '🏷️'
        };
        return icons[type] || '•';
    }

    /**
     * Position popup near cursor
     * @private
     */
    _position(position) {
        const popup = this.popup;
        const windowWidth = window.innerWidth;
        const windowHeight = window.innerHeight;
        const popupRect = popup.getBoundingClientRect();

        const margin = 10; // Margin from screen edges
        const cursorOffset = 20; // Offset from cursor position

        let x = position.x;
        let y = position.y + cursorOffset; // Default: below cursor

        // Adjust horizontal position if popup would go off-screen
        if (x + popupRect.width > windowWidth - margin) {
            x = windowWidth - popupRect.width - margin;
        }
        if (x < margin) {
            x = margin;
        }

        // Check if there's enough space below the cursor
        const spaceBelow = windowHeight - (position.y + cursorOffset);
        const spaceAbove = position.y - cursorOffset;

        if (spaceBelow < popupRect.height && spaceAbove > spaceBelow) {
            // Not enough space below, and more space above - show above cursor
            y = position.y - popupRect.height - 5;

            // Make sure it doesn't go above the top of the screen
            if (y < margin) {
                y = margin;
            }
        } else {
            // Show below cursor
            y = position.y + cursorOffset;

            // Make sure it doesn't go below the bottom of the screen
            if (y + popupRect.height > windowHeight - margin) {
                y = windowHeight - popupRect.height - margin;
            }
        }

        popup.style.left = `${x}px`;
        popup.style.top = `${y}px`;
    }

    /**
     * Handle keyboard navigation
     * @param {KeyboardEvent} event - Keyboard event
     * @returns {boolean} True if event was handled
     */
    handleKeyboard(event) {
        if (!this.visible) {
            return false;
        }

        // Ignore Tab key if popup was just shown (within 100ms)
        if (event.key === 'Tab' && this.justShown) {
            event.preventDefault();
            return true;
        }

        switch (event.key) {
            case 'ArrowDown':
                event.preventDefault();
                this.selectNext();
                return true;

            case 'ArrowUp':
                event.preventDefault();
                this.selectPrevious();
                return true;

            case 'Tab':
                event.preventDefault();
                this.selectCurrent();
                return true;

            case 'Enter':
                event.preventDefault();
                this.selectCurrent();
                return true;

            case 'Escape':
                event.preventDefault();
                this.cancel();
                return true;

            default:
                // Don't cancel on regular typing - let auto-complete handle it
                // Only cancel on special keys like Ctrl+C, etc.
                if (event.ctrlKey || event.metaKey || event.altKey) {
                    this.cancel();
                    return false;
                }
                // For regular typing, just hide and let the new auto-complete trigger
                this.cancel();
                return false;
        }
    }

    /**
     * Select next item in list
     */
    selectNext() {
        if (this.completions.length === 0) return;

        this.selectedIndex = (this.selectedIndex + 1) % this.completions.length;
        this._updateSelection();
    }

    /**
     * Select previous item in list
     */
    selectPrevious() {
        if (this.completions.length === 0) return;

        this.selectedIndex = (this.selectedIndex - 1 + this.completions.length) % this.completions.length;
        this._updateSelection();
    }

    /**
     * Select current item and trigger callback
     */
    selectCurrent() {
        if (this.completions.length > 0 && this.onSelectCallback) {
            const selected = this.completions[this.selectedIndex];
            this.onSelectCallback(selected);
        }
        this.hide();
    }

    /**
     * Select specific item by index
     * @param {number} index - Item index
     */
    selectItem(index) {
        if (index >= 0 && index < this.completions.length && this.onSelectCallback) {
            const selected = this.completions[index];
            this.onSelectCallback(selected);
        }
        this.hide();
    }

    /**
     * Cancel completion and trigger callback
     */
    cancel() {
        if (this.onCancelCallback) {
            this.onCancelCallback();
        }
        this.hide();
    }

    /**
     * Update visual selection
     * @private
     */
    _updateSelection() {
        const items = this.popup.querySelectorAll('.completion-item');
        items.forEach((item, index) => {
            if (index === this.selectedIndex) {
                item.classList.add('selected');
                // Scroll into view if needed
                item.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
            } else {
                item.classList.remove('selected');
            }
        });
    }

    /**
     * Escape HTML to prevent XSS
     * @private
     */
    _escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Check if popup is currently visible
     * @returns {boolean}
     */
    isVisible() {
        return this.visible;
    }

    /**
     * Get currently selected completion
     * @returns {Object|null}
     */
    getSelected() {
        if (this.completions.length > 0) {
            return this.completions[this.selectedIndex];
        }
        return null;
    }

    /**
     * Destroy the UI component and cleanup
     */
    destroy() {
        if (this.popup && this.popup.parentNode) {
            this.popup.parentNode.removeChild(this.popup);
        }
        this.popup = null;
        this.completions = [];
        this.visible = false;
    }
}


// Export for use in other modules
window.CompletionUI = CompletionUI;

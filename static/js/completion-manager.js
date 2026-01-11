/**
 * Completion Manager
 *
 * Coordinates completion functionality between cache, UI, and API.
 * Provides the main interface for terminal intellisense.
 */

class CompletionManager {
    constructor(terminal, websocket) {
        this.terminal = terminal;
        this.websocket = websocket;

        // Initialize components
        this.cache = new window.CompletionCache(100, 300000); // 100 items, 5min TTL
        this.ui = new window.CompletionUI(terminal.element);
        this.prefetcher = new window.CompletionPrefetcher(
            this.cache,
            this._fetchCompletions.bind(this)
        );

        // State
        this.enabled = true;
        this.sessionId = null;
        this.currentCwd = '/';
        this.shellPath = '/bin/bash';
        this.currentLine = '';
        this.cursorPos = 0;
        this.enableAI = true;
        this.apiBaseUrl = '/api/v1/completions';

        // Track if we're currently showing completions
        this.active = false;

        // Auto-complete settings
        this.autoCompleteEnabled = true;
        this.autoCompleteMinChars = 2; // Minimum characters before showing suggestions
        this.autoCompleteDelay = 300; // Delay in ms before showing suggestions
        this.autoCompleteTimer = null;

        // Callback to notify terminal when line changes
        this.onLineChangeCallback = null;

        // Bind methods
        this._onSelect = this._onSelect.bind(this);
        this._onCancel = this._onCancel.bind(this);
    }

    /**
     * Initialize the completion manager
     * @param {string} sessionId - Terminal session ID
     * @param {Object} options - Configuration options
     */
    initialize(sessionId, options = {}) {
        this.sessionId = sessionId;
        this.currentCwd = options.cwd || this.currentCwd;
        this.shellPath = options.shellPath || this.shellPath;
        this.enableAI = options.enableAI !== undefined ? options.enableAI : true;

        console.log('CompletionManager initialized', {
            sessionId,
            cwd: this.currentCwd,
            shellPath: this.shellPath,
            enableAI: this.enableAI
        });
    }

    /**
     * Update session context (cwd, shell, etc.)
     * @param {Object} context - Updated context
     */
    updateContext(context) {
        if (context.cwd) this.currentCwd = context.cwd;
        if (context.shellPath) this.shellPath = context.shellPath;
        if (context.enableAI !== undefined) this.enableAI = context.enableAI;
    }

    /**
     * Update current line and cursor position from terminal
     * @param {string} line - Current command line
     * @param {number} cursorPos - Cursor position
     */
    updateLine(line, cursorPos) {
        this.currentLine = line;
        this.cursorPos = cursorPos;

        // Auto-complete: show suggestions after typing
        if (this.autoCompleteEnabled && this.enabled && !this.active) {
            // Clear existing timer
            if (this.autoCompleteTimer) {
                clearTimeout(this.autoCompleteTimer);
            }

            // Extract current word being typed
            let wordStart = cursorPos;
            for (let i = cursorPos - 1; i >= 0; i--) {
                if ([' ', '\t', '\n', ';', '|', '&', '(', ')'].includes(line[i])) {
                    wordStart = i + 1;
                    break;
                }
                if (i === 0) {
                    wordStart = 0;
                }
            }
            const currentWord = line.slice(wordStart, cursorPos);

            // Only trigger if word length >= minimum chars
            if (currentWord.length >= this.autoCompleteMinChars) {
                this.autoCompleteTimer = setTimeout(() => {
                    this.trigger();
                }, this.autoCompleteDelay);
            }
        }

        // Schedule prefetch on idle (for cache warming)
        if (this.enabled && !this.active) {
            this.prefetcher.schedulePrefetch(
                line,
                cursorPos,
                this.currentCwd,
                this._getSessionContext()
            );
        }
    }

    /**
     * Trigger completion (usually on Tab key)
     * @returns {Promise<boolean>} True if completions were shown
     */
    async trigger() {
        if (!this.enabled || this.active) {
            return false;
        }

        // Get cursor position in terminal viewport
        const cursorCoords = this._getCursorCoordinates();
        if (!cursorCoords) {
            console.warn('Could not get cursor coordinates');
            return false;
        }

        // Check cache first
        let completions = this.cache.get(this.currentLine, this.cursorPos, this.currentCwd);

        if (!completions) {
            // Fetch from API
            try {
                completions = await this._fetchCompletions(
                    this.currentLine,
                    this.cursorPos,
                    this.currentCwd,
                    this._getSessionContext()
                );

                if (completions && completions.length > 0) {
                    // Cache the results
                    this.cache.set(this.currentLine, this.cursorPos, this.currentCwd, completions);
                }
            } catch (error) {
                console.error('Failed to fetch completions:', error);
                return false;
            }
        }

        if (!completions || completions.length === 0) {
            return false;
        }

        // Show UI
        this.active = true;
        this.ui.show(completions, cursorCoords, this._onSelect, this._onCancel);

        return true;
    }

    /**
     * Handle keyboard events for completion navigation
     * @param {KeyboardEvent} event - Keyboard event
     * @returns {boolean} True if event was handled
     */
    handleKeyboard(event) {
        return this.ui.handleKeyboard(event);
    }

    /**
     * Fetch completions from API
     * @private
     */
    async _fetchCompletions(line, cursorPos, cwd, sessionContext) {
        const response = await fetch(`${this.apiBaseUrl}/suggest`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                line: line,
                cursorPos: cursorPos,
                sessionId: sessionContext.sessionId,
                shellPath: sessionContext.shellPath,
                cwd: cwd,
                enableAI: sessionContext.enableAI,
                userId: 'default'
            })
        });

        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }

        const data = await response.json();
        return data.completions || [];
    }

    /**
     * Get session context for API calls
     * @private
     */
    _getSessionContext() {
        return {
            sessionId: this.sessionId,
            shellPath: this.shellPath,
            enableAI: this.enableAI
        };
    }

    /**
     * Get cursor coordinates in viewport
     * @private
     */
    _getCursorCoordinates() {
        try {
            // Get terminal buffer cursor position
            const buffer = this.terminal.buffer.active;
            const cursorY = buffer.cursorY;
            const cursorX = buffer.cursorX;

            // Get terminal element position
            const terminalElement = this.terminal.element;
            const terminalRect = terminalElement.getBoundingClientRect();

            // Calculate character dimensions
            const cellWidth = terminalRect.width / this.terminal.cols;
            const cellHeight = terminalRect.height / this.terminal.rows;

            // Calculate absolute cursor position
            const x = terminalRect.left + (cursorX * cellWidth);
            const y = terminalRect.top + (cursorY * cellHeight);

            return { x, y };
        } catch (error) {
            console.error('Error getting cursor coordinates:', error);
            return null;
        }
    }

    /**
     * Handle completion selection
     * @private
     */
    _onSelect(completion) {
        console.log('Selected completion:', completion);

        // Calculate the final line after completion
        const line = this.currentLine;
        const cursorPos = this.cursorPos;

        // Find start of current word
        let wordStart = cursorPos;
        for (let i = cursorPos - 1; i >= 0; i--) {
            if ([' ', '\t', '\n', ';', '|', '&', '(', ')'].includes(line[i])) {
                wordStart = i + 1;
                break;
            }
            if (i === 0) {
                wordStart = 0;
            }
        }

        const currentWord = line.slice(wordStart, cursorPos);
        const completionText = completion.text;

        // Calculate the new line after completion
        let newLine, newCursorPos;
        if (completionText.startsWith(currentWord)) {
            // Append the rest of the completion
            newLine = line.slice(0, cursorPos) + completionText.slice(currentWord.length) + line.slice(cursorPos);
            newCursorPos = cursorPos + (completionText.length - currentWord.length);
        } else {
            // Replace the word
            newLine = line.slice(0, wordStart) + completionText + line.slice(cursorPos);
            newCursorPos = wordStart + completionText.length;
        }

        // Calculate what to insert
        const insertText = this._calculateInsertText(completion);

        if (insertText) {
            // Send to terminal via websocket
            this._insertCompletion(insertText);

            // Update current line state immediately (don't wait for PTY echo)
            this.currentLine = newLine;
            this.cursorPos = newCursorPos;

            // Notify terminal to update its line state
            if (this.onLineChangeCallback) {
                this.onLineChangeCallback(newLine, newCursorPos);
            }
        }

        this.active = false;
    }

    /**
     * Calculate text to insert based on current line
     * @private
     */
    _calculateInsertText(completion) {
        const line = this.currentLine;
        const cursorPos = this.cursorPos;

        // Find start of current word
        let wordStart = cursorPos;
        for (let i = cursorPos - 1; i >= 0; i--) {
            if ([' ', '\t', '\n', ';', '|', '&', '(', ')'].includes(line[i])) {
                wordStart = i + 1;
                break;
            }
            if (i === 0) {
                wordStart = 0;
            }
        }

        const currentWord = line.slice(wordStart, cursorPos);
        const completionText = completion.text;

        // Return the part that needs to be inserted
        if (completionText.startsWith(currentWord)) {
            return completionText.slice(currentWord.length);
        } else {
            // Replace entire word
            // First delete current word, then insert completion
            const deleteCount = currentWord.length;
            return '\b'.repeat(deleteCount) + completionText;
        }
    }

    /**
     * Insert completion text into terminal
     * @private
     */
    _insertCompletion(text) {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            // Send input through websocket
            this.websocket.send(JSON.stringify({
                type: 'input',
                data: text,
                sessionId: this.sessionId,
                timestamp: new Date().toISOString()
            }));
        }
    }

    /**
     * Handle completion cancellation
     * @private
     */
    _onCancel() {
        console.log('Completion cancelled');
        this.active = false;

        // Clear auto-complete timer when cancelled
        if (this.autoCompleteTimer) {
            clearTimeout(this.autoCompleteTimer);
            this.autoCompleteTimer = null;
        }
    }

    /**
     * Enable/disable completion
     * @param {boolean} enabled - Enable state
     */
    setEnabled(enabled) {
        this.enabled = enabled;
        if (!enabled) {
            this.ui.hide();
            this.active = false;
            this.prefetcher.cancel();
            if (this.autoCompleteTimer) {
                clearTimeout(this.autoCompleteTimer);
                this.autoCompleteTimer = null;
            }
        }
    }

    /**
     * Enable/disable auto-complete
     * @param {boolean} enabled - Auto-complete enable state
     */
    setAutoCompleteEnabled(enabled) {
        this.autoCompleteEnabled = enabled;
        if (!enabled && this.autoCompleteTimer) {
            clearTimeout(this.autoCompleteTimer);
            this.autoCompleteTimer = null;
        }
    }

    /**
     * Set auto-complete minimum characters
     * @param {number} minChars - Minimum characters before showing suggestions
     */
    setAutoCompleteMinChars(minChars) {
        this.autoCompleteMinChars = Math.max(1, minChars);
    }

    /**
     * Set auto-complete delay
     * @param {number} delay - Delay in milliseconds
     */
    setAutoCompleteDelay(delay) {
        this.autoCompleteDelay = Math.max(0, delay);
    }

    /**
     * Clear cache
     */
    clearCache() {
        this.cache.clear();
    }

    /**
     * Get statistics
     */
    getStats() {
        return {
            enabled: this.enabled,
            active: this.active,
            autoComplete: {
                enabled: this.autoCompleteEnabled,
                minChars: this.autoCompleteMinChars,
                delay: this.autoCompleteDelay
            },
            cache: this.cache.getStats(),
            sessionId: this.sessionId
        };
    }

    /**
     * Cleanup and destroy
     */
    destroy() {
        this.setEnabled(false);
        this.ui.destroy();
        this.cache.clear();
    }
}


// Export for use in terminal.js
window.CompletionManager = CompletionManager;

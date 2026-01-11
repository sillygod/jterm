/**
 * Completion Cache Module
 *
 * Provides LRU (Least Recently Used) caching for completion results
 * to minimize redundant API calls and improve response time.
 */

class CompletionCache {
    constructor(maxSize = 100, ttlMs = 300000) { // 5 minutes TTL
        this.maxSize = maxSize;
        this.ttlMs = ttlMs;
        this.cache = new Map(); // Map<cacheKey, {completions, timestamp}>
    }

    /**
     * Generate a cache key from completion request parameters
     * @param {string} line - Command line
     * @param {number} cursorPos - Cursor position
     * @param {string} cwd - Current working directory
     * @returns {string} Cache key
     */
    _generateKey(line, cursorPos, cwd) {
        // Extract the word being completed
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

        const word = line.slice(wordStart, cursorPos);
        const lineContext = line.slice(0, cursorPos);

        // Key includes: word being completed + command context + cwd
        return `${word}|${lineContext}|${cwd}`;
    }

    /**
     * Get cached completions if available and not expired
     * @param {string} line - Command line
     * @param {number} cursorPos - Cursor position
     * @param {string} cwd - Current working directory
     * @returns {Array|null} Cached completions or null
     */
    get(line, cursorPos, cwd) {
        const key = this._generateKey(line, cursorPos, cwd);
        const cached = this.cache.get(key);

        if (!cached) {
            return null;
        }

        // Check if expired
        const now = Date.now();
        if (now - cached.timestamp > this.ttlMs) {
            this.cache.delete(key);
            return null;
        }

        // Move to end (mark as recently used)
        this.cache.delete(key);
        this.cache.set(key, cached);

        return cached.completions;
    }

    /**
     * Store completions in cache
     * @param {string} line - Command line
     * @param {number} cursorPos - Cursor position
     * @param {string} cwd - Current working directory
     * @param {Array} completions - Completion items to cache
     */
    set(line, cursorPos, cwd, completions) {
        const key = this._generateKey(line, cursorPos, cwd);

        // Remove oldest entries if at max size
        if (this.cache.size >= this.maxSize) {
            // Map iterator returns entries in insertion order
            const firstKey = this.cache.keys().next().value;
            this.cache.delete(firstKey);
        }

        this.cache.set(key, {
            completions: completions,
            timestamp: Date.now()
        });
    }

    /**
     * Clear all cached completions
     */
    clear() {
        this.cache.clear();
    }

    /**
     * Get cache statistics
     * @returns {Object} Cache stats
     */
    getStats() {
        return {
            size: this.cache.size,
            maxSize: this.maxSize,
            ttlMs: this.ttlMs
        };
    }

    /**
     * Remove expired entries (garbage collection)
     */
    cleanup() {
        const now = Date.now();
        const keysToDelete = [];

        for (const [key, value] of this.cache.entries()) {
            if (now - value.timestamp > this.ttlMs) {
                keysToDelete.push(key);
            }
        }

        keysToDelete.forEach(key => this.cache.delete(key));

        return keysToDelete.length;
    }
}


/**
 * Completion Prefetch Manager
 *
 * Intelligently prefetches completions based on user typing patterns
 */
class CompletionPrefetcher {
    constructor(cache, fetchCallback) {
        this.cache = cache;
        this.fetchCallback = fetchCallback; // Function to fetch completions
        this.prefetchQueue = [];
        this.isProcessing = false;
        this.debounceTimer = null;
        this.debounceDelay = 500; // Wait 500ms of idle before prefetching
    }

    /**
     * Schedule a prefetch when user pauses typing
     * @param {string} line - Command line
     * @param {number} cursorPos - Cursor position
     * @param {string} cwd - Current working directory
     * @param {Object} sessionContext - Session context for API call
     */
    schedulePrefetch(line, cursorPos, cwd, sessionContext) {
        // Clear existing timer
        if (this.debounceTimer) {
            clearTimeout(this.debounceTimer);
        }

        // Check if already cached
        const cached = this.cache.get(line, cursorPos, cwd);
        if (cached) {
            return; // Already have results
        }

        // Schedule prefetch after debounce delay
        this.debounceTimer = setTimeout(async () => {
            try {
                const completions = await this.fetchCallback(line, cursorPos, cwd, sessionContext);
                if (completions && completions.length > 0) {
                    this.cache.set(line, cursorPos, cwd, completions);
                }
            } catch (error) {
                console.debug('Prefetch failed:', error);
                // Silently fail for prefetch
            }
        }, this.debounceDelay);
    }

    /**
     * Cancel any pending prefetch
     */
    cancel() {
        if (this.debounceTimer) {
            clearTimeout(this.debounceTimer);
            this.debounceTimer = null;
        }
    }
}


// Export for use in other modules
window.CompletionCache = CompletionCache;
window.CompletionPrefetcher = CompletionPrefetcher;

/**
 * AI Assistant Integration
 *
 * Provides UI integration for the AI Assistant including:
 * - Chat interface
 * - Command suggestions
 * - Output explanation
 * - Voice integration
 */

class AIAssistant {
    constructor(sessionId = null) {
        this.sessionId = sessionId;
        this.isInitialized = false;
        this.isConnected = false;
        this.voiceAssistant = null;

        // UI elements
        this.sidebar = null;
        this.statusIndicator = null;
        this.statusText = null;
        this.chatContainer = null;
        this.chatMessages = null;
        this.chatInput = null;
        this.sendButton = null;
        this.voiceButton = null;

        this.init();
    }

    init() {
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setupUI());
        } else {
            this.setupUI();
        }
    }

    setupUI() {
        // Get UI elements
        this.sidebar = document.getElementById('ai-sidebar');
        this.statusIndicator = this.sidebar?.querySelector('.status-indicator');
        this.statusText = this.sidebar?.querySelector('.status-text');
        this.chatContainer = document.getElementById('ai-chat');
        this.chatMessages = document.getElementById('chat-messages');
        this.chatInput = document.getElementById('chat-input');
        this.sendButton = this.chatContainer?.querySelector('button[type="submit"]');

        if (!this.sidebar) {
            console.warn('AI sidebar not found in DOM');
            return;
        }

        // Show sidebar
        this.sidebar.style.display = 'block';

        // Check if AI is configured
        this.checkConfiguration();

        // Setup event listeners
        this.setupEventListeners();

        // Initialize voice assistant if available
        if (window.VoiceAssistant && this.sessionId) {
            this.voiceAssistant = new window.VoiceAssistant(this.sessionId);
        }

        this.isInitialized = true;
    }

    async checkConfiguration() {
        try {
            // Wait a bit for terminal to connect
            await new Promise(resolve => setTimeout(resolve, 1000));

            const sessionId = this.getCurrentSessionId() || '00000000-0000-0000-0000-000000000001';

            // Check if AI endpoints are available
            const response = await fetch('/api/v1/ai/chat?sessionId=' + sessionId, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: 'ping',
                    stream: false,
                    includeContext: false
                })
            });

            // If we get a response (even if it's an error), the API is available
            this.setStatus('online', 'AI Assistant Ready');
            this.enableChat();
        } catch (error) {
            console.error('AI configuration check failed:', error);
            this.setStatus('offline', 'AI Assistant Not Available');
        }
    }

    setStatus(status, text) {
        if (this.statusIndicator) {
            this.statusIndicator.className = `status-indicator ${status}`;
        }
        if (this.statusText) {
            this.statusText.textContent = text;
        }

        this.isConnected = (status === 'online');
    }

    enableChat() {
        if (this.chatContainer) {
            this.chatContainer.style.display = 'block';
        }
        if (this.chatInput) {
            this.chatInput.disabled = false;
        }
        if (this.sendButton) {
            this.sendButton.disabled = false;
        }
    }

    setupEventListeners() {
        // Chat form submission
        const chatForm = this.chatContainer?.querySelector('form');
        if (chatForm) {
            chatForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                await this.sendMessage();
            });
        }

        // Listen for AI response events from voice assistant
        document.addEventListener('ai-response', (e) => {
            if (e.detail.response) {
                this.displayMessage('assistant', e.detail.response);
            }
        });

        // Listen for voice processing events
        document.addEventListener('voice-processing', (e) => {
            if (e.detail.transcript) {
                this.displayMessage('user', e.detail.transcript);
            }
        });
    }

    async sendMessage() {
        const message = this.chatInput?.value.trim();
        if (!message) return;

        // Get session ID from terminal
        const currentSessionId = this.getCurrentSessionId();
        if (!currentSessionId) {
            this.displayMessage('system', 'Please wait for terminal to connect...');
            return;
        }

        // Display user message
        this.displayMessage('user', message);

        // Clear input
        if (this.chatInput) {
            this.chatInput.value = '';
        }

        // Show loading indicator
        this.displayMessage('assistant', 'Thinking...', true);

        try {
            const response = await fetch(`/api/v1/ai/chat?sessionId=${currentSessionId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: message,
                    stream: false,
                    includeContext: true
                })
            });

            if (!response.ok) {
                throw new Error(`AI request failed: ${response.statusText}`);
            }

            const data = await response.json();

            // Remove loading indicator
            this.removeLastMessage();

            // Display AI response
            this.displayMessage('assistant', data.response);

            // Dispatch event for other components
            document.dispatchEvent(new CustomEvent('ai-response', {
                detail: {
                    message: message,
                    response: data.response,
                    responseTime: data.responseTime
                }
            }));

        } catch (error) {
            console.error('AI message error:', error);
            this.removeLastMessage();
            this.displayMessage('system', `Error: ${error.message}`);
        }
    }

    displayMessage(role, content, isLoading = false) {
        if (!this.chatMessages) return;

        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${role}${isLoading ? ' loading' : ''}`;

        const roleSpan = document.createElement('span');
        roleSpan.className = 'message-role';
        roleSpan.textContent = role === 'user' ? 'You' : role === 'assistant' ? 'AI' : 'System';

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';

        // Render markdown for assistant messages, plain text for others
        if (role === 'assistant' && !isLoading && typeof marked !== 'undefined') {
            try {
                contentDiv.innerHTML = marked.parse(content);
            } catch (e) {
                console.error('Markdown parsing error:', e);
                contentDiv.textContent = content;
            }
        } else {
            contentDiv.textContent = content;
        }

        messageDiv.appendChild(roleSpan);
        messageDiv.appendChild(contentDiv);

        this.chatMessages.appendChild(messageDiv);

        // Scroll to bottom
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }

    removeLastMessage() {
        if (!this.chatMessages) return;

        const lastMessage = this.chatMessages.lastElementChild;
        if (lastMessage) {
            lastMessage.remove();
        }
    }

    async getSuggestions(partialCommand = null, goal = null) {
        const sessionId = this.getCurrentSessionId();
        if (!sessionId) return [];

        try {
            const response = await fetch(`/api/v1/ai/suggest?sessionId=${sessionId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    partialCommand: partialCommand,
                    goal: goal,
                    maxSuggestions: 5
                })
            });

            if (!response.ok) {
                throw new Error(`Suggestions request failed: ${response.statusText}`);
            }

            const data = await response.json();
            return data.suggestions || [];

        } catch (error) {
            console.error('Suggestions error:', error);
            return [];
        }
    }

    async explainOutput(command, output) {
        const sessionId = this.getCurrentSessionId();
        if (!sessionId) return null;

        try {
            const response = await fetch(`/api/v1/ai/explain?sessionId=${sessionId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    command: command,
                    output: output,
                    explainErrors: true
                })
            });

            if (!response.ok) {
                throw new Error(`Explanation request failed: ${response.statusText}`);
            }

            const data = await response.json();
            return data;

        } catch (error) {
            console.error('Explanation error:', error);
            return null;
        }
    }

    getCurrentSessionId() {
        // Try to get session ID from global terminal instance
        if (window.webTerminal && window.webTerminal.sessionId) {
            return window.webTerminal.sessionId;
        }

        // Fallback to stored session ID
        return this.sessionId;
    }

    setSessionId(sessionId) {
        this.sessionId = sessionId;
        if (this.voiceAssistant) {
            this.voiceAssistant.setSessionId(sessionId);
        }

        // Recheck configuration with new session ID
        if (this.isInitialized) {
            this.checkConfiguration();
        }
    }

    toggleSidebar() {
        if (this.sidebar) {
            const parent = this.sidebar.closest('.sidebar');
            if (parent) {
                parent.style.display = parent.style.display === 'none' ? 'block' : 'none';
            }
        }
    }
}

// Initialize AI Assistant when DOM is ready
let aiAssistant = null;

document.addEventListener('DOMContentLoaded', () => {
    // Get session ID from URL or other source
    const urlParams = new URLSearchParams(window.location.search);
    const sessionId = urlParams.get('sessionId') || '00000000-0000-0000-0000-000000000001';

    aiAssistant = new AIAssistant(sessionId);

    // Expose to window for global access
    window.aiAssistant = aiAssistant;

    console.log('AI Assistant initialized');
});

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { AIAssistant };
}

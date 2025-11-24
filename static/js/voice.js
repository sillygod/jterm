/**
 * Voice.js - Web Speech API integration for voice input/output
 *
 * Provides voice recognition and text-to-speech capabilities for the terminal,
 * allowing users to interact with the AI assistant using voice commands.
 */

class VoiceInput {
    constructor() {
        this.recognition = null;
        this.isListening = false;
        this.isSupported = false;
        this.language = 'en-US';
        this.continuous = false;
        this.interimResults = true;

        // Callbacks
        this.onResult = null;
        this.onError = null;
        this.onStart = null;
        this.onEnd = null;

        // UI elements
        this.micButton = null;
        this.statusIndicator = null;
        this.transcript = null;

        // Auto-send mechanism
        this.silenceTimeout = null;
        this.silenceDelay = 1500; // 1.5 seconds of silence before auto-send
        this.lastTranscript = '';

        this.init();
    }

    init() {
        // Check for Web Speech API support
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

        if (!SpeechRecognition) {
            console.warn('Web Speech API not supported in this browser');
            this.isSupported = false;
            return;
        }

        this.isSupported = true;
        this.recognition = new SpeechRecognition();

        // Configure recognition with safe defaults
        this.recognition.continuous = this.continuous;
        this.recognition.interimResults = this.interimResults;

        // Use browser's default language if available, fallback to en-US
        try {
            this.language = navigator.language || 'en-US';
            this.recognition.lang = this.language;
        } catch (e) {
            console.warn('Failed to set language, using default');
            this.recognition.lang = 'en-US';
        }

        this.recognition.maxAlternatives = 1;

        // Setup event handlers
        this.setupEventHandlers();

        // Setup UI when DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setupUI());
        } else {
            this.setupUI();
        }
    }

    setupEventHandlers() {
        if (!this.recognition) return;

        this.recognition.onstart = () => {
            this.isListening = true;
            this.updateUI();
            if (this.onStart) this.onStart();
            this.dispatchEvent('voice-start');
        };

        this.recognition.onend = () => {
            this.isListening = false;
            this.updateUI();
            if (this.onEnd) this.onEnd();
            this.dispatchEvent('voice-end');
        };

        this.recognition.onresult = (event) => {
            let interimTranscript = '';
            let finalTranscript = '';

            for (let i = event.resultIndex; i < event.results.length; i++) {
                const transcript = event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                    finalTranscript += transcript + ' ';
                } else {
                    interimTranscript += transcript;
                }
            }

            const currentTranscript = (finalTranscript || interimTranscript).trim();

            // Update transcript display
            if (this.transcript) {
                this.transcript.textContent = currentTranscript;
            }

            // Store the current transcript for auto-send
            this.lastTranscript = currentTranscript;

            // Clear any existing silence timeout
            if (this.silenceTimeout) {
                clearTimeout(this.silenceTimeout);
            }

            // If we have a final result, send immediately
            if (finalTranscript) {
                console.log('Final transcript detected, sending immediately:', finalTranscript.trim());

                // Call result callback
                if (this.onResult) {
                    this.onResult(finalTranscript.trim());
                }

                // Dispatch event with isFinal=true
                this.dispatchEvent('voice-result', {
                    transcript: finalTranscript.trim(),
                    isFinal: true
                });

                // Stop listening after final result
                this.stop();
            } else if (currentTranscript) {
                // For interim results, set a timeout to auto-send after silence
                this.silenceTimeout = setTimeout(() => {
                    if (this.lastTranscript && this.isListening) {
                        console.log('Silence detected, auto-sending transcript:', this.lastTranscript);

                        // Call result callback
                        if (this.onResult) {
                            this.onResult(this.lastTranscript);
                        }

                        // Dispatch as final result
                        this.dispatchEvent('voice-result', {
                            transcript: this.lastTranscript,
                            isFinal: true
                        });

                        // Stop listening
                        this.stop();
                    }
                }, this.silenceDelay);
            }
        };

        this.recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);

            // Clear any pending silence timeout
            if (this.silenceTimeout) {
                clearTimeout(this.silenceTimeout);
                this.silenceTimeout = null;
            }

            let errorMessage = 'Voice recognition error';
            switch (event.error) {
                case 'no-speech':
                    errorMessage = 'No speech detected';
                    break;
                case 'audio-capture':
                    errorMessage = 'No microphone found';
                    break;
                case 'not-allowed':
                    errorMessage = 'Microphone permission denied';
                    break;
                case 'network':
                    errorMessage = 'Network error';
                    break;
                default:
                    errorMessage = `Error: ${event.error}`;
            }

            if (this.onError) this.onError(errorMessage);
            this.dispatchEvent('voice-error', { error: errorMessage });
        };
    }

    setupUI() {
        this.micButton = document.querySelector('.voice-input-button');
        this.statusIndicator = document.querySelector('.voice-status');
        this.transcript = document.querySelector('.voice-transcript');

        if (this.micButton) {
            this.micButton.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.toggle();
            });

            // Disable if not supported
            if (!this.isSupported) {
                this.micButton.disabled = true;
                this.micButton.title = 'Voice input not supported in this browser';
            }
        }

        this.updateUI();
    }

    start() {
        if (!this.isSupported) {
            console.warn('Voice recognition not supported');
            if (this.onError) {
                this.onError('Voice recognition not supported in this browser');
            }
            return false;
        }

        if (this.isListening) {
            console.warn('Already listening');
            return false;
        }

        // Reset transcript and timeout
        this.lastTranscript = '';
        if (this.silenceTimeout) {
            clearTimeout(this.silenceTimeout);
            this.silenceTimeout = null;
        }

        try {
            this.recognition.start();
            return true;
        } catch (error) {
            console.error('Failed to start voice recognition:', error);
            if (this.onError) {
                this.onError(`Failed to start: ${error.message}`);
            }
            return false;
        }
    }

    stop() {
        if (!this.isListening) return;

        // Clear any pending silence timeout
        if (this.silenceTimeout) {
            clearTimeout(this.silenceTimeout);
            this.silenceTimeout = null;
        }

        try {
            this.recognition.stop();
        } catch (error) {
            console.error('Failed to stop voice recognition:', error);
        }
    }

    toggle() {
        if (this.isListening) {
            this.stop();
        } else {
            this.start();
        }
    }

    setLanguage(language) {
        this.language = language;
        if (this.recognition) {
            this.recognition.lang = language;
        }
    }

    updateUI() {
        if (this.micButton) {
            if (this.isListening) {
                this.micButton.classList.add('listening');
                this.micButton.title = 'Stop listening';
            } else {
                this.micButton.classList.remove('listening');
                this.micButton.title = 'Start voice input';
            }
        }

        if (this.statusIndicator) {
            if (this.isListening) {
                this.statusIndicator.textContent = 'Listening...';
                this.statusIndicator.classList.add('active');
            } else {
                this.statusIndicator.textContent = '';
                this.statusIndicator.classList.remove('active');
            }
        }
    }

    dispatchEvent(eventName, detail = {}) {
        const event = new CustomEvent(eventName, { detail });
        document.dispatchEvent(event);
    }
}

class VoiceOutput {
    constructor() {
        this.synthesis = window.speechSynthesis;
        this.isSupported = !!this.synthesis;
        this.isSpeaking = false;
        this.voice = null;
        this.rate = 1.0;
        this.pitch = 1.0;
        this.volume = 1.0;
        this.language = 'en-US';

        // Callbacks
        this.onStart = null;
        this.onEnd = null;
        this.onError = null;

        this.init();
    }

    init() {
        if (!this.isSupported) {
            console.warn('Speech synthesis not supported in this browser');
            return;
        }

        // Load voices when available
        if (this.synthesis.getVoices().length > 0) {
            this.loadVoices();
        } else {
            this.synthesis.addEventListener('voiceschanged', () => this.loadVoices());
        }
    }

    loadVoices() {
        const voices = this.synthesis.getVoices();

        // Try to find a voice for the current language
        this.voice = voices.find(v => v.lang.startsWith(this.language)) || voices[0];

        this.dispatchEvent('voices-loaded', { voices: voices.length });
    }

    speak(text, options = {}) {
        if (!this.isSupported) {
            console.warn('Speech synthesis not supported');
            return false;
        }

        // Cancel any ongoing speech
        this.cancel();

        const utterance = new SpeechSynthesisUtterance(text);

        // Apply settings
        utterance.voice = options.voice || this.voice;
        utterance.rate = options.rate || this.rate;
        utterance.pitch = options.pitch || this.pitch;
        utterance.volume = options.volume || this.volume;
        utterance.lang = options.language || this.language;

        // Setup event handlers
        utterance.onstart = () => {
            this.isSpeaking = true;
            if (this.onStart) this.onStart();
            this.dispatchEvent('speech-start');
        };

        utterance.onend = () => {
            this.isSpeaking = false;
            if (this.onEnd) this.onEnd();
            this.dispatchEvent('speech-end');
        };

        utterance.onerror = (event) => {
            console.error('Speech synthesis error:', event.error);
            this.isSpeaking = false;
            if (this.onError) this.onError(event.error);
            this.dispatchEvent('speech-error', { error: event.error });
        };

        // Speak
        this.synthesis.speak(utterance);
        return true;
    }

    pause() {
        if (this.isSupported && this.isSpeaking) {
            this.synthesis.pause();
        }
    }

    resume() {
        if (this.isSupported) {
            this.synthesis.resume();
        }
    }

    cancel() {
        if (this.isSupported) {
            this.synthesis.cancel();
            this.isSpeaking = false;
        }
    }

    setVoice(voiceName) {
        const voices = this.synthesis.getVoices();
        this.voice = voices.find(v => v.name === voiceName) || this.voice;
    }

    setRate(rate) {
        this.rate = Math.max(0.1, Math.min(10, rate));
    }

    setPitch(pitch) {
        this.pitch = Math.max(0, Math.min(2, pitch));
    }

    setVolume(volume) {
        this.volume = Math.max(0, Math.min(1, volume));
    }

    setLanguage(language) {
        this.language = language;
        this.loadVoices();
    }

    dispatchEvent(eventName, detail = {}) {
        const event = new CustomEvent(eventName, { detail });
        document.dispatchEvent(event);
    }
}

class VoiceAssistant {
    constructor(sessionId = null) {
        this.sessionId = sessionId;
        this.voiceInput = new VoiceInput();
        this.voiceOutput = new VoiceOutput();
        this.isProcessing = false;
        this.enableTTS = true;
        this.autoSend = true; // Automatically send transcript to chat

        this.init();
    }

    init() {
        // Listen for voice-result events instead of using callbacks
        document.addEventListener('voice-result', (e) => {
            if (e.detail.isFinal) {
                console.log('Voice result received via event:', e.detail.transcript);
                if (this.autoSend) {
                    this.sendToChat(e.detail.transcript);
                } else {
                    this.processVoiceCommand(e.detail.transcript);
                }
            }
        });

        console.log('Voice assistant listening for voice-result events');

        // Listen for AI responses
        document.addEventListener('ai-response', (e) => {
            if (this.enableTTS && e.detail.response) {
                this.voiceOutput.speak(e.detail.response);
            }
        });
    }

    sendToChat(transcript) {
        // Find the chat input and send button
        const chatInput = document.getElementById('chat-input');
        const sendButton = chatInput?.closest('form')?.querySelector('button[type="submit"]');

        if (chatInput && sendButton) {
            // Set the input value
            chatInput.value = transcript;

            // Trigger the send button click
            sendButton.click();

            console.log('Sent to chat:', transcript);
        } else {
            console.warn('Chat input or send button not found, falling back to API');
            this.processVoiceCommand(transcript);
        }
    }

    async processVoiceCommand(transcript) {
        if (this.isProcessing) return;

        this.isProcessing = true;
        this.dispatchEvent('voice-processing', { transcript });

        try {
            // Send to AI assistant API
            const response = await fetch(`/api/v1/ai/chat?sessionId=${this.sessionId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: transcript,
                    stream: false,
                    includeContext: true
                })
            });

            if (!response.ok) {
                throw new Error(`AI request failed: ${response.statusText}`);
            }

            const data = await response.json();

            // Dispatch AI response event
            this.dispatchEvent('ai-response', {
                transcript,
                response: data.response,
                responseTime: data.responseTime
            });

            // Speak response if TTS enabled
            if (this.enableTTS) {
                this.voiceOutput.speak(data.response);
            }

        } catch (error) {
            console.error('Voice command processing error:', error);
            this.dispatchEvent('voice-error', { error: error.message });
        } finally {
            this.isProcessing = false;
        }
    }

    async sendVoiceToAPI(audioBlob) {
        // Alternative: Send audio directly to voice API endpoint
        const formData = new FormData();
        formData.append('audio', audioBlob, 'voice.webm');
        formData.append('language', this.voiceInput.language);
        formData.append('enableTTS', this.enableTTS);

        try {
            const response = await fetch(`/api/v1/ai/voice?sessionId=${this.sessionId}`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error(`Voice API request failed: ${response.statusText}`);
            }

            const data = await response.json();

            this.dispatchEvent('ai-response', {
                transcription: data.transcription,
                response: data.response,
                responseTime: data.responseTime,
                audioUrl: data.audioUrl
            });

            // Play audio response if available
            if (data.audioUrl) {
                this.playAudioResponse(data.audioUrl);
            }

            return data;
        } catch (error) {
            console.error('Voice API error:', error);
            this.dispatchEvent('voice-error', { error: error.message });
            return null;
        }
    }

    playAudioResponse(audioUrl) {
        const audio = new Audio(audioUrl);
        audio.play().catch(error => {
            console.error('Failed to play audio response:', error);
        });
    }

    setSessionId(sessionId) {
        this.sessionId = sessionId;
    }

    enableTextToSpeech(enabled) {
        this.enableTTS = enabled;
    }

    startListening() {
        return this.voiceInput.start();
    }

    stopListening() {
        this.voiceInput.stop();
    }

    speak(text, options) {
        return this.voiceOutput.speak(text, options);
    }

    dispatchEvent(eventName, detail = {}) {
        const event = new CustomEvent(eventName, { detail });
        document.dispatchEvent(event);
    }
}

// Audio recorder for sending raw audio to API
class AudioRecorder {
    constructor() {
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.isRecording = false;
        this.stream = null;
    }

    async start() {
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            this.mediaRecorder = new MediaRecorder(this.stream);

            this.mediaRecorder.ondataavailable = (event) => {
                this.audioChunks.push(event.data);
            };

            this.mediaRecorder.onstop = () => {
                this.isRecording = false;
            };

            this.audioChunks = [];
            this.mediaRecorder.start();
            this.isRecording = true;

            return true;
        } catch (error) {
            console.error('Failed to start audio recording:', error);
            return false;
        }
    }

    stop() {
        return new Promise((resolve) => {
            if (!this.mediaRecorder || !this.isRecording) {
                resolve(null);
                return;
            }

            this.mediaRecorder.onstop = () => {
                const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
                this.audioChunks = [];
                this.isRecording = false;

                // Stop all tracks
                if (this.stream) {
                    this.stream.getTracks().forEach(track => track.stop());
                }

                resolve(audioBlob);
            };

            this.mediaRecorder.stop();
        });
    }
}

// Initialize global instances
let voiceInput = null;
let voiceOutput = null;
let voiceAssistant = null;

function initializeVoice() {
    // Only initialize once
    if (voiceInput) return;

    console.log('Initializing voice system...');

    voiceInput = new VoiceInput();
    voiceOutput = new VoiceOutput();

    // Expose to window for global access FIRST
    window.voiceInput = voiceInput;
    window.voiceOutput = voiceOutput;

    // Then initialize voice assistant (will connect to voiceInput)
    voiceAssistant = new VoiceAssistant();
    window.voiceAssistant = voiceAssistant;

    console.log('Voice system initialized:', {
        inputSupported: voiceInput.isSupported,
        outputSupported: voiceOutput.isSupported,
        voiceAssistant: !!voiceAssistant
    });
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeVoice);
} else {
    initializeVoice();
}

// Also try to reinitialize when AI chat is loaded
setTimeout(initializeVoice, 1000);

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { VoiceInput, VoiceOutput, VoiceAssistant, AudioRecorder };
}

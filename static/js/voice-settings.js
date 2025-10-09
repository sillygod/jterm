/**
 * Voice Settings UI Handler
 */

(function() {
    let voiceSettingsInitialized = false;

    function initVoiceSettings() {
        if (voiceSettingsInitialized) return;

        // Get elements
        const languageSelect = document.getElementById('voice-language');
        const continuousCheckbox = document.getElementById('voice-continuous');
        const interimCheckbox = document.getElementById('voice-interim');
        const ttsEnabledCheckbox = document.getElementById('tts-enabled');
        const ttsVoiceSelect = document.getElementById('tts-voice');
        const ttsRateSlider = document.getElementById('tts-rate');
        const ttsPitchSlider = document.getElementById('tts-pitch');
        const ttsVolumeSlider = document.getElementById('tts-volume');
        const testVoiceButton = document.getElementById('test-voice-button');
        const saveButton = document.getElementById('save-voice-settings');

        if (!languageSelect) return;

        // Populate TTS voices
        function populateVoices() {
            if (window.voiceOutput && window.voiceOutput.synthesis) {
                const voices = window.voiceOutput.synthesis.getVoices();
                ttsVoiceSelect.innerHTML = '<option value="">Default</option>';
                voices.forEach(voice => {
                    const option = document.createElement('option');
                    option.value = voice.name;
                    option.textContent = `${voice.name} (${voice.lang})`;
                    ttsVoiceSelect.appendChild(option);
                });
            }
        }

        // Update slider value displays
        ttsRateSlider?.addEventListener('input', (e) => {
            document.getElementById('tts-rate-value').textContent = e.target.value;
        });

        ttsPitchSlider?.addEventListener('input', (e) => {
            document.getElementById('tts-pitch-value').textContent = e.target.value;
        });

        ttsVolumeSlider?.addEventListener('input', (e) => {
            const percentage = Math.round(e.target.value * 100);
            document.getElementById('tts-volume-value').textContent = `${percentage}%`;
        });

        // Test voice button
        testVoiceButton?.addEventListener('click', () => {
            const testText = "Hello! This is a test of the text to speech system.";

            if (window.voiceOutput) {
                const options = {
                    rate: parseFloat(ttsRateSlider.value),
                    pitch: parseFloat(ttsPitchSlider.value),
                    volume: parseFloat(ttsVolumeSlider.value)
                };

                if (ttsVoiceSelect.value) {
                    window.voiceOutput.setVoice(ttsVoiceSelect.value);
                }

                window.voiceOutput.speak(testText, options);
            } else {
                alert('Text-to-speech not available');
            }
        });

        // Save settings
        saveButton?.addEventListener('click', () => {
            // Save to localStorage
            const settings = {
                language: languageSelect.value,
                continuous: continuousCheckbox.checked,
                interim: interimCheckbox.checked,
                ttsEnabled: ttsEnabledCheckbox.checked,
                ttsVoice: ttsVoiceSelect.value,
                ttsRate: parseFloat(ttsRateSlider.value),
                ttsPitch: parseFloat(ttsPitchSlider.value),
                ttsVolume: parseFloat(ttsVolumeSlider.value)
            };

            localStorage.setItem('voiceSettings', JSON.stringify(settings));

            // Apply settings
            if (window.voiceInput) {
                window.voiceInput.setLanguage(settings.language);
                window.voiceInput.continuous = settings.continuous;
                window.voiceInput.interimResults = settings.interim;
            }

            if (window.voiceOutput) {
                window.voiceOutput.setRate(settings.ttsRate);
                window.voiceOutput.setPitch(settings.ttsPitch);
                window.voiceOutput.setVolume(settings.ttsVolume);
                if (settings.ttsVoice) {
                    window.voiceOutput.setVoice(settings.ttsVoice);
                }
            }

            if (window.voiceAssistant) {
                window.voiceAssistant.enableTextToSpeech(settings.ttsEnabled);
            }

            // Close modal
            document.getElementById('voice-settings-modal').style.display = 'none';

            // Show success message
            alert('Voice settings saved!');
        });

        // Load saved settings
        function loadSettings() {
            const saved = localStorage.getItem('voiceSettings');
            if (saved) {
                try {
                    const settings = JSON.parse(saved);

                    if (settings.language) languageSelect.value = settings.language;
                    if (settings.continuous !== undefined) continuousCheckbox.checked = settings.continuous;
                    if (settings.interim !== undefined) interimCheckbox.checked = settings.interim;
                    if (settings.ttsEnabled !== undefined) ttsEnabledCheckbox.checked = settings.ttsEnabled;
                    if (settings.ttsVoice) ttsVoiceSelect.value = settings.ttsVoice;
                    if (settings.ttsRate !== undefined) {
                        ttsRateSlider.value = settings.ttsRate;
                        document.getElementById('tts-rate-value').textContent = settings.ttsRate;
                    }
                    if (settings.ttsPitch !== undefined) {
                        ttsPitchSlider.value = settings.ttsPitch;
                        document.getElementById('tts-pitch-value').textContent = settings.ttsPitch;
                    }
                    if (settings.ttsVolume !== undefined) {
                        ttsVolumeSlider.value = settings.ttsVolume;
                        const percentage = Math.round(settings.ttsVolume * 100);
                        document.getElementById('tts-volume-value').textContent = `${percentage}%`;
                    }
                } catch (e) {
                    console.error('Failed to load voice settings:', e);
                }
            }
        }

        // Initialize
        populateVoices();
        loadSettings();

        // Reload voices when they change (some browsers load them async)
        if (window.speechSynthesis) {
            window.speechSynthesis.onvoiceschanged = populateVoices;
        }

        voiceSettingsInitialized = true;
    }

    // Initialize when modal is opened
    document.addEventListener('click', (e) => {
        if (e.target.id === 'voice-settings-button' ||
            e.target.closest('#voice-settings-button')) {
            setTimeout(initVoiceSettings, 100);
        }
    });

    // Also try to initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            setTimeout(initVoiceSettings, 500);
        });
    } else {
        setTimeout(initVoiceSettings, 500);
    }
})();

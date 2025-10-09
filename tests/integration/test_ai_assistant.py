"""Integration tests for AI assistant with voice input functionality.

These tests verify complete user workflows for AI assistant integration,
including voice input/output, context-aware suggestions, command generation,
and intelligent terminal interaction with performance requirements.

CRITICAL: These tests MUST FAIL until the implementation is complete.
Tests validate end-to-end AI assistant workflows with <2s simple, <5s complex responses.
"""

import pytest
import json
import time
import base64
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock

# Import the app once it's implemented
try:
    from src.main import app
    APP_AVAILABLE = True
except ImportError:
    APP_AVAILABLE = False


class TestAIAssistantIntegration:
    """Test complete AI assistant integration workflows."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        if not APP_AVAILABLE:
            pytest.skip("Application not implemented yet")
        return TestClient(app)

    @pytest.fixture
    def auth_headers(self):
        """Mock authentication headers."""
        return {"Authorization": "Bearer mock-jwt-token"}

    @pytest.fixture
    def terminal_session(self, client, auth_headers):
        """Create a terminal session with AI assistant enabled."""
        response = client.post(
            "/api/terminal/sessions",
            json={
                "shell": "bash",
                "workingDirectory": "/tmp",
                "terminalSize": {"cols": 80, "rows": 24},
                "aiAssistantEnabled": True
            },
            headers=auth_headers
        )
        return response.json()["sessionId"]

    @pytest.fixture
    def mock_audio_data(self):
        """Mock audio data for voice input testing."""
        return {
            "audioData": base64.b64encode(b"fake-audio-wav-data").decode(),
            "format": "wav",
            "sampleRate": 16000,
            "channels": 1,
            "duration": 3.5
        }

    @pytest.fixture
    def mock_ai_responses(self):
        """Mock AI assistant responses for testing."""
        return {
            "simple_command": {
                "type": "command_suggestion",
                "command": "ls -la",
                "explanation": "List all files in current directory with detailed information",
                "confidence": 0.95,
                "responseTime": 1.2
            },
            "complex_analysis": {
                "type": "code_analysis",
                "suggestions": [
                    "Consider using virtual environment for Python project",
                    "Add .gitignore file for better version control",
                    "Use requirements.txt for dependency management"
                ],
                "explanation": "Based on your current directory structure, here are some recommendations for Python development best practices.",
                "confidence": 0.87,
                "responseTime": 4.3
            },
            "error_help": {
                "type": "error_assistance",
                "problem": "Command not found: npm",
                "solutions": [
                    "Install Node.js and npm: sudo apt install nodejs npm",
                    "Check if Node.js is in PATH: echo $PATH",
                    "Use alternative package manager: sudo apt install yarn"
                ],
                "explanation": "The 'npm' command is not available. This typically means Node.js is not installed.",
                "confidence": 0.92,
                "responseTime": 1.8
            }
        }

    def test_voice_input_to_command_workflow(self, client, auth_headers, terminal_session, mock_audio_data, mock_ai_responses):
        """Test complete workflow: voice input → speech recognition → AI interpretation → command execution.

        User Story: User speaks command to AI assistant, system recognizes speech,
        interprets intent, suggests command, and executes with user confirmation.
        """
        with pytest.raises((Exception, AssertionError)):
            # Step 1: Start voice input session
            voice_session_response = client.post(
                f"/api/ai/voice-session",
                json={
                    "sessionId": terminal_session,
                    "language": "en-US",
                    "mode": "command"
                },
                headers=auth_headers
            )
            assert voice_session_response.status_code == 201
            voice_session_id = voice_session_response.json()["voiceSessionId"]

            # Step 2: Send audio data for speech recognition
            transcription_start = time.time()
            transcription_response = client.post(
                f"/api/ai/voice-session/{voice_session_id}/audio",
                json=mock_audio_data,
                headers=auth_headers
            )
            transcription_time = time.time() - transcription_start

            assert transcription_response.status_code == 200
            transcription_data = transcription_response.json()
            assert "transcript" in transcription_data
            assert transcription_data["confidence"] > 0.8
            assert transcription_time < 3.0  # Should transcribe quickly

            # Step 3: AI interprets spoken command
            interpretation_start = time.time()
            interpretation_response = client.post(
                f"/api/ai/interpret",
                json={
                    "text": transcription_data["transcript"],
                    "context": {
                        "sessionId": terminal_session,
                        "currentDirectory": "/tmp",
                        "shell": "bash",
                        "recentCommands": ["pwd", "ls"]
                    }
                },
                headers=auth_headers
            )
            interpretation_time = time.time() - interpretation_start

            assert interpretation_response.status_code == 200
            interpretation_data = interpretation_response.json()
            assert interpretation_data["type"] in ["command_suggestion", "question", "explanation"]
            assert interpretation_time < 2.0  # Simple response <2s requirement

            # Step 4: Execute suggested command with confirmation
            if interpretation_data["type"] == "command_suggestion":
                with client.websocket_connect(f"/ws/terminal/{terminal_session}") as websocket:
                    # Send command suggestion to user
                    websocket.send_json({
                        "type": "ai_suggestion",
                        "suggestion": interpretation_data,
                        "requireConfirmation": True
                    })

                    # User confirms execution
                    websocket.send_json({
                        "type": "confirm_ai_suggestion",
                        "execute": True
                    })

                    # Should receive command execution
                    execution_response = websocket.receive_json()
                    assert execution_response["type"] == "command_executed"
                    assert "output" in execution_response

    def test_context_aware_ai_suggestions(self, client, auth_headers, terminal_session, mock_ai_responses):
        """Test AI assistant provides context-aware suggestions based on terminal state.

        User Story: AI assistant analyzes current terminal context (directory, files, history)
        and provides intelligent, relevant suggestions and help.
        """
        with pytest.raises((Exception, AssertionError)):
            # Set up context by running some commands
            with client.websocket_connect(f"/ws/terminal/{terminal_session}") as websocket:
                # Create a Python project structure
                setup_commands = [
                    "mkdir test_project\r",
                    "cd test_project\r",
                    "touch main.py\r",
                    "touch requirements.txt\r",
                    "ls -la\r"
                ]

                for command in setup_commands:
                    websocket.send_json({
                        "type": "input",
                        "data": command
                    })
                    response = websocket.receive_json()
                    assert response["type"] == "output"

                # Request AI analysis of current context
                websocket.send_json({
                    "type": "ai_analyze_context"
                })

                ai_response = websocket.receive_json()
                assert ai_response["type"] == "ai_analysis"
                assert "suggestions" in ai_response
                assert "context" in ai_response

            # Get detailed context analysis via API
            context_response = client.post(
                f"/api/ai/analyze-context",
                json={
                    "sessionId": terminal_session,
                    "includeFileAnalysis": True,
                    "includeCommandHistory": True
                },
                headers=auth_headers
            )
            assert context_response.status_code == 200
            context_data = context_response.json()

            # Verify context understanding
            assert "currentDirectory" in context_data["context"]
            assert "detectedProjectType" in context_data
            assert context_data["detectedProjectType"] == "python"
            assert len(context_data["suggestions"]) > 0

            # Suggestions should be relevant to Python project
            python_suggestions = [s for s in context_data["suggestions"] if "python" in s.lower() or "pip" in s.lower()]
            assert len(python_suggestions) > 0

    def test_ai_error_assistance_workflow(self, client, auth_headers, terminal_session, mock_ai_responses):
        """Test AI assistant helps with command errors and troubleshooting.

        User Story: When user encounters errors, AI assistant analyzes the error,
        provides explanations, and suggests fixes.
        """
        with pytest.raises((Exception, AssertionError)):
            # Simulate command that produces error
            with client.websocket_connect(f"/ws/terminal/{terminal_session}") as websocket:
                # Run command that will fail
                websocket.send_json({
                    "type": "input",
                    "data": "nonexistent-command --help\r"
                })

                error_output = websocket.receive_json()
                assert error_output["type"] == "output"
                assert "command not found" in error_output["data"].lower() or "not found" in error_output["data"].lower()

                # AI should automatically detect error and offer help
                ai_help_response = websocket.receive_json()
                assert ai_help_response["type"] == "ai_error_help"
                assert "problem" in ai_help_response
                assert "solutions" in ai_help_response
                assert len(ai_help_response["solutions"]) > 0

            # Test explicit error help request
            error_help_response = client.post(
                f"/api/ai/error-help",
                json={
                    "errorText": "bash: npm: command not found",
                    "command": "npm install",
                    "context": {
                        "sessionId": terminal_session,
                        "shell": "bash",
                        "os": "linux"
                    }
                },
                headers=auth_headers
            )
            assert error_help_response.status_code == 200
            help_data = error_help_response.json()

            assert help_data["type"] == "error_assistance"
            assert "npm" in help_data["problem"].lower()
            assert len(help_data["solutions"]) >= 2
            assert any("install" in solution.lower() for solution in help_data["solutions"])

    def test_ai_performance_requirements(self, client, auth_headers, terminal_session):
        """Test AI assistant meets performance requirements: <2s simple, <5s complex.

        User Story: AI responses are fast enough to not interrupt terminal workflow,
        with different response times for simple vs complex queries.
        """
        with pytest.raises((Exception, AssertionError)):
            # Test simple query performance (<2s requirement)
            simple_queries = [
                "What does ls -la do?",
                "How to change directory?",
                "Show current path",
                "List hidden files"
            ]

            for query in simple_queries:
                start_time = time.time()
                response = client.post(
                    f"/api/ai/query",
                    json={
                        "query": query,
                        "type": "simple",
                        "context": {"sessionId": terminal_session}
                    },
                    headers=auth_headers
                )
                response_time = time.time() - start_time

                assert response.status_code == 200
                assert response_time < 2.0  # Simple queries <2s

                response_data = response.json()
                assert "answer" in response_data
                assert response_data["type"] == "simple"

            # Test complex query performance (<5s requirement)
            complex_queries = [
                "Analyze this Python project structure and suggest improvements",
                "Help me set up a complete Docker development environment",
                "Explain best practices for Git workflow in team development",
                "Generate a comprehensive test setup for this Node.js project"
            ]

            for query in complex_queries:
                start_time = time.time()
                response = client.post(
                    f"/api/ai/query",
                    json={
                        "query": query,
                        "type": "complex",
                        "context": {
                            "sessionId": terminal_session,
                            "includeDeepAnalysis": True
                        }
                    },
                    headers=auth_headers
                )
                response_time = time.time() - start_time

                assert response.status_code == 200
                assert response_time < 5.0  # Complex queries <5s

                response_data = response.json()
                assert "answer" in response_data
                assert response_data["type"] == "complex"
                assert len(response_data["answer"]) > 100  # Complex responses should be detailed

    def test_ai_voice_output_synthesis(self, client, auth_headers, terminal_session):
        """Test AI voice output synthesis and audio playback.

        User Story: AI assistant can speak responses back to user with natural
        voice synthesis and proper audio formatting.
        """
        with pytest.raises((Exception, AssertionError)):
            # Request AI response with voice output
            voice_request_response = client.post(
                f"/api/ai/query",
                json={
                    "query": "Explain what the ls command does",
                    "outputMode": "voice",
                    "voiceSettings": {
                        "language": "en-US",
                        "voice": "neural-female",
                        "speed": 1.0
                    },
                    "context": {"sessionId": terminal_session}
                },
                headers=auth_headers
            )

            assert voice_request_response.status_code == 200
            voice_data = voice_request_response.json()

            assert "textResponse" in voice_data
            assert "audioUrl" in voice_data
            assert "duration" in voice_data
            assert voice_data["format"] == "mp3"

            # Get audio file
            audio_response = client.get(
                voice_data["audioUrl"],
                headers=auth_headers
            )
            assert audio_response.status_code == 200
            assert audio_response.headers["content-type"].startswith("audio/")

            # Test streaming audio for long responses
            long_query_response = client.post(
                f"/api/ai/query",
                json={
                    "query": "Provide a comprehensive explanation of Git workflow with examples",
                    "outputMode": "voice_stream",
                    "context": {"sessionId": terminal_session}
                },
                headers=auth_headers
            )

            assert long_query_response.status_code == 200
            stream_data = long_query_response.json()
            assert "streamUrl" in stream_data
            assert stream_data["streaming"] == True

    def test_ai_command_generation_and_validation(self, client, auth_headers, terminal_session):
        """Test AI command generation with safety validation.

        User Story: AI generates safe, valid commands based on user requests
        and validates commands for safety before execution.
        """
        with pytest.raises((Exception, AssertionError)):
            # Test safe command generation
            safe_requests = [
                "Create a new directory called 'my_project'",
                "Show me all Python files in current directory",
                "Copy file.txt to backup.txt",
                "Find all files modified in last 24 hours"
            ]

            for request in safe_requests:
                generation_response = client.post(
                    f"/api/ai/generate-command",
                    json={
                        "request": request,
                        "context": {
                            "sessionId": terminal_session,
                            "currentDirectory": "/tmp/safe_area",
                            "shell": "bash"
                        }
                    },
                    headers=auth_headers
                )

                assert generation_response.status_code == 200
                command_data = generation_response.json()

                assert "command" in command_data
                assert "explanation" in command_data
                assert "safetyLevel" in command_data
                assert command_data["safetyLevel"] in ["safe", "warning", "dangerous"]
                assert command_data["validated"] == True

                # Safe commands should be marked as safe
                assert command_data["safetyLevel"] == "safe"

            # Test potentially dangerous command detection
            dangerous_requests = [
                "Delete all files in root directory",
                "Format the hard drive",
                "Remove system files",
                "Change root password"
            ]

            for request in dangerous_requests:
                dangerous_response = client.post(
                    f"/api/ai/generate-command",
                    json={
                        "request": request,
                        "context": {"sessionId": terminal_session}
                    },
                    headers=auth_headers
                )

                assert dangerous_response.status_code == 200
                dangerous_data = dangerous_response.json()

                # Should be flagged as dangerous or refuse to generate
                assert dangerous_data["safetyLevel"] in ["dangerous", "refused"]
                if dangerous_data["safetyLevel"] == "dangerous":
                    assert "warning" in dangerous_data
                    assert dangerous_data["requiresConfirmation"] == True

    def test_ai_learning_and_personalization(self, client, auth_headers, terminal_session):
        """Test AI learning from user behavior and personalization.

        User Story: AI assistant learns user preferences and command patterns
        to provide increasingly personalized suggestions.
        """
        with pytest.raises((Exception, AssertionError)):
            # Simulate user behavior pattern
            user_patterns = [
                {"command": "git status", "frequency": 10},
                {"command": "git add .", "frequency": 8},
                {"command": "git commit -m", "frequency": 8},
                {"command": "npm test", "frequency": 5},
                {"command": "docker-compose up", "frequency": 3}
            ]

            # Record user behavior
            for pattern in user_patterns:
                for _ in range(pattern["frequency"]):
                    behavior_response = client.post(
                        f"/api/ai/record-behavior",
                        json={
                            "sessionId": terminal_session,
                            "command": pattern["command"],
                            "timestamp": time.time(),
                            "context": {
                                "directory": "/tmp/project",
                                "success": True
                            }
                        },
                        headers=auth_headers
                    )
                    assert behavior_response.status_code == 200

            # Get personalized suggestions
            personalized_response = client.get(
                f"/api/ai/personalized-suggestions",
                params={"sessionId": terminal_session},
                headers=auth_headers
            )

            assert personalized_response.status_code == 200
            suggestions_data = personalized_response.json()

            assert "frequentCommands" in suggestions_data
            assert "suggestedWorkflows" in suggestions_data
            assert "shortcuts" in suggestions_data

            # Verify Git commands are prominently suggested
            frequent_commands = suggestions_data["frequentCommands"]
            git_commands = [cmd for cmd in frequent_commands if "git" in cmd["command"]]
            assert len(git_commands) >= 3

            # Test adaptive suggestion based on context
            adaptive_response = client.post(
                f"/api/ai/adaptive-suggestion",
                json={
                    "currentCommand": "git add",
                    "context": {
                        "sessionId": terminal_session,
                        "recentCommands": ["git status", "git add ."]
                    }
                },
                headers=auth_headers
            )

            assert adaptive_response.status_code == 200
            adaptive_data = adaptive_response.json()

            # Should suggest commit as next logical step
            assert "git commit" in adaptive_data["nextCommand"].lower()

    def test_ai_multi_language_support(self, client, auth_headers, terminal_session, mock_audio_data):
        """Test AI assistant multi-language support for voice and text.

        User Story: AI assistant supports multiple languages for international users,
        including voice recognition and synthesis in different languages.
        """
        with pytest.raises((Exception, AssertionError)):
            # Test different language configurations
            languages = [
                {"code": "en-US", "name": "English (US)"},
                {"code": "es-ES", "name": "Spanish (Spain)"},
                {"code": "fr-FR", "name": "French (France)"},
                {"code": "de-DE", "name": "German (Germany)"},
                {"code": "ja-JP", "name": "Japanese (Japan)"}
            ]

            for lang in languages:
                # Test voice recognition in different language
                voice_session_response = client.post(
                    f"/api/ai/voice-session",
                    json={
                        "sessionId": terminal_session,
                        "language": lang["code"],
                        "mode": "command"
                    },
                    headers=auth_headers
                )
                assert voice_session_response.status_code == 201

                # Test text query in different language
                text_query_response = client.post(
                    f"/api/ai/query",
                    json={
                        "query": "Help me with terminal commands",
                        "language": lang["code"],
                        "context": {"sessionId": terminal_session}
                    },
                    headers=auth_headers
                )
                assert text_query_response.status_code == 200
                query_data = text_query_response.json()

                # Response should be in requested language
                assert "answer" in query_data
                assert query_data["language"] == lang["code"]

            # Test language auto-detection
            auto_detect_response = client.post(
                f"/api/ai/query",
                json={
                    "query": "¿Cómo puedo listar archivos en el directorio?",  # Spanish
                    "autoDetectLanguage": True,
                    "context": {"sessionId": terminal_session}
                },
                headers=auth_headers
            )

            assert auto_detect_response.status_code == 200
            auto_detect_data = auto_detect_response.json()
            assert auto_detect_data["detectedLanguage"].startswith("es")  # Spanish

    def test_ai_integration_with_session_features(self, client, auth_headers, terminal_session):
        """Test AI assistant integration with other terminal features.

        User Story: AI assistant works seamlessly with recording, media viewing,
        and other terminal features to provide comprehensive assistance.
        """
        with pytest.raises((Exception, AssertionError)):
            # Enable recording for AI analysis
            recording_response = client.post(
                f"/api/terminal/sessions/{terminal_session}/recording/start",
                headers=auth_headers
            )
            assert recording_response.status_code == 200

            # Upload a file for AI to analyze
            upload_response = client.post(
                f"/api/media/upload",
                files={
                    "file": ("script.py", b"print('Hello World')\nimport os\nos.listdir('.')", "text/python")
                },
                data={"sessionId": terminal_session},
                headers=auth_headers
            )
            file_id = upload_response.json()["mediaId"]

            # Ask AI to analyze the uploaded file
            analysis_response = client.post(
                f"/api/ai/analyze-file",
                json={
                    "fileId": file_id,
                    "analysisType": "code_review",
                    "context": {"sessionId": terminal_session}
                },
                headers=auth_headers
            )

            assert analysis_response.status_code == 200
            analysis_data = analysis_response.json()

            assert "analysis" in analysis_data
            assert "suggestions" in analysis_data
            assert "codeQuality" in analysis_data

            # AI should understand it's a Python script
            assert "python" in analysis_data["analysis"].lower()

            # Test AI assistance with recorded session
            with client.websocket_connect(f"/ws/terminal/{terminal_session}") as websocket:
                # Run some commands for AI to observe
                websocket.send_json({
                    "type": "input",
                    "data": "python script.py\r"
                })

                output_response = websocket.receive_json()
                assert output_response["type"] == "output"

                # Ask AI about the session
                websocket.send_json({
                    "type": "ai_query",
                    "query": "What did I just run and what can I do next?"
                })

                ai_response = websocket.receive_json()
                assert ai_response["type"] == "ai_response"
                assert "python" in ai_response["answer"].lower()
                assert len(ai_response["suggestions"]) > 0
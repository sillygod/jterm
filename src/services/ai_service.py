"""AI assistant service with provider abstraction and context management.

This service provides AI assistance with multiple provider support (OpenAI, Anthropic, Local),
context-aware responses, performance optimization for <2s simple/<5s complex responses,
and voice input/output capabilities.
"""

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Union, Callable, AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from src.models.ai_context import AIContext
from src.models.terminal_session import TerminalSession
from src.database.base import AsyncSessionLocal


logger = logging.getLogger(__name__)


class AIProvider(str, Enum):
    """AI provider enumeration."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"
    HUGGINGFACE = "huggingface"
    COHERE = "cohere"


class ResponseType(str, Enum):
    """AI response type enumeration."""
    TEXT = "text"
    VOICE = "voice"
    COMMAND = "command"
    EXPLANATION = "explanation"
    SUGGESTION = "suggestion"


class MessageRole(str, Enum):
    """Message role enumeration."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass
class AIConfig:
    """AI service configuration."""
    default_provider: AIProvider = AIProvider.OPENAI
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    local_endpoint: Optional[str] = None
    local_api_key: Optional[str] = None  # For OpenAI-compatible providers that need auth
    default_model: str = "gpt-4"
    max_tokens: int = 1000
    temperature: float = 0.7
    timeout: float = 30.0
    simple_response_target: float = 2.0  # seconds
    complex_response_target: float = 5.0  # seconds
    enable_voice: bool = True
    enable_streaming: bool = True
    context_window: int = 8192


@dataclass
class AIMessage:
    """AI conversation message."""
    message_id: str
    role: MessageRole
    content: str
    timestamp: datetime
    message_type: ResponseType = ResponseType.TEXT
    tokens: int = 0
    processing_time: float = 0.0
    confidence: float = 1.0
    sources: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        return {
            "messageId": self.message_id,
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "type": self.message_type.value,
            "tokens": self.tokens,
            "processingTime": self.processing_time,
            "confidence": self.confidence,
            "sources": self.sources,
            "metadata": self.metadata
        }


@dataclass
class AIResponse:
    """AI response with metadata."""
    content: str
    message_type: ResponseType = ResponseType.TEXT
    tokens: int = 0
    processing_time: float = 0.0
    confidence: float = 1.0
    sources: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


class AIProviderError(Exception):
    """Base exception for AI provider operations."""
    pass


class AIProviderTimeoutError(AIProviderError):
    """Raised when AI provider operation times out."""
    pass


class AIProviderRateLimitError(AIProviderError):
    """Raised when AI provider rate limit is exceeded."""
    pass


class AIProviderQuotaError(AIProviderError):
    """Raised when AI provider quota is exceeded."""
    pass


class BaseAIProvider(ABC):
    """Abstract base class for AI providers."""

    def __init__(self, config: AIConfig):
        self.config = config

    @abstractmethod
    async def generate_response(self, messages: List[AIMessage], **kwargs) -> AIResponse:
        """Generate AI response from messages."""
        pass

    @abstractmethod
    async def stream_response(self, messages: List[AIMessage], **kwargs) -> AsyncGenerator[str, None]:
        """Stream AI response from messages."""
        pass

    @abstractmethod
    async def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        pass

    @abstractmethod
    async def validate_connection(self) -> bool:
        """Validate provider connection and credentials."""
        pass


class OpenAIProvider(BaseAIProvider):
    """OpenAI API provider implementation."""

    def __init__(self, config: AIConfig):
        super().__init__(config)
        if not OPENAI_AVAILABLE:
            raise AIProviderError("OpenAI library not available")

        if not config.openai_api_key:
            raise AIProviderError("OpenAI API key not provided")

        openai.api_key = config.openai_api_key

    async def generate_response(self, messages: List[AIMessage], **kwargs) -> AIResponse:
        """Generate response using OpenAI API."""
        start_time = time.time()

        try:
            # Convert messages to OpenAI format
            openai_messages = self._convert_messages(messages)

            # Make API call
            response = await openai.ChatCompletion.acreate(
                model=kwargs.get("model", self.config.default_model),
                messages=openai_messages,
                max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                temperature=kwargs.get("temperature", self.config.temperature),
                timeout=self.config.timeout
            )

            processing_time = time.time() - start_time

            # Extract response data
            choice = response.choices[0]
            content = choice.message.content
            tokens = response.usage.total_tokens

            return AIResponse(
                content=content,
                tokens=tokens,
                processing_time=processing_time,
                confidence=1.0 - (choice.finish_reason != "stop") * 0.2,
                metadata={
                    "model": response.model,
                    "finish_reason": choice.finish_reason,
                    "usage": response.usage
                }
            )

        except openai.RateLimitError as e:
            raise AIProviderRateLimitError(f"OpenAI rate limit exceeded: {e}")
        except openai.InvalidRequestError as e:
            raise AIProviderError(f"OpenAI invalid request: {e}")
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"OpenAI API error: {e}")
            return AIResponse(
                content="",
                processing_time=processing_time,
                error=str(e)
            )

    async def stream_response(self, messages: List[AIMessage], **kwargs) -> AsyncGenerator[str, None]:
        """Stream response using OpenAI API."""
        try:
            openai_messages = self._convert_messages(messages)

            response = await openai.ChatCompletion.acreate(
                model=kwargs.get("model", self.config.default_model),
                messages=openai_messages,
                max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                temperature=kwargs.get("temperature", self.config.temperature),
                stream=True,
                timeout=self.config.timeout
            )

            async for chunk in response:
                if chunk.choices[0].delta.get("content"):
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"OpenAI streaming error: {e}")
            yield f"Error: {e}"

    async def estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough approximation)."""
        # Simple approximation: ~4 characters per token
        return len(text) // 4

    async def validate_connection(self) -> bool:
        """Validate OpenAI connection."""
        try:
            await openai.Model.alist()
            return True
        except Exception as e:
            logger.error(f"OpenAI connection validation failed: {e}")
            return False

    def _convert_messages(self, messages: List[AIMessage]) -> List[Dict[str, str]]:
        """Convert internal messages to OpenAI format."""
        return [
            {"role": msg.role.value, "content": msg.content}
            for msg in messages
        ]


class AnthropicProvider(BaseAIProvider):
    """Anthropic Claude API provider implementation."""

    def __init__(self, config: AIConfig):
        super().__init__(config)
        if not ANTHROPIC_AVAILABLE:
            raise AIProviderError("Anthropic library not available")

        if not config.anthropic_api_key:
            raise AIProviderError("Anthropic API key not provided")

        self.client = anthropic.AsyncAnthropic(api_key=config.anthropic_api_key)

    async def generate_response(self, messages: List[AIMessage], **kwargs) -> AIResponse:
        """Generate response using Anthropic API."""
        start_time = time.time()

        try:
            # Convert messages to Anthropic format
            anthropic_messages = self._convert_messages(messages)

            # Make API call
            response = await self.client.messages.create(
                model=kwargs.get("model", "claude-3-sonnet-20240229"),
                messages=anthropic_messages,
                max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                temperature=kwargs.get("temperature", self.config.temperature)
            )

            processing_time = time.time() - start_time

            return AIResponse(
                content=response.content[0].text,
                tokens=response.usage.input_tokens + response.usage.output_tokens,
                processing_time=processing_time,
                confidence=1.0,
                metadata={
                    "model": response.model,
                    "usage": response.usage
                }
            )

        except anthropic.RateLimitError as e:
            raise AIProviderRateLimitError(f"Anthropic rate limit exceeded: {e}")
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Anthropic API error: {e}")
            return AIResponse(
                content="",
                processing_time=processing_time,
                error=str(e)
            )

    async def stream_response(self, messages: List[AIMessage], **kwargs) -> AsyncGenerator[str, None]:
        """Stream response using Anthropic API."""
        try:
            anthropic_messages = self._convert_messages(messages)

            async with self.client.messages.stream(
                model=kwargs.get("model", "claude-3-sonnet-20240229"),
                messages=anthropic_messages,
                max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                temperature=kwargs.get("temperature", self.config.temperature)
            ) as stream:
                async for text in stream.text_stream:
                    yield text

        except Exception as e:
            logger.error(f"Anthropic streaming error: {e}")
            yield f"Error: {e}"

    async def estimate_tokens(self, text: str) -> int:
        """Estimate token count."""
        return len(text) // 4

    async def validate_connection(self) -> bool:
        """Validate Anthropic connection."""
        try:
            # Simple test request
            await self.client.messages.create(
                model="claude-3-haiku-20240307",
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=1
            )
            return True
        except Exception as e:
            logger.error(f"Anthropic connection validation failed: {e}")
            return False

    def _convert_messages(self, messages: List[AIMessage]) -> List[Dict[str, str]]:
        """Convert internal messages to Anthropic format."""
        return [
            {"role": msg.role.value, "content": msg.content}
            for msg in messages
            if msg.role != MessageRole.SYSTEM  # Anthropic handles system prompts differently
        ]


class LocalProvider(BaseAIProvider):
    """Local AI provider implementation (OpenAI-compatible endpoints).

    Supports:
    - Ollama (local)
    - Mistral AI
    - together.ai
    - Groq
    - OpenRouter
    - Any OpenAI-compatible API
    """

    def __init__(self, config: AIConfig):
        super().__init__(config)
        if not AIOHTTP_AVAILABLE:
            raise AIProviderError("aiohttp library not available")

        if not config.local_endpoint:
            raise AIProviderError("Local endpoint not provided")

        self.endpoint = config.local_endpoint
        self.api_key = config.local_api_key  # Optional, for providers that need auth

    async def generate_response(self, messages: List[AIMessage], **kwargs) -> AIResponse:
        """Generate response using local endpoint."""
        start_time = time.time()

        try:
            # Build headers
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": kwargs.get("model", self.config.default_model),
                    "messages": self._convert_messages(messages),
                    "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
                    "temperature": kwargs.get("temperature", self.config.temperature)
                }

                async with session.post(
                    f"{self.endpoint}/v1/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=self.config.timeout
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        processing_time = time.time() - start_time

                        choice = data["choices"][0]
                        return AIResponse(
                            content=choice["message"]["content"],
                            tokens=data.get("usage", {}).get("total_tokens", 0),
                            processing_time=processing_time,
                            confidence=1.0,
                            metadata={"model": data.get("model", "unknown")}
                        )
                    else:
                        error_text = await response.text()
                        raise AIProviderError(f"Local API error: {response.status} - {error_text}")

        except asyncio.TimeoutError:
            raise AIProviderTimeoutError("Local AI request timed out")
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Local AI error: {e}")
            return AIResponse(
                content="",
                processing_time=processing_time,
                error=str(e)
            )

    async def stream_response(self, messages: List[AIMessage], **kwargs) -> AsyncGenerator[str, None]:
        """Stream response from local endpoint."""
        try:
            # Build headers
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": kwargs.get("model", self.config.default_model),
                    "messages": self._convert_messages(messages),
                    "stream": True
                }

                async with session.post(
                    f"{self.endpoint}/v1/chat/completions",
                    json=payload,
                    headers=headers
                ) as response:
                    async for line in response.content:
                        if line.startswith(b"data: "):
                            try:
                                data = json.loads(line[6:])
                                if "choices" in data and data["choices"]:
                                    delta = data["choices"][0].get("delta", {})
                                    if "content" in delta:
                                        yield delta["content"]
                            except json.JSONDecodeError:
                                continue

        except Exception as e:
            logger.error(f"Local AI streaming error: {e}")
            yield f"Error: {e}"

    async def estimate_tokens(self, text: str) -> int:
        """Estimate token count."""
        return len(text) // 4

    async def validate_connection(self) -> bool:
        """Validate local endpoint connection."""
        try:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.endpoint}/v1/models",
                    headers=headers,
                    timeout=5
                ) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"Local AI connection validation failed: {e}")
            return False

    def _convert_messages(self, messages: List[AIMessage]) -> List[Dict[str, str]]:
        """Convert internal messages to OpenAI-compatible format."""
        return [
            {"role": msg.role.value, "content": msg.content}
            for msg in messages
        ]


class ContextManager:
    """Manages AI conversation context and terminal state."""

    def __init__(self):
        self._context_cache: Dict[str, AIContext] = {}

    async def get_context(self, session_id: str) -> Optional[AIContext]:
        """Get AI context for session."""
        if session_id in self._context_cache:
            return self._context_cache[session_id]

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(AIContext).where(AIContext.session_id == session_id)
            )
            context = result.scalar_one_or_none()

            if context:
                self._context_cache[session_id] = context

            return context

    async def update_context(self, session_id: str, message: AIMessage) -> None:
        """Update context with new message."""
        context = await self.get_context(session_id)
        if not context:
            return

        # Add message to context
        message_id = context.add_message(
            role=message.role.value,
            content=message.content,
            message_type=message.message_type.value,
            tokens=message.tokens,
            processing_time=message.processing_time,
            confidence=message.confidence,
            sources=message.sources
        )

        # Prune context if needed
        if context.should_prune_context():
            context.prune_conversation_history()

        # Update database
        async with AsyncSessionLocal() as db:
            await db.merge(context)
            await db.commit()

        return message_id

    async def update_terminal_context(self, session_id: str, command: str, output: str, exit_code: int = 0) -> None:
        """Update terminal context."""
        context = await self.get_context(session_id)
        if context:
            context.update_terminal_context(command, output, exit_code)

            async with AsyncSessionLocal() as db:
                await db.merge(context)
                await db.commit()

    def clear_cache(self, session_id: str = None) -> None:
        """Clear context cache."""
        if session_id:
            self._context_cache.pop(session_id, None)
        else:
            self._context_cache.clear()


class AIService:
    """Main AI assistant service."""

    def __init__(self, config: AIConfig = None):
        self.config = config or AIConfig()
        self.providers: Dict[AIProvider, BaseAIProvider] = {}
        self.context_manager = ContextManager()
        self._initialize_providers()

    def _initialize_providers(self) -> None:
        """Initialize AI providers based on configuration."""
        try:
            if self.config.openai_api_key and OPENAI_AVAILABLE:
                self.providers[AIProvider.OPENAI] = OpenAIProvider(self.config)
        except Exception as e:
            logger.warning(f"Failed to initialize OpenAI provider: {e}")

        try:
            if self.config.anthropic_api_key and ANTHROPIC_AVAILABLE:
                self.providers[AIProvider.ANTHROPIC] = AnthropicProvider(self.config)
        except Exception as e:
            logger.warning(f"Failed to initialize Anthropic provider: {e}")

        try:
            if self.config.local_endpoint and AIOHTTP_AVAILABLE:
                self.providers[AIProvider.LOCAL] = LocalProvider(self.config)
        except Exception as e:
            logger.warning(f"Failed to initialize Local provider: {e}")

        if not self.providers:
            logger.warning("No AI providers available")

    async def generate_response(self, session_id: str, user_input: str,
                              response_type: ResponseType = ResponseType.TEXT,
                              provider: Optional[AIProvider] = None,
                              **kwargs) -> AIResponse:
        """Generate AI response for user input."""
        start_time = time.time()

        try:
            # Get provider
            provider = provider or self.config.default_provider
            ai_provider = self.providers.get(provider)

            if not ai_provider:
                return AIResponse(
                    content="AI service not available",
                    error="No AI provider configured"
                )

            # Get context
            context = await self.context_manager.get_context(session_id)
            if not context:
                return AIResponse(
                    content="Context not found",
                    error="AI context not initialized"
                )

            # Build messages
            messages = await self._build_messages(context, user_input, response_type)

            # Generate response
            response = await ai_provider.generate_response(messages, **kwargs)

            # Update context
            if response.content and not response.error:
                # Add user message
                user_message = AIMessage(
                    message_id="",
                    role=MessageRole.USER,
                    content=user_input,
                    timestamp=datetime.now(timezone.utc),
                    message_type=response_type
                )
                await self.context_manager.update_context(session_id, user_message)

                # Add assistant response
                assistant_message = AIMessage(
                    message_id="",
                    role=MessageRole.ASSISTANT,
                    content=response.content,
                    timestamp=datetime.now(timezone.utc),
                    message_type=response.message_type,
                    tokens=response.tokens,
                    processing_time=response.processing_time,
                    confidence=response.confidence,
                    sources=response.sources
                )
                await self.context_manager.update_context(session_id, assistant_message)

            # Log performance
            total_time = time.time() - start_time
            target_time = (self.config.simple_response_target if len(user_input) < 100
                          else self.config.complex_response_target)

            if total_time > target_time:
                logger.warning(f"AI response took {total_time:.2f}s (target: {target_time}s)")

            return response

        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            return AIResponse(
                content="",
                processing_time=time.time() - start_time,
                error=str(e)
            )

    async def stream_response(self, session_id: str, user_input: str,
                            provider: Optional[AIProvider] = None,
                            **kwargs) -> AsyncGenerator[str, None]:
        """Stream AI response for user input."""
        try:
            provider = provider or self.config.default_provider
            ai_provider = self.providers.get(provider)

            if not ai_provider:
                yield "AI service not available"
                return

            context = await self.context_manager.get_context(session_id)
            if not context:
                yield "Context not found"
                return

            messages = await self._build_messages(context, user_input, ResponseType.TEXT)

            # Stream response
            full_response = ""
            async for chunk in ai_provider.stream_response(messages, **kwargs):
                full_response += chunk
                yield chunk

            # Update context after streaming
            if full_response:
                user_message = AIMessage(
                    message_id="",
                    role=MessageRole.USER,
                    content=user_input,
                    timestamp=datetime.now(timezone.utc)
                )
                await self.context_manager.update_context(session_id, user_message)

                assistant_message = AIMessage(
                    message_id="",
                    role=MessageRole.ASSISTANT,
                    content=full_response,
                    timestamp=datetime.now(timezone.utc)
                )
                await self.context_manager.update_context(session_id, assistant_message)

        except Exception as e:
            logger.error(f"Error streaming AI response: {e}")
            yield f"Error: {e}"

    async def chat(self, session_id: str, user_id: str, message: str,
                   include_context: bool = True, stream: bool = False, **kwargs):
        """Chat with AI assistant.

        Args:
            session_id: Terminal session ID
            user_id: User ID
            message: User message
            include_context: Include conversation context
            stream: Enable streaming response

        Returns:
            Dict with response data or async generator for streaming
        """
        import uuid
        from datetime import datetime, timezone

        if stream:
            # Return streaming response
            return self.stream_response(session_id, message, **kwargs)
        else:
            # Generate regular response
            response = await self.generate_response(
                session_id=session_id,
                user_input=message,
                response_type=ResponseType.TEXT,
                **kwargs
            )

            return {
                "message_id": str(uuid.uuid4()),
                "response": response.content,
                "response_time": response.processing_time,
                "token_count": response.tokens,
                "confidence": response.confidence
            }

    async def explain_command(self, session_id: str, command: str) -> AIResponse:
        """Explain a terminal command."""
        prompt = f"Explain this terminal command in simple terms: {command}"
        return await self.generate_response(
            session_id, prompt, ResponseType.EXPLANATION
        )

    async def suggest_commands(self, session_id: str, goal: str) -> AIResponse:
        """Suggest commands to achieve a goal."""
        prompt = f"Suggest terminal commands to: {goal}"
        return await self.generate_response(
            session_id, prompt, ResponseType.SUGGESTION
        )

    async def process_voice(self, session_id: str, user_id: str, audio_data: bytes,
                          language: str = "en-US", enable_tts: bool = False, **kwargs):
        """Process voice input (placeholder - requires speech recognition service).

        Args:
            session_id: Terminal session ID
            user_id: User ID
            audio_data: Audio data bytes
            language: Language code
            enable_tts: Enable text-to-speech response

        Returns:
            Dict with transcription and response
        """
        import uuid

        # TODO: Implement actual speech recognition
        # For now, return a placeholder response
        return {
            "message_id": str(uuid.uuid4()),
            "transcription": "Voice recognition not yet implemented",
            "response": "Please use text input for now. Voice recognition requires additional services.",
            "response_time": 0.1,
            "audio_url": None
        }

    async def get_suggestions(self, session_id: str, user_id: str,
                            partial_command: str = None, goal: str = None,
                            max_suggestions: int = 5, **kwargs):
        """Get command suggestions.

        Args:
            session_id: Terminal session ID
            user_id: User ID
            partial_command: Partial command to complete
            goal: Desired outcome
            max_suggestions: Maximum suggestions to return

        Returns:
            Dict with suggestions and response time
        """
        import time

        start_time = time.time()

        # Build prompt
        if partial_command:
            prompt = f"Complete this command: {partial_command}"
        elif goal:
            prompt = f"Suggest commands to: {goal}"
        else:
            prompt = "Suggest useful terminal commands"

        # Get suggestions from AI
        response = await self.generate_response(
            session_id=session_id,
            user_input=prompt,
            response_type=ResponseType.SUGGESTION
        )

        # Parse response into suggestions (simple parsing)
        suggestions = []
        if response.content:
            lines = response.content.split('\n')
            for line in lines[:max_suggestions]:
                line = line.strip()
                if line and (line.startswith('-') or line.startswith('•') or line[0].isdigit()):
                    # Extract command from bullet point
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        cmd = parts[0].strip('- •0123456789.').strip()
                        desc = parts[1].strip()
                        suggestions.append({
                            "command": cmd,
                            "description": desc,
                            "confidence": 0.8,
                            "category": "general"
                        })

        return {
            "suggestions": suggestions,
            "response_time": time.time() - start_time
        }

    async def explain_output(self, session_id: str, user_id: str,
                           command: str, output: str, explain_errors: bool = True, **kwargs):
        """Explain command output.

        Args:
            session_id: Terminal session ID
            user_id: User ID
            command: Command that was executed
            output: Command output
            explain_errors: Focus on error explanation

        Returns:
            Dict with explanation and suggestions
        """
        import time

        start_time = time.time()

        # Build prompt
        if explain_errors:
            prompt = f"Explain this error from command '{command}':\n{output[:500]}"
        else:
            prompt = f"Explain this output from command '{command}':\n{output[:500]}"

        # Get explanation from AI
        response = await self.generate_response(
            session_id=session_id,
            user_input=prompt,
            response_type=ResponseType.EXPLANATION
        )

        return {
            "explanation": response.content,
            "suggested_fixes": [],  # TODO: Parse from response
            "related_commands": [],  # TODO: Parse from response
            "response_time": time.time() - start_time
        }

    async def get_context(self, session_id: str, limit: int = 50, **kwargs):
        """Get AI conversation context.

        Args:
            session_id: Terminal session ID
            limit: Maximum messages to return

        Returns:
            Dict with messages and context info
        """
        context = await self.context_manager.get_context(session_id)
        if not context:
            return {
                "messages": [],
                "total_messages": 0,
                "context_tokens": 0
            }

        messages = context.get_recent_messages(limit)

        return {
            "messages": messages,
            "total_messages": len(messages),
            "context_tokens": sum(msg.get("tokens", 0) for msg in messages)
        }

    async def clear_context(self, session_id: str, **kwargs):
        """Clear AI conversation context.

        Args:
            session_id: Terminal session ID
        """
        self.context_manager.clear_cache(session_id)

        # Also clear from database
        context = await self.context_manager.get_context(session_id)
        if context:
            context.conversation_history = []
            context.total_tokens = 0

            async with AsyncSessionLocal() as db:
                await db.merge(context)
                await db.commit()

    async def update_terminal_context(self, session_id: str, command: str, output: str, exit_code: int = 0) -> None:
        """Update terminal context with command execution."""
        await self.context_manager.update_terminal_context(session_id, command, output, exit_code)

    async def initialize_session_context(self, session_id: str, user_id: str,
                                       provider: AIProvider = None,
                                       model: str = None) -> AIContext:
        """Initialize AI context for a new session."""
        async with AsyncSessionLocal() as db:
            context = AIContext(
                session_id=session_id,
                user_id=user_id,
                model_provider=provider or self.config.default_provider,
                model_name=model or self.config.default_model,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                context_window=self.config.context_window
            )

            db.add(context)
            await db.commit()
            await db.refresh(context)

            return context

    async def get_context_stats(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get AI context statistics."""
        context = await self.context_manager.get_context(session_id)
        return context.get_usage_summary() if context else None

    async def validate_providers(self) -> Dict[AIProvider, bool]:
        """Validate all configured providers."""
        results = {}
        for provider_type, provider in self.providers.items():
            try:
                results[provider_type] = await provider.validate_connection()
            except Exception as e:
                logger.error(f"Error validating {provider_type}: {e}")
                results[provider_type] = False

        return results

    async def _build_messages(self, context: AIContext, user_input: str,
                            response_type: ResponseType) -> List[AIMessage]:
        """Build message list for AI provider."""
        messages = []

        # System message
        system_prompt = self._build_system_prompt(context, response_type)
        messages.append(AIMessage(
            message_id="system",
            role=MessageRole.SYSTEM,
            content=system_prompt,
            timestamp=datetime.now(timezone.utc)
        ))

        # Recent conversation history
        for msg_data in context.get_recent_messages(10):
            messages.append(AIMessage(
                message_id=msg_data["messageId"],
                role=MessageRole(msg_data["role"]),
                content=msg_data["content"],
                timestamp=datetime.fromisoformat(msg_data["timestamp"].replace('Z', '+00:00')),
                message_type=ResponseType(msg_data.get("type", "text"))
            ))

        # Current user input
        messages.append(AIMessage(
            message_id="current",
            role=MessageRole.USER,
            content=user_input,
            timestamp=datetime.now(timezone.utc),
            message_type=response_type
        ))

        return messages

    def _build_system_prompt(self, context: AIContext, response_type: ResponseType) -> str:
        """Build system prompt based on context and response type."""
        base_prompt = context.system_prompt or "You are a helpful AI assistant integrated into a terminal environment."

        # Add terminal context
        terminal_context = context.terminal_context or {}
        recent_commands = terminal_context.get("recentCommands", [])

        if recent_commands:
            recent_cmd_text = "\n".join([
                f"$ {cmd.get('command', '')} (exit: {cmd.get('exitCode', 0)})"
                for cmd in recent_commands[-3:]  # Last 3 commands
            ])
            base_prompt += f"\n\nRecent terminal activity:\n{recent_cmd_text}"

        # Add current directory
        current_dir = terminal_context.get("currentDirectory", "/")
        base_prompt += f"\n\nCurrent directory: {current_dir}"

        # Customize for response type
        if response_type == ResponseType.EXPLANATION:
            base_prompt += "\n\nProvide clear, concise explanations suitable for users learning terminal commands."
        elif response_type == ResponseType.SUGGESTION:
            base_prompt += "\n\nSuggest practical terminal commands with brief explanations."
        elif response_type == ResponseType.COMMAND:
            base_prompt += "\n\nProvide specific terminal commands to solve the user's request."

        return base_prompt


# Global service instance
ai_service = AIService()


async def get_ai_service() -> AIService:
    """Dependency injection for AI service."""
    return ai_service
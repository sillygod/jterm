"""Application configuration loaded from environment variables."""

import os
from typing import Optional
from functools import lru_cache

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    # Core settings
    TERMINAL_DEBUG: bool = os.getenv("TERMINAL_DEBUG", "false").lower() == "true"
    TERMINAL_HOST: str = os.getenv("TERMINAL_HOST", "0.0.0.0")
    TERMINAL_PORT: int = int(os.getenv("TERMINAL_PORT", "8000"))
    TERMINAL_SECRET_KEY: str = os.getenv("TERMINAL_SECRET_KEY", "your-secret-key-change-in-production")

    # Desktop mode detection
    IS_DESKTOP_MODE: bool = os.getenv("JTERM_DESKTOP_MODE", "false").lower() == "true"
    DESKTOP_DB_PATH: Optional[str] = os.getenv("JTERM_DESKTOP_DB_PATH")

    # Database
    @property
    def database_url(self) -> str:
        """Get database URL with desktop mode support."""
        if self.IS_DESKTOP_MODE and self.DESKTOP_DB_PATH:
            return f"sqlite+aiosqlite:///{self.DESKTOP_DB_PATH}"
        return os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./webterminal.db")

    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./webterminal.db")

    # Security & Authentication
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "30"))

    # CORS
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000")

    # AI Assistant
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "openai")  # openai|anthropic|local

    # OpenAI
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4")

    # Anthropic
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229")

    # Local/OpenAI-Compatible Provider (Mistral AI, together.ai, Groq, etc.)
    LOCAL_AI_ENDPOINT: Optional[str] = os.getenv("LOCAL_AI_ENDPOINT")
    LOCAL_AI_API_KEY: Optional[str] = os.getenv("LOCAL_AI_API_KEY")
    LOCAL_AI_MODEL: str = os.getenv("LOCAL_AI_MODEL", "mistral-large-latest")

    # Media settings
    MEDIA_MAX_SIZE: int = int(os.getenv("MEDIA_MAX_SIZE", "52428800"))  # 50MB
    MEDIA_STORAGE_PATH: str = os.getenv("MEDIA_STORAGE_PATH", "./uploads")

    # Session recording
    RECORDING_MAX_DURATION: int = int(os.getenv("RECORDING_MAX_DURATION", "3600"))  # 1 hour
    RECORDING_RETENTION_DAYS: int = int(os.getenv("RECORDING_RETENTION_DAYS", "30"))

    # Performance & Caching
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "3600"))
    SESSION_CACHE_SIZE: int = int(os.getenv("SESSION_CACHE_SIZE", "1000"))
    MEDIA_CACHE_SIZE: int = int(os.getenv("MEDIA_CACHE_SIZE", "100"))

    # WebSocket settings
    WEBSOCKET_PING_INTERVAL: int = int(os.getenv("WEBSOCKET_PING_INTERVAL", "20"))
    WEBSOCKET_PING_TIMEOUT: int = int(os.getenv("WEBSOCKET_PING_TIMEOUT", "10"))
    WEBSOCKET_CLOSE_TIMEOUT: int = int(os.getenv("WEBSOCKET_CLOSE_TIMEOUT", "10"))

    @property
    def ai_model(self) -> str:
        """Get the AI model based on the selected provider."""
        if self.AI_PROVIDER == "openai":
            return self.OPENAI_MODEL
        elif self.AI_PROVIDER == "anthropic":
            return self.ANTHROPIC_MODEL
        elif self.AI_PROVIDER == "local":
            return self.LOCAL_AI_MODEL
        return "gpt-4"

    def get_ai_config(self):
        """Get AI configuration for the selected provider."""
        from src.services.ai_service import AIConfig, AIProvider

        provider_map = {
            "openai": AIProvider.OPENAI,
            "anthropic": AIProvider.ANTHROPIC,
            "local": AIProvider.LOCAL
        }

        return AIConfig(
            default_provider=provider_map.get(self.AI_PROVIDER, AIProvider.OPENAI),
            openai_api_key=self.OPENAI_API_KEY,
            anthropic_api_key=self.ANTHROPIC_API_KEY,
            local_endpoint=self.LOCAL_AI_ENDPOINT,
            local_api_key=self.LOCAL_AI_API_KEY,
            default_model=self.ai_model,
            max_tokens=1000,
            temperature=0.7,
            timeout=30.0,
            simple_response_target=2.0,
            complex_response_target=5.0,
            enable_voice=True,
            enable_streaming=True,
            context_window=8192
        )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()

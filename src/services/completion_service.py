"""Unified completion service combining shell and AI suggestions.

This service provides intelligent command-line completions by combining:
1. Fast shell-native completions (bash/zsh compgen)
2. AI-powered contextual suggestions
3. Custom jterm commands (imgcat, bookcat, etc.)
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict

from src.services.shell_completion_service import (
    get_shell_completion_service,
    CompletionItem,
    ShellCompletionService
)
from src.services.ai_service import ai_service, AIService
from src.services.git_completion_service import (
    get_git_completion_service,
    GitCompletionService,
    GitCompletionItem
)

logger = logging.getLogger(__name__)


# Custom jterm commands with descriptions
CUSTOM_COMMANDS = {
    'imgcat': 'View/edit images in terminal (supports clipboard, URLs, history)',
    'vidcat': 'Play videos in terminal (max 50MB)',
    'mdcat': 'Render markdown files with syntax highlighting',
    'htmlcat': 'Preview HTML files with sandboxing',
    'bookcat': 'Read ebooks (PDF/EPUB) with foliate-js viewer',
    'logcat': 'View and analyze log files',
    'certcat': 'Display and analyze SSL certificates',
    'sqlcat': 'Execute SQL queries and view results',
    'curlcat': 'Enhanced HTTP request viewer',
    'jwtcat': 'Decode and analyze JWT tokens',
    'wscat': 'WebSocket client for terminal',
}


@dataclass
class UnifiedCompletion:
    """Unified completion result with metadata."""
    text: str  # The completion text
    display: str  # Display text
    type: str  # Type: command, file, directory, option, variable, custom
    description: Optional[str] = None  # Description
    source: str = "shell"  # Source: shell, ai, custom
    confidence: float = 1.0  # Confidence score (0-1)
    priority: int = 0  # Priority for sorting (higher = more important)


class CompletionService:
    """Unified completion service."""

    def __init__(
        self,
        shell_service: Optional[ShellCompletionService] = None,
        ai_service: Optional[AIService] = None,
        git_service: Optional[GitCompletionService] = None
    ):
        """Initialize the completion service.

        Args:
            shell_service: Shell completion service (optional, will create if None)
            ai_service: AI service (optional, will create if None)
            git_service: Git completion service (optional, will create if None)
        """
        self.shell_service = shell_service or get_shell_completion_service()
        self.ai_service = ai_service
        self.git_service = git_service or get_git_completion_service()
        self.enable_ai = ai_service is not None
        self.ai_timeout = 2.0  # Max time to wait for AI suggestions
        self.max_total_results = 20  # Max total completions to return

    def _get_custom_command_completions(self, word: str) -> List[UnifiedCompletion]:
        """Get completions for custom jterm commands.

        Args:
            word: Partial command to complete

        Returns:
            List of custom command completions
        """
        completions = []

        for cmd, desc in CUSTOM_COMMANDS.items():
            if cmd.startswith(word):
                completions.append(UnifiedCompletion(
                    text=cmd,
                    display=cmd,
                    type="custom",
                    description=desc,
                    source="custom",
                    confidence=1.0,
                    priority=10  # High priority for custom commands
                ))

        return completions

    def _merge_completions(
        self,
        shell_completions: List[CompletionItem],
        git_completions: List[GitCompletionItem],
        ai_completions: List[Dict[str, Any]],
        custom_completions: List[UnifiedCompletion],
        word: str
    ) -> List[UnifiedCompletion]:
        """Merge and deduplicate completions from all sources.

        Args:
            shell_completions: Completions from shell
            git_completions: Completions from git
            ai_completions: Completions from AI
            custom_completions: Custom command completions
            word: The word being completed

        Returns:
            Merged and sorted list of completions
        """
        all_completions: Dict[str, UnifiedCompletion] = {}

        # Add custom commands first (highest priority)
        for comp in custom_completions:
            all_completions[comp.text] = comp

        # Add git completions (high priority, context-specific)
        for comp in git_completions:
            if comp.text not in all_completions:
                all_completions[comp.text] = UnifiedCompletion(
                    text=comp.text,
                    display=comp.text,
                    type=comp.type,
                    description=comp.description,
                    source="git",
                    confidence=1.0,
                    priority=8  # High priority for git completions
                )

        # Add shell completions
        for comp in shell_completions:
            if comp.text not in all_completions:
                all_completions[comp.text] = UnifiedCompletion(
                    text=comp.text,
                    display=comp.display,
                    type=comp.type,
                    description=comp.description,
                    source=comp.source,
                    confidence=1.0,
                    priority=5  # Medium priority for shell completions
                )

        # Add AI completions (if not already present)
        for ai_comp in ai_completions:
            cmd = ai_comp.get('command', '')
            if cmd and cmd not in all_completions:
                all_completions[cmd] = UnifiedCompletion(
                    text=cmd,
                    display=cmd,
                    type="command",
                    description=ai_comp.get('description'),
                    source="ai",
                    confidence=ai_comp.get('confidence', 0.7),
                    priority=3  # Lower priority for AI completions
                )

        # Sort by priority (desc), then confidence (desc), then alphabetically
        sorted_completions = sorted(
            all_completions.values(),
            key=lambda x: (-x.priority, -x.confidence, x.text)
        )

        return sorted_completions[:self.max_total_results]

    async def _get_ai_completions(
        self,
        line: str,
        cursor_pos: int,
        session_id: str,
        user_id: str = "default"
    ) -> List[Dict[str, Any]]:
        """Get AI-powered completions asynchronously.

        Args:
            line: Command line text
            cursor_pos: Cursor position
            session_id: Terminal session ID
            user_id: User ID

        Returns:
            List of AI completion suggestions
        """
        if not self.enable_ai or not self.ai_service:
            return []

        try:
            # Extract the partial command
            line_before = line[:cursor_pos]

            result = await asyncio.wait_for(
                self.ai_service.get_suggestions(
                    session_id=session_id,
                    user_id=user_id,
                    partial_command=line_before,
                    max_suggestions=5
                ),
                timeout=self.ai_timeout
            )

            return result.get('suggestions', [])

        except asyncio.TimeoutError:
            logger.warning("AI completion timed out")
            return []
        except Exception as e:
            logger.error(f"Error getting AI completions: {e}")
            return []

    async def get_completions(
        self,
        line: str,
        cursor_pos: int,
        session_id: str,
        shell_path: str = "/bin/bash",
        cwd: str = ".",
        enable_ai: bool = True,
        user_id: str = "default"
    ) -> List[Dict[str, Any]]:
        """Get unified completions from all sources.

        Args:
            line: Full command line text
            cursor_pos: Cursor position in the line
            session_id: Terminal session ID
            shell_path: Path to the shell executable
            cwd: Current working directory
            enable_ai: Whether to include AI suggestions
            user_id: User ID for AI service

        Returns:
            List of completion dictionaries
        """
        logger.debug(f"Getting completions for line='{line}', pos={cursor_pos}")

        # Parse the current word being completed
        word_start = cursor_pos
        for i in range(cursor_pos - 1, -1, -1):
            if line[i] in (' ', '\t', '\n', ';', '|', '&', '(', ')'):
                word_start = i + 1
                break
            if i == 0:
                word_start = 0

        word = line[word_start:cursor_pos]

        # Get completions from different sources concurrently
        tasks = []

        logger.info(f"[CompletionService] Getting completions for line='{line}', cwd='{cwd}'")

        # 1. Shell completions (always enabled, fast)
        shell_task = asyncio.create_task(
            self.shell_service.get_completions(line, cursor_pos, shell_path, cwd)
        )
        tasks.append(shell_task)

        # 2. Git completions (context-aware, fast)
        logger.info("[CompletionService] Creating git completion task")
        git_task = asyncio.create_task(
            self.git_service.get_completions(line, cursor_pos, cwd)
        )
        tasks.append(git_task)

        # 3. AI completions (optional, slower)
        ai_task = None
        if enable_ai and self.enable_ai:
            ai_task = asyncio.create_task(
                self._get_ai_completions(line, cursor_pos, session_id, user_id)
            )
            tasks.append(ai_task)

        # 4. Custom commands (synchronous, fast)
        custom_completions = self._get_custom_command_completions(word)

        # Wait for all tasks with timeout protection
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            shell_completions = results[0] if not isinstance(results[0], Exception) else []
            git_completions = results[1] if not isinstance(results[1], Exception) else []
            ai_completions = results[2] if ai_task and len(results) > 2 and not isinstance(results[2], Exception) else []

            logger.info(f"[CompletionService] Results: shell={len(shell_completions)}, git={len(git_completions)}, ai={len(ai_completions)}")

            # Log git results if any
            if isinstance(results[1], Exception):
                logger.error(f"[CompletionService] Git completion error: {results[1]}")

        except Exception as e:
            logger.error(f"Error gathering completions: {e}")
            shell_completions = []
            git_completions = []
            ai_completions = []

        # Merge all completions
        unified = self._merge_completions(
            shell_completions,
            git_completions,
            ai_completions,
            custom_completions,
            word
        )

        # Convert to dictionaries for JSON serialization
        return [asdict(comp) for comp in unified]

    async def get_completion_description(
        self,
        command: str,
        prefer_ai: bool = False,
        session_id: Optional[str] = None
    ) -> Optional[str]:
        """Get description for a command.

        Args:
            command: Command name
            prefer_ai: Whether to prefer AI-generated description
            session_id: Terminal session ID (for AI)

        Returns:
            Command description or None
        """
        # Check custom commands first
        if command in CUSTOM_COMMANDS:
            return CUSTOM_COMMANDS[command]

        # Try shell description (whatis)
        if not prefer_ai:
            desc = await self.shell_service.get_command_description(command)
            if desc:
                return desc

        # Fall back to AI if enabled
        if self.enable_ai and self.ai_service and session_id:
            try:
                result = await asyncio.wait_for(
                    self.ai_service.explain_command(
                        session_id=session_id,
                        user_id="default",
                        command=command
                    ),
                    timeout=1.0
                )
                return result.get('explanation')
            except Exception as e:
                logger.error(f"Error getting AI description: {e}")

        return None


# Singleton instance
_completion_service: Optional[CompletionService] = None


def get_completion_service(enable_ai: bool = True) -> CompletionService:
    """Get or create the completion service singleton.

    Args:
        enable_ai: Whether to enable AI-powered completions

    Returns:
        Completion service instance
    """
    global _completion_service
    if _completion_service is None:
        ai_svc = ai_service if enable_ai else None
        _completion_service = CompletionService(ai_service=ai_svc)
    return _completion_service

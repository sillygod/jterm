"""Shell completion service for terminal intellisense.

This service provides shell-native completion suggestions by executing
bash/zsh completion commands and parsing the results.
"""

import asyncio
import logging
import os
import shlex
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ShellType(str, Enum):
    """Supported shell types."""
    BASH = "bash"
    ZSH = "zsh"
    SH = "sh"
    FISH = "fish"
    UNKNOWN = "unknown"


@dataclass
class CompletionItem:
    """Single completion suggestion item."""
    text: str  # The completion text
    display: str  # Display text (may include description)
    type: str  # Type: command, file, directory, option, variable, etc.
    description: Optional[str] = None  # Additional description
    source: str = "shell"  # Source: shell, ai, cache


class ShellCompletionService:
    """Service for fetching shell-native completions."""

    def __init__(self):
        """Initialize the shell completion service."""
        self.timeout = 1.0  # Max time to wait for completion (seconds)
        self.max_results = 50  # Max number of completions to return

    def _detect_shell(self, shell_path: str) -> ShellType:
        """Detect shell type from shell path.

        Args:
            shell_path: Path to the shell executable (e.g., /bin/bash)

        Returns:
            Detected shell type
        """
        shell_name = os.path.basename(shell_path).lower()

        if 'bash' in shell_name:
            return ShellType.BASH
        elif 'zsh' in shell_name:
            return ShellType.ZSH
        elif 'fish' in shell_name:
            return ShellType.FISH
        elif shell_name == 'sh':
            return ShellType.SH
        else:
            return ShellType.UNKNOWN

    def _parse_command_line(self, line: str, cursor_pos: int) -> Tuple[str, str, int]:
        """Parse command line to extract completion context.

        Args:
            line: Full command line
            cursor_pos: Cursor position in the line

        Returns:
            Tuple of (line_before_cursor, word_to_complete, word_start_pos)
        """
        line_before = line[:cursor_pos]

        # Find the start of the current word
        word_start = cursor_pos
        for i in range(cursor_pos - 1, -1, -1):
            if line[i] in (' ', '\t', '\n', ';', '|', '&', '(', ')'):
                word_start = i + 1
                break
            if i == 0:
                word_start = 0

        word_to_complete = line[word_start:cursor_pos]

        return line_before, word_to_complete, word_start

    async def _get_bash_completions(
        self,
        line: str,
        cursor_pos: int,
        cwd: str
    ) -> List[CompletionItem]:
        """Get completions using bash's compgen.

        Args:
            line: Command line text
            cursor_pos: Cursor position
            cwd: Current working directory

        Returns:
            List of completion items
        """
        line_before, word, word_start = self._parse_command_line(line, cursor_pos)

        # Expand ~ in cwd
        expanded_cwd = os.path.expanduser(cwd)

        # Determine what type of completion we need
        words = line_before.split()

        # If it's the first word, complete commands
        if len(words) <= 1:
            cmd = f"compgen -c -- {shlex.quote(word)}"
            completion_type = "command"
        else:
            # Otherwise, try file/directory completion
            cmd = f"compgen -f -- {shlex.quote(word)}"
            completion_type = "file"

        try:
            # Execute compgen in bash
            process = await asyncio.create_subprocess_exec(
                'bash', '-c', cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=expanded_cwd
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout
            )

            if process.returncode != 0:
                logger.warning(f"Bash completion failed: {stderr.decode()}")
                return []

            # Parse results
            completions = []
            lines = stdout.decode().strip().split('\n')

            for line_text in lines[:self.max_results]:
                if not line_text:
                    continue

                # Check if it's a directory (for file completions)
                item_type = completion_type
                if completion_type == "file":
                    full_path = os.path.join(expanded_cwd, line_text)
                    if os.path.isdir(full_path):
                        item_type = "directory"
                        line_text = line_text + "/"

                completions.append(CompletionItem(
                    text=line_text,
                    display=line_text,
                    type=item_type,
                    source="shell"
                ))

            return completions

        except asyncio.TimeoutError:
            logger.warning("Bash completion timed out")
            return []
        except Exception as e:
            logger.error(f"Error getting bash completions: {e}")
            return []

    async def _get_zsh_completions(
        self,
        line: str,
        cursor_pos: int,
        cwd: str
    ) -> List[CompletionItem]:
        """Get completions using zsh's completion system.

        Args:
            line: Command line text
            cursor_pos: Cursor position
            cwd: Current working directory

        Returns:
            List of completion items
        """
        # ZSH completion is more complex - for now, fall back to simple approach
        # In the future, we could use zsh's _complete or compdump

        line_before, word, word_start = self._parse_command_line(line, cursor_pos)
        words = line_before.split()

        # Expand ~ in cwd
        expanded_cwd = os.path.expanduser(cwd)

        # Simple file/command completion
        if len(words) <= 1:
            # Command completion
            cmd = f"print -l ${{(k)commands}} | grep '^{word}'"
            completion_type = "command"
        else:
            # File completion using glob
            cmd = f"print -l {word}*(N)"
            completion_type = "file"

        try:
            process = await asyncio.create_subprocess_exec(
                'zsh', '-c', cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=expanded_cwd
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout
            )

            if process.returncode != 0:
                # Fall back to bash-style completion
                return await self._get_bash_completions(line, cursor_pos, cwd)

            completions = []
            lines = stdout.decode().strip().split('\n')

            for line_text in lines[:self.max_results]:
                if not line_text:
                    continue

                item_type = completion_type
                if completion_type == "file" and os.path.isdir(os.path.join(expanded_cwd, line_text)):
                    item_type = "directory"
                    line_text = line_text + "/"

                completions.append(CompletionItem(
                    text=line_text,
                    display=line_text,
                    type=item_type,
                    source="shell"
                ))

            return completions

        except asyncio.TimeoutError:
            logger.warning("Zsh completion timed out")
            return []
        except Exception as e:
            logger.error(f"Error getting zsh completions: {e}")
            # Fall back to bash
            return await self._get_bash_completions(line, cursor_pos, cwd)

    async def get_completions(
        self,
        line: str,
        cursor_pos: int,
        shell_path: str = "/bin/bash",
        cwd: str = "."
    ) -> List[CompletionItem]:
        """Get shell completions for the current command line.

        Args:
            line: Full command line text
            cursor_pos: Cursor position in the line
            shell_path: Path to the shell executable
            cwd: Current working directory

        Returns:
            List of completion items
        """
        shell_type = self._detect_shell(shell_path)

        logger.debug(f"Getting completions for shell={shell_type}, line='{line}', pos={cursor_pos}")

        try:
            if shell_type == ShellType.BASH or shell_type == ShellType.SH:
                return await self._get_bash_completions(line, cursor_pos, cwd)
            elif shell_type == ShellType.ZSH:
                return await self._get_zsh_completions(line, cursor_pos, cwd)
            elif shell_type == ShellType.FISH:
                # Fish completion not implemented yet - fall back to bash
                logger.warning("Fish completion not implemented, using bash fallback")
                return await self._get_bash_completions(line, cursor_pos, cwd)
            else:
                logger.warning(f"Unknown shell type: {shell_type}")
                return await self._get_bash_completions(line, cursor_pos, cwd)

        except Exception as e:
            logger.error(f"Error getting completions: {e}")
            return []

    async def get_command_description(self, command: str) -> Optional[str]:
        """Get brief description of a command using man/whatis.

        Args:
            command: Command name

        Returns:
            Brief description or None
        """
        try:
            process = await asyncio.create_subprocess_exec(
                'whatis', command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=0.5
            )

            if process.returncode == 0:
                # whatis output format: "command (section) - description"
                output = stdout.decode().strip()
                if ' - ' in output:
                    return output.split(' - ', 1)[1]

            return None

        except Exception:
            return None


# Singleton instance
_shell_completion_service: Optional[ShellCompletionService] = None


def get_shell_completion_service() -> ShellCompletionService:
    """Get or create the shell completion service singleton.

    Returns:
        Shell completion service instance
    """
    global _shell_completion_service
    if _shell_completion_service is None:
        _shell_completion_service = ShellCompletionService()
    return _shell_completion_service

"""Git-specific completion service.

Provides intelligent completions for git commands like:
- git checkout <branch>
- git merge <branch>
- git branch <branch>
- git push <remote> <branch>
etc.
"""

import asyncio
import logging
import os
from typing import List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class GitCompletionItem:
    """Git completion item."""
    text: str
    type: str  # branch, tag, remote, file, etc.
    description: Optional[str] = None


class GitCompletionService:
    """Service for git-specific completions."""

    def __init__(self):
        """Initialize git completion service."""
        self.timeout = 1.0

    async def _run_git_command(self, args: List[str], cwd: str) -> Optional[str]:
        """Run a git command and return output.

        Args:
            args: Git command arguments (e.g., ['branch', '-a'])
            cwd: Working directory

        Returns:
            Command output or None if failed
        """
        try:
            expanded_cwd = os.path.expanduser(cwd)

            process = await asyncio.create_subprocess_exec(
                'git', *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=expanded_cwd
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout
            )

            if process.returncode == 0:
                return stdout.decode().strip()
            else:
                logger.debug(f"Git command failed: {stderr.decode()}")
                return None

        except asyncio.TimeoutError:
            logger.warning("Git command timed out")
            return None
        except Exception as e:
            logger.error(f"Error running git command: {e}")
            return None

    async def _get_branches(self, cwd: str, include_remote: bool = True) -> List[GitCompletionItem]:
        """Get list of git branches.

        Args:
            cwd: Working directory
            include_remote: Include remote branches

        Returns:
            List of branch completion items
        """
        args = ['branch', '-a'] if include_remote else ['branch']
        output = await self._run_git_command(args, cwd)

        if not output:
            return []

        branches = []
        for line in output.split('\n'):
            line = line.strip()
            if not line:
                continue

            # Remove * prefix (current branch marker)
            if line.startswith('* '):
                line = line[2:].strip()

            # Parse branch name
            if line.startswith('remotes/'):
                # Remote branch: remotes/origin/main
                branch_type = 'remote-branch'
                # Extract just the branch name after remote/
                parts = line.split('/', 2)
                if len(parts) >= 3:
                    branch_name = parts[2]
                    remote_name = parts[1]
                    desc = f"Remote: {remote_name}"
                else:
                    branch_name = line
                    desc = "Remote branch"
            else:
                # Local branch
                branch_type = 'branch'
                branch_name = line
                desc = "Local branch"

            branches.append(GitCompletionItem(
                text=branch_name,
                type=branch_type,
                description=desc
            ))

        return branches

    async def _get_remotes(self, cwd: str) -> List[GitCompletionItem]:
        """Get list of git remotes.

        Args:
            cwd: Working directory

        Returns:
            List of remote completion items
        """
        output = await self._run_git_command(['remote'], cwd)

        if not output:
            return []

        remotes = []
        for line in output.split('\n'):
            line = line.strip()
            if line:
                remotes.append(GitCompletionItem(
                    text=line,
                    type='remote',
                    description='Git remote'
                ))

        return remotes

    async def _get_tags(self, cwd: str) -> List[GitCompletionItem]:
        """Get list of git tags.

        Args:
            cwd: Working directory

        Returns:
            List of tag completion items
        """
        output = await self._run_git_command(['tag'], cwd)

        if not output:
            return []

        tags = []
        for line in output.split('\n'):
            line = line.strip()
            if line:
                tags.append(GitCompletionItem(
                    text=line,
                    type='tag',
                    description='Git tag'
                ))

        return tags

    async def get_completions(
        self,
        line: str,
        cursor_pos: int,
        cwd: str
    ) -> List[GitCompletionItem]:
        """Get git completions based on command context.

        Args:
            line: Full command line
            cursor_pos: Cursor position
            cwd: Working directory (may be ~, will be expanded)

        Returns:
            List of git completion items
        """
        # Expand ~ to actual home directory
        expanded_cwd = os.path.expanduser(cwd)
        logger.info(f"[GitCompletion] Called with line='{line}', cursor_pos={cursor_pos}, cwd='{cwd}' -> '{expanded_cwd}'")

        # Parse the command line
        words = line[:cursor_pos].split()
        logger.info(f"[GitCompletion] Parsed words: {words}")

        if not words or words[0] != 'git':
            logger.info(f"[GitCompletion] Not a git command, returning empty")
            return []

        # Not in a git repo?
        is_git_repo = await self._run_git_command(['rev-parse', '--git-dir'], expanded_cwd)
        if not is_git_repo:
            logger.info(f"[GitCompletion] Not in a git repository (checked: {expanded_cwd})")
            return []

        logger.info("[GitCompletion] In a git repository")

        # Determine git subcommand
        if len(words) < 2:
            # User typed "git " - suggest subcommands
            logger.info("[GitCompletion] No subcommand yet, letting shell handle it")
            return []  # Let shell completion handle git subcommands

        subcommand = words[1]
        logger.info(f"[GitCompletion] Subcommand: {subcommand}, word count: {len(words)}")

        # Context-aware completions based on subcommand
        if subcommand in ['checkout', 'co', 'switch']:
            # git checkout <branch>
            logger.info("[GitCompletion] Getting branches for checkout")
            result = await self._get_branches(cwd, include_remote=True)
            logger.info(f"[GitCompletion] Returning {len(result)} branches")
            return result

        elif subcommand in ['merge', 'rebase', 'cherry-pick']:
            # git merge <branch>
            logger.info("[GitCompletion] Getting branches for merge/rebase")
            return await self._get_branches(cwd, include_remote=False)

        elif subcommand == 'branch':
            # git branch -d <branch>
            if len(words) >= 3 and words[2] in ['-d', '-D', '-m', '-M']:
                logger.info("[GitCompletion] Getting branches for branch delete")
                return await self._get_branches(cwd, include_remote=False)
            logger.info("[GitCompletion] Branch command but no flag")
            return []

        elif subcommand == 'push':
            # git push <remote> <branch>
            if len(words) == 2:
                # Suggest remotes
                logger.info("[GitCompletion] Getting remotes for push")
                return await self._get_remotes(cwd)
            elif len(words) == 3:
                # Suggest branches
                logger.info("[GitCompletion] Getting branches for push")
                return await self._get_branches(cwd, include_remote=False)
            logger.info("[GitCompletion] Push command but wrong word count")
            return []

        elif subcommand == 'pull':
            # git pull <remote> <branch>
            if len(words) == 2:
                logger.info("[GitCompletion] Getting remotes for pull")
                result = await self._get_remotes(cwd)
                logger.info(f"[GitCompletion] Returning {len(result)} remotes")
                return result
            elif len(words) == 3:
                logger.info("[GitCompletion] Getting branches for pull")
                return await self._get_branches(cwd, include_remote=True)
            logger.info(f"[GitCompletion] Pull command but word count is {len(words)}")
            return []

        elif subcommand == 'tag':
            # git tag -d <tag>
            if len(words) >= 3 and words[2] in ['-d', '-v']:
                return await self._get_tags(cwd)
            return []

        elif subcommand == 'remote':
            # git remote remove <remote>
            if len(words) >= 3 and words[2] in ['remove', 'rm', 'show']:
                return await self._get_remotes(cwd)
            return []

        # Default: no specific completions
        return []


# Singleton instance
_git_completion_service: Optional[GitCompletionService] = None


def get_git_completion_service() -> GitCompletionService:
    """Get or create git completion service singleton.

    Returns:
        Git completion service instance
    """
    global _git_completion_service
    if _git_completion_service is None:
        _git_completion_service = GitCompletionService()
    return _git_completion_service

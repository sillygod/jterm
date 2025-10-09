"""Theme management service for visual styling and customization.

This service handles theme creation, validation, VS Code import, real-time preview,
marketplace functionality, and theme sharing with security validation.
"""

import asyncio
import json
import logging
import re
import zipfile
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, or_, and_

from src.models.theme_config import ThemeConfiguration
from src.models.terminal_session import TerminalSession
from src.models.user_profile import UserProfile
from src.database.base import AsyncSessionLocal


logger = logging.getLogger(__name__)


class ThemeValidationError(Exception):
    """Raised when theme validation fails."""
    pass


class ThemeImportError(Exception):
    """Raised when theme import fails."""
    pass


class ThemeExportError(Exception):
    """Raised when theme export fails."""
    pass


@dataclass
class ThemeConfig:
    """Theme service configuration."""
    themes_dir: str = "./themes"
    marketplace_enabled: bool = True
    allow_custom_css: bool = True
    max_custom_css_size: int = 50000  # 50KB
    enable_vscode_import: bool = True
    enable_real_time_preview: bool = True
    max_themes_per_user: int = 50


@dataclass
class VSCodeTheme:
    """VS Code theme structure."""
    name: str
    type: str  # light or dark
    colors: Dict[str, str]
    token_colors: List[Dict[str, Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ThemeValidationResult:
    """Theme validation result."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


class ThemeValidator:
    """Handles theme validation and security checks."""

    @staticmethod
    def validate_theme_config(theme_data: Dict[str, Any]) -> ThemeValidationResult:
        """Validate complete theme configuration."""
        result = ThemeValidationResult(is_valid=True)

        try:
            # Validate required fields
            required_fields = ["name", "colors", "fonts"]
            for field in required_fields:
                if field not in theme_data:
                    result.errors.append(f"Missing required field: {field}")
                    result.is_valid = False

            # Validate colors
            if "colors" in theme_data:
                color_validation = ThemeValidator._validate_colors(theme_data["colors"])
                result.errors.extend(color_validation.errors)
                result.warnings.extend(color_validation.warnings)

            # Validate fonts
            if "fonts" in theme_data:
                font_validation = ThemeValidator._validate_fonts(theme_data["fonts"])
                result.errors.extend(font_validation.errors)
                result.warnings.extend(font_validation.warnings)

            # Validate animations
            if "animations" in theme_data:
                anim_validation = ThemeValidator._validate_animations(theme_data["animations"])
                result.errors.extend(anim_validation.errors)
                result.warnings.extend(anim_validation.warnings)

            # Validate custom CSS
            if "custom_css" in theme_data and theme_data["custom_css"]:
                css_validation = ThemeValidator._validate_custom_css(theme_data["custom_css"])
                result.errors.extend(css_validation.errors)
                result.warnings.extend(css_validation.warnings)

            # Update validity
            result.is_valid = len(result.errors) == 0

        except Exception as e:
            result.errors.append(f"Validation error: {e}")
            result.is_valid = False

        return result

    @staticmethod
    def _validate_colors(colors: Dict[str, str]) -> ThemeValidationResult:
        """Validate color palette."""
        result = ThemeValidationResult(is_valid=True)

        required_colors = [
            "background", "foreground", "cursor", "selection",
            "black", "red", "green", "yellow", "blue", "magenta", "cyan", "white",
            "brightBlack", "brightRed", "brightGreen", "brightYellow",
            "brightBlue", "brightMagenta", "brightCyan", "brightWhite"
        ]

        for color_name in required_colors:
            if color_name not in colors:
                result.errors.append(f"Missing required color: {color_name}")
                continue

            color_value = colors[color_name]
            if not ThemeValidator._is_valid_color(color_value):
                result.errors.append(f"Invalid color format for {color_name}: {color_value}")

        # Check contrast ratios
        if "background" in colors and "foreground" in colors:
            contrast = ThemeValidator._calculate_contrast_ratio(
                colors["background"], colors["foreground"]
            )
            if contrast < 4.5:
                result.warnings.append(f"Low contrast ratio: {contrast:.2f} (recommended: >4.5)")

        result.is_valid = len(result.errors) == 0
        return result

    @staticmethod
    def _validate_fonts(fonts: Dict[str, Any]) -> ThemeValidationResult:
        """Validate font configuration."""
        result = ThemeValidationResult(is_valid=True)

        required_fields = ["family", "size", "weight", "lineHeight"]
        for field in required_fields:
            if field not in fonts:
                result.errors.append(f"Missing required font field: {field}")

        # Validate font size
        if "size" in fonts:
            size = fonts["size"]
            if not isinstance(size, (int, float)) or size < 8 or size > 32:
                result.errors.append("Font size must be between 8 and 32")

        # Validate line height
        if "lineHeight" in fonts:
            line_height = fonts["lineHeight"]
            if not isinstance(line_height, (int, float)) or line_height < 0.5 or line_height > 3.0:
                result.errors.append("Line height must be between 0.5 and 3.0")

        result.is_valid = len(result.errors) == 0
        return result

    @staticmethod
    def _validate_animations(animations: Dict[str, Any]) -> ThemeValidationResult:
        """Validate animation configuration."""
        result = ThemeValidationResult(is_valid=True)

        # Validate animation durations
        if "fadeInText" in animations and isinstance(animations["fadeInText"], dict):
            duration = animations["fadeInText"].get("duration", 200)
            if not isinstance(duration, int) or duration < 0 or duration > 5000:
                result.errors.append("Fade-in duration must be between 0 and 5000ms")

        if "cursorBlink" in animations and isinstance(animations["cursorBlink"], dict):
            interval = animations["cursorBlink"].get("interval", 1000)
            if not isinstance(interval, int) or interval < 100 or interval > 5000:
                result.errors.append("Cursor blink interval must be between 100 and 5000ms")

        result.is_valid = len(result.errors) == 0
        return result

    @staticmethod
    def _validate_custom_css(css: str) -> ThemeValidationResult:
        """Validate custom CSS for security."""
        result = ThemeValidationResult(is_valid=True)

        # Size check
        if len(css) > 50000:
            result.errors.append("Custom CSS exceeds 50KB limit")

        # Security patterns
        dangerous_patterns = [
            r'@import\s+url\s*\(',
            r'expression\s*\(',
            r'javascript:',
            r'vbscript:',
            r'data:.*script',
            r'<script',
            r'</script>'
        ]

        css_lower = css.lower()
        for pattern in dangerous_patterns:
            if re.search(pattern, css_lower):
                result.errors.append(f"Dangerous CSS pattern detected: {pattern}")

        result.is_valid = len(result.errors) == 0
        return result

    @staticmethod
    def _is_valid_color(color: str) -> bool:
        """Validate color format."""
        if not isinstance(color, str):
            return False

        # Hex color validation
        hex_pattern = r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3}|[A-Fa-f0-9]{8})$'
        if re.match(hex_pattern, color):
            return True

        # RGBA color validation
        rgba_pattern = r'^rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*(0?\.\d+|1|0))?\s*\)$'
        return bool(re.match(rgba_pattern, color))

    @staticmethod
    def _calculate_contrast_ratio(color1: str, color2: str) -> float:
        """Calculate contrast ratio between two colors."""
        try:
            def get_luminance(color: str) -> float:
                # Simple hex to RGB conversion
                if color.startswith('#'):
                    hex_color = color.lstrip('#')
                    if len(hex_color) == 3:
                        hex_color = ''.join([c*2 for c in hex_color])
                    r = int(hex_color[0:2], 16) / 255.0
                    g = int(hex_color[2:4], 16) / 255.0
                    b = int(hex_color[4:6], 16) / 255.0

                    # Calculate relative luminance
                    def srgb_to_linear(c):
                        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

                    r_lin = srgb_to_linear(r)
                    g_lin = srgb_to_linear(g)
                    b_lin = srgb_to_linear(b)

                    return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin

                return 0.5  # Default for invalid colors

            lum1 = get_luminance(color1)
            lum2 = get_luminance(color2)

            # Ensure lighter color is numerator
            lighter = max(lum1, lum2)
            darker = min(lum1, lum2)

            return (lighter + 0.05) / (darker + 0.05)

        except Exception:
            return 1.0  # Default contrast ratio


class VSCodeThemeImporter:
    """Handles VS Code theme import functionality."""

    @staticmethod
    async def import_from_file(file_data: bytes, filename: str) -> ThemeConfiguration:
        """Import theme from VS Code theme file."""
        try:
            # Handle zip files (VS Code extension packages)
            if filename.endswith('.vsix') or filename.endswith('.zip'):
                return await VSCodeThemeImporter._import_from_zip(file_data)

            # Handle JSON files
            elif filename.endswith('.json'):
                return await VSCodeThemeImporter._import_from_json(file_data)

            else:
                raise ThemeImportError(f"Unsupported file format: {filename}")

        except Exception as e:
            logger.error(f"Error importing VS Code theme: {e}")
            raise ThemeImportError(f"Failed to import theme: {e}")

    @staticmethod
    async def _import_from_zip(zip_data: bytes) -> ThemeConfiguration:
        """Import theme from VS Code extension package."""
        with zipfile.ZipFile(BytesIO(zip_data), 'r') as zip_file:
            # Find theme files
            theme_files = [f for f in zip_file.namelist() if f.endswith('.json') and 'theme' in f.lower()]

            if not theme_files:
                raise ThemeImportError("No theme files found in package")

            # Read first theme file
            theme_data = json.loads(zip_file.read(theme_files[0]))
            return await VSCodeThemeImporter._convert_vscode_theme(theme_data)

    @staticmethod
    async def _import_from_json(json_data: bytes) -> ThemeConfiguration:
        """Import theme from JSON file."""
        theme_data = json.loads(json_data.decode('utf-8'))
        return await VSCodeThemeImporter._convert_vscode_theme(theme_data)

    @staticmethod
    async def _convert_vscode_theme(vscode_theme: Dict[str, Any]) -> ThemeConfiguration:
        """Convert VS Code theme to internal format."""
        # Extract basic info
        name = vscode_theme.get('name', 'Imported Theme')
        theme_type = vscode_theme.get('type', 'dark')

        # Convert colors
        vscode_colors = vscode_theme.get('colors', {})
        terminal_colors = VSCodeThemeImporter._convert_colors(vscode_colors, theme_type)

        # Basic font configuration
        fonts = {
            "family": "monospace",
            "size": 14,
            "weight": "normal",
            "lineHeight": 1.2,
            "letterSpacing": 0
        }

        # Basic animation configuration
        animations = {
            "enabled": True,
            "fadeInText": {"enabled": True, "duration": 200, "easing": "ease-out"},
            "cursorBlink": {"enabled": True, "interval": 1000},
            "typewriterEffect": {"enabled": False, "speed": 50},
            "particleEffects": {"enabled": False, "type": "stars"}
        }

        # Cursor configuration
        cursor = {
            "style": "block",
            "blink": True,
            "color": terminal_colors.get("cursor", "#ffffff")
        }

        # Background configuration
        background = {
            "color": terminal_colors.get("background", "#000000"),
            "image": None,
            "opacity": 1.0,
            "blur": 0
        }

        # Create theme configuration
        theme_config = ThemeConfiguration(
            name=name,
            description=f"Imported from VS Code theme: {name}",
            author="VS Code Import",
            colors=terminal_colors,
            fonts=fonts,
            animations=animations,
            cursor=cursor,
            background=background
        )

        return theme_config

    @staticmethod
    def _convert_colors(vscode_colors: Dict[str, str], theme_type: str) -> Dict[str, str]:
        """Convert VS Code colors to terminal color palette."""
        # Default terminal colors based on theme type
        if theme_type == 'light':
            defaults = {
                "background": "#ffffff",
                "foreground": "#000000",
                "cursor": "#000000",
                "selection": "#0000ff40"
            }
        else:
            defaults = {
                "background": "#000000",
                "foreground": "#ffffff",
                "cursor": "#ffffff",
                "selection": "#ffffff40"
            }

        # Map VS Code colors to terminal colors
        color_mapping = {
            "editor.background": "background",
            "editor.foreground": "foreground",
            "editorCursor.foreground": "cursor",
            "editor.selectionBackground": "selection",
            "terminal.ansiBlack": "black",
            "terminal.ansiRed": "red",
            "terminal.ansiGreen": "green",
            "terminal.ansiYellow": "yellow",
            "terminal.ansiBlue": "blue",
            "terminal.ansiMagenta": "magenta",
            "terminal.ansiCyan": "cyan",
            "terminal.ansiWhite": "white",
            "terminal.ansiBrightBlack": "brightBlack",
            "terminal.ansiBrightRed": "brightRed",
            "terminal.ansiBrightGreen": "brightGreen",
            "terminal.ansiBrightYellow": "brightYellow",
            "terminal.ansiBrightBlue": "brightBlue",
            "terminal.ansiBrightMagenta": "brightMagenta",
            "terminal.ansiBrightCyan": "brightCyan",
            "terminal.ansiBrightWhite": "brightWhite"
        }

        # Convert colors
        terminal_colors = defaults.copy()
        for vscode_key, terminal_key in color_mapping.items():
            if vscode_key in vscode_colors:
                terminal_colors[terminal_key] = vscode_colors[vscode_key]

        # Fill in missing ANSI colors with defaults
        ansi_defaults = {
            "black": "#000000", "red": "#ff0000", "green": "#00ff00", "yellow": "#ffff00",
            "blue": "#0000ff", "magenta": "#ff00ff", "cyan": "#00ffff", "white": "#ffffff",
            "brightBlack": "#808080", "brightRed": "#ff8080", "brightGreen": "#80ff80",
            "brightYellow": "#ffff80", "brightBlue": "#8080ff", "brightMagenta": "#ff80ff",
            "brightCyan": "#80ffff", "brightWhite": "#ffffff"
        }

        for key, default_value in ansi_defaults.items():
            if key not in terminal_colors:
                terminal_colors[key] = default_value

        return terminal_colors


class ThemeMarketplace:
    """Handles theme marketplace functionality."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def get_featured_themes(self, limit: int = 10) -> List[ThemeConfiguration]:
        """Get featured themes from marketplace."""
        result = await self.db.execute(
            select(ThemeConfiguration)
            .where(
                and_(
                    ThemeConfiguration.is_public == True,
                    ThemeConfiguration.rating >= 400  # 4.0+ rating
                )
            )
            .order_by(ThemeConfiguration.download_count.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def search_themes(self, query: str, limit: int = 20) -> List[ThemeConfiguration]:
        """Search themes by name or author."""
        search_pattern = f"%{query}%"
        result = await self.db.execute(
            select(ThemeConfiguration)
            .where(
                and_(
                    ThemeConfiguration.is_public == True,
                    or_(
                        ThemeConfiguration.name.ilike(search_pattern),
                        ThemeConfiguration.author.ilike(search_pattern),
                        ThemeConfiguration.description.ilike(search_pattern)
                    )
                )
            )
            .order_by(ThemeConfiguration.rating.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def get_themes_by_category(self, category: str, limit: int = 20) -> List[ThemeConfiguration]:
        """Get themes by category (light/dark)."""
        # Determine theme type based on background color
        if category.lower() == "light":
            # Themes with lighter backgrounds
            color_condition = ThemeConfiguration.colors["background"].astext.notlike("#0%")
        else:
            # Themes with darker backgrounds
            color_condition = ThemeConfiguration.colors["background"].astext.like("#0%")

        result = await self.db.execute(
            select(ThemeConfiguration)
            .where(
                and_(
                    ThemeConfiguration.is_public == True,
                    color_condition
                )
            )
            .order_by(ThemeConfiguration.download_count.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def rate_theme(self, theme_id: str, user_id: str, rating: float) -> bool:
        """Rate a theme (0.0 - 5.0)."""
        try:
            # Get theme
            result = await self.db.execute(
                select(ThemeConfiguration).where(ThemeConfiguration.theme_id == theme_id)
            )
            theme = result.scalar_one_or_none()

            if not theme:
                return False

            # Update rating (simplified - in production, track individual ratings)
            current_rating = theme.get_rating_float()
            new_rating = (current_rating + rating) / 2  # Simple average
            theme.set_rating_float(new_rating)

            await self.db.commit()
            return True

        except Exception as e:
            logger.error(f"Error rating theme: {e}")
            return False


class ThemeService:
    """Main theme management service."""

    def __init__(self, config: ThemeConfig = None):
        self.config = config or ThemeConfig()
        self._ensure_directories()

    def _ensure_directories(self):
        """Ensure required directories exist."""
        Path(self.config.themes_dir).mkdir(parents=True, exist_ok=True)

    async def create_theme(self, user_id: str, theme_data: Dict[str, Any]) -> ThemeConfiguration:
        """Create a new theme."""
        # Validate theme
        validation = ThemeValidator.validate_theme_config(theme_data)
        if not validation.is_valid:
            raise ThemeValidationError(f"Theme validation failed: {validation.errors}")

        async with AsyncSessionLocal() as db:
            # Check user theme limit
            user_theme_count = await self._get_user_theme_count(db, user_id)
            if user_theme_count >= self.config.max_themes_per_user:
                raise ThemeValidationError(f"Theme limit exceeded ({self.config.max_themes_per_user})")

            # Create theme
            theme = ThemeConfiguration(
                name=theme_data["name"],
                description=theme_data.get("description", ""),
                author=theme_data.get("author", "Anonymous"),
                colors=theme_data["colors"],
                fonts=theme_data["fonts"],
                animations=theme_data.get("animations", {}),
                cursor=theme_data.get("cursor", {}),
                background=theme_data.get("background", {}),
                custom_css=theme_data.get("custom_css")
            )

            db.add(theme)
            await db.commit()
            await db.refresh(theme)

            logger.info(f"Created theme: {theme.theme_id} by user {user_id}")
            return theme

    async def get_theme(self, theme_id: str) -> Optional[ThemeConfiguration]:
        """Get theme by ID."""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(ThemeConfiguration).where(ThemeConfiguration.theme_id == theme_id)
            )
            return result.scalar_one_or_none()

    async def update_theme(self, theme_id: str, user_id: str, theme_data: Dict[str, Any]) -> Optional[ThemeConfiguration]:
        """Update existing theme."""
        async with AsyncSessionLocal() as db:
            # Get theme
            result = await db.execute(
                select(ThemeConfiguration).where(ThemeConfiguration.theme_id == theme_id)
            )
            theme = result.scalar_one_or_none()

            if not theme:
                return None

            # Check ownership (skip for built-in themes)
            if not theme.is_built_in and theme.author != user_id:
                raise ThemeValidationError("Not authorized to update this theme")

            # Validate updates
            validation = ThemeValidator.validate_theme_config(theme_data)
            if not validation.is_valid:
                raise ThemeValidationError(f"Theme validation failed: {validation.errors}")

            # Update theme
            for field in ["name", "description", "colors", "fonts", "animations", "cursor", "background"]:
                if field in theme_data:
                    setattr(theme, field, theme_data[field])

            if "custom_css" in theme_data:
                theme.custom_css = theme_data["custom_css"]

            theme.updated_at = datetime.now(timezone.utc)

            await db.commit()
            await db.refresh(theme)

            return theme

    async def delete_theme(self, theme_id: str, user_id: str) -> bool:
        """Delete theme."""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(ThemeConfiguration).where(ThemeConfiguration.theme_id == theme_id)
            )
            theme = result.scalar_one_or_none()

            if not theme:
                return False

            # Check ownership
            if not theme.is_built_in and theme.author != user_id:
                return False

            # Cannot delete built-in themes
            if theme.is_built_in:
                return False

            await db.delete(theme)
            await db.commit()

            logger.info(f"Deleted theme: {theme_id}")
            return True

    async def import_vscode_theme(self, file_data: bytes, filename: str, user_id: str) -> ThemeConfiguration:
        """Import VS Code theme."""
        try:
            # Import theme
            theme = await VSCodeThemeImporter.import_from_file(file_data, filename)
            theme.author = user_id

            # Save to database
            async with AsyncSessionLocal() as db:
                db.add(theme)
                await db.commit()
                await db.refresh(theme)

            logger.info(f"Imported VS Code theme: {theme.theme_id}")
            return theme

        except Exception as e:
            logger.error(f"Error importing VS Code theme: {e}")
            raise ThemeImportError(f"Failed to import theme: {e}")

    async def export_theme(self, theme_id: str, format: str = "json") -> bytes:
        """Export theme in specified format."""
        theme = await self.get_theme(theme_id)
        if not theme:
            raise ThemeExportError("Theme not found")

        if format.lower() == "json":
            return json.dumps(theme.export_config(), indent=2).encode('utf-8')
        else:
            raise ThemeExportError(f"Unsupported export format: {format}")

    async def apply_theme_to_session(self, session_id: str, theme_id: str) -> bool:
        """Apply theme to terminal session."""
        async with AsyncSessionLocal() as db:
            # Verify theme exists
            theme_result = await db.execute(
                select(ThemeConfiguration).where(ThemeConfiguration.theme_id == theme_id)
            )
            theme = theme_result.scalar_one_or_none()

            if not theme:
                return False

            # Update session
            stmt = (
                update(TerminalSession)
                .where(TerminalSession.session_id == session_id)
                .values(theme_id=theme_id)
            )
            await db.execute(stmt)
            await db.commit()

            return True

    async def get_user_themes(self, user_id: str) -> List[ThemeConfiguration]:
        """Get themes created by user."""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(ThemeConfiguration)
                .where(ThemeConfiguration.author == user_id)
                .order_by(ThemeConfiguration.created_at.desc())
            )
            return result.scalars().all()

    async def get_built_in_themes(self) -> List[ThemeConfiguration]:
        """Get built-in system themes."""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(ThemeConfiguration)
                .where(ThemeConfiguration.is_built_in == True)
                .order_by(ThemeConfiguration.name)
            )
            return result.scalars().all()

    async def clone_theme(self, theme_id: str, user_id: str, new_name: str) -> Optional[ThemeConfiguration]:
        """Clone existing theme."""
        original_theme = await self.get_theme(theme_id)
        if not original_theme:
            return None

        # Create new theme based on original
        theme_data = original_theme.export_config()
        theme_data["name"] = new_name
        theme_data["author"] = user_id

        return await self.create_theme(user_id, theme_data)

    async def validate_theme(self, theme_data: Dict[str, Any]) -> ThemeValidationResult:
        """Validate theme configuration."""
        return ThemeValidator.validate_theme_config(theme_data)

    async def get_marketplace(self) -> ThemeMarketplace:
        """Get marketplace instance."""
        async with AsyncSessionLocal() as db:
            return ThemeMarketplace(db)

    async def publish_theme(self, theme_id: str, user_id: str) -> bool:
        """Publish theme to marketplace."""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(ThemeConfiguration).where(
                    ThemeConfiguration.theme_id == theme_id,
                    ThemeConfiguration.author == user_id
                )
            )
            theme = result.scalar_one_or_none()

            if not theme:
                return False

            theme.is_public = True
            await db.commit()

            logger.info(f"Published theme to marketplace: {theme_id}")
            return True

    async def _get_user_theme_count(self, db: AsyncSession, user_id: str) -> int:
        """Get count of themes created by user."""
        result = await db.execute(
            select(ThemeConfiguration)
            .where(ThemeConfiguration.author == user_id)
        )
        return len(result.scalars().all())

    async def initialize_built_in_themes(self) -> None:
        """Initialize built-in system themes."""
        built_in_themes = [
            {
                "name": "Dark Terminal",
                "description": "Classic dark terminal theme",
                "colors": {
                    "background": "#000000", "foreground": "#ffffff", "cursor": "#ffffff",
                    "selection": "#ffffff40", "black": "#000000", "red": "#ff0000",
                    "green": "#00ff00", "yellow": "#ffff00", "blue": "#0000ff",
                    "magenta": "#ff00ff", "cyan": "#00ffff", "white": "#ffffff",
                    "brightBlack": "#808080", "brightRed": "#ff8080", "brightGreen": "#80ff80",
                    "brightYellow": "#ffff80", "brightBlue": "#8080ff", "brightMagenta": "#ff80ff",
                    "brightCyan": "#80ffff", "brightWhite": "#ffffff"
                }
            },
            {
                "name": "Light Terminal",
                "description": "Clean light terminal theme",
                "colors": {
                    "background": "#ffffff", "foreground": "#000000", "cursor": "#000000",
                    "selection": "#0000ff40", "black": "#000000", "red": "#cc0000",
                    "green": "#00cc00", "yellow": "#cccc00", "blue": "#0000cc",
                    "magenta": "#cc00cc", "cyan": "#00cccc", "white": "#cccccc",
                    "brightBlack": "#666666", "brightRed": "#ff0000", "brightGreen": "#00ff00",
                    "brightYellow": "#ffff00", "brightBlue": "#0000ff", "brightMagenta": "#ff00ff",
                    "brightCyan": "#00ffff", "brightWhite": "#ffffff"
                }
            }
        ]

        async with AsyncSessionLocal() as db:
            for theme_data in built_in_themes:
                # Check if theme already exists
                result = await db.execute(
                    select(ThemeConfiguration).where(
                        ThemeConfiguration.name == theme_data["name"],
                        ThemeConfiguration.is_built_in == True
                    )
                )
                existing = result.scalar_one_or_none()

                if not existing:
                    theme = ThemeConfiguration(
                        name=theme_data["name"],
                        description=theme_data["description"],
                        author="System",
                        is_built_in=True,
                        colors=theme_data["colors"],
                        fonts={"family": "monospace", "size": 14, "weight": "normal", "lineHeight": 1.2},
                        animations={"enabled": True},
                        cursor={"style": "block", "blink": True},
                        background={"color": theme_data["colors"]["background"]}
                    )
                    db.add(theme)

            await db.commit()


# Global service instance
theme_service = ThemeService()


async def get_theme_service() -> ThemeService:
    """Dependency injection for theme service."""
    return theme_service
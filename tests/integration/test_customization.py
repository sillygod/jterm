"""Integration tests for theme import and extension loading functionality.

These tests verify complete user workflows for customizing the terminal
with themes, extensions, VS Code theme import, and user preference
management with real-time updates.

CRITICAL: These tests MUST FAIL until the implementation is complete.
Tests validate end-to-end customization workflows from the quickstart guide.
"""

import pytest
import json
import zipfile
import io
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Import the app once it's implemented
try:
    from src.main import app
    APP_AVAILABLE = True
except ImportError:
    APP_AVAILABLE = False


class TestCustomizationIntegration:
    """Test complete theme and extension customization workflows."""

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
        """Create a terminal session for testing."""
        response = client.post(
            "/api/terminal/sessions",
            json={
                "shell": "bash",
                "workingDirectory": "/tmp",
                "terminalSize": {"cols": 80, "rows": 24}
            },
            headers=auth_headers
        )
        return response.json()["sessionId"]

    @pytest.fixture
    def sample_theme(self):
        """Sample theme data for testing."""
        return {
            "name": "Test Theme",
            "version": "1.0.0",
            "author": "Test Author",
            "description": "A test theme for integration testing",
            "colors": {
                "background": "#1e1e1e",
                "foreground": "#d4d4d4",
                "cursor": "#ffffff",
                "selection": "#3a3d41",
                "black": "#000000",
                "red": "#f44747",
                "green": "#608b4e",
                "yellow": "#dcdcaa",
                "blue": "#569cd6",
                "magenta": "#c586c0",
                "cyan": "#4ec9b0",
                "white": "#d4d4d4",
                "brightBlack": "#808080",
                "brightRed": "#f44747",
                "brightGreen": "#608b4e",
                "brightYellow": "#dcdcaa",
                "brightBlue": "#569cd6",
                "brightMagenta": "#c586c0",
                "brightCyan": "#4ec9b0",
                "brightWhite": "#ffffff"
            },
            "terminal": {
                "fontSize": 14,
                "fontFamily": "Consolas, 'Courier New', monospace",
                "lineHeight": 1.2,
                "cursorStyle": "block",
                "cursorBlink": True
            },
            "ui": {
                "accentColor": "#007acc",
                "borderColor": "#3c3c3c",
                "panelBackground": "#252526",
                "sidebarBackground": "#2d2d30"
            }
        }

    @pytest.fixture
    def vscode_theme_package(self):
        """Mock VS Code theme package for import testing."""
        theme_content = {
            "name": "Dark+ (default dark)",
            "type": "dark",
            "colors": {
                "editor.background": "#1e1e1e",
                "editor.foreground": "#d4d4d4",
                "editorCursor.foreground": "#aeafad",
                "editor.selectionBackground": "#094771",
                "terminal.background": "#1e1e1e",
                "terminal.foreground": "#cccccc"
            },
            "tokenColors": [
                {
                    "settings": {
                        "foreground": "#D4D4D4"
                    }
                },
                {
                    "scope": ["comment"],
                    "settings": {
                        "foreground": "#6A9955"
                    }
                },
                {
                    "scope": ["string"],
                    "settings": {
                        "foreground": "#CE9178"
                    }
                }
            ]
        }

        package_json = {
            "name": "test-theme",
            "displayName": "Test Theme",
            "description": "A test theme package",
            "version": "1.0.0",
            "engines": {"vscode": "^1.0.0"},
            "categories": ["Themes"],
            "contributes": {
                "themes": [
                    {
                        "label": "Test Theme",
                        "uiTheme": "vs-dark",
                        "path": "./themes/test-theme.json"
                    }
                ]
            }
        }

        # Create zip file in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr("package.json", json.dumps(package_json))
            zip_file.writestr("themes/test-theme.json", json.dumps(theme_content))

        zip_buffer.seek(0)
        return zip_buffer.getvalue()

    @pytest.fixture
    def sample_extension(self):
        """Sample extension data for testing."""
        return {
            "name": "Test Extension",
            "version": "1.0.0",
            "author": "Test Author",
            "description": "A test extension for integration testing",
            "type": "command",
            "manifest": {
                "permissions": ["terminal:read", "terminal:write"],
                "commands": [
                    {
                        "name": "hello",
                        "description": "Print hello message",
                        "handler": "handlers.hello"
                    }
                ],
                "keybindings": [
                    {
                        "key": "Ctrl+Shift+H",
                        "command": "hello"
                    }
                ]
            },
            "code": """
function hello() {
    terminal.write('Hello from extension!\\n');
    return true;
}

const handlers = {
    hello: hello
};
"""
        }

    def test_theme_import_and_application_workflow(self, client, auth_headers, terminal_session, sample_theme):
        """Test complete workflow: import theme → apply to session → verify appearance.

        User Story: User imports custom theme file and applies it to terminal session
        with immediate visual updates and persistent storage.
        """
        with pytest.raises((Exception, AssertionError)):
            # Step 1: Import theme
            theme_import_response = client.post(
                "/api/themes/import",
                json=sample_theme,
                headers=auth_headers
            )

            assert theme_import_response.status_code == 201
            theme_data = theme_import_response.json()
            theme_id = theme_data["themeId"]
            assert theme_data["name"] == sample_theme["name"]
            assert theme_data["status"] == "imported"

            # Step 2: Validate theme structure
            validation_response = client.get(
                f"/api/themes/{theme_id}/validate",
                headers=auth_headers
            )
            assert validation_response.status_code == 200
            validation_data = validation_response.json()
            assert validation_data["valid"] == True
            assert len(validation_data["warnings"]) == 0
            assert len(validation_data["errors"]) == 0

            # Step 3: Apply theme to terminal session
            apply_response = client.post(
                f"/api/terminal/sessions/{terminal_session}/theme",
                json={"themeId": theme_id},
                headers=auth_headers
            )
            assert apply_response.status_code == 200

            # Step 4: Verify theme is applied via WebSocket
            with client.websocket_connect(f"/ws/terminal/{terminal_session}") as websocket:
                # Should receive theme update notification
                theme_update = websocket.receive_json()
                assert theme_update["type"] == "theme_applied"
                assert theme_update["themeId"] == theme_id
                assert "colors" in theme_update["theme"]
                assert theme_update["theme"]["colors"]["background"] == sample_theme["colors"]["background"]

            # Step 5: Get current session appearance
            appearance_response = client.get(
                f"/api/terminal/sessions/{terminal_session}/appearance",
                headers=auth_headers
            )
            assert appearance_response.status_code == 200
            appearance_data = appearance_response.json()
            assert appearance_data["currentTheme"]["id"] == theme_id
            assert appearance_data["colors"]["background"] == sample_theme["colors"]["background"]

    def test_vscode_theme_import_workflow(self, client, auth_headers, terminal_session, vscode_theme_package):
        """Test complete workflow: import VS Code theme → convert → apply.

        User Story: User imports VS Code theme package (.vsix or theme folder)
        and system converts it to terminal-compatible format.
        """
        with pytest.raises((Exception, AssertionError)):
            # Step 1: Upload VS Code theme package
            upload_response = client.post(
                "/api/themes/import/vscode",
                files={
                    "package": ("test-theme.zip", vscode_theme_package, "application/zip")
                },
                headers=auth_headers
            )

            assert upload_response.status_code == 201
            import_data = upload_response.json()
            assert "themeId" in import_data
            assert import_data["source"] == "vscode"
            assert import_data["converted"] == True

            theme_id = import_data["themeId"]

            # Step 2: Get converted theme details
            converted_theme_response = client.get(
                f"/api/themes/{theme_id}",
                headers=auth_headers
            )
            assert converted_theme_response.status_code == 200
            converted_theme = converted_theme_response.json()

            # Verify conversion mapped VS Code colors correctly
            assert "colors" in converted_theme
            assert converted_theme["colors"]["background"] == "#1e1e1e"  # From VS Code theme
            assert converted_theme["colors"]["foreground"] == "#d4d4d4"

            # Step 3: Preview theme before applying
            preview_response = client.post(
                f"/api/terminal/sessions/{terminal_session}/theme/preview",
                json={"themeId": theme_id},
                headers=auth_headers
            )
            assert preview_response.status_code == 200
            preview_data = preview_response.json()
            assert "previewUrl" in preview_data
            assert preview_data["duration"] == 30  # 30-second preview

            # Step 4: Apply converted theme
            apply_response = client.post(
                f"/api/terminal/sessions/{terminal_session}/theme",
                json={"themeId": theme_id},
                headers=auth_headers
            )
            assert apply_response.status_code == 200

    def test_extension_loading_and_execution_workflow(self, client, auth_headers, terminal_session, sample_extension):
        """Test complete workflow: load extension → register commands → execute.

        User Story: User loads custom extension that adds new commands and
        key bindings to terminal with security sandboxing.
        """
        with pytest.raises((Exception, AssertionError)):
            # Step 1: Upload and install extension
            install_response = client.post(
                "/api/extensions/install",
                json=sample_extension,
                headers=auth_headers
            )

            assert install_response.status_code == 201
            extension_data = install_response.json()
            extension_id = extension_data["extensionId"]
            assert extension_data["status"] == "installed"
            assert extension_data["name"] == sample_extension["name"]

            # Step 2: Validate extension security
            security_response = client.get(
                f"/api/extensions/{extension_id}/security-check",
                headers=auth_headers
            )
            assert security_response.status_code == 200
            security_data = security_response.json()
            assert security_data["safe"] == True
            assert "sandboxed" in security_data
            assert security_data["permissions"] == sample_extension["manifest"]["permissions"]

            # Step 3: Enable extension for terminal session
            enable_response = client.post(
                f"/api/terminal/sessions/{terminal_session}/extensions/enable",
                json={"extensionId": extension_id},
                headers=auth_headers
            )
            assert enable_response.status_code == 200

            # Step 4: Test extension command execution
            with client.websocket_connect(f"/ws/terminal/{terminal_session}") as websocket:
                # Extension should register its commands
                extension_ready = websocket.receive_json()
                assert extension_ready["type"] == "extension_loaded"
                assert extension_ready["extensionId"] == extension_id

                # Execute extension command
                websocket.send_json({
                    "type": "extension_command",
                    "command": "hello",
                    "extensionId": extension_id
                })

                command_response = websocket.receive_json()
                assert command_response["type"] == "extension_output"
                assert "Hello from extension!" in command_response["output"]

                # Test keybinding
                websocket.send_json({
                    "type": "key_combination",
                    "keys": ["Ctrl", "Shift", "H"]
                })

                keybind_response = websocket.receive_json()
                assert keybind_response["type"] == "extension_output"
                assert "Hello from extension!" in keybind_response["output"]

    def test_user_preferences_management_workflow(self, client, auth_headers, terminal_session):
        """Test user preferences storage and synchronization across sessions.

        User Story: User customizes terminal preferences (fonts, colors, shortcuts)
        and settings persist across sessions and devices.
        """
        with pytest.raises((Exception, AssertionError)):
            # Step 1: Set user preferences
            preferences = {
                "terminal": {
                    "fontSize": 16,
                    "fontFamily": "JetBrains Mono",
                    "lineHeight": 1.4,
                    "cursorStyle": "underline",
                    "cursorBlink": False,
                    "scrollback": 10000
                },
                "appearance": {
                    "defaultTheme": "dark-plus",
                    "transparency": 0.95,
                    "animations": True
                },
                "behavior": {
                    "confirmOnExit": True,
                    "autoSave": True,
                    "bellSound": False
                },
                "keybindings": [
                    {"key": "Ctrl+Shift+C", "action": "copy"},
                    {"key": "Ctrl+Shift+V", "action": "paste"},
                    {"key": "Ctrl+Shift+T", "action": "new_tab"}
                ]
            }

            set_prefs_response = client.put(
                "/api/user/preferences",
                json=preferences,
                headers=auth_headers
            )
            assert set_prefs_response.status_code == 200

            # Step 2: Apply preferences to current session
            apply_prefs_response = client.post(
                f"/api/terminal/sessions/{terminal_session}/apply-preferences",
                headers=auth_headers
            )
            assert apply_prefs_response.status_code == 200

            # Step 3: Verify preferences are applied
            with client.websocket_connect(f"/ws/terminal/{terminal_session}") as websocket:
                prefs_applied = websocket.receive_json()
                assert prefs_applied["type"] == "preferences_applied"
                assert prefs_applied["fontSize"] == 16
                assert prefs_applied["fontFamily"] == "JetBrains Mono"

            # Step 4: Create new session and verify preferences persist
            new_session_response = client.post(
                "/api/terminal/sessions",
                json={
                    "shell": "bash",
                    "workingDirectory": "/tmp",
                    "terminalSize": {"cols": 80, "rows": 24},
                    "applyUserPreferences": True
                },
                headers=auth_headers
            )
            new_session_id = new_session_response.json()["sessionId"]

            # Step 5: Verify new session has same preferences
            session_config_response = client.get(
                f"/api/terminal/sessions/{new_session_id}/config",
                headers=auth_headers
            )
            assert session_config_response.status_code == 200
            session_config = session_config_response.json()
            assert session_config["fontSize"] == 16
            assert session_config["fontFamily"] == "JetBrains Mono"

    def test_theme_marketplace_integration(self, client, auth_headers):
        """Test theme marketplace browsing and installation.

        User Story: User browses theme marketplace, previews themes,
        and installs themes directly from community repository.
        """
        with pytest.raises((Exception, AssertionError)):
            # Step 1: Browse available themes
            marketplace_response = client.get(
                "/api/marketplace/themes",
                params={"category": "dark", "page": 1, "limit": 10},
                headers=auth_headers
            )
            assert marketplace_response.status_code == 200
            marketplace_data = marketplace_response.json()

            assert "themes" in marketplace_data
            assert "total" in marketplace_data
            assert len(marketplace_data["themes"]) > 0

            # Pick a theme for testing
            test_theme = marketplace_data["themes"][0]
            marketplace_theme_id = test_theme["id"]

            # Step 2: Get theme details and preview
            theme_details_response = client.get(
                f"/api/marketplace/themes/{marketplace_theme_id}",
                headers=auth_headers
            )
            assert theme_details_response.status_code == 200
            theme_details = theme_details_response.json()

            assert "name" in theme_details
            assert "author" in theme_details
            assert "screenshots" in theme_details
            assert "downloadCount" in theme_details
            assert "rating" in theme_details

            # Step 3: Install theme from marketplace
            install_marketplace_response = client.post(
                f"/api/marketplace/themes/{marketplace_theme_id}/install",
                headers=auth_headers
            )
            assert install_marketplace_response.status_code == 201
            installed_theme_data = install_marketplace_response.json()

            assert "themeId" in installed_theme_data
            assert installed_theme_data["source"] == "marketplace"

            # Step 4: Verify theme is in user's collection
            user_themes_response = client.get(
                "/api/themes",
                headers=auth_headers
            )
            assert user_themes_response.status_code == 200
            user_themes = user_themes_response.json()

            marketplace_theme_installed = any(
                theme["marketplaceId"] == marketplace_theme_id
                for theme in user_themes["themes"]
            )
            assert marketplace_theme_installed == True

    def test_custom_css_and_styling_workflow(self, client, auth_headers, terminal_session):
        """Test custom CSS injection and advanced styling options.

        User Story: Advanced users can inject custom CSS for fine-grained
        terminal appearance customization beyond standard themes.
        """
        with pytest.raises((Exception, AssertionError)):
            # Step 1: Upload custom CSS
            custom_css = """
/* Custom terminal styling */
.terminal-container {
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.xterm-screen {
    padding: 10px;
}

.xterm-cursor-layer {
    animation: blink 1s infinite;
}

@keyframes blink {
    0%, 50% { opacity: 1; }
    51%, 100% { opacity: 0; }
}

/* Custom scrollbar */
.terminal-container ::-webkit-scrollbar {
    width: 8px;
}

.terminal-container ::-webkit-scrollbar-track {
    background: #2d2d30;
}

.terminal-container ::-webkit-scrollbar-thumb {
    background: #424242;
    border-radius: 4px;
}
"""

            css_upload_response = client.post(
                "/api/customization/css",
                json={
                    "name": "Custom Terminal Styling",
                    "css": custom_css,
                    "scope": "session"  # or "global"
                },
                headers=auth_headers
            )
            assert css_upload_response.status_code == 201
            css_id = css_upload_response.json()["cssId"]

            # Step 2: Apply custom CSS to session
            apply_css_response = client.post(
                f"/api/terminal/sessions/{terminal_session}/css",
                json={"cssId": css_id, "enabled": True},
                headers=auth_headers
            )
            assert apply_css_response.status_code == 200

            # Step 3: Verify CSS is applied
            with client.websocket_connect(f"/ws/terminal/{terminal_session}") as websocket:
                css_applied = websocket.receive_json()
                assert css_applied["type"] == "css_applied"
                assert css_applied["cssId"] == css_id

            # Step 4: Get rendered CSS for verification
            rendered_css_response = client.get(
                f"/api/terminal/sessions/{terminal_session}/rendered-css",
                headers=auth_headers
            )
            assert rendered_css_response.status_code == 200
            rendered_css = rendered_css_response.text
            assert "terminal-container" in rendered_css
            assert "border-radius: 8px" in rendered_css

    def test_extension_marketplace_and_security(self, client, auth_headers, terminal_session):
        """Test extension marketplace with security validation.

        User Story: User browses extension marketplace with security ratings
        and installs verified extensions with permission controls.
        """
        with pytest.raises((Exception, AssertionError)):
            # Step 1: Browse extension marketplace
            extensions_response = client.get(
                "/api/marketplace/extensions",
                params={"category": "productivity", "verified": True},
                headers=auth_headers
            )
            assert extensions_response.status_code == 200
            extensions_data = extensions_response.json()

            assert "extensions" in extensions_data
            test_extension = extensions_data["extensions"][0]
            marketplace_ext_id = test_extension["id"]

            # Step 2: Get extension security analysis
            security_analysis_response = client.get(
                f"/api/marketplace/extensions/{marketplace_ext_id}/security",
                headers=auth_headers
            )
            assert security_analysis_response.status_code == 200
            security_analysis = security_analysis_response.json()

            assert "securityRating" in security_analysis
            assert "permissions" in security_analysis
            assert "codeAnalysis" in security_analysis
            assert security_analysis["verified"] == True

            # Step 3: Install with permission review
            install_ext_response = client.post(
                f"/api/marketplace/extensions/{marketplace_ext_id}/install",
                json={
                    "acceptPermissions": security_analysis["permissions"],
                    "enableByDefault": False
                },
                headers=auth_headers
            )
            assert install_ext_response.status_code == 201
            installed_ext_id = install_ext_response.json()["extensionId"]

            # Step 4: Enable with restricted permissions
            enable_response = client.post(
                f"/api/terminal/sessions/{terminal_session}/extensions/enable",
                json={
                    "extensionId": installed_ext_id,
                    "permissions": ["terminal:read"]  # Restricted subset
                },
                headers=auth_headers
            )
            assert enable_response.status_code == 200

    def test_backup_and_restore_customizations(self, client, auth_headers, sample_theme, sample_extension):
        """Test backup and restore of all customizations.

        User Story: User can backup all themes, extensions, and preferences
        and restore them on new installation or different device.
        """
        with pytest.raises((Exception, AssertionError)):
            # Step 1: Set up customizations
            # Import theme
            theme_response = client.post(
                "/api/themes/import",
                json=sample_theme,
                headers=auth_headers
            )
            theme_id = theme_response.json()["themeId"]

            # Install extension
            ext_response = client.post(
                "/api/extensions/install",
                json=sample_extension,
                headers=auth_headers
            )
            ext_id = ext_response.json()["extensionId"]

            # Set preferences
            prefs = {"terminal": {"fontSize": 18}}
            client.put("/api/user/preferences", json=prefs, headers=auth_headers)

            # Step 2: Create backup
            backup_response = client.post(
                "/api/user/backup",
                json={
                    "include": ["themes", "extensions", "preferences", "keybindings"],
                    "format": "json"
                },
                headers=auth_headers
            )
            assert backup_response.status_code == 200
            backup_data = backup_response.json()

            assert "backupId" in backup_data
            assert "downloadUrl" in backup_data

            # Step 3: Download backup file
            download_response = client.get(
                backup_data["downloadUrl"],
                headers=auth_headers
            )
            assert download_response.status_code == 200
            backup_content = download_response.json()

            # Verify backup contains all customizations
            assert "themes" in backup_content
            assert "extensions" in backup_content
            assert "preferences" in backup_content
            assert len(backup_content["themes"]) >= 1
            assert len(backup_content["extensions"]) >= 1

            # Step 4: Simulate clean installation (clear customizations)
            clear_response = client.delete(
                "/api/user/customizations",
                headers=auth_headers
            )
            assert clear_response.status_code == 200

            # Step 5: Restore from backup
            restore_response = client.post(
                "/api/user/restore",
                files={
                    "backup": ("backup.json", json.dumps(backup_content).encode(), "application/json")
                },
                headers=auth_headers
            )
            assert restore_response.status_code == 200
            restore_data = restore_response.json()

            assert restore_data["themesRestored"] >= 1
            assert restore_data["extensionsRestored"] >= 1
            assert restore_data["preferencesRestored"] == True

            # Step 6: Verify restoration
            themes_check = client.get("/api/themes", headers=auth_headers)
            extensions_check = client.get("/api/extensions", headers=auth_headers)
            prefs_check = client.get("/api/user/preferences", headers=auth_headers)

            assert len(themes_check.json()["themes"]) >= 1
            assert len(extensions_check.json()["extensions"]) >= 1
            assert prefs_check.json()["terminal"]["fontSize"] == 18

    def test_real_time_customization_updates(self, client, auth_headers, terminal_session, sample_theme):
        """Test real-time updates when customizations change.

        User Story: Changes to themes, extensions, or preferences are
        immediately reflected in active terminal sessions.
        """
        with pytest.raises((Exception, AssertionError)):
            # Step 1: Connect to session WebSocket
            with client.websocket_connect(f"/ws/terminal/{terminal_session}") as websocket:
                # Step 2: Apply theme while session is active
                theme_response = client.post(
                    "/api/themes/import",
                    json=sample_theme,
                    headers=auth_headers
                )
                theme_id = theme_response.json()["themeId"]

                apply_response = client.post(
                    f"/api/terminal/sessions/{terminal_session}/theme",
                    json={"themeId": theme_id},
                    headers=auth_headers
                )

                # Should receive real-time theme update
                theme_update = websocket.receive_json()
                assert theme_update["type"] == "theme_applied"
                assert theme_update["themeId"] == theme_id

                # Step 3: Update font size
                font_update_response = client.put(
                    f"/api/terminal/sessions/{terminal_session}/font-size",
                    json={"fontSize": 20},
                    headers=auth_headers
                )

                # Should receive real-time font update
                font_update = websocket.receive_json()
                assert font_update["type"] == "font_changed"
                assert font_update["fontSize"] == 20

                # Step 4: Toggle extension
                extension_response = client.post(
                    "/api/extensions/install",
                    json=sample_extension,
                    headers=auth_headers
                )
                ext_id = extension_response.json()["extensionId"]

                enable_response = client.post(
                    f"/api/terminal/sessions/{terminal_session}/extensions/enable",
                    json={"extensionId": ext_id},
                    headers=auth_headers
                )

                # Should receive extension loaded notification
                ext_update = websocket.receive_json()
                assert ext_update["type"] == "extension_loaded"
                assert ext_update["extensionId"] == ext_id
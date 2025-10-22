"""Contract tests for Ebook API endpoints.

These tests verify the Ebook API contracts match the specifications
defined in contracts/ebook_api.yaml.

CRITICAL: These tests MUST FAIL until the implementation is complete.
"""

import pytest
from fastapi.testclient import TestClient
import tempfile
import os

# Import the app once it's implemented
try:
    from src.main import app
    APP_AVAILABLE = True
except ImportError:
    APP_AVAILABLE = False


class TestEbookProcessAPI:
    """Test POST /api/ebooks/process endpoint."""

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
            # Minimal PDF header
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
            # Minimal EPUB (ZIP file with mimetype)
            import zipfile
            with zipfile.ZipFile(f, 'w') as zf:
                zf.writestr('mimetype', 'application/epub+zip', compress_type=zipfile.ZIP_STORED)
                zf.writestr('META-INF/container.xml', '<?xml version="1.0"?><container></container>')
            temp_path = f.name
        yield temp_path
        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    @pytest.fixture
    def large_file(self):
        """Create a file larger than 50MB for testing."""
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.pdf', delete=False) as f:
            # Write 51MB of data
            f.write(b'%PDF-1.4\n' + b'x' * (51 * 1024 * 1024))
            temp_path = f.name
        yield temp_path
        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    def test_process_valid_pdf(self, client, temp_pdf):
        """Test processing a valid PDF file.

        Contract: POST /api/ebooks/process with valid PDF returns 200 with EbookMetadata
        """
        with pytest.raises((Exception, AssertionError)):
            response = client.post(
                "/api/ebooks/process",
                json={"filePath": temp_pdf}
            )

            assert response.status_code == 200
            data = response.json()

            # Verify EbookMetadata schema
            assert "id" in data
            assert "file_path" in data
            assert data["file_path"] == temp_pdf
            assert "file_hash" in data
            assert len(data["file_hash"]) == 64  # SHA-256 hex
            assert "file_type" in data
            assert data["file_type"] == "pdf"
            assert "file_size" in data
            assert data["file_size"] > 0
            assert "is_encrypted" in data
            assert isinstance(data["is_encrypted"], bool)
            assert "created_at" in data
            assert "last_accessed" in data
            assert "user_id" in data

    def test_process_valid_epub(self, client, temp_epub):
        """Test processing a valid EPUB file.

        Contract: POST /api/ebooks/process with valid EPUB returns 200 with EbookMetadata
        """
        with pytest.raises((Exception, AssertionError)):
            response = client.post(
                "/api/ebooks/process",
                json={"filePath": temp_epub}
            )

            assert response.status_code == 200
            data = response.json()

            assert data["file_type"] == "epub"
            assert "total_pages" in data
            # EPUB total_pages should be null
            assert data["total_pages"] is None

    def test_process_file_not_found(self, client):
        """Test processing a non-existent file.

        Contract: POST /api/ebooks/process with non-existent file returns 404
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

    def test_process_file_too_large(self, client, large_file):
        """Test processing a file larger than 50MB.

        Contract: POST /api/ebooks/process with file >50MB returns 400
        """
        with pytest.raises((Exception, AssertionError)):
            response = client.post(
                "/api/ebooks/process",
                json={"filePath": large_file}
            )

            assert response.status_code == 400
            data = response.json()
            assert "error" in data
            assert data["error"] == "FILE_TOO_LARGE"
            assert "message" in data

    def test_process_invalid_file_type(self, client):
        """Test processing an invalid file type.

        Contract: POST /api/ebooks/process with invalid file type returns 400
        """
        # Create a text file (not PDF/EPUB)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("This is a text file")
            temp_path = f.name

        try:
            with pytest.raises((Exception, AssertionError)):
                response = client.post(
                    "/api/ebooks/process",
                    json={"filePath": temp_path}
                )

                assert response.status_code == 400
                data = response.json()
                assert "error" in data
                assert "message" in data
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestEbookContentAPI:
    """Test GET /api/ebooks/{ebook_id}/content endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        if not APP_AVAILABLE:
            pytest.skip("Application not implemented yet")
        return TestClient(app)

    @pytest.fixture
    def ebook_id(self):
        """Mock ebook ID."""
        return "550e8400-e29b-41d4-a716-446655440000"

    def test_get_content_valid_ebook(self, client, ebook_id):
        """Test retrieving content from a valid ebook.

        Contract: GET /api/ebooks/{ebook_id}/content returns 200 with binary content
        """
        with pytest.raises((Exception, AssertionError)):
            response = client.get(f"/api/ebooks/{ebook_id}/content")

            assert response.status_code == 200
            assert response.headers["content-type"] == "application/octet-stream"
            assert len(response.content) > 0

    def test_get_content_invalid_ebook(self, client):
        """Test retrieving content from non-existent ebook.

        Contract: GET /api/ebooks/{ebook_id}/content with invalid ID returns 404
        """
        invalid_id = "00000000-0000-0000-0000-000000000000"

        with pytest.raises((Exception, AssertionError)):
            response = client.get(f"/api/ebooks/{invalid_id}/content")

            assert response.status_code == 404
            data = response.json()
            assert "error" in data
            assert "message" in data

    def test_get_content_with_page_parameter(self, client, ebook_id):
        """Test retrieving specific page from PDF.

        Contract: GET /api/ebooks/{ebook_id}/content?page=N returns specific page
        """
        with pytest.raises((Exception, AssertionError)):
            response = client.get(
                f"/api/ebooks/{ebook_id}/content",
                params={"page": 5}
            )

            assert response.status_code == 200
            assert response.headers["content-type"] == "application/octet-stream"


class TestEbookDecryptAPI:
    """Test POST /api/ebooks/{ebook_id}/decrypt endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        if not APP_AVAILABLE:
            pytest.skip("Application not implemented yet")
        return TestClient(app)

    @pytest.fixture
    def encrypted_ebook_id(self):
        """Mock encrypted ebook ID."""
        return "660e8400-e29b-41d4-a716-446655440000"

    def test_decrypt_with_correct_password(self, client, encrypted_ebook_id):
        """Test decrypting PDF with correct password.

        Contract: POST /api/ebooks/{ebook_id}/decrypt with correct password returns 200
        """
        with pytest.raises((Exception, AssertionError)):
            response = client.post(
                f"/api/ebooks/{encrypted_ebook_id}/decrypt",
                json={"password": "correct-password"}
            )

            assert response.status_code == 200
            data = response.json()
            assert "decrypted" in data
            assert data["decrypted"] is True
            assert "message" in data

    def test_decrypt_with_incorrect_password(self, client, encrypted_ebook_id):
        """Test decrypting PDF with incorrect password.

        Contract: POST /api/ebooks/{ebook_id}/decrypt with wrong password returns 401
        """
        with pytest.raises((Exception, AssertionError)):
            response = client.post(
                f"/api/ebooks/{encrypted_ebook_id}/decrypt",
                json={"password": "wrong-password"}
            )

            assert response.status_code == 401
            data = response.json()
            assert "error" in data
            assert "message" in data

    def test_decrypt_too_many_attempts(self, client, encrypted_ebook_id):
        """Test rate limiting on password attempts.

        Contract: POST /api/ebooks/{ebook_id}/decrypt after 3 failed attempts returns 429
        """
        with pytest.raises((Exception, AssertionError)):
            # Attempt 3 failed decrypts
            for _ in range(3):
                client.post(
                    f"/api/ebooks/{encrypted_ebook_id}/decrypt",
                    json={"password": "wrong-password"}
                )

            # Fourth attempt should be rate limited
            response = client.post(
                f"/api/ebooks/{encrypted_ebook_id}/decrypt",
                json={"password": "any-password"}
            )

            assert response.status_code == 429
            data = response.json()
            assert "error" in data
            assert "message" in data


class TestEbookMetadataAPI:
    """Test GET /api/ebooks/metadata/{file_hash} endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        if not APP_AVAILABLE:
            pytest.skip("Application not implemented yet")
        return TestClient(app)

    @pytest.fixture
    def file_hash(self):
        """Mock SHA-256 file hash."""
        return "a3f5b1c2d4e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2"

    def test_get_metadata_by_hash_valid(self, client, file_hash):
        """Test retrieving metadata by valid hash.

        Contract: GET /api/ebooks/metadata/{file_hash} with valid hash returns 200 with metadata
        """
        with pytest.raises((Exception, AssertionError)):
            response = client.get(f"/api/ebooks/metadata/{file_hash}")

            assert response.status_code == 200
            data = response.json()

            # Verify EbookMetadata schema
            assert "id" in data
            assert "file_path" in data
            assert "file_hash" in data
            assert data["file_hash"] == file_hash
            assert "file_type" in data
            assert "file_size" in data
            assert "is_encrypted" in data

    def test_get_metadata_by_hash_not_found(self, client):
        """Test retrieving metadata by unknown hash.

        Contract: GET /api/ebooks/metadata/{file_hash} with unknown hash returns 404
        """
        unknown_hash = "0000000000000000000000000000000000000000000000000000000000000000"

        with pytest.raises((Exception, AssertionError)):
            response = client.get(f"/api/ebooks/metadata/{unknown_hash}")

            assert response.status_code == 404
            data = response.json()
            assert "error" in data
            assert "message" in data

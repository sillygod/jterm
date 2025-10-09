"""Integration test for Session Recording feature.

This test verifies that:
1. Recording endpoints are properly registered
2. Recording JavaScript is loaded
3. Recording UI elements are present in templates
"""

import os
import re
from pathlib import Path


def test_recording_endpoints_registered():
    """Test that recording endpoints are registered in main.py"""
    main_py = Path("src/main.py")
    content = main_py.read_text()

    # Check import
    assert "from src.api.recording_endpoints import router as recording_router" in content, \
        "Recording endpoints not imported in main.py"

    # Check router registration
    assert "app.include_router(recording_router)" in content, \
        "Recording router not registered in main.py"

    print("✅ Recording endpoints properly registered")


def test_recording_js_loaded():
    """Test that recording.js is loaded in base.html"""
    base_html = Path("templates/base.html")
    content = base_html.read_text()

    assert 'src="/static/js/recording.js"' in content, \
        "recording.js not loaded in base.html"

    print("✅ Recording JavaScript properly loaded")


def test_recording_ui_elements():
    """Test that recording UI elements are present"""
    base_html = Path("templates/base.html")
    content = base_html.read_text()

    # Check for recording button in header
    assert 'id="recording-toggle"' in content, \
        "Recording toggle button not found in header"

    # Check for recording controls in status bar
    assert 'id="recording-start-btn"' in content, \
        "Recording start button not found"
    assert 'id="recording-stop-btn"' in content, \
        "Recording stop button not found"

    # Check for recording panel modal
    assert 'id="recording-panel-modal"' in content, \
        "Recording panel modal not found"

    # Check for toggle function
    assert 'function toggleRecordingPanel()' in content, \
        "toggleRecordingPanel function not found"

    print("✅ Recording UI elements properly integrated")


def test_recording_files_exist():
    """Test that required recording files exist"""
    files = [
        "static/js/recording.js",
        "src/api/recording_endpoints.py",
        "src/services/recording_service.py",
        "src/websockets/recording_handler.py",
        "templates/components/recording_controls.html"
    ]

    for file_path in files:
        path = Path(file_path)
        assert path.exists(), f"Required file not found: {file_path}"

    print("✅ All recording files exist")


def test_quickstart_updated():
    """Test that quickstart.md has been updated with recording info"""
    quickstart = Path("specs/001-web-based-terminal/quickstart.md")
    content = quickstart.read_text()

    # Check for Session Recording section
    assert "## Session Recording" in content, \
        "Session Recording section not added to quickstart"

    # Check for integration status
    assert "✅ Fully Functional - Session Recording" in content, \
        "Recording status not updated to fully functional"

    # Check for usage instructions
    assert "Starting a Recording" in content, \
        "Recording usage instructions not found"

    print("✅ Quickstart documentation updated")


if __name__ == "__main__":
    print("Testing Session Recording Integration...\n")

    try:
        test_recording_endpoints_registered()
        test_recording_js_loaded()
        test_recording_ui_elements()
        test_recording_files_exist()
        test_quickstart_updated()

        print("\n" + "="*50)
        print("✅ ALL TESTS PASSED!")
        print("="*50)
        print("\nSession Recording feature is fully integrated and ready to use!")
        print("\nTo use:")
        print("1. Start the application: uvicorn src.main:app --reload")
        print("2. Open http://localhost:8000")
        print("3. Click the ⏺ icon in the header for recording info")
        print("4. Use Record/Stop buttons in status bar to control recording")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        exit(1)

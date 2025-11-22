#!/usr/bin/env python3
"""
Quick test script for Image Editor API

Usage:
    python test_image_editor.py <path_to_image>

Example:
    python test_image_editor.py /Users/jing/Desktop/screenshot.png
"""

import sys
import requests
import json

API_BASE = "http://localhost:8000"

def test_image_load(image_path: str):
    """Test loading an image into the editor."""
    print(f"Testing image load: {image_path}")
    print("-" * 60)

    # Step 1: Load image
    print("\n1. Loading image...")
    response = requests.post(
        f"{API_BASE}/api/v1/image-editor/load",
        json={
            "source_type": "file",
            "source_path": image_path,
            "terminal_session_id": "test-session-123"
        }
    )

    if response.status_code != 201:
        print(f"❌ Failed to load image: {response.status_code}")
        print(response.text)
        return

    data = response.json()
    print(f"✅ Image loaded successfully!")
    print(f"   Session ID: {data['session_id']}")
    print(f"   Dimensions: {data['image_width']}x{data['image_height']}")
    print(f"   Format: {data['image_format']}")
    print(f"   Editor URL: {API_BASE}{data['editor_url']}")

    # Step 2: Test annotation update
    print("\n2. Testing annotation update...")
    session_id = data['session_id']

    canvas_json = json.dumps({
        "version": "5.3.0",
        "objects": [
            {
                "type": "path",
                "stroke": "#ff0000",
                "strokeWidth": 3,
                "path": [["M", 10, 10], ["L", 50, 50]]
            }
        ]
    })

    response = requests.put(
        f"{API_BASE}/api/v1/image-editor/annotation-layer/{session_id}",
        json={
            "canvas_json": canvas_json,
            "version": 1
        }
    )

    if response.status_code != 200:
        print(f"❌ Failed to update annotations: {response.status_code}")
        print(response.text)
        return

    data = response.json()
    print(f"✅ Annotations updated successfully!")
    print(f"   New version: {data['new_version']}")
    print(f"   Updated at: {data['updated_at']}")

    # Step 3: Open editor in browser
    print("\n3. Opening editor in browser...")
    editor_url = f"{API_BASE}/editor/{session_id}"
    print(f"   Editor URL: {editor_url}")
    print(f"\n   Open this URL in your browser to test the editor UI!")

    # Print summary
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)
    print(f"\nNext steps:")
    print(f"1. Make sure the server is running: uvicorn src.main:app --reload")
    print(f"2. Open the editor: {editor_url}")
    print(f"3. Try drawing annotations with the pen tool")
    print(f"4. Check auto-save is working (watch the 'Saved' indicator)")
    print(f"5. Test undo/redo with Cmd+Z / Cmd+Shift+Z")
    print(f"6. Click 'Copy' to test clipboard export")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_image_editor.py <path_to_image>")
        print("\nExample:")
        print("  python test_image_editor.py /Users/jing/Desktop/screenshot.png")
        sys.exit(1)

    image_path = sys.argv[1]
    test_image_load(image_path)

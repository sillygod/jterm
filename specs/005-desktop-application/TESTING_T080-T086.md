# Manual Testing Guide: T080-T086 (Image Editor Testing)

**Feature**: Desktop Application - Image Editor Integration
**Date**: 2025-12-30
**Tasks**: T080-T086 (User Story 5 - Image Editing with Native Tools)

---

## Prerequisites

Before starting these tests, ensure:
1. ✅ Desktop application builds successfully (`cargo tauri dev` or built DMG/MSI)
2. ✅ Python backend is running (bundled or standalone)
3. ✅ T001-T079 are complete (foundational setup, clipboard commands implemented)
4. ✅ You have test images available (PNG, JPEG, GIF, etc.)
5. ✅ System clipboard tools available:
   - **macOS**: Preview.app
   - **Windows**: Paint, Paint 3D
   - **Linux**: GIMP, Kolourpaint

---

## T080: Test Clipboard Copy

**Goal**: Verify that editing an image in jterm and copying it to the clipboard works correctly, and the edited image can be pasted in external applications.

### Test Steps

1. **Start jterm desktop application**
   ```bash
   cargo tauri dev
   # Or launch the built application (DMG/MSI/AppImage)
   ```

2. **Load an image for editing**
   ```bash
   imgcat /path/to/test-image.png
   ```
   - Expected: Image editor UI appears with the image loaded
   - Expected: Canvas shows the original image
   - Expected: Drawing tools toolbar is visible

3. **Make edits to the image**
   - Click "Pen" tool
   - Draw some freehand lines on the image
   - Change color to blue (#0000ff)
   - Draw more lines
   - Add text: Click "Text" tool, click on canvas, type "Test Edit"
   - Add a shape: Click "Rectangle" tool, draw a rectangle

4. **Copy to clipboard**
   - Click the "Copy to Clipboard" button in the editor toolbar
   - Expected: Success message appears: "Copied to clipboard! Ready to paste in other applications."
   - Expected: Console log shows: `[ImageEditor] Successfully copied to clipboard via Tauri`

5. **Paste in external application (macOS)**
   ```bash
   # Open Preview
   open -a Preview
   # In Preview: File > New from Clipboard (Cmd+N)
   ```
   - Expected: Preview shows the edited image with all annotations (lines, text, rectangle)
   - Expected: Image dimensions match the original
   - Expected: All edits are visible and rendered correctly

6. **Paste in external application (Windows)**
   ```powershell
   # Open Paint
   start mspaint
   # In Paint: Ctrl+V to paste
   ```
   - Expected: Paint shows the edited image with all annotations
   - Expected: Image dimensions match the original
   - Expected: All edits are visible and rendered correctly

7. **Paste in external application (Linux)**
   ```bash
   # Open GIMP
   gimp
   # In GIMP: File > Create > From Clipboard
   ```
   - Expected: GIMP shows the edited image with all annotations
   - Expected: Image dimensions match the original
   - Expected: All edits are visible and rendered correctly

8. **Test clipboard copy from clipboard-loaded image**
   ```bash
   # First, copy an image to clipboard using external app
   # macOS: Open image in Preview, Cmd+A, Cmd+C
   # Windows: Open image in Paint, Ctrl+A, Ctrl+C
   # Linux: Open image in GIMP, Select All, Copy

   # Then load from clipboard in jterm
   imgcat --clipboard
   ```
   - Expected: Image loads from clipboard successfully
   - Expected: Editor UI appears

   ```bash
   # Make edits (draw, add text, etc.)
   # Click "Copy to Clipboard"
   ```
   - Expected: Success message: "Copied edited image back to clipboard! Ready to paste."
   - Expected: Pasting in external app shows the edited version with all annotations

### Success Criteria
- ✅ Edited images copy to clipboard successfully
- ✅ Pasted images in external apps show all annotations correctly
- ✅ Image dimensions are preserved
- ✅ Different source types (file vs clipboard) show appropriate success messages
- ✅ Console logs confirm Tauri clipboard API is used (not browser API)

### Error Cases to Test
- **No edits made**: Copy unedited image to clipboard → should work
- **Large image (>4096px)**: Copy to clipboard → should downsample if needed
- **Multiple annotations**: Draw 10+ objects → copy → all should appear in paste

---

## T081: Verify Image Editor Service Works with Desktop Paths

**Goal**: Verify that the Python image editor service correctly handles platform-specific absolute paths in desktop mode.

### Test Steps

1. **Test with absolute path (macOS)**
   ```bash
   imgcat /Users/username/Pictures/test-image.png
   ```
   - Expected: Image loads successfully
   - Expected: Session record in database uses absolute path
   - Check database:
     ```bash
     sqlite3 ~/Library/Application\ Support/jterm/webterminal.db
     SELECT source_path FROM image_sessions ORDER BY created_at DESC LIMIT 1;
     ```
   - Expected: Shows `/Users/username/Pictures/test-image.png`

2. **Test with absolute path (Windows)**
   ```powershell
   imgcat "C:\Users\username\Pictures\test-image.png"
   ```
   - Expected: Image loads successfully
   - Check database:
     ```powershell
     sqlite3 "%APPDATA%\jterm\webterminal.db"
     SELECT source_path FROM image_sessions ORDER BY created_at DESC LIMIT 1;
     ```
   - Expected: Shows `C:\Users\username\Pictures\test-image.png`

3. **Test with absolute path (Linux)**
   ```bash
   imgcat /home/username/Pictures/test-image.png
   ```
   - Expected: Image loads successfully
   - Check database:
     ```bash
     sqlite3 ~/.local/share/jterm/webterminal.db
     SELECT source_path FROM image_sessions ORDER BY created_at DESC LIMIT 1;
     ```
   - Expected: Shows `/home/username/Pictures/test-image.png`

4. **Test with URL**
   ```bash
   imgcat https://picsum.photos/800/600
   ```
   - Expected: Image loads from URL
   - Expected: Session record shows URL as source_path
   - Expected: Temporary file is created in platform-specific temp directory

5. **Test clipboard source**
   ```bash
   imgcat --clipboard
   ```
   - Expected: Image loads from clipboard
   - Expected: Session record shows `source_type = 'clipboard'`
   - Expected: `source_path` is NULL or temporary file path

6. **Test saving edited image**
   ```bash
   # Load image, make edits, click "Save" button
   # Check that saved file path uses platform-specific directory
   ```
   - Expected: Saved file appears in correct platform directory
   - Expected: File permissions are correct

### Success Criteria
- ✅ All path types (absolute, URL, clipboard) work correctly
- ✅ Database records show correct platform-specific paths
- ✅ No path validation errors (traversal, permission issues)
- ✅ Temporary files created in platform-specific temp directories

---

## T082: Test Drawing Tools

**Goal**: Verify that all drawing tools (pen, arrow, text, shapes) work correctly with customization options.

### Test Steps

1. **Test Pen Tool**
   ```bash
   imgcat /path/to/test-image.png
   ```
   - Click "Pen" tool
   - Draw freehand lines on canvas
   - Expected: Lines appear smoothly as you draw

   - Change stroke width to 1
   - Draw thin lines
   - Expected: Lines are 1px wide

   - Change stroke width to 10
   - Draw thick lines
   - Expected: Lines are 10px wide

   - Change color to red (#ff0000)
   - Draw red lines
   - Expected: Lines are red

   - Change color to blue (#0000ff)
   - Draw blue lines
   - Expected: Lines are blue

2. **Test Arrow Tool**
   - Click "Arrow" tool
   - Draw arrow from point A to point B
   - Expected: Arrow appears with arrowhead pointing to B

   - Change arrow color to green (#00ff00)
   - Draw green arrow
   - Expected: Arrow is green

   - Change stroke width to 5
   - Draw thick arrow
   - Expected: Arrow stroke is 5px wide

3. **Test Text Tool**
   - Click "Text" tool
   - Click on canvas at specific location
   - Type "Hello World"
   - Expected: Text input dialog appears
   - Expected: Text "Hello World" appears on canvas

   - Change font size to 24
   - Add new text "Large Text"
   - Expected: Text is larger (24px)

   - Change font size to 12
   - Add new text "Small Text"
   - Expected: Text is smaller (12px)

   - Enable bold
   - Add new text "Bold Text"
   - Expected: Text is bold

   - Enable italic
   - Add new text "Italic Text"
   - Expected: Text is italicized

   - Change text color to red
   - Add new text "Red Text"
   - Expected: Text is red

4. **Test Rectangle Tool**
   - Click "Rectangle" tool
   - Disable fill
   - Draw rectangle (drag from corner to corner)
   - Expected: Rectangle outline appears (no fill)

   - Enable fill
   - Set fill color to rgba(255, 0, 0, 0.3) (semi-transparent red)
   - Draw filled rectangle
   - Expected: Rectangle has red semi-transparent fill + stroke

   - Change stroke color to blue
   - Draw blue outlined rectangle
   - Expected: Rectangle outline is blue

5. **Test Circle Tool**
   - Click "Circle" tool
   - Disable fill
   - Draw circle (drag from center)
   - Expected: Circle outline appears

   - Enable fill
   - Set fill color to rgba(0, 255, 0, 0.5) (semi-transparent green)
   - Draw filled circle
   - Expected: Circle has green semi-transparent fill + stroke

6. **Test Line Tool**
   - Click "Line" tool
   - Draw straight line from point A to point B
   - Expected: Straight line appears

   - Change stroke width to 8
   - Change color to purple (#800080)
   - Draw thick purple line
   - Expected: Line is thick and purple

### Success Criteria
- ✅ All 6 drawing tools work (pen, arrow, text, rectangle, circle, line)
- ✅ Stroke width customization works (1px to 10px)
- ✅ Color customization works (any hex color)
- ✅ Fill enable/disable works for shapes
- ✅ Fill color customization works (supports rgba transparency)
- ✅ Text font size works (12px to 48px)
- ✅ Text bold/italic styling works
- ✅ All drawings render correctly on canvas

---

## T083: Test Filters

**Goal**: Verify that image filters (blur, sharpen, brightness, contrast, saturation) work correctly with real-time preview.

### Test Steps

1. **Test Blur Filter**
   ```bash
   imgcat /path/to/test-image.png
   ```
   - Click "Filters" dropdown
   - Select "Blur"
   - Expected: Blur strength slider appears (default: 50)

   - Move slider to 0
   - Expected: Image appears sharp (no blur)

   - Move slider to 100
   - Expected: Image is heavily blurred

   - Move slider to 50
   - Click "Apply"
   - Expected: Blur filter is applied permanently
   - Expected: Canvas shows blurred image

2. **Test Sharpen Filter**
   - Click "Filters" → "Sharpen"
   - Expected: Sharpen strength slider appears

   - Move slider to 100
   - Expected: Image edges are sharpened (enhanced)

   - Click "Apply"
   - Expected: Sharpen filter applied

3. **Test Brightness Filter**
   - Click "Filters" → "Brightness"
   - Expected: Brightness slider appears (range: -100 to +100)

   - Move slider to -50
   - Expected: Image becomes darker

   - Move slider to +50
   - Expected: Image becomes brighter

   - Move slider to 0
   - Expected: Image returns to original brightness

   - Move slider to +30
   - Click "Apply"
   - Expected: Brightness increased by 30%

4. **Test Contrast Filter**
   - Click "Filters" → "Contrast"
   - Expected: Contrast slider appears (range: -100 to +100)

   - Move slider to -50
   - Expected: Image contrast decreases (looks washed out)

   - Move slider to +50
   - Expected: Image contrast increases (darker darks, lighter lights)

   - Click "Apply"
   - Expected: Contrast filter applied

5. **Test Saturation Filter**
   - Click "Filters" → "Saturation"
   - Expected: Saturation slider appears (range: -100 to +100)

   - Move slider to -100
   - Expected: Image becomes grayscale (no color)

   - Move slider to 0
   - Expected: Image returns to normal saturation

   - Move slider to +100
   - Expected: Image colors are highly saturated (vivid)

   - Click "Apply"
   - Expected: Saturation filter applied

6. **Test Multiple Filters**
   - Apply Brightness +20
   - Apply Contrast +30
   - Apply Saturation +10
   - Apply Blur 20
   - Expected: All filters combine correctly
   - Expected: Image shows cumulative effect of all filters

7. **Test Filter Reset**
   - Click "Reset Filters" button
   - Expected: All filters reset to default (original image restored)
   - Expected: Any applied filters are removed

### Success Criteria
- ✅ All 5 filters work (blur, sharpen, brightness, contrast, saturation)
- ✅ Real-time preview updates as slider moves
- ✅ Filter ranges are correct (blur: 0-100, brightness/contrast/saturation: -100 to +100)
- ✅ Multiple filters can be applied sequentially
- ✅ "Apply" button commits filter changes
- ✅ "Reset" button removes all filters and restores original
- ✅ Filters work on images loaded from file, URL, and clipboard

---

## T084: Test Undo/Redo with 50-Operation Circular Buffer

**Goal**: Verify that undo/redo functionality works correctly with a 50-operation circular buffer.

### Test Steps

1. **Test Basic Undo**
   ```bash
   imgcat /path/to/test-image.png
   ```
   - Draw a red line (operation 1)
   - Draw a blue circle (operation 2)
   - Draw green text "Test" (operation 3)
   - Expected: 3 objects on canvas

   - Click "Undo" button (or Cmd/Ctrl+Z)
   - Expected: Green text disappears
   - Expected: 2 objects remain (red line, blue circle)

   - Click "Undo" again
   - Expected: Blue circle disappears
   - Expected: 1 object remains (red line)

   - Click "Undo" again
   - Expected: Red line disappears
   - Expected: Canvas shows only original image (no annotations)

2. **Test Basic Redo**
   - Click "Redo" button (or Cmd/Ctrl+Shift+Z)
   - Expected: Red line reappears

   - Click "Redo" again
   - Expected: Blue circle reappears

   - Click "Redo" again
   - Expected: Green text reappears
   - Expected: All 3 objects visible

3. **Test Undo/Redo Limits**
   - Click "Undo" 3 times (all annotations removed)
   - Click "Undo" again
   - Expected: Nothing happens (already at initial state)
   - Expected: "Undo" button becomes disabled

   - Click "Redo" 3 times (all annotations restored)
   - Click "Redo" again
   - Expected: Nothing happens (already at latest state)
   - Expected: "Redo" button becomes disabled

4. **Test Redo Stack Clearing**
   - Draw 3 objects (operations 1-3)
   - Undo 2 times (back to operation 1)
   - Expected: Redo stack has 2 operations

   - Draw a new object (operation 2b - different from original operation 2)
   - Expected: Redo stack is cleared
   - Expected: Cannot redo original operations 2 and 3
   - Expected: Can only undo to operation 1, then to initial state

5. **Test 50-Operation Circular Buffer**
   ```javascript
   // In browser console (or via script)
   const editor = window.ImageEditor.instances[sessionId];

   // Perform 60 operations
   for (let i = 0; i < 60; i++) {
       editor.drawingTools.addText(`Text ${i}`, 50 + i * 5, 50);
   }
   ```
   - Expected: 60 text objects on canvas

   - Click "Undo" 50 times
   - Expected: Can undo last 50 operations (operations 11-60)
   - Expected: Operations 1-10 are lost (circular buffer overflow)
   - Expected: Canvas shows text objects 1-10

   - Click "Undo" again
   - Expected: Nothing happens (undo stack exhausted)
   - Expected: Cannot undo beyond 50 operations

6. **Test Undo/Redo with Filters**
   - Draw a line (operation 1)
   - Apply brightness filter (operation 2)
   - Draw a circle (operation 3)
   - Apply blur filter (operation 4)

   - Undo (operation 4 removed)
   - Expected: Blur filter is unapplied

   - Undo (operation 3 removed)
   - Expected: Circle disappears

   - Undo (operation 2 removed)
   - Expected: Brightness filter is unapplied

   - Undo (operation 1 removed)
   - Expected: Line disappears

   - Redo 4 times
   - Expected: All operations restored in order (line, brightness, circle, blur)

### Success Criteria
- ✅ Undo removes last operation correctly
- ✅ Redo restores undone operation correctly
- ✅ Undo/redo buttons disable when stack is exhausted
- ✅ New operations clear redo stack
- ✅ Circular buffer maintains max 50 operations
- ✅ Operations beyond 50 are lost (FIFO)
- ✅ Filters can be undone/redone like drawing operations
- ✅ Keyboard shortcuts work (Cmd/Ctrl+Z, Cmd/Ctrl+Shift+Z)

---

## T085: Test Session History

**Goal**: Verify that the last 20 images viewed/edited are accessible via `imgcat --history`.

### Test Steps

1. **View multiple images to build history**
   ```bash
   # View 25 different images
   imgcat image1.png
   # (close editor or load next image)
   imgcat image2.png
   imgcat image3.png
   # ... continue up to image25.png
   ```
   - Expected: Each image loads successfully
   - Expected: Session history is recorded in database

2. **Check session history**
   ```bash
   imgcat --history
   ```
   - Expected: Terminal shows list of last 20 images
   - Expected: List shows images 6-25 (most recent 20)
   - Expected: Images 1-5 are NOT shown (LRU eviction)
   - Expected: Each entry shows:
     ```
     1. /path/to/image25.png (last viewed: 2025-12-30 10:45)
     2. /path/to/image24.png (last viewed: 2025-12-30 10:44)
     ...
     20. /path/to/image6.png (last viewed: 2025-12-30 10:26)
     ```

3. **Re-edit a recent image from history**
   ```bash
   imgcat -e 1
   ```
   - Expected: Image editor opens with image25.png
   - Expected: Image loads successfully in edit mode

4. **Re-edit an older image from history**
   ```bash
   imgcat -e 15
   ```
   - Expected: Image editor opens with the 15th image in history
   - Expected: Image loads successfully

5. **Test history persistence across sessions**
   - Close jterm desktop application
   - Relaunch jterm
   ```bash
   imgcat --history
   ```
   - Expected: History persists (shows same 20 images)
   - Expected: Database retained history records

6. **Test history with edited images**
   ```bash
   imgcat image30.png
   # Make edits (draw, add text, apply filter)
   # Save or copy to clipboard

   imgcat --history
   ```
   - Expected: image30.png appears in history
   - Expected: Entry shows `(edited)` flag if modifications were made

7. **Test history cleanup (7-day retention)**
   ```bash
   # Manually update database to simulate old entries
   sqlite3 ~/Library/Application\ Support/jterm/webterminal.db
   UPDATE session_history SET last_viewed_at = datetime('now', '-8 days') WHERE image_path LIKE '%image6.png';

   # Trigger cleanup job (or wait for daily cleanup)
   # Then check history
   imgcat --history
   ```
   - Expected: image6.png is removed from history (older than 7 days)
   - Expected: Only entries within 7 days remain

### Success Criteria
- ✅ `imgcat --history` shows last 20 images
- ✅ LRU eviction works (oldest images removed when limit exceeded)
- ✅ `imgcat -e <index>` opens image from history in edit mode
- ✅ History persists across application restarts
- ✅ Edited images are flagged in history
- ✅ 7-day retention cleanup works correctly
- ✅ History is per-terminal session (not global across all sessions)

---

## T086: Test Export

**Goal**: Verify that edited images can be saved in multiple formats (PNG, JPEG, WebP, GIF, BMP).

### Test Steps

1. **Test PNG Export**
   ```bash
   imgcat test-image.png
   # Make edits (draw, add text, apply filter)
   # Click "Save" or "Export" button
   ```
   - Expected: Native file dialog appears (macOS: NSOpenPanel, Windows: File Explorer, Linux: GTK)
   - Select location: `~/Desktop/edited-image.png`
   - Click "Save"
   - Expected: File saved successfully
   - Expected: Success message: "Image saved to ~/Desktop/edited-image.png"

   - Verify saved file:
     ```bash
     ls -lh ~/Desktop/edited-image.png
     file ~/Desktop/edited-image.png
     ```
   - Expected: File exists
   - Expected: File type is PNG
   - Expected: File size is reasonable (not corrupted)

   - Open in external app:
     ```bash
     open ~/Desktop/edited-image.png  # macOS
     ```
   - Expected: Image opens in Preview/default viewer
   - Expected: All edits are visible (annotations, filters)

2. **Test JPEG Export**
   ```bash
   imgcat test-image.png
   # Make edits
   # Click "Save As" → Select format: "JPEG"
   ```
   - Save as `~/Desktop/edited-image.jpg`
   - Expected: File saved successfully

   - Verify:
     ```bash
     file ~/Desktop/edited-image.jpg
     ```
   - Expected: File type is JPEG
   - Open in external app
   - Expected: All edits visible (note: JPEG is lossy, some quality loss expected)

3. **Test WebP Export**
   ```bash
   imgcat test-image.png
   # Make edits
   # Click "Save As" → Select format: "WebP"
   ```
   - Save as `~/Desktop/edited-image.webp`
   - Expected: File saved successfully

   - Verify:
     ```bash
     file ~/Desktop/edited-image.webp
     ```
   - Expected: File type is WebP
   - Open in external app (browsers support WebP)
   - Expected: All edits visible

4. **Test GIF Export**
   ```bash
   imgcat test-image.png
   # Make edits
   # Click "Save As" → Select format: "GIF"
   ```
   - Save as `~/Desktop/edited-image.gif`
   - Expected: File saved successfully

   - Verify:
     ```bash
     file ~/Desktop/edited-image.gif
     ```
   - Expected: File type is GIF
   - Open in external app
   - Expected: All edits visible (note: GIF supports max 256 colors, some quality loss expected)

5. **Test BMP Export**
   ```bash
   imgcat test-image.png
   # Make edits
   # Click "Save As" → Select format: "BMP"
   ```
   - Save as `~/Desktop/edited-image.bmp`
   - Expected: File saved successfully

   - Verify:
     ```bash
     file ~/Desktop/edited-image.bmp
     ```
   - Expected: File type is BMP
   - Open in external app
   - Expected: All edits visible (BMP is lossless)

6. **Test Export with File Dialog Filters**
   - Click "Save As"
   - Expected: File dialog shows format filter dropdown
   - Expected: Available formats: PNG, JPEG, WebP, GIF, BMP
   - Select "JPEG"
   - Expected: Default extension changes to `.jpg`
   - Type filename without extension: `test-export`
   - Expected: System automatically adds `.jpg` extension
   - Save
   - Expected: File saved as `test-export.jpg`

7. **Test Export Overwrite Protection**
   ```bash
   # Save image as test.png
   # Make different edits
   # Try to save as test.png again
   ```
   - Expected: File dialog shows overwrite confirmation
   - Click "Cancel"
   - Expected: Original file is NOT overwritten
   - Click "Save" and confirm overwrite
   - Expected: Original file IS overwritten with new edits

8. **Test Export with Large Image (>4096px)**
   ```bash
   imgcat large-image-5000x5000.png
   # Make edits
   # Click "Save"
   ```
   - Expected: Image is downsampled to max 4096px (if needed)
   - Save as `large-export.png`
   - Verify:
     ```bash
     sips -g pixelWidth -g pixelHeight ~/Desktop/large-export.png  # macOS
     ```
   - Expected: Image dimensions ≤ 4096px (aspect ratio preserved)

### Success Criteria
- ✅ All 5 formats export correctly (PNG, JPEG, WebP, GIF, BMP)
- ✅ Native file dialog appears with format filters
- ✅ Default file extensions are set correctly per format
- ✅ Saved files can be opened in external applications
- ✅ All edits (annotations, filters) are preserved in exported files
- ✅ Overwrite protection works (confirmation dialog)
- ✅ Large images are downsampled appropriately
- ✅ Export works for images loaded from file, URL, and clipboard

---

## Test Summary Report Template

After completing all tests, fill out this summary:

```
=== T080-T086 Test Summary ===
Date: YYYY-MM-DD
Tester: [Your Name]
Platform: [macOS / Windows / Linux]
Build: [DMG / MSI / AppImage version]

T080: Clipboard Copy
[ ] PASS  [ ] FAIL  [ ] PARTIAL
Notes:

T081: Desktop Paths
[ ] PASS  [ ] FAIL  [ ] PARTIAL
Notes:

T082: Drawing Tools
[ ] PASS  [ ] FAIL  [ ] PARTIAL
Notes:

T083: Filters
[ ] PASS  [ ] FAIL  [ ] PARTIAL
Notes:

T084: Undo/Redo
[ ] PASS  [ ] FAIL  [ ] PARTIAL
Notes:

T085: Session History
[ ] PASS  [ ] FAIL  [ ] PARTIAL
Notes:

T086: Export
[ ] PASS  [ ] FAIL  [ ] PARTIAL
Notes:

=== Overall Result ===
[ ] ALL TESTS PASSED - Ready for T087+
[ ] SOME TESTS FAILED - Blockers identified below

Blockers/Issues:
1.
2.
3.

Next Steps:
-
```

---

## Troubleshooting

### Issue: Clipboard copy fails with "Failed to copy to clipboard using Tauri"

**Check**:
1. Verify Tauri clipboard plugin is installed: `grep tauri-plugin-clipboard src-tauri/Cargo.toml`
2. Check `src-tauri/tauri.conf.json` has clipboard permissions enabled
3. Check console logs for error details

**Fix**:
```bash
cd src-tauri
cargo add tauri-plugin-clipboard-manager
```

---

### Issue: Image editor doesn't load in desktop mode

**Check**:
1. Verify Python backend is running: `curl http://localhost:8000/health`
2. Check browser console for JavaScript errors
3. Verify Fabric.js loaded: `console.log(typeof fabric)`

**Fix**:
- Ensure `static/js/image-editor.js` is bundled correctly by PyInstaller
- Check PyInstaller `--add-data` flags include `static/`

---

### Issue: Filters don't apply or cause errors

**Check**:
1. Verify Pillow library is bundled: Check PyInstaller hidden imports
2. Check Python backend logs for filter processing errors

**Fix**:
```bash
# Add Pillow to PyInstaller spec
pyinstaller --hidden-import PIL ...
```

---

### Issue: Session history not persisting

**Check**:
1. Verify database path is correct for platform
2. Check database permissions: `ls -l ~/Library/Application\ Support/jterm/webterminal.db`
3. Query database directly:
   ```bash
   sqlite3 ~/Library/Application\ Support/jterm/webterminal.db
   SELECT COUNT(*) FROM session_history;
   ```

**Fix**:
- Ensure Python backend uses correct platform-specific database path
- Check `src/config.py` detects desktop mode correctly

---

## Notes

- These are **manual tests** - automated testing will be implemented in future tasks
- Screenshots should be taken for each test case to document results
- All test results should be recorded in the summary report template above
- If any test fails, mark the task as incomplete in `tasks.md` and create GitHub issue

---

**Ready to test!** Start with T080 and work through each test sequentially.

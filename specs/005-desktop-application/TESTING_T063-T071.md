# Testing Guide: T063-T071 - User Story 4: Inline Media Viewing

**Status**: T063-T065 ✅ VERIFIED | T066-T071 📝 MANUAL TESTING REQUIRED

## Completed Verification Tasks

### ✅ T063: Media Service Bundling
**Status**: VERIFIED
- **Location**: `src/services/media_service.py` (749 lines)
- **Bundling Method**: Automatic via `--collect-all src` in `scripts/build-python.sh`
- **Dependencies Included**:
  - PIL/Pillow (hidden imports: PIL, PIL.Image, PIL.ImageDraw, PIL.ImageFilter, PIL.ImageEnhance)
  - File validation, security scanning, thumbnail generation
- **Result**: ✅ Media service will be bundled correctly

### ✅ T064: Ebook Service Bundling
**Status**: VERIFIED
- **Location**: `src/services/ebook_service.py` (21KB)
- **Bundling Method**: Automatic via `--collect-all src` in `scripts/build-python.sh`
- **Dependencies**: PyPDF2/pypdf, ebooklib (imported conditionally)
- **Features**: PDF/EPUB validation, metadata extraction, password decryption, SHA-256 caching
- **Result**: ✅ Ebook service will be bundled correctly

### ✅ T065: Media API Endpoints Accessibility
**Status**: VERIFIED
- **Location**: `src/api/media_endpoints.py`
- **Router Registration**: Line 594 in `src/main.py` - `app.include_router(media_router)`
- **Endpoint Prefix**: `/api/v1/media`
- **Key Endpoints**:
  - `POST /api/v1/media/upload` - Upload media files
  - `GET /api/v1/media/{asset_id}` - Get media asset
  - `GET /api/v1/media/{asset_id}/file` - Serve media file
  - `GET /api/v1/media/{asset_id}/thumbnail` - Serve thumbnail
  - `DELETE /api/v1/media/{asset_id}` - Delete media asset
- **Result**: ✅ Endpoints will be accessible from Tauri WebView

---

## Manual Testing Tasks (T066-T071)

**Prerequisites**:
1. Desktop application must be built: `./scripts/build-python.sh && cargo tauri build`
2. Application must be running: `cargo tauri dev` (development) OR launch the built app
3. Test files must be available (see "Test File Preparation" below)

### Test File Preparation

Create a test directory with sample files:

```bash
mkdir -p ~/jterm-test-files
cd ~/jterm-test-files

# Test Image (small - should load <1s)
curl -o test-image-small.png https://via.placeholder.com/800x600.png

# Test Image (10MB - max size for images)
curl -o test-image-10mb.png https://picsum.photos/4000/3000

# Test Video (small MP4)
# Download a small sample video or use:
# ffmpeg -f lavfi -i testsrc=duration=10:size=1280x720:rate=30 -pix_fmt yuv420p test-video-small.mp4

# Test PDF (small)
curl -o test-pdf-small.pdf https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf

# Test EPUB (5MB - should load <2s)
# Download from Project Gutenberg or similar

# Large files for size limit testing (T071)
# Create 50MB video file
# dd if=/dev/urandom of=test-video-50mb.mp4 bs=1M count=50

# Create 11MB image (should be rejected - limit is 10MB)
# dd if=/dev/urandom of=test-image-11mb.png bs=1M count=11
```

---

### 📋 T066: Test Image Rendering with `imgcat`

**Objective**: Verify images display inline in <1 second

**Test Steps**:

1. **Launch Desktop App**:
   ```bash
   cargo tauri dev
   ```

2. **Test Small Image**:
   ```bash
   imgcat ~/jterm-test-files/test-image-small.png
   ```

   **Expected Result**:
   - ✅ Image renders inline in terminal
   - ✅ Loads in <1 second
   - ✅ Aspect ratio preserved
   - ✅ Image scrolls with terminal output

3. **Test 10MB Image (max size)**:
   ```bash
   imgcat ~/jterm-test-files/test-image-10mb.png
   ```

   **Expected Result**:
   - ✅ Image loads successfully
   - ✅ Loads in <1 second (downsampling may apply for large images)
   - ✅ No errors

4. **Test Image Formats**:
   Test multiple formats: PNG, JPEG, GIF, WebP, BMP
   ```bash
   imgcat test.png
   imgcat test.jpg
   imgcat test.gif
   imgcat test.webp
   imgcat test.bmp
   ```

**Acceptance Criteria**:
- [ ] Images display inline in terminal output
- [ ] Load time <1 second for typical images
- [ ] All supported formats render correctly
- [ ] Images maintain position when scrolling terminal

**Notes**:
- If images don't render, check browser console for errors
- Verify media service logs in Python backend
- Check that `src/api/media_endpoints.py` is accessible

---

### 📋 T067: Test Video Playback Controls

**Objective**: Verify HTML5 video controls work (play, pause, seek)

**Test Steps**:

1. **Test Small Video**:
   ```bash
   # Assuming a cat command for video exists (e.g., videocat or imgcat for video)
   imgcat ~/jterm-test-files/test-video-small.mp4
   ```

2. **Verify Video Controls**:
   - ✅ Click play button → video starts playing
   - ✅ Click pause button → video pauses
   - ✅ Drag seek bar → video jumps to position
   - ✅ Volume controls work
   - ✅ Fullscreen toggle works (if supported)

3. **Test Video Scrolling**:
   - Run several commands to push video up in terminal
   - Verify video player scrolls with content
   - Verify playback continues while scrolled

**Acceptance Criteria**:
- [ ] HTML5 video player loads
- [ ] All standard controls work (play, pause, seek, volume)
- [ ] Video maintains position when scrolling
- [ ] No playback issues or freezing

**Notes**:
- Video playback depends on browser codec support
- MP4/H.264 should work on all platforms
- WebM/VP9 may have platform-specific support

---

### 📋 T068: Test PDF Rendering with `bookcat`

**Objective**: Verify foliate-js loads and renders PDFs in <3s for 10MB files

**Test Steps**:

1. **Test Small PDF**:
   ```bash
   bookcat ~/jterm-test-files/test-pdf-small.pdf
   ```

   **Expected Result**:
   - ✅ PDF viewer opens inline
   - ✅ First page renders
   - ✅ Load time <3 seconds
   - ✅ Navigation controls work

2. **Test PDF Navigation**:
   - Click next page → advances to page 2
   - Click previous page → returns to page 1
   - Jump to specific page number
   - Search text (if supported by foliate-js)

3. **Test Password-Protected PDF** (if implemented):
   ```bash
   bookcat ~/jterm-test-files/test-pdf-encrypted.pdf
   ```

   **Expected Result**:
   - ✅ Password prompt appears
   - ✅ Correct password unlocks PDF
   - ✅ Incorrect password shows error

4. **Test 10MB PDF Performance**:
   - Load a 10MB PDF file
   - Measure load time (should be <3 seconds)
   - Verify smooth page navigation

**Acceptance Criteria**:
- [ ] PDF renders inline using foliate-js
- [ ] Load time <3 seconds for 10MB files
- [ ] Page navigation works smoothly
- [ ] Text selection/search works (if supported)
- [ ] Password-protected PDFs handled correctly

**Notes**:
- foliate-js is a JavaScript ebook reader library
- Verify `static/js/` contains foliate-js or CDN link
- Check ebook endpoints in `src/api/ebook_endpoints.py`

---

### 📋 T069: Test EPUB Rendering with `bookcat`

**Objective**: Verify EPUB pagination works in <2s for 5MB files

**Test Steps**:

1. **Test Small EPUB**:
   ```bash
   bookcat ~/jterm-test-files/test-book.epub
   ```

   **Expected Result**:
   - ✅ EPUB viewer opens inline
   - ✅ First chapter/section renders
   - ✅ Load time <2 seconds
   - ✅ Pagination controls work

2. **Test EPUB Navigation**:
   - Click next page → advances through content
   - Click previous page → goes back
   - Table of contents (if available)
   - Jump to specific chapter

3. **Test Text Formatting**:
   - Verify fonts render correctly
   - Check image embedding (if EPUB contains images)
   - Verify links work (internal and external)

4. **Test 5MB EPUB Performance**:
   - Load a 5MB EPUB file
   - Measure load time (should be <2 seconds)
   - Verify smooth navigation

**Acceptance Criteria**:
- [ ] EPUB renders inline using foliate-js
- [ ] Load time <2 seconds for 5MB files
- [ ] Pagination works smoothly
- [ ] Text formatting preserved
- [ ] Images embedded in EPUB display correctly

**Notes**:
- EPUB is essentially a zipped HTML file
- Verify ebooklib is included in PyInstaller bundle
- Check ebook service handles EPUB extraction

---

### 📋 T070: Test Media Viewer Scrolling Behavior

**Objective**: Verify media viewers scroll with terminal output and maintain position

**Test Steps**:

1. **Setup**:
   - Display an image: `imgcat test-image.png`
   - Display a video: `imgcat test-video.mp4`
   - Display a PDF: `bookcat test-document.pdf`

2. **Test Scrolling**:
   ```bash
   # Run commands that generate output
   ls -la
   cat large-file.txt
   echo "More content"
   echo "More content"
   echo "More content"
   ```

3. **Verify Behavior**:
   - ✅ Media viewers scroll up with new terminal output
   - ✅ Media viewers maintain their position in the output history
   - ✅ Scrolling back shows media in original position
   - ✅ No layout breaking or overlapping content

4. **Test Window Resize**:
   - Resize desktop window while media is displayed
   - Verify media reflows/resizes appropriately
   - Check that terminal output adjusts correctly

**Acceptance Criteria**:
- [ ] Media content scrolls naturally with terminal output
- [ ] Media position maintained when scrolling back
- [ ] No layout issues or content overlap
- [ ] Window resize handles media gracefully

**Notes**:
- This tests the HTMX/JavaScript integration
- Verify xterm.js and media viewers coordinate scrolling
- Check z-index and positioning CSS

---

### 📋 T071: Verify File Size Limit Enforcement

**Objective**: Ensure 50MB video, 10MB image, 50MB ebook limits are enforced

**Test Steps**:

1. **Test Image Size Limit (10MB max)**:
   ```bash
   # Should succeed (10MB is the limit)
   imgcat test-image-10mb.png

   # Should fail with error (11MB exceeds limit)
   imgcat test-image-11mb.png
   ```

   **Expected Result**:
   - ✅ 10MB image loads successfully
   - ✅ 11MB image rejected with error message
   - ✅ Error message: "File size exceeds 10MB limit for images"

2. **Test Video Size Limit (50MB max)**:
   ```bash
   # Should succeed
   imgcat test-video-50mb.mp4

   # Should fail (51MB exceeds limit)
   imgcat test-video-51mb.mp4
   ```

   **Expected Result**:
   - ✅ 50MB video loads successfully
   - ✅ 51MB video rejected with error message
   - ✅ Error message: "File size exceeds 50MB limit for videos"

3. **Test Ebook Size Limit (50MB max)**:
   ```bash
   # Should succeed
   bookcat test-pdf-50mb.pdf

   # Should fail (51MB exceeds limit)
   bookcat test-pdf-51mb.pdf
   ```

   **Expected Result**:
   - ✅ 50MB ebook loads successfully
   - ✅ 51MB ebook rejected with error message
   - ✅ Error message: "File size exceeds 50MB limit for ebooks"

4. **Test HTML Size Limit (5MB max)**:
   ```bash
   # Should succeed
   cat test-page-5mb.html

   # Should fail (6MB exceeds limit)
   cat test-page-6mb.html
   ```

**Acceptance Criteria**:
- [ ] 10MB image limit enforced
- [ ] 50MB video limit enforced
- [ ] 50MB ebook limit enforced
- [ ] 5MB HTML limit enforced
- [ ] Clear error messages shown for oversized files
- [ ] No crashes or silent failures

**File Size Limits (from `src/services/media_service.py:62-69`)**:
```python
max_image_size: int = 10 * 1024 * 1024  # 10MB
max_video_size: int = 50 * 1024 * 1024  # 50MB
max_html_size: int = 5 * 1024 * 1024    # 5MB
max_document_size: int = 10 * 1024 * 1024  # 10MB (for PDFs/EPUBs)
```

**Notes**:
- Size validation occurs in `media_service._validate_file_size()`
- Should raise `MediaSizeError` exception
- Check FastAPI endpoint error handling

---

## Test Execution Checklist

### Pre-Test Setup
- [ ] Desktop application built successfully
- [ ] Test files prepared in `~/jterm-test-files/`
- [ ] Application launches without errors
- [ ] Terminal emulator functional

### T066: Image Rendering
- [ ] Small image renders (<1s)
- [ ] 10MB image renders (<1s with downsampling)
- [ ] Multiple formats supported
- [ ] Images scroll correctly

### T067: Video Playback
- [ ] Video player loads
- [ ] Play/pause controls work
- [ ] Seek/scrubbing works
- [ ] Video scrolls with terminal

### T068: PDF Rendering
- [ ] PDF viewer loads
- [ ] Renders in <3s for 10MB files
- [ ] Page navigation works
- [ ] Password PDFs handled

### T069: EPUB Rendering
- [ ] EPUB viewer loads
- [ ] Renders in <2s for 5MB files
- [ ] Pagination works
- [ ] Formatting preserved

### T070: Media Scrolling
- [ ] Media scrolls with output
- [ ] Position maintained
- [ ] No layout issues
- [ ] Window resize works

### T071: Size Limits
- [ ] 10MB image limit enforced
- [ ] 50MB video limit enforced
- [ ] 50MB ebook limit enforced
- [ ] Error messages clear

---

## Troubleshooting

### Media Not Rendering
1. **Check Browser Console**: Look for JavaScript errors
2. **Check Python Backend Logs**: Verify media service is running
3. **Verify Endpoints**: Test `curl http://localhost:8000/api/v1/media/health` (if exists)
4. **Check File Paths**: Ensure files are accessible by Python backend

### Performance Issues
1. **Check CPU Usage**: `top` or Task Manager
2. **Check Memory**: Verify <500MB usage
3. **Check Network**: Media should be local (no external calls)
4. **Enable Profiling**: Add performance logging to media service

### Size Limit Not Working
1. **Check Media Service Config**: Verify `MediaConfig` values
2. **Check Error Handling**: Ensure exceptions propagate to UI
3. **Test with cURL**: Bypass UI and test API directly
   ```bash
   curl -X POST -F "file=@test-11mb.png" http://localhost:8000/api/v1/media/upload
   ```

---

## Success Criteria for Phase 6 (User Story 4)

**All tasks (T063-T071) must pass** for Phase 6 to be considered complete:

✅ **T063-T065**: Services and endpoints verified (COMPLETE)
📝 **T066-T071**: Manual testing pending

**Definition of Done**:
- [ ] All media types render correctly (images, videos, PDFs, EPUBs)
- [ ] Performance targets met (<1s images, <3s PDFs, <2s EPUBs)
- [ ] File size limits enforced correctly
- [ ] Media scrolling works naturally with terminal
- [ ] No regressions in existing functionality

**Checkpoint**: Once all tests pass, User Story 4 is complete and media viewing works identically to the web version in the desktop application.

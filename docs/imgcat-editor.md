# imgcat Image Editor - User Guide

**Version**: 1.0
**Last Updated**: 2025-11-18

## Overview

The imgcat image editor is a comprehensive web-based image editing tool integrated into jterm. It enables you to annotate screenshots, apply filters, crop and resize images, and manage editing sessions directly from your terminal.

## Quick Start

### Basic Usage

```bash
# View an image
imgcat screenshot.png

# Load image from clipboard (macOS/Windows)
imgcat --clipboard

# Load image from URL
imgcat https://example.com/image.png

# Open recent image history
imgcat --history

# Re-edit 2nd most recent image
imgcat -e 2
```

## Features

### 1. Drawing Tools

#### Pen Tool
- **Purpose**: Free-hand drawing and annotations
- **Usage**: Select pen tool, click and drag to draw
- **Customization**: Adjust color and stroke width in toolbar
- **Best For**: Highlighting areas, circling bugs, sketching

#### Arrow Tool
- **Purpose**: Point to specific areas with directional indicators
- **Usage**: Select arrow tool, click and drag from tail to head
- **Customization**: Color and stroke width
- **Best For**: Bug reports, documentation, tutorials

#### Text Tool
- **Purpose**: Add text annotations
- **Usage**: Select text tool, click to place, type text
- **Customization**: Font size (12pt-72pt), color, bold, italic, background
- **Best For**: Labels, descriptions, notes
- **Editing**: Double-click existing text to edit content

#### Rectangle Tool
- **Purpose**: Draw rectangular shapes
- **Usage**: Select rectangle tool, click and drag
- **Customization**: Color, stroke width, fill (optional)
- **Best For**: Highlighting regions, creating borders

#### Circle Tool
- **Purpose**: Draw circular/oval shapes
- **Usage**: Select circle tool, click and drag from center
- **Customization**: Color, stroke width, fill (optional)
- **Best For**: Highlighting points, creating diagrams

#### Line Tool
- **Purpose**: Draw straight lines
- **Usage**: Select line tool, click and drag
- **Tip**: Hold Shift to snap to 45° angles
- **Best For**: Connecting elements, creating diagrams

### 2. Image Operations

#### Crop
1. Click crop tool in toolbar
2. Drag selection rectangle around desired area
3. Click "Apply Crop" button
4. **Note**: Annotations are cleared after cropping

#### Resize
1. Click resize tool in toolbar
2. Enter target dimensions (width and/or height)
3. Check "Maintain Aspect Ratio" to preserve proportions
4. Click "Apply Resize"
5. **Note**: Annotations are scaled proportionally

#### Filters

**Client-Side Adjustments** (real-time preview):
- **Brightness**: Adjust from 0% (black) to 200% (double brightness)
- **Contrast**: Adjust from 0% (gray) to 200% (high contrast)
- **Saturation**: Adjust from 0% (grayscale) to 200% (oversaturated)

**Server-Side Filters** (applied on click):
- **Blur**: Gaussian blur with radius 0-20 pixels
- **Sharpen**: Unsharp mask with intensity 0-10

**Usage**:
1. Adjust sliders for live preview
2. Click "Apply" to commit changes
3. Click "Reset All" to revert to original

### 3. Clipboard Operations

#### Copy Image to Clipboard
1. Make your edits
2. Click "Copy to Clipboard" button
3. Paste in other applications (Slack, email, etc.)
4. **Browser Permission**: You'll be prompted for clipboard access on first use

#### Load from Clipboard
**macOS**:
```bash
imgcat --clipboard  # Uses built-in AppleScript
# Or with pngpaste: pngpaste - | imgcat
```

**Linux (Wayland)**:
```bash
wl-paste -t image/png | imgcat
```

**Linux (X11)**:
```bash
xclip -selection clipboard -t image/png -o | imgcat
```

**Windows**:
```bash
imgcat --clipboard  # Uses PowerShell Get-Clipboard
```

### 4. Undo/Redo

- **Undo**: Cmd+Z (macOS) / Ctrl+Z (Windows/Linux)
- **Redo**: Cmd+Shift+Z (macOS) / Ctrl+Shift+Z (Windows/Linux)
- **History Depth**: 50 operations (circular buffer)
- **Scope**: All operations (drawing, filtering, cropping, resizing)

### 5. Session History

The editor automatically tracks your 20 most recently viewed/edited images per terminal session.

#### View History
```bash
imgcat --history
```

Output:
```
Recent images:
  1. screenshot.png (viewed 3 times)
  2. diagram.png (edited)
  3. https://example.com/bug.png
  ...
```

#### Quick Re-Edit
```bash
# Edit most recent image
imgcat -e 1
# Or shortcut:
imgcat --edit-last

# Edit 3rd most recent
imgcat -e 3
```

**History Retention**: 7 days

### 6. Save Operations

#### Save to File
1. Click "Save" button
2. Enter filename (or use suggested name)
3. File is saved with edits applied

**For Clipboard Sources**: You'll be prompted for a filename since the original source has no path.

**For URL Sources**: Suggested filename extracted from URL (e.g., `screenshot.png` from URL).

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Cmd/Ctrl + Z` | Undo |
| `Cmd/Ctrl + Shift + Z` | Redo |
| `Delete` / `Backspace` | Delete selected object |
| `Esc` | Deselect tool/object |
| `Shift + Drag` (line tool) | Snap to 45° angles |

## Performance Tips

### Large Images (>4096px)
- Images are automatically downsampled for editing performance
- Original resolution restored on save
- Recommended max: 32,767px per dimension (browser limit)

### Many Annotations (>50 objects)
- Canvas operations may slow down with 100+ objects
- Consider flattening by saving and reopening
- Undo/redo uses compressed snapshots

### File Size Limits
- **Maximum**: 50MB per image
- Supported formats: PNG, JPEG, GIF, WebP, BMP

## Troubleshooting

### Clipboard Not Working

**Problem**: "Clipboard is empty" error

**macOS Solutions**:
1. Copy image data, not file path (Right-click → "Copy Image")
2. Use screenshot with `Cmd+Shift+Control+4` to copy to clipboard
3. Install `pngpaste`: `brew install pngpaste`

**Linux Solutions**:
1. Install `wl-clipboard` (Wayland) or `xclip` (X11)
2. Check clipboard utility: `wl-paste --list-types` or `xclip -selection clipboard -t TARGETS -o`

**Windows Solutions**:
1. Ensure PowerShell is available
2. Copy image (not file) to clipboard

### Can't Load Image

**Problem**: "File not found" or "Invalid image"

**Solutions**:
1. Check file path is absolute (not relative)
2. Verify file extension: .png, .jpg, .jpeg, .gif, .webp, .bmp
3. Check file size <50MB
4. Verify image file is not corrupt: `file screenshot.png`

### Slow Performance

**Problem**: Editor is slow or unresponsive

**Solutions**:
1. Image size: Reduce resolution before editing large images
2. Annotations: Flatten by saving and reopening
3. Browser: Close other tabs, restart browser
4. Check browser console for errors

### URL Loading Fails

**Problem**: "Failed to download image from URL"

**Possible Causes**:
1. **Network**: Check internet connection
2. **Timeout**: URL took >10 seconds to respond
3. **Size**: Image >50MB
4. **Format**: Content-Type is not `image/*`
5. **SSRF Protection**: URL points to private IP (blocked for security)

### History Missing

**Problem**: `imgcat --history` shows empty

**Causes**:
1. **New session**: History is per-terminal session
2. **Expired**: Entries older than 7 days are auto-deleted
3. **Database**: Check SQLite database for session_history table

## Security Features

### Path Validation
- Directory traversal blocked (`..` in paths)
- Symbolic links require explicit permission
- File extension validation

### URL Loading
- Only HTTP/HTTPS allowed
- Private IPs blocked (SSRF prevention)
- 10-second timeout
- 50MB size limit

### SQL Injection Prevention
- All UUIDs validated with regex
- Parameterized queries only

### Clipboard Access
- Browser permission required
- No persistent monitoring
- Data cleared after session

## Technical Details

### Storage
- **Sessions**: SQLite (`image_sessions` table)
- **Annotations**: SQLite (`annotation_layers` table) with Fabric.js JSON
- **Undo/Redo**: SQLite (`edit_operations` table), gzip-compressed
- **History**: SQLite (`session_history` table), 7-day retention
- **Temporary Files**: System temp directory, auto-cleanup after 24-48 hours

### Image Processing
- **Backend**: Pillow (Python) for filters, crop, resize
- **Frontend**: Fabric.js 5.3.0 for canvas management
- **Compression**: Gzip for canvas snapshots (60-80% size reduction)
- **Downsampling**: >4096px images scaled for editing performance

### Performance Metrics
- Image load: <1 second (5MB files)
- Canvas operations: <50ms
- Undo/redo: <100ms
- Filter preview: <200ms (client-side)

## API Reference

For developers integrating with the image editor, see:
- API contracts: `specs/004-imgcat-editor/contracts/api-endpoints.yaml`
- Data model: `specs/004-imgcat-editor/data-model.md`
- JavaScript flow: `docs/image-editor-javascript-flow.md`

## Support

For issues or feature requests:
1. Check troubleshooting section above
2. Review error messages in browser console (F12)
3. Check server logs for backend errors
4. Report issues: [GitHub Issues](https://github.com/anthropics/claude-code/issues)

## Version History

### v1.0 (2025-11-18) - Initial Release
- Drawing tools (pen, arrow, text, shapes)
- Image operations (crop, resize, filters)
- Clipboard integration (load/save)
- Session history (20 images, 7-day retention)
- URL loading with SSRF protection
- Undo/redo (50 operations)
- Security hardening (path validation, UUID validation)
- Performance optimizations (downsampling, compression)

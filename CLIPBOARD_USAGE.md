# Clipboard Image Usage for imgcat

## ✨ PRIMARY METHOD: Python PIL.ImageGrab (Built-in!)

**`imgcat --clipboard` now uses PIL.ImageGrab by default!**

The `imgcat` command has been updated to use **PIL.ImageGrab** (built into Pillow) for clipboard access on macOS and Windows. **No external tools required!**

### How it works:
1. When you run `imgcat --clipboard`, it executes a Python script using PIL.ImageGrab
2. On macOS/Windows: Uses native clipboard APIs (Cocoa/Win32)
3. On Linux: Falls back to wl-paste or xclip if Pillow not available

## Important: pbpaste Does NOT Work for Images!

`pbpaste` on macOS is **text-only**. For images, use `imgcat --clipboard` or one of the methods below.

## Quick Test

1. **Copy an image to clipboard:**
   - Screenshot: Press `⌘⇧⌃4` (select area, copies to clipboard)
   - From browser/Finder: Right-click image → "Copy Image" (NOT "Copy Image Address")

2. **Paste into imgcat:**
   ```bash
   imgcat --clipboard
   ```

This uses Python's PIL.ImageGrab (built into Pillow) - no shell utilities needed!

## Platform-Specific Methods

### macOS

**Option 1: PIL.ImageGrab via Python (PRIMARY - Built into Pillow)**
```bash
imgcat --clipboard
```

This uses Python's PIL.ImageGrab which is built into Pillow. Works on macOS and Windows with no external dependencies.

**Option 2: pngpaste (Alternative, requires installation)**
```bash
# Install pngpaste
brew install pngpaste

# Use it
pngpaste - | imgcat
# or
imgcat --clipboard  # Will auto-detect and use pngpaste
```

**What DOESN'T work:**
```bash
pbpaste | imgcat  # ❌ FAILS - pbpaste is text-only!
```

### Linux

**Wayland:**
```bash
# Install wl-clipboard
sudo apt-get install wl-clipboard

# Use it
wl-paste -t image/png | imgcat
# or
imgcat --clipboard
```

**X11:**
```bash
# Install xclip
sudo apt-get install xclip

# Use it
xclip -selection clipboard -t image/png -o | imgcat
# or
imgcat --clipboard
```

### Windows

```bash
imgcat --clipboard
```

Uses PowerShell's `Get-Clipboard -Format Image` (built-in).

## Troubleshooting

### "Clipboard is empty or does not contain image data"

**Make sure you copied an IMAGE, not a FILE PATH:**
- ✅ Right-click on image → "Copy Image"
- ✅ Screenshot with `⌘⇧⌃4` (macOS)
- ❌ Copy file in Finder (this copies the file path, not the image data)

### "Failed to read image from clipboard"

**On macOS:**
1. Try installing pngpaste: `brew install pngpaste`
2. Make sure you're copying PNG-compatible images
3. Some apps (like Preview) may copy in non-standard formats - try screenshotting instead

**On Linux:**
1. Make sure you have `wl-paste` or `xclip` installed
2. Check that your clipboard manager supports image data

## How It Works

### macOS (AppleScript method)
The AppleScript approach extracts clipboard data as PNG:
```applescript
set theImage to (the clipboard as «class PNGf»)
```

This reads the clipboard as PNG format and outputs raw bytes to stdout.

### macOS (pngpaste method)
`pngpaste` is a dedicated tool for extracting PNG images from macOS clipboard.

### Linux
- `wl-paste -t image/png`: Wayland clipboard tool
- `xclip -selection clipboard -t image/png -o`: X11 clipboard tool

Both extract PNG data from the clipboard and output to stdout.

## Testing

```bash
# 1. Take a screenshot (copies to clipboard on macOS)
⌘⇧⌃4

# 2. Paste into imgcat
imgcat --clipboard

# 3. Should open image editor with your screenshot
```

## Technical Details

- **Image format:** The clipboard tools extract images as PNG
- **Maximum size:** 50MB (imgcat limit)
- **Maximum dimensions:** 32767×32767 pixels (Canvas API limit)
- **Supported clipboard formats:** PNG (primary), JPEG, GIF, WebP, BMP

## Error Messages Explained

| Error | Cause | Solution |
|-------|-------|----------|
| "pbpaste does not work for images" | Using pbpaste for image data | Use `imgcat --clipboard` or `pngpaste` |
| "Clipboard is empty" | Nothing copied to clipboard | Copy an image first |
| "No image data" | Copied file path instead of image | Right-click image → "Copy Image" |
| "Failed to read clipboard" | Clipboard tool not installed | Install pngpaste/wl-paste/xclip |

## Additional Resources

- pngpaste: https://github.com/jcsalterego/pngpaste
- wl-clipboard: https://github.com/bugaevc/wl-clipboard
- xclip: https://github.com/astrand/xclip

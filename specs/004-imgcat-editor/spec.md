# Feature Specification: imgcat Image Editor

**Feature Branch**: `004-imgcat-editor`
**Created**: 2025-11-12
**Status**: Draft
**Input**: User description: "Extend imgcat command with comprehensive image editing capabilities. Users can edit images from file paths, clipboard, URLs, or previously displayed images. Editing features include drawing, text annotations, cropping, filters, rotation, resizing, and more. Edited images can be saved to file or copied to clipboard."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Annotate Screenshot for Bug Report (Priority: P1)

As a developer debugging an issue, I need to capture a screenshot, circle the problem area, add arrows and text annotations, then copy to clipboard so I can quickly paste it into Slack, GitHub issues, or email without switching to an external editor.

**Why this priority**: This is the core workflow that drives the feature request. Developers frequently need to communicate visual issues and the current workflow requires switching to external editors, breaking concentration and slowing down communication. This story delivers immediate, tangible value.

**Independent Test**: Can be fully tested by running `imgcat screenshot.png`, adding visual annotations (pen, arrow, text), and copying the result to clipboard. Delivers standalone value as a complete annotation workflow without requiring any other stories.

**Acceptance Scenarios**:

1. **Given** I have a screenshot file, **When** I run `imgcat screenshot.png`, **Then** an image viewer opens with editing tools visible
2. **Given** the image editor is open, **When** I select the pen tool and draw a circle around a UI element, **Then** the circle appears in red (default color) on the image
3. **Given** I've drawn annotations, **When** I select the arrow tool and draw from point A to point B, **Then** an arrow appears pointing from A to B with a clear direction indicator
4. **Given** I've added visual annotations, **When** I select the text tool and click on the image, **Then** I can type text that appears on the image at the clicked location
5. **Given** I've completed my annotations, **When** I click "Copy to Clipboard", **Then** the edited image is copied to clipboard and I can paste it in other applications (Slack, email, etc.)
6. **Given** I've made edits, **When** I click undo, **Then** the most recent edit is removed and I can continue editing or redo the undone action

---

### User Story 2 - Edit Image from Clipboard (Priority: P1)

As a user working with screenshots and copied images, I need to paste an image from my clipboard directly into the terminal for editing so I can annotate images without first saving them to disk.

**Why this priority**: Clipboard workflow is essential for speed and convenience. Many users copy images directly (using system screenshot tools) before having a filename. This story eliminates the save-then-edit friction and makes the tool feel native to modern workflows.

**Independent Test**: Can be fully tested by copying an image to clipboard, running `imgcat --clipboard` or `pbpaste | imgcat`, making edits, and either saving to disk or copying back to clipboard. Provides complete clipboard-to-clipboard workflow value.

**Acceptance Scenarios**:

1. **Given** I have an image in my clipboard, **When** I run `pbpaste | imgcat`, **Then** the image editor opens with the clipboard image loaded and ready for editing
2. **Given** I have an image in my clipboard, **When** I run `imgcat --clipboard`, **Then** the image editor opens with the clipboard image loaded
3. **Given** I'm editing a clipboard image, **When** I make changes and click save, **Then** I'm prompted for a filename and location to save the file
4. **Given** I'm editing a clipboard image, **When** I click "Copy to Clipboard", **Then** the edited version replaces the original clipboard content

---

### User Story 3 - Crop and Resize Images (Priority: P1)

As a user preparing images for documentation or sharing, I need to crop unwanted areas and resize images to appropriate dimensions so they fit platform requirements (e.g., GitHub issue size limits, Slack optimal dimensions) and focus attention on relevant content.

**Why this priority**: Cropping and resizing are fundamental image editing operations that complement annotations. Users often need to remove sensitive information, focus on specific areas, or meet size constraints before sharing. This is a core editing capability expected in any image editor.

**Independent Test**: Can be fully tested by opening an image, selecting crop tool to define a region, applying the crop, then using resize to change dimensions, and saving the result. Delivers standalone value for basic image preparation tasks.

**Acceptance Scenarios**:

1. **Given** I have an image open in the editor, **When** I select the crop tool and drag to define a rectangular region, **Then** the area outside the rectangle is dimmed/highlighted to show what will be removed
2. **Given** I've selected a crop region, **When** I click "Apply Crop", **Then** the image is cropped to the selected region and the dimmed area is removed
3. **Given** I have an image open, **When** I select "Resize" and enter new dimensions (width/height in pixels or percentage), **Then** the image is resized to the specified dimensions
4. **Given** I'm resizing an image, **When** I enable "Maintain Aspect Ratio" and change one dimension, **Then** the other dimension adjusts automatically to preserve proportions
5. **Given** I've cropped or resized an image, **When** I click undo, **Then** the image reverts to its previous state

---

### User Story 4 - Apply Filters and Adjustments (Priority: P2)

As a user enhancing image quality or aesthetics, I need to apply common filters and adjustments (brightness, contrast, saturation, blur, sharpen) so I can improve visibility, highlight important areas, or create visual effects for better communication.

**Why this priority**: While not as critical as annotations and basic editing, filters and adjustments enhance the professional quality of shared images. They help compensate for poor screenshot quality or emphasize important details. This is a secondary enhancement that builds on the core functionality.

**Independent Test**: Can be fully tested by opening an image, applying various filters/adjustments with live preview, and saving the enhanced result. Provides standalone value for image quality improvement without requiring other stories.

**Acceptance Scenarios**:

1. **Given** I have an image open, **When** I select "Brightness" adjustment and move the slider, **Then** I see a live preview of brightness changes
2. **Given** I'm adjusting brightness, **When** I click "Apply", **Then** the brightness adjustment is permanently applied to the image
3. **Given** I have an image open, **When** I select "Contrast" adjustment, **Then** I can increase or decrease contrast with live preview
4. **Given** I have an image open, **When** I select "Blur" filter and adjust intensity, **Then** the selected area or entire image is blurred
5. **Given** I have an image open, **When** I select "Sharpen" filter, **Then** image edges become more defined
6. **Given** I've applied filters, **When** I click "Reset All", **Then** all filters are removed and the image returns to its original state

---

### User Story 5 - Edit Previously Displayed Images (Priority: P2)

As a terminal user working with multiple images in a session, I need to quickly re-edit an image I viewed earlier without retyping the full path so I can iterate on edits or compare multiple versions efficiently.

**Why this priority**: This improves workflow efficiency for power users who work with multiple images. It leverages the existing terminal session context. However, it's a convenience feature that doesn't block core functionality - users can always re-run imgcat with the file path.

**Independent Test**: Can be fully tested by viewing multiple images with imgcat, then running a command (e.g., `imgcat --history` or `imgcat -e 2`) to re-open a previously viewed image for editing. Provides standalone value as a session history feature.

**Acceptance Scenarios**:

1. **Given** I've viewed 3 images in my terminal session using imgcat, **When** I run `imgcat --history`, **Then** I see a numbered list of previously viewed images in this session
2. **Given** I see the history list, **When** I select an image number (e.g., press 2), **Then** that image opens in the editor
3. **Given** I've viewed images in my session, **When** I run `imgcat --edit-last`, **Then** the most recently viewed image opens in the editor
4. **Given** I've viewed images in my session, **When** I run `imgcat -e 2`, **Then** the second most recent image opens in the editor
5. **Given** no images have been viewed in the session, **When** I run `imgcat --history`, **Then** I receive a message "No images in session history"

---

### User Story 6 - Load and Edit Images from URLs (Priority: P3)

As a user collaborating with remote teams or working with web content, I need to load images directly from URLs for editing so I can annotate shared screenshots, web assets, or images from issue trackers without manually downloading them first.

**Why this priority**: URL support adds convenience for certain workflows but isn't essential for the core use case. Most users work with local files or clipboard images. This is a nice-to-have that expands the tool's versatility but can be deferred.

**Independent Test**: Can be fully tested by running `imgcat https://example.com/image.png`, verifying the image loads, making edits, and saving. Provides standalone value as a URL-loading capability without requiring other stories.

**Acceptance Scenarios**:

1. **Given** I have a public image URL, **When** I run `imgcat https://example.com/screenshot.png`, **Then** the image is downloaded and opens in the editor
2. **Given** I'm loading an image from URL, **When** the download is in progress, **Then** I see a progress indicator (e.g., "Loading image from URL...")
3. **Given** the URL is invalid or the image fails to load, **When** I attempt to load the image, **Then** I receive an error message "Failed to load image from URL: [reason]"
4. **Given** I've loaded an image from URL and made edits, **When** I click save, **Then** I'm prompted for a local filename (original URL filename suggested by default)
5. **Given** I've loaded an image from URL, **When** I click "Copy to Clipboard", **Then** the edited image is copied to clipboard without requiring a save

---

### User Story 7 - Advanced Drawing and Shapes (Priority: P2)

As a user creating detailed annotations, I need to draw various shapes (rectangles, circles, lines, freehand) with customizable colors, stroke widths, and fill options so I can create clear, professional-looking visual explanations.

**Why this priority**: Expands on the basic pen tool from Story 1, providing more sophisticated annotation capabilities. While useful for professional documentation, the basic pen and arrow tools cover most immediate needs. This enhances annotation quality but isn't blocking.

**Independent Test**: Can be fully tested by opening an image, selecting various shape tools (rectangle, circle, line), customizing colors/widths, drawing shapes, and saving. Provides standalone value as enhanced drawing capabilities.

**Acceptance Scenarios**:

1. **Given** I have an image open, **When** I select the rectangle tool and drag on the canvas, **Then** a rectangle is drawn with the default stroke color and width
2. **Given** I've selected a drawing tool, **When** I click the color picker and choose a color, **Then** subsequent drawings use the selected color
3. **Given** I'm using a shape tool, **When** I adjust the stroke width slider (1-10 pixels), **Then** the shape is drawn with the specified width
4. **Given** I've selected the circle tool, **When** I toggle "Fill" option, **Then** the circle is drawn as filled rather than just outlined
5. **Given** I'm using the line tool, **When** I hold Shift while dragging, **Then** the line snaps to 45-degree angles (0°, 45°, 90°, etc.)
6. **Given** I've drawn multiple shapes, **When** I select the selection tool and click a shape, **Then** I can move, resize, or delete the selected shape

---

### User Story 8 - Text Annotations with Formatting (Priority: P2)

As a user adding explanatory text to images, I need to customize font size, color, style (bold/italic), and background so my text annotations are readable, professional, and appropriately emphasized for different contexts.

**Why this priority**: Builds on basic text tool from Story 1, adding formatting capabilities for more professional results. While basic text is essential (P1), formatting options improve quality but aren't critical for initial value delivery.

**Independent Test**: Can be fully tested by opening an image, adding text with various formatting options (font size, color, bold, background), and verifying the text appears as formatted. Provides standalone value as enhanced text capabilities.

**Acceptance Scenarios**:

1. **Given** I've selected the text tool and clicked on the image, **When** I type text and select a font size from the dropdown (12-72pt), **Then** the text appears at the selected size
2. **Given** I'm adding text, **When** I click the color picker and choose a text color, **Then** the text appears in the selected color
3. **Given** I'm adding text, **When** I click the bold button, **Then** the text appears in bold weight
4. **Given** I'm adding text, **When** I click the italic button, **Then** the text appears in italic style
5. **Given** I'm adding text, **When** I enable "Text Background" and choose a background color, **Then** the text has a colored background box for better contrast
6. **Given** I've added formatted text, **When** I click the text to select it, **Then** I can edit the text content or change formatting options

---

### Edge Cases

- What happens when trying to load a corrupt or invalid image file?
- How does the system handle very large images (>50MB) that may impact performance?
- What happens when clipboard is empty and user runs `imgcat --clipboard`?
- How does the system handle URL timeouts or network failures during image loading?
- What happens when user tries to save to a location without write permissions?
- How does the system handle rapid undo/redo operations?
- What happens when text annotations extend beyond image boundaries?
- How does the system handle saving edits to read-only files?
- What happens when multiple imgcat instances try to edit the same file simultaneously?
- How does the system handle very narrow or very wide terminal windows for the editor UI?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST support loading images from file paths specified as command arguments (e.g., `imgcat path/to/image.png`)
- **FR-002**: System MUST support loading images from clipboard via `imgcat --clipboard` flag or stdin pipe (`pbpaste | imgcat`)
- **FR-003**: System MUST support loading images from HTTP/HTTPS URLs (e.g., `imgcat https://example.com/image.png`)
- **FR-004**: System MUST provide a pen/freehand drawing tool with customizable color and stroke width
- **FR-005**: System MUST provide an arrow annotation tool for directional indicators
- **FR-006**: System MUST provide a text annotation tool allowing users to click and type text on the image
- **FR-007**: System MUST support copy to clipboard functionality for edited images
- **FR-008**: System MUST support save to file functionality with filename prompt for clipboard/URL sources
- **FR-009**: System MUST provide undo/redo functionality for all editing operations
- **FR-010**: System MUST provide crop tool with visual selection rectangle and dimmed preview
- **FR-011**: System MUST provide resize functionality with width/height input and aspect ratio lock option
- **FR-012**: System MUST support image format validation and display error messages for unsupported/corrupt files
- **FR-013**: System MUST provide brightness, contrast, and saturation adjustment controls with live preview
- **FR-014**: System MUST provide blur and sharpen filters with adjustable intensity
- **FR-015**: System MUST maintain session history of viewed images for quick re-editing
- **FR-016**: System MUST provide shape drawing tools (rectangle, circle, line) with fill and stroke options
- **FR-017**: System MUST provide text formatting options (font size, color, bold, italic, background)
- **FR-018**: System MUST support selection, moving, and deletion of individual annotation elements
- **FR-019**: System MUST preserve original image when editing and only modify on explicit save/copy actions
- **FR-020**: System MUST support common image formats (PNG, JPEG, GIF, WebP, BMP)
- **FR-021**: System MUST display loading indicators for network operations (URL downloads)
- **FR-022**: System MUST handle file permission errors gracefully with informative error messages
- **FR-023**: System MUST limit maximum image file size to 50MB (consistent with existing jterm media limits)
- **FR-024**: System MUST provide a "Reset All" function to remove all filters and adjustments
- **FR-025**: System MUST detect empty clipboard and display appropriate error message

### Key Entities

- **Image**: Represents the loaded image being edited, including source (file path, clipboard, URL), format, dimensions, and current editing state
- **Annotation Layer**: Represents the collection of edits/annotations applied to an image, including drawings, text, shapes, and their properties
- **Drawing Tool**: Represents a specific editing capability (pen, arrow, text, shape) with its configuration (color, width, fill, font)
- **Edit Operation**: Represents a single editing action in the undo/redo history stack, allowing operations to be reversed
- **Session History**: Represents the list of previously viewed images in the current terminal session for quick re-editing

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can annotate a screenshot and copy to clipboard in under 30 seconds from command execution
- **SC-002**: System loads and displays images from file paths in under 1 second for images up to 5MB
- **SC-003**: Editing operations (draw, text, shape) render on canvas with less than 50ms latency (feels instant)
- **SC-004**: Undo/redo operations complete in under 100ms
- **SC-005**: Image loading from URLs completes within 10 seconds or shows timeout error
- **SC-006**: 95% of users successfully complete annotation tasks on first attempt without external documentation
- **SC-007**: Clipboard operations (copy/paste) complete in under 2 seconds for images up to 10MB
- **SC-008**: Filter/adjustment previews update in under 200ms when slider is adjusted
- **SC-009**: System handles at least 100 annotation elements on a single image without performance degradation
- **SC-010**: Crop and resize operations complete in under 1 second for images up to 10MB

## Assumptions *(mandatory)*

- Users have clipboard utilities installed (pbpaste on macOS, xclip on Linux, clip.exe on Windows)
- Terminal environment supports displaying graphical UI for the image editor (web-based UI via jterm's existing architecture)
- Users have write permissions to intended save locations
- Network connectivity is available for URL-based image loading
- Image editor UI will be served via jterm's existing FastAPI/HTMX architecture
- Browser environment supports HTML5 Canvas API for drawing operations
- Default annotation colors follow common conventions (red for highlights, black for text)
- Text annotations default to system sans-serif font for compatibility
- Session history is limited to current terminal session (not persisted between sessions)
- Maximum image dimensions are limited by browser canvas limitations (typically 32,767 pixels per dimension)

## Dependencies *(mandatory)*

- Existing jterm terminal emulation and WebSocket infrastructure
- Existing jterm media viewing capabilities (imgcat foundation)
- FastAPI backend for image processing and file operations
- Browser Canvas API for image editing operations
- Clipboard API support in browser for copy/paste functionality
- Python image processing library (e.g., Pillow) for server-side operations
- File system access for saving edited images
- Network access for URL-based image loading

## Out of Scope *(mandatory)*

- Advanced photo editing features (layers, masks, gradients, complex filters)
- Batch editing of multiple images simultaneously
- Image format conversion functionality
- Integration with external image editing tools
- AI-powered editing features (auto-enhance, content-aware fill, object removal)
- Collaborative real-time editing with multiple users
- Cloud storage integration for saving images
- Mobile device support (focused on desktop terminal workflow)
- Video or animated GIF editing capabilities
- RAW image format support
- PDF or document annotation (separate feature: bookcat)
- Authentication-required image URL sources (OAuth, API keys)

## Security & Privacy Considerations *(optional)*

- Image data from clipboard or URLs should be temporarily stored and cleaned up after session ends
- URL loading should validate/sanitize URLs to prevent SSRF attacks
- File operations should validate paths to prevent directory traversal attacks
- Clipboard access requires user permission in browser environment
- Edited images should not be cached persistently without explicit user save action
- URL downloads should respect reasonable timeout limits to prevent resource exhaustion
- File size limits (50MB) should be enforced to prevent memory exhaustion attacks

## Performance Considerations *(optional)*

- Image rendering should use efficient canvas operations to maintain <50ms draw latency
- Large images may need to be downsampled for editing and upsampled on save to maintain performance
- Undo/redo history should be limited to reasonable depth (e.g., 50 operations) to prevent memory issues
- Filter/adjustment previews should debounce slider input to prevent excessive recalculation
- URL downloads should stream rather than loading entirely into memory
- Session history should limit retained images (e.g., last 20 images) to prevent memory growth

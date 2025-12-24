# Tauri Commands API Contract

**Feature**: 005-desktop-application
**Date**: 2025-12-13
**Status**: Complete

## Overview

This document defines the Tauri command interface (IPC bridge between JavaScript frontend and Rust backend). Tauri commands provide native desktop functionality that cannot be implemented in the Python backend.

**Communication Pattern**:
```
JavaScript UI → window.__TAURI__.invoke('command_name', args) → Rust Command → Native OS API
```

---

## Command Categories

### 1. Application Lifecycle Commands
### 2. Clipboard Commands
### 3. File Dialog Commands
### 4. Menu Commands
### 5. System Integration Commands

**Note**: PTY operations are handled by the existing Python backend via WebSocket (same as web version). Tauri only provides native OS features that cannot be implemented in Python/browser.

---

## 1. Application Lifecycle Commands

### `app_ready`

**Description**: Notify Tauri that the UI is ready to display.

**Request**:
```typescript
interface AppReadyRequest {
  // No parameters
}
```

**Response**:
```typescript
interface AppReadyResponse {
  app_version: string;      // Application version (e.g., "1.0.0")
  platform: string;          // Platform: "macos", "windows", "linux"
  database_path: string;     // Absolute path to database
  is_first_launch: boolean;  // True if first launch (for onboarding)
}
```

**Errors**:
- None (always succeeds)

**Usage**:
```javascript
const appInfo = await window.__TAURI__.invoke('app_ready');
console.log(`Running jterm ${appInfo.app_version} on ${appInfo.platform}`);
```

---

### `get_database_path`

**Description**: Get the platform-specific database path.

**Request**:
```typescript
interface GetDatabasePathRequest {
  // No parameters
}
```

**Response**:
```typescript
interface GetDatabasePathResponse {
  path: string;  // Absolute path to database
}
```

**Errors**:
- None (always returns platform-specific path)

**Example Response**:
```json
{
  "path": "/Users/john/Library/Application Support/jterm/webterminal.db"
}
```

---

### `quit_app`

**Description**: Gracefully quit the application.

**Request**:
```typescript
interface QuitAppRequest {
  force?: boolean;  // Force quit without prompting (default: false)
}
```

**Response**:
```typescript
interface QuitAppResponse {
  // No response (app quits)
}
```

**Behavior**:
- If `force=false`: Prompt user to save unsaved work before quitting
- If `force=true`: Quit immediately
- Cleanup: Terminate all PTY processes, close database connections, delete temp files

**Usage**:
```javascript
await window.__TAURI__.invoke('quit_app', { force: false });
```

---

## 2. Clipboard Commands

### `get_clipboard_text`

**Description**: Get text from system clipboard.

**Request**:
```typescript
interface GetClipboardTextRequest {
  // No parameters
}
```

**Response**:
```typescript
interface GetClipboardTextResponse {
  text: string | null;      // Clipboard text (null if empty or not text)
}
```

**Errors**:
- `"ClipboardAccessDenied"`: User denied clipboard access (macOS/Windows permissions)

**Usage**:
```javascript
const text = await window.__TAURI__.invoke('get_clipboard_text');
console.log(`Clipboard: ${text}`);
```

---

### `set_clipboard_text`

**Description**: Set system clipboard to text.

**Request**:
```typescript
interface SetClipboardTextRequest {
  text: string;             // Text to copy
}
```

**Response**:
```typescript
interface SetClipboardTextResponse {
  success: boolean;         // Always true
}
```

**Errors**:
- `"ClipboardAccessDenied"`: User denied clipboard access

**Usage**:
```javascript
await window.__TAURI__.invoke('set_clipboard_text', {
  text: 'Hello, world!'
});
```

---

### `get_clipboard_image`

**Description**: Get image from system clipboard.

**Request**:
```typescript
interface GetClipboardImageRequest {
  format?: string;          // Output format: "png", "jpeg" (default: "png")
}
```

**Response**:
```typescript
interface GetClipboardImageResponse {
  image_data: string | null;  // Base64-encoded image (null if empty or not image)
  width: number | null;       // Image width in pixels
  height: number | null;      // Image height in pixels
  format: string | null;      // Actual format: "png", "jpeg"
}
```

**Errors**:
- `"ClipboardAccessDenied"`: User denied clipboard access
- `"ImageDecodeFailed"`: Failed to decode clipboard image

**Usage**:
```javascript
const image = await window.__TAURI__.invoke('get_clipboard_image', {
  format: 'png'
});
if (image.image_data) {
  const blob = base64ToBlob(image.image_data, 'image/png');
  // Load image in editor
}
```

---

### `set_clipboard_image`

**Description**: Set system clipboard to image.

**Request**:
```typescript
interface SetClipboardImageRequest {
  image_data: string;       // Base64-encoded image
  format: string;           // Image format: "png", "jpeg"
}
```

**Response**:
```typescript
interface SetClipboardImageResponse {
  success: boolean;         // Always true
}
```

**Errors**:
- `"ClipboardAccessDenied"`: User denied clipboard access
- `"InvalidImageData"`: Invalid base64 or image format
- `"ImageEncodeFailed"`: Failed to encode image for clipboard

**Usage**:
```javascript
const imageBlob = await canvas.toBlob();
const base64 = await blobToBase64(imageBlob);
await window.__TAURI__.invoke('set_clipboard_image', {
  image_data: base64,
  format: 'png'
});
```

---

## 3. File Dialog Commands

### `select_file`

**Description**: Show native file selection dialog.

**Request**:
```typescript
interface SelectFileRequest {
  title?: string;           // Dialog title (default: "Select File")
  filters?: FileFilter[];   // File type filters
  default_path?: string;    // Default directory
  multiple?: boolean;       // Allow multiple selection (default: false)
}

interface FileFilter {
  name: string;             // Filter name (e.g., "Images")
  extensions: string[];     // Extensions (e.g., ["png", "jpg", "jpeg"])
}
```

**Response**:
```typescript
interface SelectFileResponse {
  paths: string[] | null;   // Selected file paths (null if cancelled)
}
```

**Errors**:
- `"DialogFailed"`: Failed to show dialog

**Usage**:
```javascript
const result = await window.__TAURI__.invoke('select_file', {
  title: 'Select an image',
  filters: [{
    name: 'Images',
    extensions: ['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp']
  }],
  multiple: false
});
if (result.paths) {
  console.log(`Selected: ${result.paths[0]}`);
}
```

---

### `select_directory`

**Description**: Show native directory selection dialog.

**Request**:
```typescript
interface SelectDirectoryRequest {
  title?: string;           // Dialog title (default: "Select Directory")
  default_path?: string;    // Default directory
}
```

**Response**:
```typescript
interface SelectDirectoryResponse {
  path: string | null;      // Selected directory path (null if cancelled)
}
```

**Errors**:
- `"DialogFailed"`: Failed to show dialog

**Usage**:
```javascript
const result = await window.__TAURI__.invoke('select_directory', {
  title: 'Select output directory'
});
if (result.path) {
  console.log(`Selected: ${result.path}`);
}
```

---

### `save_file`

**Description**: Show native save file dialog.

**Request**:
```typescript
interface SaveFileRequest {
  title?: string;           // Dialog title (default: "Save File")
  filters?: FileFilter[];   // File type filters
  default_path?: string;    // Default file name/path
}
```

**Response**:
```typescript
interface SaveFileResponse {
  path: string | null;      // Save file path (null if cancelled)
}
```

**Errors**:
- `"DialogFailed"`: Failed to show dialog

**Usage**:
```javascript
const result = await window.__TAURI__.invoke('save_file', {
  title: 'Save recording',
  filters: [{
    name: 'ASCIINEMA',
    extensions: ['cast']
  }],
  default_path: 'recording.cast'
});
if (result.path) {
  // Save file to result.path
}
```

---

## 4. Menu Commands

### `update_menu_item`

**Description**: Update a menu item state (enabled/disabled, checked, label).

**Request**:
```typescript
interface UpdateMenuItemRequest {
  menu_id: string;          // Menu item ID (e.g., "recording_start")
  enabled?: boolean;        // Enable/disable
  checked?: boolean;        // Check/uncheck (for checkable items)
  label?: string;           // Update label
}
```

**Response**:
```typescript
interface UpdateMenuItemResponse {
  success: boolean;         // Always true
}
```

**Errors**:
- `"MenuItemNotFound"`: Menu item ID does not exist

**Usage**:
```javascript
// Disable "Start Recording" menu item when recording
await window.__TAURI__.invoke('update_menu_item', {
  menu_id: 'recording_start',
  enabled: false
});

// Enable "Stop Recording" menu item
await window.__TAURI__.invoke('update_menu_item', {
  menu_id: 'recording_stop',
  enabled: true
});
```

---

### `show_context_menu`

**Description**: Show a custom context menu at cursor position.

**Request**:
```typescript
interface ShowContextMenuRequest {
  items: ContextMenuItem[];
  x?: number;               // X position (default: cursor)
  y?: number;               // Y position (default: cursor)
}

interface ContextMenuItem {
  id: string;               // Unique item ID
  label: string;            // Display label
  enabled?: boolean;        // Enabled (default: true)
  checked?: boolean;        // Checked (for checkable items)
  separator?: boolean;      // Is separator (default: false)
  submenu?: ContextMenuItem[];  // Nested menu items
}
```

**Response**:
```typescript
interface ShowContextMenuResponse {
  selected_id: string | null;  // Selected item ID (null if dismissed)
}
```

**Errors**:
- `"MenuCreationFailed"`: Failed to create context menu

**Usage**:
```javascript
const result = await window.__TAURI__.invoke('show_context_menu', {
  items: [
    { id: 'copy', label: 'Copy', enabled: true },
    { id: 'paste', label: 'Paste', enabled: true },
    { separator: true },
    { id: 'clear', label: 'Clear Terminal', enabled: true }
  ]
});
if (result.selected_id === 'copy') {
  // Handle copy action
}
```

---

## 5. System Integration Commands

### `open_external_url`

**Description**: Open a URL in the system's default browser.

**Request**:
```typescript
interface OpenExternalUrlRequest {
  url: string;              // URL to open
}
```

**Response**:
```typescript
interface OpenExternalUrlResponse {
  success: boolean;         // Always true
}
```

**Errors**:
- `"InvalidUrl"`: URL is malformed
- `"OpenFailed"`: Failed to open URL

**Usage**:
```javascript
await window.__TAURI__.invoke('open_external_url', {
  url: 'https://github.com/user/jterm'
});
```

---

### `show_in_folder`

**Description**: Show a file in the system's file manager.

**Request**:
```typescript
interface ShowInFolderRequest {
  path: string;             // Absolute file path
}
```

**Response**:
```typescript
interface ShowInFolderResponse {
  success: boolean;         // Always true
}
```

**Errors**:
- `"FileNotFound"`: File does not exist
- `"OpenFailed"`: Failed to open file manager

**Usage**:
```javascript
await window.__TAURI__.invoke('show_in_folder', {
  path: '/Users/john/Downloads/recording.cast'
});
```

---

### `get_system_info`

**Description**: Get system information (OS, version, architecture).

**Request**:
```typescript
interface GetSystemInfoRequest {
  // No parameters
}
```

**Response**:
```typescript
interface GetSystemInfoResponse {
  platform: string;         // "macos", "windows", "linux"
  os_version: string;       // OS version (e.g., "14.2.1")
  arch: string;             // Architecture: "x64", "arm64"
  hostname: string;         // Computer hostname
  username: string;         // Current user
  home_dir: string;         // Home directory path
}
```

**Errors**:
- None (always succeeds)

**Usage**:
```javascript
const sysInfo = await window.__TAURI__.invoke('get_system_info');
console.log(`Running on ${sysInfo.platform} ${sysInfo.os_version} (${sysInfo.arch})`);
```

---

### `set_window_title`

**Description**: Set the window title.

**Request**:
```typescript
interface SetWindowTitleRequest {
  title: string;            // New window title
}
```

**Response**:
```typescript
interface SetWindowTitleResponse {
  success: boolean;         // Always true
}
```

**Errors**:
- None (always succeeds)

**Usage**:
```javascript
await window.__TAURI__.invoke('set_window_title', {
  title: 'jterm - ~/projects/myapp'
});
```

---

### `notify`

**Description**: Show a system notification.

**Request**:
```typescript
interface NotifyRequest {
  title: string;            // Notification title
  body: string;             // Notification body
  icon?: string;            // Icon path (optional)
}
```

**Response**:
```typescript
interface NotifyResponse {
  success: boolean;         // Always true
}
```

**Errors**:
- `"NotificationFailed"`: Failed to show notification

**Usage**:
```javascript
await window.__TAURI__.invoke('notify', {
  title: 'Recording Complete',
  body: 'Terminal session has been saved.'
});
```

---

## Error Handling

All Tauri commands return `Result<T, String>` in Rust, which translates to Promise rejection in JavaScript.

**JavaScript Error Handling**:
```javascript
try {
  const result = await window.__TAURI__.invoke('select_file', { ... });
} catch (error) {
  console.error(`Command failed: ${error}`);
  // Handle specific errors
  if (error === 'DialogFailed') {
    alert('Failed to show file dialog');
  }
}
```

**Rust Error Handling**:
```rust
#[tauri::command]
fn select_file(title: Option<String>, filters: Vec<FileFilter>) -> Result<SelectFileResponse, String> {
    match show_file_dialog(title, filters) {
        Ok(paths) => Ok(SelectFileResponse { paths }),
        Err(e) => Err("DialogFailed".to_string())
    }
}
```

---

## Summary

This contract defines **25 Tauri commands** across 5 categories:

- **Application Lifecycle**: 3 commands (app_ready, get_database_path, quit_app)
- **Clipboard**: 4 commands (get/set text, get/set image)
- **File Dialogs**: 3 commands (select file, select directory, save file)
- **Menu**: 2 commands (update menu item, show context menu)
- **System Integration**: 13 commands (open URL, show in folder, system info, window title, notifications, etc.)

All commands are **asynchronous** (return `Promise` in JavaScript) and follow a **consistent error handling pattern** (Promise rejection with error string).

**PTY Operations**: Not included in Tauri commands - handled by existing Python backend via WebSocket (same as web version). This maximizes code reuse and avoids duplicating the battle-tested Python PTY service.

**Ready to proceed to implementation**

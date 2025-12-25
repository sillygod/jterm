// Menu commands for native menu bar integration
// Provides platform-specific menu operations and context menu support

use serde::{Deserialize, Serialize};
use tauri::{AppHandle, Manager, Runtime};
use std::sync::Mutex;

/// Platform detection for menu customization
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Platform {
    MacOS,
    Windows,
    Linux,
}

impl Platform {
    /// Detect current platform
    pub fn current() -> Self {
        #[cfg(target_os = "macos")]
        return Platform::MacOS;

        #[cfg(target_os = "windows")]
        return Platform::Windows;

        #[cfg(target_os = "linux")]
        return Platform::Linux;

        #[cfg(not(any(target_os = "macos", target_os = "windows", target_os = "linux")))]
        compile_error!("Unsupported platform");
    }

    /// Check if this is macOS
    pub fn is_macos(&self) -> bool {
        matches!(self, Platform::MacOS)
    }

    /// Check if this is Windows
    pub fn is_windows(&self) -> bool {
        matches!(self, Platform::Windows)
    }

    /// Check if this is Linux
    pub fn is_linux(&self) -> bool {
        matches!(self, Platform::Linux)
    }

    /// Get platform-specific modifier key name
    pub fn modifier_key(&self) -> &'static str {
        match self {
            Platform::MacOS => "Cmd",
            Platform::Windows | Platform::Linux => "Ctrl",
        }
    }
}

/// Menu item state for dynamic updates
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MenuItemState {
    pub id: String,
    pub enabled: bool,
    pub checked: bool,
    pub title: Option<String>,
}

/// Global menu state manager
pub struct MenuState {
    items: Mutex<std::collections::HashMap<String, MenuItemState>>,
}

impl MenuState {
    pub fn new() -> Self {
        Self {
            items: Mutex::new(std::collections::HashMap::new()),
        }
    }

    pub fn update_item(&self, id: String, state: MenuItemState) {
        let mut items = self.items.lock().unwrap();
        items.insert(id, state);
    }

    pub fn get_item(&self, id: &str) -> Option<MenuItemState> {
        let items = self.items.lock().unwrap();
        items.get(id).cloned()
    }
}

/// Update menu item state (enable/disable, check/uncheck, change title)
#[tauri::command]
pub async fn update_menu_item<R: Runtime>(
    app: AppHandle<R>,
    id: String,
    enabled: Option<bool>,
    checked: Option<bool>,
    title: Option<String>,
) -> Result<(), String> {
    // Get menu state from app state
    let state = app.state::<MenuState>();

    // Get current state or create new
    let mut menu_state = state.get_item(&id).unwrap_or(MenuItemState {
        id: id.clone(),
        enabled: true,
        checked: false,
        title: None,
    });

    // Update fields
    if let Some(e) = enabled {
        menu_state.enabled = e;
    }
    if let Some(c) = checked {
        menu_state.checked = c;
    }
    if let Some(t) = title {
        menu_state.title = Some(t);
    }

    // Save state
    state.update_item(id.clone(), menu_state);

    // Note: Actual menu update would require accessing the menu handle
    // This is a simplified version - full implementation would need to
    // rebuild the menu or use Tauri's menu update APIs when available

    Ok(())
}

/// Context menu item definition
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ContextMenuItem {
    pub id: String,
    pub label: String,
    pub enabled: bool,
    pub shortcut: Option<String>,
}

/// Show context menu at cursor position
#[tauri::command]
pub async fn show_context_menu<R: Runtime>(
    _app: AppHandle<R>,
    items: Vec<ContextMenuItem>,
    x: i32,
    y: i32,
) -> Result<String, String> {
    // For now, return a placeholder
    // Full implementation would use Tauri's context menu APIs
    // or platform-specific native menu APIs

    println!("Context menu requested at ({}, {}) with {} items", x, y, items.len());
    for item in &items {
        println!("  - {} ({})", item.label, item.id);
    }

    // Return empty string to indicate no item selected
    // In a full implementation, this would show a native menu and return the selected item ID
    Ok(String::new())
}

/// Get platform information for menu customization
#[tauri::command]
pub async fn get_platform_info() -> Result<serde_json::Value, String> {
    let platform = Platform::current();

    Ok(serde_json::json!({
        "platform": match platform {
            Platform::MacOS => "macos",
            Platform::Windows => "windows",
            Platform::Linux => "linux",
        },
        "is_macos": platform.is_macos(),
        "is_windows": platform.is_windows(),
        "is_linux": platform.is_linux(),
        "modifier_key": platform.modifier_key(),
    }))
}

/// Menu event handler types
pub enum MenuEvent {
    NewTab,
    CloseTab,
    Copy,
    Paste,
    Clear,
    ShowRecordingControls,
    ShowPerformanceMonitor,
    ShowAIAssistant,
    About,
    Preferences,
    Quit,
}

impl MenuEvent {
    /// Get event ID for menu item
    pub fn id(&self) -> &'static str {
        match self {
            MenuEvent::NewTab => "new_tab",
            MenuEvent::CloseTab => "close_tab",
            MenuEvent::Copy => "copy",
            MenuEvent::Paste => "paste",
            MenuEvent::Clear => "clear",
            MenuEvent::ShowRecordingControls => "show_recording_controls",
            MenuEvent::ShowPerformanceMonitor => "show_performance_monitor",
            MenuEvent::ShowAIAssistant => "show_ai_assistant",
            MenuEvent::About => "about",
            MenuEvent::Preferences => "preferences",
            MenuEvent::Quit => "quit",
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_platform_detection() {
        let platform = Platform::current();

        #[cfg(target_os = "macos")]
        assert_eq!(platform, Platform::MacOS);

        #[cfg(target_os = "windows")]
        assert_eq!(platform, Platform::Windows);

        #[cfg(target_os = "linux")]
        assert_eq!(platform, Platform::Linux);
    }

    #[test]
    fn test_modifier_key() {
        #[cfg(target_os = "macos")]
        assert_eq!(Platform::current().modifier_key(), "Cmd");

        #[cfg(any(target_os = "windows", target_os = "linux"))]
        assert_eq!(Platform::current().modifier_key(), "Ctrl");
    }

    #[test]
    fn test_menu_state() {
        let state = MenuState::new();

        let item = MenuItemState {
            id: "test".to_string(),
            enabled: true,
            checked: false,
            title: Some("Test Item".to_string()),
        };

        state.update_item("test".to_string(), item.clone());

        let retrieved = state.get_item("test");
        assert!(retrieved.is_some());
        assert_eq!(retrieved.unwrap().id, "test");
    }
}

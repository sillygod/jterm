// Clipboard commands for image copy/paste functionality
// Uses tauri-plugin-clipboard-manager for native clipboard access

use tauri::command;
use tauri::image::Image;
use tauri_plugin_clipboard_manager::ClipboardExt;
use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize)]
pub struct ImageData {
    pub rgba: Vec<u8>,
    pub width: u32,
    pub height: u32,
}

/// Read image from clipboard
/// Returns RGBA pixel data and dimensions
#[command]
pub async fn get_clipboard_image(app: tauri::AppHandle) -> Result<ImageData, String> {
    log::info!("[Clipboard] Reading image from clipboard");

    match app.clipboard().read_image() {
        Ok(image) => {
            log::info!("[Clipboard] Successfully read image: {}x{}", image.width(), image.height());
            Ok(ImageData {
                rgba: image.rgba().to_vec(),
                width: image.width(),
                height: image.height(),
            })
        }
        Err(e) => {
            log::error!("[Clipboard] Failed to read image: {}", e);
            Err(format!("Failed to read image from clipboard: {}", e))
        }
    }
}

/// Write image to clipboard
/// Accepts RGBA pixel data and dimensions
#[command]
pub async fn set_clipboard_image(
    app: tauri::AppHandle,
    rgba: Vec<u8>,
    width: u32,
    height: u32,
) -> Result<(), String> {
    log::info!("[Clipboard] Writing image to clipboard: {}x{}", width, height);

    // Validate dimensions
    let expected_len = (width * height * 4) as usize;
    if rgba.len() != expected_len {
        let error_msg = format!(
            "Invalid RGBA data length: expected {} bytes for {}x{} image, got {} bytes",
            expected_len, width, height, rgba.len()
        );
        log::error!("[Clipboard] {}", error_msg);
        return Err(error_msg);
    }

    // Create Image from RGBA data
    let image_data = Image::new_owned(rgba, width, height);

    match app.clipboard().write_image(&image_data) {
        Ok(_) => {
            log::info!("[Clipboard] Successfully wrote image to clipboard");
            Ok(())
        }
        Err(e) => {
            log::error!("[Clipboard] Failed to write image: {}", e);
            Err(format!("Failed to write image to clipboard: {}", e))
        }
    }
}

/// Read text from clipboard
#[command]
pub async fn get_clipboard_text(app: tauri::AppHandle) -> Result<String, String> {
    log::info!("[Clipboard] Reading text from clipboard");

    match app.clipboard().read_text() {
        Ok(text) => {
            log::info!("[Clipboard] Successfully read {} characters", text.len());
            Ok(text)
        }
        Err(e) => {
            log::error!("[Clipboard] Failed to read text: {}", e);
            Err(format!("Failed to read text from clipboard: {}", e))
        }
    }
}

/// Write text to clipboard
#[command]
pub async fn set_clipboard_text(app: tauri::AppHandle, text: String) -> Result<(), String> {
    log::info!("[Clipboard] Writing {} characters to clipboard", text.len());

    match app.clipboard().write_text(text) {
        Ok(_) => {
            log::info!("[Clipboard] Successfully wrote text to clipboard");
            Ok(())
        }
        Err(e) => {
            log::error!("[Clipboard] Failed to write text: {}", e);
            Err(format!("Failed to write text to clipboard: {}", e))
        }
    }
}

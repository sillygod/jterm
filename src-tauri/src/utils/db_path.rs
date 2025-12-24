use std::path::PathBuf;
use tauri::{AppHandle, Manager};

/// Get platform-specific database directory path
///
/// - macOS: ~/Library/Application Support/jterm
/// - Windows: %APPDATA%\jterm
/// - Linux: ~/.local/share/jterm
pub fn get_database_directory(app_handle: &AppHandle) -> anyhow::Result<PathBuf> {
    let app_data_dir = app_handle
        .path()
        .app_data_dir()
        .map_err(|e| anyhow::anyhow!("Failed to get app data directory: {}", e))?;

    // Ensure directory exists
    std::fs::create_dir_all(&app_data_dir)?;

    Ok(app_data_dir)
}

/// Get the full database file path
///
/// Returns the path to webterminal.db in the platform-specific directory
pub fn get_database_path(app_handle: &AppHandle) -> anyhow::Result<PathBuf> {
    let db_dir = get_database_directory(app_handle)?;
    let db_path = db_dir.join("webterminal.db");

    Ok(db_path)
}

/// Get the full database file path without AppHandle (for commands)
///
/// Uses dirs crate for platform-specific paths
pub fn get_database_path_static() -> anyhow::Result<PathBuf> {
    let app_data_dir = dirs::data_local_dir()
        .ok_or_else(|| anyhow::anyhow!("Failed to get app data directory"))?
        .join("jterm");

    // Ensure directory exists
    std::fs::create_dir_all(&app_data_dir)?;

    let db_path = app_data_dir.join("webterminal.db");
    Ok(db_path)
}

/// Get platform-specific media directory path
///
/// - macOS: ~/Library/Application Support/jterm/media
/// - Windows: %APPDATA%\jterm\media
/// - Linux: ~/.local/share/jterm/media
pub fn get_media_directory(app_handle: &AppHandle) -> anyhow::Result<PathBuf> {
    let app_data_dir = get_database_directory(app_handle)?;
    let media_dir = app_data_dir.join("media");

    // Ensure directory exists
    std::fs::create_dir_all(&media_dir)?;

    Ok(media_dir)
}

/// Get platform-specific temporary directory path
///
/// - macOS: ~/Library/Caches/jterm/temp
/// - Windows: %LOCALAPPDATA%\jterm\temp
/// - Linux: ~/.cache/jterm/temp
pub fn get_temp_directory(app_handle: &AppHandle) -> anyhow::Result<PathBuf> {
    let cache_dir = app_handle
        .path()
        .app_cache_dir()
        .map_err(|e| anyhow::anyhow!("Failed to get cache directory: {}", e))?;

    let temp_dir = cache_dir.join("temp");

    // Ensure directory exists
    std::fs::create_dir_all(&temp_dir)?;

    Ok(temp_dir)
}

/// Check if web version database exists in current directory
///
/// Used for migration from web to desktop version
pub fn check_web_database_exists() -> Option<PathBuf> {
    let web_db_path = PathBuf::from("webterminal.db");
    if web_db_path.exists() {
        Some(web_db_path)
    } else {
        None
    }
}

/// Get platform name as string
pub fn get_platform_name() -> &'static str {
    #[cfg(target_os = "macos")]
    return "macOS";

    #[cfg(target_os = "windows")]
    return "Windows";

    #[cfg(target_os = "linux")]
    return "Linux";

    #[cfg(not(any(target_os = "macos", target_os = "windows", target_os = "linux")))]
    return "Unknown";
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_platform_name() {
        let platform = get_platform_name();
        assert!(!platform.is_empty());
    }
}

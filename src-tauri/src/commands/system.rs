use serde::{Deserialize, Serialize};
use tauri::State;
use log::{info, error};

use crate::AppState;

#[derive(Debug, Serialize, Deserialize)]
pub struct AppInfo {
    pub version: String,
    pub platform: String,
    pub backend_port: Option<u16>,
    pub database_path: Option<String>,
}

/// Get application info including backend port
#[tauri::command]
pub async fn app_ready(state: State<'_, AppState>) -> Result<AppInfo, String> {
    info!("app_ready command called");

    // Get backend port from state
    let backend_guard = state.python_backend.lock().await;
    let backend_port = backend_guard.as_ref().map(|b| b.port());

    // Get platform info
    let platform = std::env::consts::OS.to_string();

    // Get database path
    let database_path = match crate::utils::db_path::get_database_path_static() {
        Ok(path) => Some(path.to_string_lossy().to_string()),
        Err(e) => {
            error!("Failed to get database path: {}", e);
            None
        }
    };

    Ok(AppInfo {
        version: env!("CARGO_PKG_VERSION").to_string(),
        platform,
        backend_port,
        database_path,
    })
}

/// Quit the application
#[tauri::command]
pub async fn quit_app(
    app: tauri::AppHandle,
    state: State<'_, AppState>,
    force: Option<bool>,
) -> Result<(), String> {
    info!("quit_app command called (force: {:?})", force);

    // Shutdown Python backend
    let mut backend_guard = state.python_backend.lock().await;
    if let Some(mut backend) = backend_guard.take() {
        if let Err(e) = backend.shutdown() {
            error!("Error shutting down Python backend: {}", e);
            if force.unwrap_or(false) {
                // Force quit even if shutdown fails
                app.exit(1);
            } else {
                return Err(format!("Failed to shutdown backend: {}", e));
            }
        }
    }

    state.logger.log_shutdown();

    // Exit the application
    app.exit(0);
    Ok(())
}

use log::{debug, error, info, warn};
use std::fs::OpenOptions;
use std::io::Write;
use std::path::PathBuf;
use tauri::{AppHandle, Manager};

/// Initialize logging for the desktop application
///
/// Sets up logging to both console (in debug mode) and file
pub fn init_logging(app_handle: &AppHandle) -> anyhow::Result<()> {
    let log_dir = get_log_directory(app_handle)?;
    std::fs::create_dir_all(&log_dir)?;

    let log_file = log_dir.join("jterm.log");
    info!("Logging initialized. Log file: {:?}", log_file);

    Ok(())
}

/// Get the platform-specific log directory
fn get_log_directory(app_handle: &AppHandle) -> anyhow::Result<PathBuf> {
    let app_data_dir = app_handle
        .path()
        .app_log_dir()
        .map_err(|e| anyhow::anyhow!("Failed to get log directory: {}", e))?;

    Ok(app_data_dir)
}

/// Log a message to both console and file
pub fn log_message(level: &str, message: &str) {
    match level {
        "debug" => debug!("{}", message),
        "info" => info!("{}", message),
        "warn" => warn!("{}", message),
        "error" => error!("{}", message),
        _ => info!("{}", message),
    }
}

/// Log desktop-specific events
pub struct DesktopLogger {
    log_file: Option<PathBuf>,
}

impl DesktopLogger {
    pub fn new(app_handle: &AppHandle) -> anyhow::Result<Self> {
        let log_dir = get_log_directory(app_handle)?;
        std::fs::create_dir_all(&log_dir)?;
        let log_file = log_dir.join("jterm.log");

        Ok(Self {
            log_file: Some(log_file),
        })
    }

    pub fn log_startup(&self) {
        info!("jterm desktop application starting...");
        self.write_to_file("INFO", "jterm desktop application starting...");
    }

    pub fn log_python_backend_start(&self, port: u16) {
        info!("Python backend starting on port {}", port);
        self.write_to_file("INFO", &format!("Python backend starting on port {}", port));
    }

    pub fn log_python_backend_ready(&self, port: u16) {
        info!("Python backend ready on port {}", port);
        self.write_to_file("INFO", &format!("Python backend ready on port {}", port));
    }

    pub fn log_error(&self, message: &str) {
        error!("{}", message);
        self.write_to_file("ERROR", message);
    }

    pub fn log_shutdown(&self) {
        info!("jterm desktop application shutting down...");
        self.write_to_file("INFO", "jterm desktop application shutting down...");
    }

    fn write_to_file(&self, level: &str, message: &str) {
        if let Some(ref log_file) = self.log_file {
            if let Ok(mut file) = OpenOptions::new()
                .create(true)
                .append(true)
                .open(log_file)
            {
                let timestamp = chrono::Local::now().format("%Y-%m-%d %H:%M:%S");
                let _ = writeln!(file, "[{}] {} - {}", timestamp, level, message);
            }
        }
    }
}

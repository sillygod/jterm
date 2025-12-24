mod commands;
mod python;
mod utils;

use log::{error, info};
use python::launcher::PythonBackend;
use std::sync::Arc;
use tauri::Manager;
use tokio::sync::Mutex;
use utils::logging::DesktopLogger;

/// Application state shared across the application
pub struct AppState {
    python_backend: Arc<Mutex<Option<PythonBackend>>>,
    logger: Arc<DesktopLogger>,
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(
            tauri_plugin_log::Builder::default()
                .level(log::LevelFilter::Info)
                .build(),
        )
        .invoke_handler(tauri::generate_handler![
            commands::system::app_ready,
            commands::system::quit_app,
        ])
        .setup(|app| {
            info!("jterm desktop application initializing...");

            // Initialize desktop logger
            let logger = match DesktopLogger::new(&app.handle()) {
                Ok(logger) => Arc::new(logger),
                Err(e) => {
                    error!("Failed to initialize logger: {}", e);
                    return Err(e.to_string().into());
                }
            };

            logger.log_startup();

            // Initialize application state
            let app_state = AppState {
                python_backend: Arc::new(Mutex::new(None)),
                logger: logger.clone(),
            };

            app.manage(app_state);

            // Launch Python backend asynchronously
            let app_handle = app.handle().clone();
            let backend_mutex = app.state::<AppState>().python_backend.clone();
            let logger_clone = logger.clone();

            tauri::async_runtime::spawn(async move {
                match PythonBackend::launch(&app_handle).await {
                    Ok(backend) => {
                        let port = backend.port();
                        let base_url = backend.base_url().to_string();
                        logger_clone.log_python_backend_ready(port);

                        // Store backend in state
                        let mut backend_guard = backend_mutex.lock().await;
                        *backend_guard = Some(backend);

                        // Update window URL to point to Python backend
                        if let Some(window) = app_handle.get_webview_window("main") {
                            if let Err(e) = window.eval(&format!(
                                "window.location.href = '{}';",
                                base_url
                            )) {
                                error!("Failed to navigate to backend URL: {}", e);
                            }
                        }
                    }
                    Err(e) => {
                        error!("Failed to launch Python backend: {}", e);
                        logger_clone.log_error(&format!("Failed to launch Python backend: {}", e));

                        // Exit application with error
                        eprintln!("FATAL: Failed to start jterm backend: {}", e);
                        std::process::exit(1);
                    }
                }
            });

            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                info!("Window close requested, shutting down...");

                // Shutdown Python backend
                let app_state = window.state::<AppState>();
                let backend_mutex = app_state.python_backend.clone();
                let logger = app_state.logger.clone();

                tauri::async_runtime::block_on(async move {
                    let mut backend_guard = backend_mutex.lock().await;
                    if let Some(mut backend) = backend_guard.take() {
                        if let Err(e) = backend.shutdown() {
                            error!("Error shutting down Python backend: {}", e);
                        }
                    }
                });

                logger.log_shutdown();
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

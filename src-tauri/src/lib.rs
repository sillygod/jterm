mod commands;
mod python;
mod utils;

use commands::MenuState;
use log::{error, info};
use python::launcher::PythonBackend;
use std::sync::Arc;
use tauri::menu::{Menu, MenuItem, PredefinedMenuItem, Submenu};
use tauri::Manager;
use tokio::sync::Mutex;
use utils::logging::DesktopLogger;

/// Application state shared across the application
pub struct AppState {
    python_backend: Arc<Mutex<Option<PythonBackend>>>,
    logger: Arc<DesktopLogger>,
}

/// Build platform-specific application menu
fn build_menu(app: &tauri::AppHandle) -> Result<Menu<tauri::Wry>, tauri::Error> {
    let menu = Menu::new(app)?;

    // Detect platform for platform-specific menus
    #[cfg(target_os = "macos")]
    {
        // macOS Application Menu (jterm)
        let app_menu = Submenu::new(
            app,
            "jterm",
            true,
        )?;

        app_menu.append(&PredefinedMenuItem::about(app, None, None)?)?;
        app_menu.append(&PredefinedMenuItem::separator(app)?)?;
        app_menu.append(&MenuItem::with_id(app, "preferences", "Preferences...", true, Some("Cmd+,"))?)?;
        app_menu.append(&PredefinedMenuItem::separator(app)?)?;
        app_menu.append(&PredefinedMenuItem::hide(app, None)?)?;
        app_menu.append(&PredefinedMenuItem::hide_others(app, None)?)?;
        app_menu.append(&PredefinedMenuItem::show_all(app, None)?)?;
        app_menu.append(&PredefinedMenuItem::separator(app)?)?;
        app_menu.append(&PredefinedMenuItem::quit(app, None)?)?;

        menu.append(&app_menu)?;
    }

    // File Menu (all platforms)
    let file_menu = Submenu::new(app, "File", true)?;

    #[cfg(target_os = "macos")]
    let new_tab_shortcut = Some("Cmd+N");
    #[cfg(not(target_os = "macos"))]
    let new_tab_shortcut = Some("Ctrl+N");

    #[cfg(target_os = "macos")]
    let close_tab_shortcut = Some("Cmd+W");
    #[cfg(not(target_os = "macos"))]
    let close_tab_shortcut = Some("Ctrl+W");

    file_menu.append(&MenuItem::with_id(app, "new_tab", "New Tab", true, new_tab_shortcut)?)?;
    file_menu.append(&MenuItem::with_id(app, "close_tab", "Close Tab", true, close_tab_shortcut)?)?;

    #[cfg(not(target_os = "macos"))]
    {
        file_menu.append(&PredefinedMenuItem::separator(app)?)?;
        file_menu.append(&PredefinedMenuItem::quit(app, None)?)?;
    }

    menu.append(&file_menu)?;

    // Edit Menu (all platforms)
    let edit_menu = Submenu::new(app, "Edit", true)?;

    #[cfg(target_os = "macos")]
    let copy_shortcut = Some("Cmd+C");
    #[cfg(not(target_os = "macos"))]
    let copy_shortcut = Some("Ctrl+C");

    #[cfg(target_os = "macos")]
    let paste_shortcut = Some("Cmd+V");
    #[cfg(not(target_os = "macos"))]
    let paste_shortcut = Some("Ctrl+V");

    edit_menu.append(&MenuItem::with_id(app, "copy", "Copy", true, copy_shortcut)?)?;
    edit_menu.append(&MenuItem::with_id(app, "paste", "Paste", true, paste_shortcut)?)?;
    edit_menu.append(&PredefinedMenuItem::separator(app)?)?;
    edit_menu.append(&MenuItem::with_id(app, "clear", "Clear", true, None::<&str>)?)?;

    menu.append(&edit_menu)?;

    // View Menu (all platforms)
    let view_menu = Submenu::new(app, "View", true)?;

    view_menu.append(&MenuItem::with_id(app, "show_recording_controls", "Recording Controls", true, None::<&str>)?)?;
    view_menu.append(&MenuItem::with_id(app, "show_performance_monitor", "Performance Monitor", true, None::<&str>)?)?;
    view_menu.append(&MenuItem::with_id(app, "show_ai_assistant", "AI Assistant", true, None::<&str>)?)?;

    menu.append(&view_menu)?;

    // Help Menu (Windows/Linux only - macOS uses app menu)
    #[cfg(not(target_os = "macos"))]
    {
        let help_menu = Submenu::new(app, "Help", true)?;
        help_menu.append(&PredefinedMenuItem::about(app, None, None)?)?;
        menu.append(&help_menu)?;
    }

    Ok(menu)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(
            tauri_plugin_log::Builder::default()
                .level(log::LevelFilter::Info)
                .build(),
        )
        .plugin(tauri_plugin_clipboard_manager::init())
        .invoke_handler(tauri::generate_handler![
            commands::system::app_ready,
            commands::system::quit_app,
            commands::menu::update_menu_item,
            commands::menu::show_context_menu,
            commands::menu::get_platform_info,
            commands::clipboard::get_clipboard_image,
            commands::clipboard::set_clipboard_image,
            commands::clipboard::get_clipboard_text,
            commands::clipboard::set_clipboard_text,
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

            // Initialize menu state
            app.manage(MenuState::new());

            // Build and set application menu
            match build_menu(&app.handle()) {
                Ok(menu) => {
                    if let Err(e) = app.set_menu(menu) {
                        error!("Failed to set application menu: {}", e);
                    }
                }
                Err(e) => {
                    error!("Failed to build application menu: {}", e);
                }
            }

            // Launch Python backend asynchronously
            let app_handle = app.handle().clone();
            let backend_mutex = app.state::<AppState>().python_backend.clone();
            let logger_clone = logger.clone();

            tauri::async_runtime::spawn(async move {
                info!("Starting Python backend...");

                match PythonBackend::launch(&app_handle).await {
                    Ok(backend) => {
                        let port = backend.port();
                        let base_url = backend.base_url().to_string();
                        logger_clone.log_python_backend_ready(port);

                        // Store backend in state
                        let mut backend_guard = backend_mutex.lock().await;
                        *backend_guard = Some(backend);

                        info!("Python backend ready at {}", base_url);

                        // Navigate main window directly to Python backend
                        if let Some(window) = app_handle.get_webview_window("main") {
                            info!("Navigating to Python backend URL: {}", base_url);

                            match window.navigate(tauri::Url::parse(&base_url).unwrap()) {
                                Ok(_) => {
                                    info!("Successfully navigated to backend");

                                    // Show window after navigation
                                    if let Err(e) = window.show() {
                                        error!("Failed to show window: {}", e);
                                    }

                                    // Inject initialization script to expose Tauri APIs for remote URLs
                                    // Tauri v2 doesn't automatically expose __TAURI__ for remote URLs
                                    let init_script = r#"
                                        (function() {
                                            console.log('[Tauri] Initializing Tauri API for remote URL');
                                            console.log('[Tauri] window.__TAURI__ available:', typeof window.__TAURI__ !== 'undefined');
                                            if (typeof window.__TAURI__ !== 'undefined') {
                                                console.log('[Tauri] __TAURI__ keys:', Object.keys(window.__TAURI__));
                                            }
                                        })();
                                    "#;

                                    if let Err(e) = window.eval(init_script) {
                                        error!("Failed to run initialization script: {}", e);
                                    }

                                    info!("Tauri APIs should be available at window.__TAURI__");
                                }
                                Err(e) => {
                                    error!("Failed to navigate to backend: {}", e);
                                }
                            }
                        }
                    }
                    Err(e) => {
                        error!("Failed to launch Python backend: {}", e);
                        logger_clone.log_error(&format!("Failed to launch Python backend: {}", e));

                        // Show error dialog
                        if let Some(window) = app_handle.get_webview_window("main") {
                            let _ = window.eval(&format!(
                                r#"alert('Failed to start jterm backend:\n\n{}');"#,
                                e.to_string().replace("'", "\\'")
                            ));
                        }

                        // Exit application with error
                        eprintln!("FATAL: Failed to start jterm backend: {}", e);
                        std::process::exit(1);
                    }
                }
            });

            Ok(())
        })
        .on_menu_event(|app, event| {
            let event_id = event.id().as_ref();
            info!("Menu event: {}", event_id);

            // Get the main window to send events to frontend
            if let Some(window) = app.get_webview_window("main") {
                // Use eval to dispatch a custom DOM event instead of Tauri event
                // This works with remote URLs like http://localhost:8000
                let script = format!(
                    r#"
                    (function() {{
                        const event = new CustomEvent('tauri-menu-event', {{
                            detail: {{ id: '{}' }}
                        }});
                        window.dispatchEvent(event);
                        console.log('[Tauri] Dispatched menu event:', '{}');
                    }})();
                    "#,
                    event_id, event_id
                );

                if let Err(e) = window.eval(&script) {
                    error!("Failed to dispatch menu event: {}", e);
                }
            }
        })
        .on_window_event(|window, event| {
            match event {
                tauri::WindowEvent::CloseRequested { .. } => {
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
                _ => {}
            }
        })
        .on_page_load(|webview, _payload| {
            // Inject debug script to verify Tauri API availability
            let script = r#"
                console.log('[Tauri Page Load] Checking API availability...');
                console.log('[Tauri Page Load] window.__TAURI__:', typeof window.__TAURI__);
                if (typeof window.__TAURI__ !== 'undefined') {
                    console.log('[Tauri Page Load] __TAURI__ keys:', Object.keys(window.__TAURI__));

                    // Log available namespaces
                    for (const key in window.__TAURI__) {
                        console.log('[Tauri Page Load] __TAURI__.' + key + ':', typeof window.__TAURI__[key]);
                        if (typeof window.__TAURI__[key] === 'object' && window.__TAURI__[key] !== null) {
                            console.log('[Tauri Page Load]   -> keys:', Object.keys(window.__TAURI__[key]));
                        }
                    }
                }
            "#;

            if let Err(e) = webview.eval(script) {
                error!("Failed to run page load debug script: {}", e);
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

use anyhow::{Context, Result};
use log::{debug, info, warn, error};
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use tauri::AppHandle;

use crate::python::health::{find_available_port, wait_for_backend_ready, HealthCheckConfig};
use crate::utils::db_path::get_database_path;

/// Python backend process manager
pub struct PythonBackend {
    process: Option<Child>,
    port: u16,
    base_url: String,
}

impl PythonBackend {
    /// Launch the Python backend as a subprocess
    ///
    /// Finds an available port, starts the Python backend using bundled venv,
    /// and waits for the backend to be ready
    pub async fn launch(app_handle: &AppHandle) -> Result<Self> {
        info!("Launching Python backend...");

        // Find available port in range 8000-9000
        let port = find_available_port(8000, 9000)
            .await
            .context("No available ports found in range 8000-9000")?;

        info!("Using port {} for Python backend", port);

        // Get database path and pass as environment variable
        let db_path = get_database_path(app_handle)?;
        info!("Database path: {:?}", db_path);

        // Get the bundled Python interpreter and app root
        let (python_path, app_root) = get_python_paths(app_handle)?;
        info!("Python interpreter: {:?}", python_path);
        info!("App root: {:?}", app_root);

        // Verify paths exist
        if !python_path.exists() {
            return Err(anyhow::anyhow!(
                "Python interpreter not found at: {:?}",
                python_path
            ));
        }
        if !app_root.exists() {
            return Err(anyhow::anyhow!(
                "App root directory not found at: {:?}",
                app_root
            ));
        }

        // Launch Python backend process using venv Python
        let mut command = Command::new(&python_path);
        command
            .arg("-m")
            .arg("uvicorn")
            .arg("src.main:app")
            .arg("--host")
            .arg("127.0.0.1")
            .arg("--port")
            .arg(port.to_string())
            .current_dir(&app_root)
            .env("JTERM_DATABASE_PATH", db_path.to_str().unwrap())
            .env("JTERM_DESKTOP_MODE", "1")
            .stdout(Stdio::piped())
            .stderr(Stdio::piped());

        debug!("Starting Python backend with command: {:?}", command);

        let child = command
            .spawn()
            .context("Failed to spawn Python backend process")?;

        info!("Python backend process started (PID: {:?})", child.id());

        // Wait for backend to be ready
        let health_config = HealthCheckConfig::default();
        wait_for_backend_ready(port, Some(health_config))
            .await
            .context("Python backend failed health check")?;

        let base_url = format!("http://localhost:{}", port);
        info!("Python backend ready at {}", base_url);

        Ok(Self {
            process: Some(child),
            port,
            base_url,
        })
    }

    /// Get the backend base URL (e.g., "http://localhost:8000")
    pub fn base_url(&self) -> &str {
        &self.base_url
    }

    /// Get the backend port
    pub fn port(&self) -> u16 {
        self.port
    }

    /// Check if the backend process is still running
    pub fn is_running(&mut self) -> bool {
        if let Some(ref mut child) = self.process {
            match child.try_wait() {
                Ok(Some(_)) => false, // Process has exited
                Ok(None) => true,     // Process is still running
                Err(_) => false,      // Error checking status
            }
        } else {
            false
        }
    }

    /// Gracefully shutdown the Python backend
    pub fn shutdown(&mut self) -> Result<()> {
        info!("Shutting down Python backend...");

        if let Some(mut child) = self.process.take() {
            // Try graceful shutdown first (platform-specific)
            #[cfg(unix)]
            {
                // Send SIGTERM for graceful shutdown
                unsafe {
                    libc::kill(child.id() as i32, libc::SIGTERM);
                }
                // Wait up to 5 seconds for graceful shutdown
                for _ in 0..50 {
                    match child.try_wait() {
                        Ok(Some(_)) => {
                            info!("Python backend shut down gracefully");
                            return Ok(());
                        }
                        Ok(None) => {
                            std::thread::sleep(std::time::Duration::from_millis(100));
                        }
                        Err(e) => {
                            warn!("Error checking backend process status: {}", e);
                            break;
                        }
                    }
                }
            }

            // Force kill if graceful shutdown failed
            warn!("Force killing Python backend process");
            child.kill().context("Failed to kill Python backend")?;
            child.wait().context("Failed to wait for Python backend")?;
            info!("Python backend process terminated");
        }

        Ok(())
    }
}

impl Drop for PythonBackend {
    fn drop(&mut self) {
        if let Err(e) = self.shutdown() {
            error!("Error shutting down Python backend: {}", e);
        }
    }
}

/// Get the path to the bundled Python interpreter and app root directory
/// Returns (python_path, app_root)
fn get_python_paths(_app_handle: &AppHandle) -> Result<(PathBuf, PathBuf)> {
    // In development mode, use the project's venv
    // In production, use the bundled venv

    #[cfg(debug_assertions)]
    {
        let python_name = get_python_executable_name();

        // Try to find the project root and venv
        let possible_roots = vec![
            // When running from project root
            std::env::current_dir()?,
            // When running from src-tauri directory
            std::env::current_dir()?.parent().map(|p| p.to_path_buf()).unwrap_or_default(),
        ];

        for root in possible_roots {
            let venv_python = root.join("venv").join("bin").join(python_name);
            if venv_python.exists() && root.join("src").exists() {
                debug!("Found Python venv at: {:?}", venv_python);
                debug!("App root: {:?}", root);
                return Ok((venv_python, root));
            }
        }

        Err(anyhow::anyhow!(
            "Python venv not found in development mode. Make sure venv exists with: python -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
        ))
    }

    #[cfg(not(debug_assertions))]
    {
        // Production mode: Use Tauri's resource directory
        let resource_dir = app_handle
            .path()
            .resource_dir()
            .context("Failed to get resource directory")?;

        let python_name = get_python_executable_name();
        let python_path = resource_dir.join("venv").join("bin").join(python_name);
        let app_root = resource_dir.clone();

        if !python_path.exists() {
            return Err(anyhow::anyhow!(
                "Python interpreter not found at: {:?}",
                python_path
            ));
        }

        Ok((python_path, app_root))
    }
}

/// Get platform-specific Python executable name
fn get_python_executable_name() -> &'static str {
    #[cfg(target_os = "windows")]
    return "python.exe";

    #[cfg(not(target_os = "windows"))]
    return "python3";
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_python_executable_name() {
        let name = get_python_executable_name();
        assert!(!name.is_empty());
    }
}

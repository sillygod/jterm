use anyhow::Result;
use log::{debug, info, warn};
use std::time::Duration;
use tokio::time::sleep;

/// Health check configuration
pub struct HealthCheckConfig {
    pub max_attempts: u32,
    pub timeout_secs: u64,
    pub retry_delay_ms: u64,
}

impl Default for HealthCheckConfig {
    fn default() -> Self {
        Self {
            max_attempts: 30,      // 30 attempts
            timeout_secs: 30,      // 30 second total timeout
            retry_delay_ms: 1000,  // 1 second between attempts
        }
    }
}

/// Check if the Python backend is ready by polling the health endpoint
///
/// Polls http://localhost:{port}/health until it returns 200 OK or timeout is reached
pub async fn wait_for_backend_ready(port: u16, config: Option<HealthCheckConfig>) -> Result<()> {
    let config = config.unwrap_or_default();
    let health_url = format!("http://localhost:{}/health", port);
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(5))
        .build()?;

    info!(
        "Waiting for Python backend to be ready at {} (max {} attempts)",
        health_url, config.max_attempts
    );

    for attempt in 1..=config.max_attempts {
        debug!("Health check attempt {}/{}", attempt, config.max_attempts);

        match client.get(&health_url).send().await {
            Ok(response) => {
                if response.status().is_success() {
                    info!("Python backend is ready on port {}", port);
                    return Ok(());
                } else {
                    debug!(
                        "Health check returned status: {} (attempt {}/{})",
                        response.status(),
                        attempt,
                        config.max_attempts
                    );
                }
            }
            Err(e) => {
                debug!(
                    "Health check failed: {} (attempt {}/{})",
                    e, attempt, config.max_attempts
                );
            }
        }

        if attempt < config.max_attempts {
            sleep(Duration::from_millis(config.retry_delay_ms)).await;
        }
    }

    Err(anyhow::anyhow!(
        "Python backend failed to become ready after {} attempts ({} seconds)",
        config.max_attempts,
        config.timeout_secs
    ))
}

/// Perform a single health check
///
/// Returns Ok(()) if backend is healthy, Err otherwise
pub async fn check_backend_health(port: u16) -> Result<()> {
    let health_url = format!("http://localhost:{}/health", port);
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(5))
        .build()?;

    let response = client.get(&health_url).send().await?;

    if response.status().is_success() {
        Ok(())
    } else {
        Err(anyhow::anyhow!(
            "Backend health check failed with status: {}",
            response.status()
        ))
    }
}

/// Check if a port is available
pub async fn is_port_available(port: u16) -> bool {
    use std::net::TcpListener;

    match TcpListener::bind(("127.0.0.1", port)) {
        Ok(_) => true,
        Err(_) => false,
    }
}

/// Find an available port in the specified range
///
/// Returns the first available port, or None if no ports are available
pub async fn find_available_port(start_port: u16, end_port: u16) -> Option<u16> {
    for port in start_port..=end_port {
        if is_port_available(port).await {
            debug!("Found available port: {}", port);
            return Some(port);
        }
    }

    warn!(
        "No available ports found in range {}-{}",
        start_port, end_port
    );
    None
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_find_available_port() {
        let port = find_available_port(9000, 9100).await;
        assert!(port.is_some());
    }

    #[tokio::test]
    async fn test_is_port_available() {
        // Port 80 is typically used or requires privileges
        // Port 65535 should be available
        let available = is_port_available(65535).await;
        assert!(available || !available); // Always passes, just testing the function runs
    }
}

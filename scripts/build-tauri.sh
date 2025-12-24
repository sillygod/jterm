#!/bin/bash
# build-tauri.sh - Complete desktop build workflow for jterm
# Builds Python backend with PyInstaller, then builds Tauri desktop application
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "=========================================="
echo "jterm Desktop Application Builder"
echo "=========================================="

# Change to project root
cd "${PROJECT_ROOT}"

# Detect platform
detect_platform() {
    case "$(uname -s)" in
        Darwin*)
            PLATFORM="macos"
            case "$(uname -m)" in
                arm64)
                    RUST_TARGET="aarch64-apple-darwin"
                    ;;
                x86_64)
                    RUST_TARGET="x86_64-apple-darwin"
                    ;;
                *)
                    echo "Error: Unsupported macOS architecture: $(uname -m)"
                    exit 1
                    ;;
            esac
            ;;
        Linux*)
            PLATFORM="linux"
            case "$(uname -m)" in
                x86_64|amd64)
                    RUST_TARGET="x86_64-unknown-linux-gnu"
                    ;;
                aarch64|arm64)
                    RUST_TARGET="aarch64-unknown-linux-gnu"
                    ;;
                *)
                    echo "Error: Unsupported Linux architecture: $(uname -m)"
                    exit 1
                    ;;
            esac
            ;;
        MINGW*|MSYS*|CYGWIN*|Windows_NT)
            PLATFORM="windows"
            RUST_TARGET="x86_64-pc-windows-msvc"
            ;;
        *)
            echo "Error: Unsupported operating system: $(uname -s)"
            exit 1
            ;;
    esac

    echo "Platform: ${PLATFORM}"
    echo "Rust target: ${RUST_TARGET}"
}

# Check required tools
check_dependencies() {
    echo "Checking dependencies..."

    # Check Rust
    if ! command -v rustc &> /dev/null; then
        echo "Error: Rust not found. Install from https://rustup.rs"
        exit 1
    fi
    RUST_VERSION=$(rustc --version | cut -d' ' -f2)
    echo "Rust version: ${RUST_VERSION}"

    # Check Cargo
    if ! command -v cargo &> /dev/null; then
        echo "Error: Cargo not found. Install Rust from https://rustup.rs"
        exit 1
    fi

    # Check Tauri CLI
    if ! cargo tauri --version &> /dev/null; then
        echo "Error: Tauri CLI not found. Install with: cargo install tauri-cli"
        exit 1
    fi
    TAURI_VERSION=$(cargo tauri --version 2>&1 | head -1)
    echo "Tauri CLI version: ${TAURI_VERSION}"

    # Check Node.js (for frontend build)
    if ! command -v node &> /dev/null; then
        echo "Warning: Node.js not found. Frontend build may fail."
    else
        NODE_VERSION=$(node --version)
        echo "Node.js version: ${NODE_VERSION}"
    fi

    # Check npm
    if ! command -v npm &> /dev/null; then
        echo "Warning: npm not found. Frontend build may fail."
    else
        NPM_VERSION=$(npm --version)
        echo "npm version: ${NPM_VERSION}"
    fi

    # Platform-specific checks
    if [[ "${PLATFORM}" == "linux" ]]; then
        # Check for required Linux dependencies
        if ! pkg-config --exists webkit2gtk-4.0 2>/dev/null && ! pkg-config --exists webkit2gtk-4.1 2>/dev/null; then
            echo "Warning: WebKitGTK not found. Install with:"
            echo "  Ubuntu/Debian: sudo apt install libwebkit2gtk-4.0-dev"
            echo "  Fedora: sudo dnf install webkit2gtk4.0-devel"
        fi
    fi
}

# Build Python backend
build_python() {
    echo ""
    echo "=========================================="
    echo "Step 1: Building Python backend"
    echo "=========================================="

    if [[ ! -f "${SCRIPT_DIR}/build-python.sh" ]]; then
        echo "Error: build-python.sh not found!"
        exit 1
    fi

    # Run Python build script
    "${SCRIPT_DIR}/build-python.sh" --skip-verify

    # Verify output exists
    PYTHON_BINARY="src-tauri/binaries/jterm-backend-${RUST_TARGET}"
    if [[ "${PLATFORM}" == "windows" ]]; then
        PYTHON_BINARY="${PYTHON_BINARY}.exe"
    fi

    if [[ ! -f "${PYTHON_BINARY}" ]]; then
        echo "Error: Python backend build failed - binary not found at ${PYTHON_BINARY}"
        exit 1
    fi

    echo "Python backend built successfully: ${PYTHON_BINARY}"
}

# Install Node.js dependencies
install_npm_deps() {
    echo ""
    echo "=========================================="
    echo "Step 2: Installing Node.js dependencies"
    echo "=========================================="

    if [[ -f "package.json" ]]; then
        if [[ -d "node_modules" ]]; then
            echo "Node modules already installed. Skipping..."
        else
            npm install
        fi
    else
        echo "No package.json found. Skipping npm install..."
    fi
}

# Build Tauri application
build_tauri() {
    echo ""
    echo "=========================================="
    echo "Step 3: Building Tauri application"
    echo "=========================================="

    # Build arguments
    TAURI_ARGS=()

    if [[ "${DEBUG_BUILD}" == "true" ]]; then
        echo "Building in debug mode..."
        TAURI_ARGS+=(--debug)
    else
        echo "Building in release mode..."
    fi

    if [[ -n "${TARGET}" ]]; then
        echo "Cross-compiling for target: ${TARGET}"
        TAURI_ARGS+=(--target "${TARGET}")
    fi

    # Run Tauri build
    cargo tauri build "${TAURI_ARGS[@]}"
}

# Find and report build outputs
report_outputs() {
    echo ""
    echo "=========================================="
    echo "Build Complete!"
    echo "=========================================="

    echo ""
    echo "Build outputs:"

    # Find bundle directory
    if [[ "${DEBUG_BUILD}" == "true" ]]; then
        BUNDLE_DIR="src-tauri/target/debug/bundle"
    else
        BUNDLE_DIR="src-tauri/target/release/bundle"
    fi

    if [[ -n "${TARGET}" ]]; then
        if [[ "${DEBUG_BUILD}" == "true" ]]; then
            BUNDLE_DIR="src-tauri/target/${TARGET}/debug/bundle"
        else
            BUNDLE_DIR="src-tauri/target/${TARGET}/release/bundle"
        fi
    fi

    if [[ ! -d "${BUNDLE_DIR}" ]]; then
        echo "Bundle directory not found at ${BUNDLE_DIR}"
        echo "Check src-tauri/target/ for outputs."
        return
    fi

    # List outputs by platform
    case "${PLATFORM}" in
        macos)
            if [[ -d "${BUNDLE_DIR}/dmg" ]]; then
                echo "  DMG: $(ls -1 "${BUNDLE_DIR}/dmg"/*.dmg 2>/dev/null | head -1)"
            fi
            if [[ -d "${BUNDLE_DIR}/macos" ]]; then
                echo "  App: $(ls -1 "${BUNDLE_DIR}/macos"/*.app 2>/dev/null | head -1)"
            fi
            ;;
        windows)
            if [[ -d "${BUNDLE_DIR}/msi" ]]; then
                echo "  MSI: $(ls -1 "${BUNDLE_DIR}/msi"/*.msi 2>/dev/null | head -1)"
            fi
            if [[ -d "${BUNDLE_DIR}/nsis" ]]; then
                echo "  NSIS: $(ls -1 "${BUNDLE_DIR}/nsis"/*.exe 2>/dev/null | head -1)"
            fi
            ;;
        linux)
            if [[ -d "${BUNDLE_DIR}/appimage" ]]; then
                echo "  AppImage: $(ls -1 "${BUNDLE_DIR}/appimage"/*.AppImage 2>/dev/null | head -1)"
            fi
            if [[ -d "${BUNDLE_DIR}/deb" ]]; then
                echo "  DEB: $(ls -1 "${BUNDLE_DIR}/deb"/*.deb 2>/dev/null | head -1)"
            fi
            if [[ -d "${BUNDLE_DIR}/rpm" ]]; then
                echo "  RPM: $(ls -1 "${BUNDLE_DIR}/rpm"/*.rpm 2>/dev/null | head -1)"
            fi
            ;;
    esac

    echo ""
    echo "To run the application:"
    case "${PLATFORM}" in
        macos)
            echo "  open \"${BUNDLE_DIR}/macos/jterm.app\""
            ;;
        windows)
            echo "  Start the MSI installer or run the NSIS executable"
            ;;
        linux)
            echo "  chmod +x \"${BUNDLE_DIR}/appimage/jterm.AppImage\" && \"${BUNDLE_DIR}/appimage/jterm.AppImage\""
            ;;
    esac
}

# Clean build artifacts
clean_build() {
    echo "Cleaning build artifacts..."

    # Clean Python build artifacts
    rm -rf build/ dist/ *.spec

    # Clean Tauri build artifacts
    rm -rf src-tauri/target/

    # Clean bundled Python binary
    rm -rf src-tauri/binaries/jterm-backend-*

    echo "Clean complete."
}

# Development mode
dev_mode() {
    echo "Starting development mode..."

    # Check if Python backend binary exists
    PYTHON_BINARY="src-tauri/binaries/jterm-backend-${RUST_TARGET}"
    if [[ "${PLATFORM}" == "windows" ]]; then
        PYTHON_BINARY="${PYTHON_BINARY}.exe"
    fi

    if [[ ! -f "${PYTHON_BINARY}" ]]; then
        echo "Python backend binary not found. Building..."
        build_python
    fi

    # Start Tauri dev server
    cargo tauri dev
}

# Show help
show_help() {
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  build       Build the desktop application (default)"
    echo "  dev         Start development mode with hot reload"
    echo "  clean       Clean all build artifacts"
    echo "  python      Build only the Python backend"
    echo "  help        Show this help message"
    echo ""
    echo "Options:"
    echo "  --debug       Build in debug mode (faster, larger binary)"
    echo "  --target T    Cross-compile for target T (e.g., x86_64-apple-darwin)"
    echo "  --skip-python Skip Python backend build (use existing binary)"
    echo ""
    echo "Examples:"
    echo "  $0                    # Build release version"
    echo "  $0 --debug            # Build debug version"
    echo "  $0 dev                # Start development mode"
    echo "  $0 clean              # Clean all artifacts"
    echo "  $0 python             # Build only Python backend"
    echo ""
}

# Main execution
main() {
    detect_platform

    # Parse command
    COMMAND="build"
    DEBUG_BUILD=false
    SKIP_PYTHON=false
    TARGET=""

    while [[ $# -gt 0 ]]; do
        case $1 in
            build)
                COMMAND="build"
                shift
                ;;
            dev)
                COMMAND="dev"
                shift
                ;;
            clean)
                COMMAND="clean"
                shift
                ;;
            python)
                COMMAND="python"
                shift
                ;;
            help|-h|--help)
                show_help
                exit 0
                ;;
            --debug)
                DEBUG_BUILD=true
                shift
                ;;
            --target)
                TARGET="$2"
                shift 2
                ;;
            --skip-python)
                SKIP_PYTHON=true
                shift
                ;;
            *)
                echo "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done

    # Execute command
    case "${COMMAND}" in
        build)
            check_dependencies
            if [[ "${SKIP_PYTHON}" != "true" ]]; then
                build_python
            fi
            install_npm_deps
            build_tauri
            report_outputs
            ;;
        dev)
            check_dependencies
            dev_mode
            ;;
        clean)
            clean_build
            ;;
        python)
            check_dependencies
            build_python
            ;;
        *)
            echo "Unknown command: ${COMMAND}"
            show_help
            exit 1
            ;;
    esac
}

main "$@"

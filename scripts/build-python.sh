#!/bin/bash
# build-python.sh - PyInstaller bundling script for jterm desktop application
# Creates platform-specific Python backend executable
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "=========================================="
echo "jterm Python Backend Builder"
echo "=========================================="

# Change to project root
cd "${PROJECT_ROOT}"

# Detect platform and set output name
detect_platform() {
    case "$(uname -s)" in
        Darwin*)
            PLATFORM="macos"
            case "$(uname -m)" in
                arm64)
                    OUTPUT_NAME="jterm-backend-aarch64-apple-darwin"
                    ;;
                x86_64)
                    OUTPUT_NAME="jterm-backend-x86_64-apple-darwin"
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
                    OUTPUT_NAME="jterm-backend-x86_64-unknown-linux-gnu"
                    ;;
                aarch64|arm64)
                    OUTPUT_NAME="jterm-backend-aarch64-unknown-linux-gnu"
                    ;;
                *)
                    echo "Error: Unsupported Linux architecture: $(uname -m)"
                    exit 1
                    ;;
            esac
            ;;
        MINGW*|MSYS*|CYGWIN*|Windows_NT)
            PLATFORM="windows"
            OUTPUT_NAME="jterm-backend-x86_64-pc-windows-msvc.exe"
            ;;
        *)
            echo "Error: Unsupported operating system: $(uname -s)"
            exit 1
            ;;
    esac

    echo "Platform: ${PLATFORM}"
    echo "Output name: ${OUTPUT_NAME}"
}

# Check for virtual environment
activate_venv() {
    if [[ -d "venv" ]]; then
        echo "Activating virtual environment..."
        if [[ "${PLATFORM}" == "windows" ]]; then
            source venv/Scripts/activate
        else
            source venv/bin/activate
        fi
    elif [[ -d ".venv" ]]; then
        echo "Activating .venv virtual environment..."
        if [[ "${PLATFORM}" == "windows" ]]; then
            source .venv/Scripts/activate
        else
            source .venv/bin/activate
        fi
    else
        echo "Warning: No virtual environment found. Using system Python."
    fi
}

# Check dependencies
check_dependencies() {
    echo "Checking dependencies..."

    # Check Python version
    PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
    PYTHON_MAJOR=$(echo "${PYTHON_VERSION}" | cut -d. -f1)
    PYTHON_MINOR=$(echo "${PYTHON_VERSION}" | cut -d. -f2)

    if [[ "${PYTHON_MAJOR}" -lt 3 ]] || [[ "${PYTHON_MAJOR}" -eq 3 && "${PYTHON_MINOR}" -lt 11 ]]; then
        echo "Error: Python 3.11+ required, found ${PYTHON_VERSION}"
        exit 1
    fi
    echo "Python version: ${PYTHON_VERSION}"

    # Check PyInstaller
    if ! command -v pyinstaller &> /dev/null; then
        echo "Error: PyInstaller not found. Install with: pip install pyinstaller>=6.0"
        exit 1
    fi
    PYINSTALLER_VERSION=$(pyinstaller --version 2>&1)
    echo "PyInstaller version: ${PYINSTALLER_VERSION}"
}

# Clean previous builds
clean_build() {
    echo "Cleaning previous builds..."
    rm -rf build/ dist/ *.spec
    rm -rf src-tauri/binaries/jterm-backend-*
}

# Run PyInstaller
run_pyinstaller() {
    echo "Running PyInstaller..."

    # Base PyInstaller arguments
    PYINSTALLER_ARGS=(
        --name "${OUTPUT_NAME}"
        --onefile
        --noconfirm
        --clean
        --log-level WARN
        --paths .
        --paths src
    )

    # Add data files if they exist
    if [[ -d "templates" ]]; then
        PYINSTALLER_ARGS+=(--add-data "templates:templates")
    fi

    if [[ -d "static" ]]; then
        PYINSTALLER_ARGS+=(--add-data "static:static")
    fi

    if [[ -d "migrations" ]]; then
        PYINSTALLER_ARGS+=(--add-data "migrations:migrations")
    fi

    # Hidden imports for FastAPI/uvicorn
    PYINSTALLER_ARGS+=(
        --hidden-import uvicorn.protocols.http.auto
        --hidden-import uvicorn.protocols.http.h11_impl
        --hidden-import uvicorn.protocols.http.httptools_impl
        --hidden-import uvicorn.protocols.websockets.auto
        --hidden-import uvicorn.protocols.websockets.websockets_impl
        --hidden-import uvicorn.protocols.websockets.wsproto_impl
        --hidden-import uvicorn.lifespan.on
        --hidden-import uvicorn.lifespan.off
        --hidden-import uvicorn.logging
        --hidden-import uvicorn.loops.auto
        --hidden-import uvicorn.loops.asyncio
    )

    # Hidden imports for SQLAlchemy/aiosqlite/asyncpg
    PYINSTALLER_ARGS+=(
        --hidden-import aiosqlite
        --hidden-import sqlalchemy.ext.asyncio
        --hidden-import sqlalchemy.dialects.sqlite
        --hidden-import asyncpg
        --collect-all asyncpg
    )

    # Hidden imports for Pillow (image processing)
    PYINSTALLER_ARGS+=(
        --hidden-import PIL
        --hidden-import PIL.Image
        --hidden-import PIL.ImageDraw
        --hidden-import PIL.ImageFilter
        --hidden-import PIL.ImageEnhance
    )

    # Hidden imports for other common dependencies
    PYINSTALLER_ARGS+=(
        --hidden-import jinja2
        --hidden-import starlette.routing
        --hidden-import starlette.middleware
        --hidden-import httptools
        --hidden-import websockets
        --hidden-import ptyprocess
        --hidden-import psutil
    )

    # Collect all src package modules automatically
    PYINSTALLER_ARGS+=(
        --collect-all src
        --copy-metadata fastapi
        --copy-metadata starlette
        --copy-metadata uvicorn
    )

    # Exclude unnecessary modules to reduce size
    PYINSTALLER_ARGS+=(
        --exclude-module tkinter
        --exclude-module matplotlib
        --exclude-module scipy
        --exclude-module numpy
        --exclude-module pandas
        --exclude-module IPython
        --exclude-module notebook
        --exclude-module test
        --exclude-module tests
    )

    # Platform-specific options
    if [[ "${PLATFORM}" == "macos" ]]; then
        # macOS-specific options
        PYINSTALLER_ARGS+=(
            --target-arch "$(uname -m)"
        )
    elif [[ "${PLATFORM}" == "windows" ]]; then
        # Windows-specific options
        PYINSTALLER_ARGS+=(
            --console
        )
    fi

    # Optimization flags
    if [[ "${STRIP:-true}" == "true" ]]; then
        PYINSTALLER_ARGS+=(--strip)
    fi

    # Run PyInstaller with root-level main.py wrapper
    pyinstaller "${PYINSTALLER_ARGS[@]}" main.py
}

# Move executable to Tauri binaries directory
move_to_tauri() {
    echo "Moving executable to src-tauri/binaries/..."

    mkdir -p src-tauri/binaries

    if [[ "${PLATFORM}" == "windows" ]]; then
        mv "dist/${OUTPUT_NAME}" "src-tauri/binaries/"
        # Create generic name copy for Tauri launcher
        cp "src-tauri/binaries/${OUTPUT_NAME}" "src-tauri/binaries/jterm-backend.exe"
    else
        mv "dist/${OUTPUT_NAME}" "src-tauri/binaries/"
        chmod +x "src-tauri/binaries/${OUTPUT_NAME}"
        # Create generic name symlink for Tauri launcher
        cd src-tauri/binaries
        ln -sf "${OUTPUT_NAME}" "jterm-backend"
        cd ../..
    fi

    # Calculate file size
    if [[ "${PLATFORM}" == "macos" || "${PLATFORM}" == "linux" ]]; then
        FILE_SIZE=$(du -h "src-tauri/binaries/${OUTPUT_NAME}" | cut -f1)
    else
        FILE_SIZE=$(stat --printf="%s" "src-tauri/binaries/${OUTPUT_NAME}" 2>/dev/null || echo "unknown")
    fi

    echo "=========================================="
    echo "Build successful!"
    echo "Output: src-tauri/binaries/${OUTPUT_NAME}"
    echo "Generic: src-tauri/binaries/jterm-backend"
    echo "Size: ${FILE_SIZE}"
    echo "=========================================="
}

# Verify the build
verify_build() {
    echo "Verifying build..."

    if [[ ! -f "src-tauri/binaries/${OUTPUT_NAME}" ]]; then
        echo "Error: Build output not found!"
        exit 1
    fi

    # Quick test: run with --version or --help if supported
    if [[ "${PLATFORM}" != "windows" ]]; then
        echo "Testing executable..."
        if timeout 5 "src-tauri/binaries/${OUTPUT_NAME}" --help 2>&1 | head -1; then
            echo "Executable test passed."
        else
            echo "Warning: Could not verify executable (may still be valid)."
        fi
    fi
}

# Main execution
main() {
    detect_platform
    activate_venv
    check_dependencies

    # Parse arguments
    CLEAN_ONLY=false
    SKIP_VERIFY=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            --clean)
                CLEAN_ONLY=true
                shift
                ;;
            --skip-verify)
                SKIP_VERIFY=true
                shift
                ;;
            --no-strip)
                STRIP=false
                shift
                ;;
            -h|--help)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --clean       Clean build artifacts only"
                echo "  --skip-verify Skip build verification"
                echo "  --no-strip    Don't strip debug symbols"
                echo "  -h, --help    Show this help message"
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    clean_build

    if [[ "${CLEAN_ONLY}" == "true" ]]; then
        echo "Clean complete."
        exit 0
    fi

    run_pyinstaller
    move_to_tauri

    if [[ "${SKIP_VERIFY}" != "true" ]]; then
        verify_build
    fi

    echo ""
    echo "Next steps:"
    echo "  1. Run 'cargo tauri dev' to test the desktop application"
    echo "  2. Run './scripts/build-tauri.sh' for production build"
}

main "$@"

# Quickstart: Desktop Application Development

**Feature**: 005-desktop-application
**Date**: 2025-12-13
**Audience**: Developers setting up jterm desktop development environment

## Prerequisites

### Required Tools

| Tool | Minimum Version | Purpose |
|------|-----------------|---------|
| **Rust** | 1.85+ | Tauri framework, native integration (edition2024 support) |
| **Node.js** | 18+ | Frontend build tools |
| **Python** | 3.11+ | Backend services (existing) |
| **Cargo** | 1.75+ | Rust package manager (installed with Rust) |
| **npm** | 9+ | Node package manager (installed with Node.js) |
| **PyInstaller** | 6.0+ | Python bundler |
| **Git** | 2.30+ | Version control |

### Platform-Specific Requirements

**macOS**:
- Xcode Command Line Tools: `xcode-select --install`
- macOS 10.15+ (Catalina or later)

**Windows**:
- Visual Studio 2022 Build Tools with C++ workload
- Windows 10+ (x64)
- Edge WebView2 Runtime (usually pre-installed)

**Linux**:
- Ubuntu 20.04+ or Fedora 35+ (or equivalent)
- WebKitGTK development packages:
  ```bash
  # Ubuntu/Debian
  sudo apt install libwebkit2gtk-4.0-dev build-essential curl wget libssl-dev libgtk-3-dev libayatana-appindicator3-dev librsvg2-dev

  # Fedora
  sudo dnf install webkit2gtk4.0-devel openssl-devel gtk3-devel libappindicator-gtk3-devel librsvg2-devel
  ```

---

## Installation

### 1. Install Rust

```bash
# macOS/Linux
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env

# Windows (download and run from https://rustup.rs)
# After installation, restart terminal
```

Verify installation:
```bash
rustc --version  # Should show 1.85 or higher
cargo --version  # Should show 1.85 or higher
```

### 2. Install Node.js

**macOS** (using Homebrew):
```bash
brew install node@18
```

**Windows** (download from https://nodejs.org):
```powershell
# Download and run the MSI installer
```

**Linux** (using nvm):
```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install 18
nvm use 18
```

Verify installation:
```bash
node --version  # Should show 18.x or higher
npm --version   # Should show 9.x or higher
```

### 3. Install Python Dependencies

```bash
# Create virtual environment (if not already created)
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install all Python dependencies (existing + PyInstaller)
pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller==6.0
```

Verify installation:
```bash
python --version       # Should show 3.11 or higher
pyinstaller --version  # Should show 6.0 or higher
```

### 4. Install Tauri CLI

```bash
cargo install tauri-cli
```

Verify installation:
```bash
cargo tauri --version  # Should show 2.9 or higher
```

### 5. Install Node.js Dependencies

```bash
npm install
```

This will install:
- Tauri API bindings (`@tauri-apps/api`)
- Existing frontend dependencies (for web UI)
- Build tools

---

## Project Setup

### 1. Initialize Tauri

```bash
# Create Tauri project structure
cargo tauri init

# Follow the prompts:
# - App name: jterm
# - Window title: jterm
# - Web assets location: ../static
# - Dev server URL: http://localhost:8000
# - Frontend dev command: npm run dev
# - Frontend build command: npm run build
```

This creates:
- `src-tauri/` directory with Rust code
- `src-tauri/Cargo.toml` with dependencies
- `src-tauri/tauri.conf.json` with configuration

### 2. Configure Tauri

Edit `src-tauri/tauri.conf.json`:

```json
{
  "build": {
    "beforeDevCommand": "",
    "beforeBuildCommand": "npm run build",
    "devPath": "http://localhost:8000",
    "distDir": "../static",
    "withGlobalTauri": true
  },
  "package": {
    "productName": "jterm",
    "version": "1.0.0"
  },
  "tauri": {
    "allowlist": {
      "all": false,
      "shell": {
        "open": true
      },
      "dialog": {
        "all": true
      },
      "clipboard": {
        "all": true
      },
      "fs": {
        "scope": ["$APPDATA/jterm/**", "$HOME/Library/Application Support/jterm/**"]
      },
      "path": {
        "all": true
      },
      "window": {
        "all": true
      }
    },
    "bundle": {
      "active": true,
      "category": "DeveloperTool",
      "copyright": "",
      "deb": {
        "depends": []
      },
      "externalBin": ["binaries/jterm-backend"],
      "icon": [
        "icons/32x32.png",
        "icons/128x128.png",
        "icons/128x128@2x.png",
        "icons/icon.icns",
        "icons/icon.ico"
      ],
      "identifier": "com.jterm.desktop",
      "longDescription": "",
      "macOS": {
        "entitlements": null,
        "exceptionDomain": "",
        "frameworks": [],
        "providerShortName": null,
        "signingIdentity": null
      },
      "resources": [],
      "shortDescription": "",
      "targets": "all",
      "windows": {
        "certificateThumbprint": null,
        "digestAlgorithm": "sha256",
        "timestampUrl": ""
      }
    },
    "security": {
      "csp": null
    },
    "updater": {
      "active": false
    },
    "windows": [
      {
        "fullscreen": false,
        "height": 600,
        "resizable": true,
        "title": "jterm",
        "width": 800,
        "minWidth": 400,
        "minHeight": 300
      }
    ]
  }
}
```

### 3. Add Tauri Dependencies

Edit `src-tauri/Cargo.toml`:

```toml
[dependencies]
serde_json = "1.0"
serde = { version = "1.0", features = ["derive"] }
tauri = { version = "2.9", features = [] }
tauri-plugin-dialog = "2.0"
tauri-plugin-clipboard-manager = "2.0"
tauri-plugin-shell = "2.0"
tokio = { version = "1", features = ["full"] }
reqwest = { version = "0.12", features = ["json"] }

[build-dependencies]
tauri-build = { version = "2.0", features = [] }
```

---

## Development Workflow

### Option 1: Two-Process Development (Recommended)

**Terminal 1** - Run Python backend:
```bash
source venv/bin/activate  # On Windows: venv\Scripts\activate
uvicorn src.main:app --reload --port 8000
```

**Terminal 2** - Run Tauri app:
```bash
cargo tauri dev
```

This launches the Tauri window pointing to `http://localhost:8000` (Python backend).

**Benefits**:
- Fast Python backend reload (existing `--reload` mode)
- Rust code recompiles on save
- Full hot-reload for frontend changes

---

### Option 2: Integrated Development

**Single command**:
```bash
npm run tauri:dev
```

Add to `package.json`:
```json
{
  "scripts": {
    "tauri:dev": "concurrently \"uvicorn src.main:app --reload --port 8000\" \"cargo tauri dev\""
  },
  "devDependencies": {
    "concurrently": "^8.0.0"
  }
}
```

Install concurrently:
```bash
npm install --save-dev concurrently
```

---

## Building for Production

### 1. Bundle Python Backend

Create `scripts/build-python.sh`:

```bash
#!/bin/bash
set -e

echo "Building Python backend with PyInstaller..."

# Activate virtual environment
source venv/bin/activate

# Detect platform
if [[ "$OSTYPE" == "darwin"* ]]; then
    PLATFORM="macos"
    OUTPUT_NAME="jterm-backend-macos"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    PLATFORM="linux"
    OUTPUT_NAME="jterm-backend-linux"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    PLATFORM="windows"
    OUTPUT_NAME="jterm-backend-windows.exe"
else
    echo "Unsupported platform: $OSTYPE"
    exit 1
fi

# Run PyInstaller
pyinstaller \
    --name "$OUTPUT_NAME" \
    --onefile \
    --noconfirm \
    --clean \
    --add-data "templates:templates" \
    --add-data "static:static" \
    --hidden-import uvicorn.protocols.http.auto \
    --hidden-import uvicorn.protocols.websockets.auto \
    --hidden-import uvicorn.lifespan.on \
    src/main.py

# Move executable to Tauri binaries directory
mkdir -p src-tauri/binaries
mv dist/$OUTPUT_NAME src-tauri/binaries/

echo "Python backend built: src-tauri/binaries/$OUTPUT_NAME"
```

Make executable:
```bash
chmod +x scripts/build-python.sh
```

Run:
```bash
./scripts/build-python.sh
```

### 2. Build Tauri Application

```bash
# Build Python backend first
./scripts/build-python.sh

# Build Tauri app with bundled Python
cargo tauri build
```

Output:
- **macOS**: `src-tauri/target/release/bundle/dmg/jterm_1.0.0_x64.dmg`
- **Windows**: `src-tauri/target/release/bundle/msi/jterm_1.0.0_x64.msi`
- **Linux**: `src-tauri/target/release/bundle/appimage/jterm_1.0.0_amd64.AppImage`

---

## Testing

### Unit Tests (Rust)

```bash
cd src-tauri
cargo test
```

### Unit Tests (Python)

```bash
source venv/bin/activate
pytest tests/
```

### Integration Tests (Tauri + Python)

```bash
# Start Python backend
uvicorn src.main:app --port 8000 &

# Run Rust integration tests
cd src-tauri
cargo test --test integration

# Kill Python backend
pkill -f uvicorn
```

### E2E Tests (Desktop App)

```bash
# Build app first
./scripts/build-python.sh
cargo tauri build

# Run E2E tests (using WebDriver)
npm run test:e2e
```

---

## Debugging

### Python Backend Debugging

Use existing debugging tools:
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
uvicorn src.main:app --reload --port 8000
```

### Rust Debugging

**VSCode** (`.vscode/launch.json`):
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "type": "lldb",
      "request": "launch",
      "name": "Tauri Development Debug",
      "cargo": {
        "args": [
          "build",
          "--manifest-path=./src-tauri/Cargo.toml",
          "--no-default-features"
        ]
      },
      "cwd": "${workspaceFolder}"
    }
  ]
}
```

**Console logging**:
```rust
// src-tauri/src/main.rs
println!("Debug: {}", value);
eprintln!("Error: {}", error);
```

### Frontend Debugging

Open DevTools in Tauri window:
- **macOS**: `Cmd + Option + I`
- **Windows/Linux**: `Ctrl + Shift + I`

Or add to `tauri.conf.json`:
```json
{
  "tauri": {
    "windows": [
      {
        "devTools": true
      }
    ]
  }
}
```

---

## Common Issues

### Issue 1: Tauri Build Fails on macOS

**Error**: `error: linker 'cc' not found`

**Solution**: Install Xcode Command Line Tools
```bash
xcode-select --install
```

---

### Issue 2: Python Backend Not Starting

**Error**: `Connection refused` when Tauri tries to connect

**Solution**: Check Python backend is running on correct port
```bash
# Terminal 1
uvicorn src.main:app --port 8000

# Terminal 2 (verify it's running)
curl http://localhost:8000/health
```

---

### Issue 3: WebKitGTK Missing (Linux)

**Error**: `error: failed to run custom build command for 'webkit2gtk-sys'`

**Solution**: Install WebKitGTK development packages
```bash
# Ubuntu/Debian
sudo apt install libwebkit2gtk-4.0-dev

# Fedora
sudo dnf install webkit2gtk4.0-devel
```

---

### Issue 4: PyInstaller Missing Modules

**Error**: `ModuleNotFoundError` when running bundled Python

**Solution**: Add hidden imports to PyInstaller spec
```bash
pyinstaller \
    --hidden-import <missing_module> \
    src/main.py
```

Common hidden imports for FastAPI:
- `uvicorn.protocols.http.auto`
- `uvicorn.protocols.websockets.auto`
- `uvicorn.lifespan.on`

---

### Issue 5: Database Not Found (Desktop)

**Error**: `OperationalError: unable to open database file`

**Solution**: Database path is platform-specific in desktop version
```rust
// Correct: Use Tauri's app_data_dir
use tauri::api::path::app_data_dir;
let db_path = app_data_dir(&config).unwrap().join("webterminal.db");

// Incorrect: Hardcoded path
let db_path = "./webterminal.db";
```

---

## File Structure Overview

```
jterm/
├── src/                       # Python backend (REUSED)
├── static/                    # Frontend assets (REUSED)
├── templates/                 # HTML templates (REUSED)
├── tests/                     # Test suite (REUSED + EXTENDED)
├── src-tauri/                 # Tauri Rust code (NEW)
│   ├── src/
│   │   ├── main.rs
│   │   ├── commands/
│   │   ├── python/
│   │   ├── platform/
│   │   └── utils/
│   ├── binaries/              # PyInstaller output
│   │   └── jterm-backend-*
│   ├── Cargo.toml
│   ├── tauri.conf.json
│   └── icons/
├── scripts/                   # Build scripts (NEW)
│   ├── build-python.sh
│   ├── build-tauri.sh
│   ├── package-macos.sh
│   ├── package-windows.sh
│   └── package-linux.sh
├── requirements.txt           # Python dependencies (REUSED)
├── package.json               # Node.js dependencies (MODIFIED)
└── README.md                  # Documentation
```

---

## Next Steps

1. ✅ **Environment Setup**: Complete installation of Rust, Node.js, Python, Tauri CLI
2. ✅ **Project Initialization**: Run `cargo tauri init` and configure `tauri.conf.json`
3. ✅ **Development**: Start Python backend + Tauri dev server
4. 📝 **Implementation**: Follow the task list in `tasks.md` (generated by `/speckit.tasks`)
5. 🧪 **Testing**: Write tests for Tauri commands and desktop-specific features
6. 📦 **Building**: Bundle Python backend and build Tauri installers
7. 🚀 **Distribution**: Sign and notarize (macOS), code sign (Windows), test installers

---

## Additional Resources

- **Tauri Documentation**: https://tauri.app/v1/guides/
- **PyInstaller Manual**: https://pyinstaller.org/en/stable/
- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **xterm.js API**: https://xtermjs.org/docs/
- **Fabric.js Docs**: http://fabricjs.com/docs/

---

## Support

For issues specific to:
- **Tauri**: https://github.com/tauri-apps/tauri/issues
- **PyInstaller**: https://github.com/pyinstaller/pyinstaller/issues
- **jterm**: https://github.com/user/jterm/issues

---

**Ready to start development!** Run `cargo tauri dev` to launch the desktop application.

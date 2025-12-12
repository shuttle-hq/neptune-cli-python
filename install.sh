#!/usr/bin/env bash
set -e

REPO="shuttle-hq/neptune-mcp"
INSTALL_DIR="${INSTALL_DIR:-$HOME/.local/bin}"
BINARY_NAME="neptune"
MAX_RETRIES=5

# Detect OS and architecture
OS="$(uname -s)"
ARCH="$(uname -m)"

case "$OS" in
    Linux*)  OS="linux" ;;
    Darwin*) OS="macos" ;;
    MINGW*|MSYS*|CYGWIN*) OS="windows" ;;
    *) echo "Unsupported OS: $OS"; exit 1 ;;
esac

case "$ARCH" in
    x86_64|amd64) ARCH="amd64" ;;
    arm64|aarch64) ARCH="arm64" ;;
    *) echo "Unsupported architecture: $ARCH"; exit 1 ;;
esac

# Windows only supports amd64
if [[ "$OS" == "windows" && "$ARCH" != "amd64" ]]; then
    echo "Windows ARM64 is not supported"
    exit 1
fi

# Build asset name
if [[ "$OS" == "windows" ]]; then
    ASSET_NAME="neptune-${OS}-${ARCH}.exe"
    BINARY_NAME="neptune.exe"
else
    ASSET_NAME="neptune-${OS}-${ARCH}"
fi

echo "Detected: $OS $ARCH"
echo "Downloading: $ASSET_NAME"

# Get latest release URL
LATEST_URL="https://github.com/${REPO}/releases/latest/download/${ASSET_NAME}"

# Create temp directory
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

# Download binary with retry mechanism
RETRY_COUNT=0
while [[ $RETRY_COUNT -lt $MAX_RETRIES ]]; do
    if curl -fsSL "$LATEST_URL" -o "$TMP_DIR/$BINARY_NAME" 2>/dev/null; then
        chmod +x "$TMP_DIR/$BINARY_NAME"
        break
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [[ $RETRY_COUNT -lt $MAX_RETRIES ]]; then
            sleep 2
        else
            echo "Download failed after $MAX_RETRIES attempts"
            exit 1
        fi
    fi
done

# Ensure install dir exists
mkdir -p "$INSTALL_DIR"

# Install
mv "$TMP_DIR/$BINARY_NAME" "$INSTALL_DIR/$BINARY_NAME"

echo "Neptune CLI installed to $INSTALL_DIR/$BINARY_NAME"

# Check if in PATH
if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
    echo ""
    echo "Add $INSTALL_DIR to your PATH:"
    echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

echo ""
echo "Installation successful! You can now use Neptune in your MCP client."

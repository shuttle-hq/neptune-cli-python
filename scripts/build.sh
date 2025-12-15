#!/usr/bin/env bash
set -e

# Build script for Neptune CLI binary

echo "Building Neptune CLI binary..."
echo ""

# Clean previous build artifacts
echo "Cleaning previous build artifacts..."
rm -rf build dist

# Run PyInstaller with the spec file
echo "Running PyInstaller..."
uv run pyinstaller neptune.spec --clean

# Check if build was successful
if [ -f "dist/neptune" ]; then
    echo ""
    echo "Build successful!"
    echo "Binary location: dist/neptune"

    # Show binary size
    size=$(du -h dist/neptune | cut -f1)
    echo "Binary size: $size"

    # Make sure it's executable
    chmod +x dist/neptune

    # Test the binary
    echo ""
    echo "Testing binary..."
    ./dist/neptune version

    echo ""
    echo "Done!"
else
    echo ""
    echo "Build failed - binary not found at dist/neptune"
    exit 1
fi

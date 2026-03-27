#!/usr/bin/env bash
set -e

echo "====================================="
echo "  Dictly - macOS / Linux Build"
echo "====================================="
echo

echo "[1/4] Installing build dependencies..."
python -m pip install -r requirements-build.txt -q

echo "[2/4] Cleaning old build output..."
rm -rf build dist

echo "[3/4] Building..."
python -m PyInstaller dictly.spec --clean --noconfirm

echo "[4/4] Creating release archive..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    ditto -c -k --sequesterRsrc --keepParent "dist/Dictly.app" "dist/Dictly-macos.zip"
else
    tar -czf "dist/Dictly-linux.tar.gz" -C dist Dictly
fi

echo
echo "Build complete."
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "  App: dist/Dictly.app"
    echo "  Zip: dist/Dictly-macos.zip"
else
    echo "  Folder: dist/Dictly"
    echo "  Tar:    dist/Dictly-linux.tar.gz"
fi

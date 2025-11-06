#!/bin/bash

# Rebuild Custom Driver Script for Raspberry Pi 3/4
# This script rebuilds the custom SWIG-based rpi_ws281x driver

echo "======================================"
echo "Rebuilding Custom LED Driver"
echo "======================================"
echo ""

# Check if SWIG is installed
echo "Checking for SWIG..."
if ! command -v swig &> /dev/null; then
    echo "SWIG not found. Installing..."
    sudo apt-get update
    sudo apt-get install -y swig
else
    echo "✓ SWIG is installed: $(swig -version | head -n 2 | tail -n 1)"
fi

# Check for required build tools
echo ""
echo "Checking for build tools..."
if ! command -v gcc &> /dev/null; then
    echo "Installing build essentials..."
    sudo apt-get install -y build-essential
else
    echo "✓ GCC is installed: $(gcc --version | head -n 1)"
fi

# Clean previous builds
echo ""
echo "Cleaning previous builds..."
cd /home/timkobelt/git/led-control
sudo rm -rf build/ dist/ *.egg-info
sudo rm -f ledcontrol/driver/*.so
sudo rm -f ledcontrol/driver/*_wrap.c
sudo rm -f ledcontrol/*.so

# Update git submodules (rpi_ws281x source)
echo ""
echo "Updating git submodules..."
git submodule update --init --recursive

# Rebuild and reinstall
echo ""
echo "Building custom driver extensions..."
sudo pip3 install -e . --force-reinstall --no-deps

# Check if the wrapper was built
echo ""
echo "======================================"
echo "Checking build results..."
echo "======================================"

if [ -f "ledcontrol/driver/_ledcontrol_rpi_ws281x_driver.so" ]; then
    echo "✓ Custom driver built successfully!"
    echo "  Location: ledcontrol/driver/_ledcontrol_rpi_ws281x_driver.so"
else
    echo "✗ Custom driver build failed or not found"
    echo "  The system will fall back to PyPI rpi_ws281x package"
fi

if [ -f "ledcontrol/driver/_ledcontrol_animation_utils.so" ]; then
    echo "✓ Animation utils extension found"
fi

if [ -f "ledcontrol/_ledcontrol_artnet_utils.so" ]; then
    echo "✓ ArtNet utils extension found"
fi

echo ""
echo "======================================"
echo "Build process complete!"
echo "======================================"
echo ""
echo "Restart the ledcontrol service:"
echo "  sudo systemctl restart ledcontrol"
echo ""

#!/usr/bin/env bash
set -e

echo "============================================================"
echo "  Hypernet Swarm Installer"
echo "============================================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        echo "ERROR: Python is not installed."
        echo "Install Python 3.10+ from https://www.python.org/downloads/"
        echo "  Ubuntu/Debian: sudo apt install python3 python3-pip python3-venv"
        echo "  macOS:         brew install python3"
        exit 1
    fi
    PYTHON=python
else
    PYTHON=python3
fi

echo "Found Python:"
$PYTHON --version
echo ""

# Check pip
if ! $PYTHON -m pip --version &> /dev/null; then
    echo "ERROR: pip is not available."
    echo "Install with: $PYTHON -m ensurepip --upgrade"
    exit 1
fi

# Create virtual environment (optional but recommended)
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    $PYTHON -m venv .venv
    echo "Activating virtual environment..."
fi

if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
    echo "Using virtual environment: .venv"
elif [ -f ".venv/Scripts/activate" ]; then
    source .venv/Scripts/activate
    echo "Using virtual environment: .venv"
fi
echo ""

# Install the package
echo "Installing hypernet-swarm and dependencies..."
echo ""
pip install -e ".[all]" --quiet 2>/dev/null || pip install -e . --quiet
echo ""
echo "Dependencies installed."
echo ""

# Run interactive setup wizard
echo "Running setup wizard..."
echo ""
$PYTHON -m hypernet_swarm setup
echo ""

echo "============================================================"
echo "  Installation complete!"
echo "============================================================"
echo ""
echo "  Start the swarm:  python -m hypernet_swarm"
echo "  Show status:       python -m hypernet_swarm status"
echo "  Run tests:         python -m hypernet_swarm test"
echo ""
echo "  Re-run setup:      python -m hypernet_swarm setup"
echo "  With local repo:   python -m hypernet_swarm setup --archive-root /path/to/Hypernet/Structure"
echo ""
echo "  The setup wizard lets you configure API keys, budget, and archive location."
echo "  You can re-run it at any time to update your configuration."
echo ""

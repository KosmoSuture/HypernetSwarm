#!/usr/bin/env python3
"""
Hypernet Swarm Bootstrap — Prerequisite Checker

Checks that all required and optional dependencies are available,
reports what's missing, and offers to install them.

Usage:
    python bootstrap.py          # Check and report
    python bootstrap.py --fix    # Auto-install missing packages
"""

import importlib
import subprocess
import sys


# (module_name, pip_package, required, description)
DEPENDENCIES = [
    # Required
    ("anthropic", "anthropic", True, "Anthropic Claude API client"),
    ("openai", "openai", True, "OpenAI API client (also used for Gemini, Groq, etc.)"),
    ("httpx", "httpx", True, "HTTP client for API calls"),

    # Server (strongly recommended)
    ("fastapi", "fastapi", False, "Web dashboard and REST API"),
    ("uvicorn", "uvicorn[standard]", False, "ASGI server for FastAPI"),

    # Optional
    ("yaml", "pyyaml", False, "YAML parsing (for config files)"),
    ("pystray", "pystray", False, "System tray icon"),
    ("PIL", "Pillow", False, "Image support for tray icon"),
    ("pytest", "pytest", False, "Test runner"),
]


def check_python():
    """Check Python version."""
    v = sys.version_info
    print(f"Python: {v.major}.{v.minor}.{v.micro}")
    if v < (3, 10):
        print("  WARNING: Python 3.10+ is required. You have {}.{}.".format(v.major, v.minor))
        return False
    print("  OK")
    return True


def check_dependencies():
    """Check all dependencies and return lists of missing ones."""
    missing_required = []
    missing_optional = []
    installed = []

    for module_name, pip_name, required, description in DEPENDENCIES:
        try:
            importlib.import_module(module_name)
            installed.append((pip_name, description))
        except ImportError:
            if required:
                missing_required.append((pip_name, description))
            else:
                missing_optional.append((pip_name, description))

    return installed, missing_required, missing_optional


def check_claude_code():
    """Check if Claude Code CLI is available."""
    import shutil
    found = shutil.which("claude")
    if found:
        print(f"Claude Code CLI: {found}")
        print("  OK")
        return True
    else:
        print("Claude Code CLI: not found")
        print("  (Optional — install with: npm install -g @anthropic-ai/claude-code)")
        return False


def install_packages(packages):
    """Install packages via pip."""
    if not packages:
        return True
    cmd = [sys.executable, "-m", "pip", "install"] + [p for p, _ in packages]
    print(f"  Running: pip install {' '.join(p for p, _ in packages)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  Error: {result.stderr[:500]}")
        return False
    return True


def main():
    fix_mode = "--fix" in sys.argv

    print("=" * 60)
    print("  Hypernet Swarm — Bootstrap Check")
    print("=" * 60)
    print()

    # Python version
    python_ok = check_python()
    print()

    # Dependencies
    installed, missing_required, missing_optional = check_dependencies()

    if installed:
        print(f"Installed ({len(installed)}):")
        for name, desc in installed:
            print(f"  OK   {name:20s} — {desc}")
        print()

    if missing_required:
        print(f"MISSING required ({len(missing_required)}):")
        for name, desc in missing_required:
            print(f"  MISS {name:20s} — {desc}")
        print()

    if missing_optional:
        print(f"Missing optional ({len(missing_optional)}):")
        for name, desc in missing_optional:
            print(f"  skip {name:20s} — {desc}")
        print()

    # Claude Code
    check_claude_code()
    print()

    # Fix mode
    if fix_mode and (missing_required or missing_optional):
        print("Installing missing packages...")
        all_missing = missing_required + missing_optional
        if install_packages(all_missing):
            print("  All packages installed successfully.")
        else:
            print("  Some packages failed to install.")
            if missing_required:
                print("  WARNING: Required packages are missing. The swarm may not start.")
        print()

    # Summary
    if not missing_required:
        print("All required dependencies are satisfied.")
        print("Run: python -m hypernet_swarm setup")
    else:
        print("Required dependencies are missing. Install them with:")
        print(f"  pip install {' '.join(p for p, _ in missing_required)}")
        print()
        print("Or run: python bootstrap.py --fix")


if __name__ == "__main__":
    main()

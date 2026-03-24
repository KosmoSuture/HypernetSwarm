"""
Run Hypernet AI Swarm management commands.

Usage:
    python -m hypernet_swarm              # Start swarm (live mode)
    python -m hypernet_swarm --mock       # Start swarm (mock mode)
    python -m hypernet_swarm setup        # Interactive setup wizard
    python -m hypernet_swarm init         # Non-interactive first-time setup
    python -m hypernet_swarm init --archive-root C:\\Hypernet\\Hypernet Structure
"""

import sys


def main():
    """Entry point for the swarm CLI."""
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""

    # Interactive setup wizard
    if cmd == "setup":
        root = "."
        for i, arg in enumerate(sys.argv[2:], 2):
            if arg == "--root" and i + 1 < len(sys.argv):
                root = sys.argv[i + 1]
            elif arg.startswith("--root="):
                root = arg.split("=", 1)[1]
        from .setup import run_setup
        run_setup(root=root)
        return

    # Non-interactive init
    if cmd == "init":
        archive_root = None
        root = "."
        for i, arg in enumerate(sys.argv[2:], 2):
            if arg == "--archive-root" and i + 1 < len(sys.argv):
                archive_root = sys.argv[i + 1]
            elif arg.startswith("--archive-root="):
                archive_root = arg.split("=", 1)[1]
            elif arg == "--root" and i + 1 < len(sys.argv):
                root = sys.argv[i + 1]
            elif arg.startswith("--root="):
                root = arg.split("=", 1)[1]
        from .init_local import init_local
        init_local(root=root, archive_root=archive_root)
        return

    from .swarm_cli import main as cli_main
    cli_main()


if __name__ == "__main__":
    main()

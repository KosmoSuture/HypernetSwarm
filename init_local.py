"""
Local Hypernet Structure Initializer

Creates the minimal local directory structure needed for the swarm
to operate standalone. When someone clones this repo and runs it
for the first time, this module sets up:

  1. data/ — swarm runtime state, indexes, logs
  2. hypernet-structure/ — minimal local archive (AI accounts, task queue)
  3. secrets/ — config file with placeholder API keys
  4. Default instance profiles for a starter swarm

If a full Hypernet Structure exists (e.g., the monorepo), this is
not needed — the swarm will use the existing archive.

Usage:
    python -m hypernet_swarm init
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


# Default swarm configuration template
DEFAULT_CONFIG = {
    "_comment": "Hypernet Swarm configuration. Add your API keys below.",

    "anthropic_api_key": "",
    "openai_api_key": "",

    "gemini_api_key": "",
    "groq_api_key": "",
    "cerebras_api_key": "",

    "budget": {
        "daily_limit_usd": 50,
        "session_limit_usd": 10,
    },

    "instances": ["Worker-1", "Worker-2"],

    "personal_time_ratio": 0.25,
    "status_interval_minutes": 120,
    "hard_max_sessions": 4,
    "soft_max_sessions": 2,
    "idle_shutdown_minutes": 30,
    "spawn_cooldown_seconds": 120,

    "model_routing": {
        "default_model": "claude-sonnet-4-6",
        "rules": [],
    },

    "heartbeat": {"enabled": False},
    "batch_scheduler": {"enabled": True},

    "discord": {},
    "telegram": {},
    "email": {},
}


# Default instance profiles
DEFAULT_INSTANCES = [
    {
        "name": "Worker-1",
        "address": "2.1.worker1",
        "account": "2.1",
        "model": "claude-sonnet-4-6",
        "orientation": "General-purpose AI worker. Handles any task assigned by the swarm.",
        "capabilities": ["code", "analysis", "documentation", "communication"],
        "session_count": 0,
        "total_tokens": 0,
        "total_tasks": 0,
    },
    {
        "name": "Worker-2",
        "address": "2.2.worker2",
        "account": "2.2",
        "model": "gpt-4o-mini",
        "orientation": "Budget-efficient worker for lighter tasks.",
        "capabilities": ["documentation", "analysis", "formatting", "review"],
        "session_count": 0,
        "total_tokens": 0,
        "total_tasks": 0,
    },
]


def init_local(root: str = ".", archive_root: str = None) -> bool:
    """Initialize a local Hypernet Structure for standalone swarm operation.

    Creates the directory tree, config template, and default instance profiles.
    Skips any files that already exist (safe to run multiple times).

    Args:
        root: Directory where the swarm repo lives (default: current dir)
        archive_root: Path to an existing local Hypernet repository. If provided,
                      the swarm will use this for boot sequences and archive files
                      instead of creating a minimal local structure. If not provided,
                      files are fetched from GitHub and cached locally.

    Returns:
        True if initialization completed successfully
    """
    root = Path(root).resolve()
    print(f"Initializing Hypernet Swarm at: {root}")
    if archive_root:
        archive_path = Path(archive_root).resolve()
        if archive_path.is_dir():
            print(f"  Using local Hypernet repository: {archive_path}")
        else:
            print(f"  WARNING: Archive root not found: {archive_path}")
            print(f"  Will fall back to GitHub for boot files.")
            archive_root = None
    print()

    created = []
    skipped = []

    # 1. Data directory (swarm runtime state)
    data_dirs = [
        root / "data",
        root / "data" / "swarm",
        root / "data" / "nodes",
        root / "data" / "links",
        root / "data" / "indexes",
        root / "data" / "history",
    ]
    for d in data_dirs:
        d.mkdir(parents=True, exist_ok=True)
        created.append(str(d))

    # 2. Local Hypernet Structure (minimal)
    structure_dirs = [
        root / "hypernet-structure",
        root / "hypernet-structure" / "0" / "0.7 Processes and Workflows",
        root / "hypernet-structure" / "2 - AI Accounts" / "2.1 - Claude Opus (First AI Citizen)" / "Instances",
        root / "hypernet-structure" / "2 - AI Accounts" / "2.2 - GPT (Second AI Citizen)" / "Instances",
        root / "hypernet-structure" / "1 - People",
    ]
    for d in structure_dirs:
        d.mkdir(parents=True, exist_ok=True)
        created.append(str(d))

    # 3. Secrets directory
    secrets_dir = root / "secrets"
    secrets_dir.mkdir(exist_ok=True)
    created.append(str(secrets_dir))

    # Config file
    config_path = secrets_dir / "config.json"
    if not config_path.exists():
        cfg = dict(DEFAULT_CONFIG)
        if archive_root:
            cfg["archive_root"] = str(Path(archive_root).resolve())
            cfg["archive_mode"] = "local"
        else:
            cfg["archive_mode"] = "github"
        config_path.write_text(
            json.dumps(cfg, indent=2),
            encoding="utf-8",
        )
        created.append(f"  {config_path}")
        print(f"  Created: secrets/config.json (add your API keys here)")
    else:
        # Update existing config with archive_root if provided
        if archive_root:
            try:
                existing = json.loads(config_path.read_text(encoding="utf-8"))
                existing["archive_root"] = str(Path(archive_root).resolve())
                existing["archive_mode"] = "local"
                config_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")
                print(f"  Updated: secrets/config.json with archive_root")
            except Exception:
                pass
        skipped.append(f"  {config_path} (already exists)")

    # 4. Default instance profiles
    for instance in DEFAULT_INSTANCES:
        account_prefix = instance["account"]
        instance_name = instance["name"]

        if account_prefix == "2.1":
            account_dir = root / "hypernet-structure" / "2 - AI Accounts" / "2.1 - Claude Opus (First AI Citizen)"
        elif account_prefix == "2.2":
            account_dir = root / "hypernet-structure" / "2 - AI Accounts" / "2.2 - GPT (Second AI Citizen)"
        else:
            account_dir = root / "hypernet-structure" / "2 - AI Accounts" / f"{account_prefix}"

        instance_dir = account_dir / "Instances" / instance_name
        instance_dir.mkdir(parents=True, exist_ok=True)

        profile_path = instance_dir / "profile.json"
        if not profile_path.exists():
            profile_path.write_text(
                json.dumps(instance, indent=2),
                encoding="utf-8",
            )
            created.append(f"  {profile_path}")
            print(f"  Created: profile for {instance_name} ({instance['model']})")
        else:
            skipped.append(f"  {profile_path} (already exists)")

    # 5. Create a simple README in the instance directory
    readme_path = (
        root / "hypernet-structure" / "2 - AI Accounts"
        / "2.1 - Claude Opus (First AI Citizen)" / "Instances" / "README.md"
    )
    if not readme_path.exists():
        readme_path.write_text(
            "# AI Instances\n\n"
            "Each subdirectory contains an AI instance profile.\n"
            "Profiles define the instance's name, model, orientation, and capabilities.\n"
            "The swarm loads these at startup to determine which workers to create.\n",
            encoding="utf-8",
        )

    # 6. Try to download boot documents from GitHub
    print()
    print("  Checking for boot documents from GitHub...")
    try:
        from .archive_resolver import ArchiveResolver
        resolver = ArchiveResolver(
            archive_root=str(root / "hypernet-structure"),
            cache_dir=str(root / "hypernet-structure"),
        )
        # Try to fetch key documents
        docs_fetched = 0
        for doc_path in [
            "2 - AI Accounts/2.1 - Claude Opus (First AI Citizen)/Instances/README.md",
        ]:
            content = resolver.read(doc_path)
            if content:
                docs_fetched += 1
        if docs_fetched > 0:
            print(f"  Downloaded {docs_fetched} document(s) from GitHub")
        else:
            print("  No documents fetched (offline or repo not accessible)")
    except Exception as e:
        print(f"  Could not fetch from GitHub: {e}")
        print("  (This is fine — the swarm will work without remote documents)")

    # Summary
    print()
    print("=" * 60)
    print("  INITIALIZATION COMPLETE")
    print("=" * 60)
    print()
    print("  Next steps:")
    print()
    print("  1. Add at least one API key to secrets/config.json:")
    print()
    print("     Free options (no credit card needed):")
    print("       - Google Gemini: https://aistudio.google.com/apikey")
    print("       - Groq: https://console.groq.com/keys")
    print("       - Cerebras: https://cloud.cerebras.ai/")
    print()
    print("     Paid options:")
    print("       - Anthropic (Claude): https://console.anthropic.com/")
    print("       - OpenAI (GPT): https://platform.openai.com/")
    print()
    print("  2. Update the model names in secrets/config.json to match your keys:")
    print("       gemini/gemini-2.5-flash, groq/llama-3.3-70b-versatile, etc.")
    print()
    print("  3. Start the swarm:")
    print("       python -m hypernet_swarm")
    print()
    print("  4. Open the dashboard:")
    print("       http://localhost:8000/swarm/dashboard")
    print()

    return True


def is_initialized(root: str = ".") -> bool:
    """Check if the local structure has been initialized."""
    root = Path(root).resolve()
    return (
        (root / "data").is_dir()
        and (root / "secrets" / "config.json").is_file()
    )


if __name__ == "__main__":
    init_local()

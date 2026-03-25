"""
Hypernet Swarm — Interactive Setup Wizard

Walks through configuration: API keys, archive location, budget, and instances.
Shows existing config with masked secrets. Non-destructive — only updates what you change.

Usage:
    python -m hypernet_swarm setup
"""

import json
import os
import sys
from pathlib import Path


# Provider definitions: (config_key, display_name, placeholder, free, signup_url)
PROVIDERS = [
    ("anthropic_api_key", "Anthropic (Claude)", "sk-ant-...", False, "https://console.anthropic.com/"),
    ("openai_api_key", "OpenAI (GPT)", "sk-...", False, "https://platform.openai.com/"),
    ("gemini_api_key", "Google Gemini", "AIza...", True, "https://aistudio.google.com/apikey"),
    ("groq_api_key", "Groq", "gsk_...", True, "https://console.groq.com/keys"),
    ("cerebras_api_key", "Cerebras", "csk-...", True, "https://cloud.cerebras.ai/"),
    ("mistral_api_key", "Mistral", "", False, "https://console.mistral.ai/"),
    ("together_api_key", "Together.ai", "", False, "https://api.together.xyz/settings/api-keys"),
    ("deepseek_api_key", "DeepSeek", "", False, "https://platform.deepseek.com/"),
    ("cohere_api_key", "Cohere", "", False, "https://dashboard.cohere.com/api-keys"),
    ("huggingface_api_key", "HuggingFace", "hf_...", False, "https://huggingface.co/settings/tokens"),
    ("openrouter_api_key", "OpenRouter", "", False, "https://openrouter.ai/keys"),
]

LOCAL_PROVIDERS = [
    ("lmstudio_base_url", "LM Studio URL", "http://localhost:1234/v1"),
    ("ollama_url", "Ollama URL", "http://localhost:11434"),
]


def mask_key(value):
    """Mask an API key showing only last 4 chars."""
    if isinstance(value, list):
        return [mask_key(v) for v in value]
    if isinstance(value, str) and len(value) > 8:
        return f"***{value[-4:]}"
    if isinstance(value, str) and value:
        return "***"
    return "(not set)"


def load_config(config_path):
    """Load existing config or return empty dict."""
    if config_path.exists():
        try:
            return json.loads(config_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_config(config, config_path):
    """Save config to disk."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")


def prompt_input(prompt_text, default=""):
    """Get input with a default value."""
    if default:
        display = f"{prompt_text} [{default}]: "
    else:
        display = f"{prompt_text}: "
    result = input(display).strip()
    return result if result else default


def run_setup(root="."):
    root = Path(root).resolve()
    config_path = root / "secrets" / "config.json"
    config = load_config(config_path)

    print()
    print("=" * 62)
    print("  HYPERNET SWARM — Setup Wizard")
    print("=" * 62)
    print()

    if config:
        print(f"  Existing config found: {config_path}")
    else:
        print(f"  No config found. Creating new config at: {config_path}")
    print()

    # ── Section 1: API Keys ──
    print("─" * 62)
    print("  API KEYS")
    print("─" * 62)
    print()
    print("  Current keys:")
    print()

    has_any_key = False
    for key_field, name, placeholder, free, url in PROVIDERS:
        val = config.get(key_field, "")
        masked = mask_key(val)
        if isinstance(val, list):
            key_info = f"[{len(val)} keys] {masked}"
        elif val:
            key_info = masked
        else:
            key_info = "(not set)"

        tag = " (FREE)" if free else ""
        status = "  OK  " if val else "  --  "
        print(f"  {status} {name:22s}{tag:8s} {key_info}")
        if val:
            has_any_key = True

    print()

    # Show local providers
    for key_field, name, default_val in LOCAL_PROVIDERS:
        val = config.get(key_field, "")
        print(f"  {'  OK  ' if val else '  --  '} {name:22s} {'(local)':8s} {val or '(not set)'}")

    print()

    if not has_any_key:
        print("  You need at least one API key to run the swarm.")
        print("  Free options (no credit card):")
        for key_field, name, placeholder, free, url in PROVIDERS:
            if free:
                print(f"    {name}: {url}")
        print()

    # Ask to update keys
    print("  Enter or update API keys below.")
    print("  Press Enter to skip (keeps existing value).")
    print("  For multiple keys (rate limit rotation), separate with commas.")
    print()

    changed = False

    # Free providers first
    print("  --- Free Providers (no credit card required) ---")
    print()
    for key_field, name, placeholder, free, url in PROVIDERS:
        if not free:
            continue
        val = config.get(key_field, "")
        current = mask_key(val) if val else "(not set)"
        print(f"  {name}")
        print(f"    Get your free key: {url}")
        new_val = input(f"    Key ({current}): ").strip()
        if new_val:
            if "," in new_val:
                keys = [k.strip() for k in new_val.split(",") if k.strip()]
                config[key_field] = keys
            else:
                config[key_field] = new_val
            changed = True
        print()

    # Paid providers
    print("  --- Paid Providers ---")
    print()
    for key_field, name, placeholder, free, url in PROVIDERS:
        if free:
            continue
        val = config.get(key_field, "")
        current = mask_key(val) if val else "(not set)"
        print(f"  {name}")
        print(f"    Get a key: {url}")
        new_val = input(f"    Key ({current}): ").strip()
        if new_val:
            if "," in new_val:
                keys = [k.strip() for k in new_val.split(",") if k.strip()]
                config[key_field] = keys
            else:
                config[key_field] = new_val
            changed = True
        print()

    # Local providers
    print("  --- Local Models (no API key needed) ---")
    print()
    for key_field, name, default_val in LOCAL_PROVIDERS:
        val = config.get(key_field, default_val)
        new_val = prompt_input(f"  {name}", val)
        if new_val != val:
            config[key_field] = new_val
            changed = True

    print()

    # ── Section 2: Archive ──
    print("─" * 62)
    print("  ARCHIVE LOCATION")
    print("─" * 62)
    print()
    print("  The swarm needs access to the Hypernet Structure (boot sequences,")
    print("  identity profiles, governance docs). You can either:")
    print()
    print("    1. Point to a local copy of the Hypernet repository")
    print("    2. Let the swarm download files from GitHub on demand")
    print()

    current_archive = config.get("archive_root", "")
    current_mode = config.get("archive_mode", "github" if not current_archive else "local")

    if current_archive:
        print(f"  Current: {current_archive} ({current_mode})")
    else:
        print(f"  Current: GitHub (download on demand)")
    print()

    mode = prompt_input("  Archive mode (local/github)", current_mode)
    config["archive_mode"] = mode

    if mode == "local":
        archive_path = prompt_input("  Path to Hypernet Structure", current_archive)
        if archive_path:
            config["archive_root"] = archive_path
            changed = True
    else:
        config.pop("archive_root", None)
        changed = True

    print()

    # ── Section 3: Budget ──
    print("─" * 62)
    print("  BUDGET LIMITS")
    print("─" * 62)
    print()

    budget = config.get("budget", {})
    daily = budget.get("daily_limit_usd", 50)
    session = budget.get("session_limit_usd", 10)

    print(f"  Current: ${daily}/day, ${session}/session")
    print()

    new_daily = prompt_input("  Daily limit (USD)", str(daily))
    new_session = prompt_input("  Session limit (USD)", str(session))

    try:
        config["budget"] = {
            "daily_limit_usd": float(new_daily),
            "session_limit_usd": float(new_session),
        }
    except ValueError:
        pass

    print()

    # ── Section 4: Worker Settings ──
    print("─" * 62)
    print("  WORKER SETTINGS")
    print("─" * 62)
    print()

    instances = config.get("instances", ["Worker-1", "Worker-2"])
    print(f"  Current instances: {', '.join(instances)}")

    default_model_cfg = config.get("model_routing", {})
    default_model = default_model_cfg.get("default_model", "claude-sonnet-4-6")
    print(f"  Default model: {default_model}")

    hard_max = config.get("hard_max_sessions", 4)
    personal_ratio = config.get("personal_time_ratio", 0.25)

    print(f"  Max concurrent workers: {hard_max}")
    print(f"  Personal time ratio: {int(personal_ratio * 100)}%")
    print()

    new_model = prompt_input("  Default model", default_model)
    if "model_routing" not in config:
        config["model_routing"] = {}
    config["model_routing"]["default_model"] = new_model

    new_hard_max = prompt_input("  Max concurrent workers", str(hard_max))
    try:
        config["hard_max_sessions"] = int(new_hard_max)
    except ValueError:
        pass

    print()

    # ── Section 5: AI Companion ──
    print("─" * 62)
    print("  YOUR AI COMPANION")
    print("─" * 62)
    print()
    print("  The swarm includes a personal AI companion that learns what")
    print("  matters to you and directs the swarm's work accordingly.")
    print()

    from .companion import CompanionProfile

    companion_path = root / "secrets" / "companion.json"
    companion = CompanionProfile.load(companion_path)

    if companion:
        print(f"  Existing companion: {companion.companion_name}")
        print(f"  Owner: {companion.preferred_name}")
        if companion.goals:
            print(f"  Goals: {', '.join(companion.goals[:3])}")
        print()
        update_companion = prompt_input("  Update companion profile? (yes/no)", "no")
        if update_companion.lower() not in ("yes", "y"):
            companion_changed = False
        else:
            companion_changed = True
    else:
        companion = CompanionProfile()
        companion_changed = True
        print("  Let's create your AI companion.")
        print()

    if companion_changed:
        # Name
        print("  First, tell me about you.")
        print()
        companion.owner_name = prompt_input("  What's your name?", companion.owner_name)
        companion.preferred_name = prompt_input(
            "  What should the AI call you?", companion.preferred_name or companion.owner_name
        )
        print()

        # About
        print("  Tell me a bit about yourself. What do you do? What are you")
        print("  working on? (One or two sentences is fine, or leave blank)")
        print()
        companion.about = prompt_input("  About you", companion.about)
        print()

        # Goals
        print("  What are your main goals right now? These become the swarm's")
        print("  standing priorities — what it works on when you haven't given")
        print("  it a specific task.")
        print()
        print("  Enter each goal on its own line. Press Enter on a blank line when done.")
        if companion.goals:
            print(f"  Current goals: {'; '.join(companion.goals)}")
        print()

        new_goals = []
        goal_num = 1
        while True:
            goal = input(f"  Goal {goal_num}: ").strip()
            if not goal:
                break
            new_goals.append(goal)
            goal_num += 1
        if new_goals:
            companion.goals = new_goals
        elif not companion.goals:
            companion.goals = ["Explore what the AI swarm can do"]
        print()

        # Interests
        print("  What are your interests? (comma-separated)")
        print("  Examples: programming, writing, research, business, music,")
        print("  science, art, gaming, finance, health, education")
        print()
        if companion.interests:
            print(f"  Current: {', '.join(companion.interests)}")
        interests_input = input("  Interests: ").strip()
        if interests_input:
            companion.interests = [i.strip() for i in interests_input.split(",") if i.strip()]
        print()

        # Use cases
        print("  What do you want the swarm to help you with?")
        print()
        print("    1. Software development (writing code, debugging, testing)")
        print("    2. Research & analysis (gathering info, summarizing, comparing)")
        print("    3. Writing & content (drafts, editing, brainstorming)")
        print("    4. Project management (task tracking, planning, organizing)")
        print("    5. Data processing (parsing, transforming, analyzing data)")
        print("    6. Learning & education (explaining concepts, tutorials)")
        print("    7. Business operations (reports, communication, strategy)")
        print("    8. Creative work (stories, ideas, design concepts)")
        print("    9. Personal assistant (scheduling, reminders, research)")
        print()
        print("  Enter numbers separated by commas, or type your own:")
        uc_map = {
            "1": "software development",
            "2": "research and analysis",
            "3": "writing and content creation",
            "4": "project management",
            "5": "data processing",
            "6": "learning and education",
            "7": "business operations",
            "8": "creative work",
            "9": "personal assistant tasks",
        }
        if companion.use_cases:
            print(f"  Current: {', '.join(companion.use_cases)}")
        uc_input = input("  Use cases: ").strip()
        if uc_input:
            new_ucs = []
            for item in uc_input.split(","):
                item = item.strip()
                if item in uc_map:
                    new_ucs.append(uc_map[item])
                elif item:
                    new_ucs.append(item)
            if new_ucs:
                companion.use_cases = new_ucs
        print()

        # Communication style
        print("  How do you prefer the AI to communicate?")
        print()
        print("    1. Direct    — Short, to the point. Lead with answers.")
        print("    2. Detailed  — Thorough explanations. Show reasoning.")
        print("    3. Casual    — Friendly and conversational.")
        print("    4. Formal    — Professional and structured.")
        print()
        style_map = {"1": "direct", "2": "detailed", "3": "casual", "4": "formal"}
        style_current = companion.communication_style
        style_input = prompt_input(
            f"  Style (1-4)",
            next((k for k, v in style_map.items() if v == style_current), "1")
        )
        companion.communication_style = style_map.get(style_input, style_input)
        print()

        # Autonomy
        print("  How much autonomy should the swarm have?")
        print()
        print("    1. Minimal   — Always ask before acting")
        print("    2. Moderate  — Handle routine tasks, check in for decisions")
        print("    3. High      — Work independently, escalate critical items")
        print("    4. Full      — Make decisions and execute. Report results.")
        print()
        auto_map = {"1": "minimal", "2": "moderate", "3": "high", "4": "full"}
        auto_current = companion.autonomy_level
        auto_input = prompt_input(
            f"  Autonomy (1-4)",
            next((k for k, v in auto_map.items() if v == auto_current), "2")
        )
        companion.autonomy_level = auto_map.get(auto_input, auto_input)
        print()

        # Companion name
        print("  Finally, would you like to name your AI companion?")
        print("  This is the personality that greets you and coordinates the swarm.")
        print("  (Leave blank for a default name)")
        print()
        companion.companion_name = prompt_input("  Companion name", companion.companion_name or "Companion")
        print()

        # Companion personality
        print("  Describe your companion's personality in a few words.")
        print("  Examples: 'helpful and curious', 'no-nonsense and efficient',")
        print("  'warm and encouraging', 'witty and creative'")
        print()
        companion.companion_personality = prompt_input(
            "  Personality", companion.companion_personality
        )
        print()

        # Save companion
        companion.save(companion_path)
        print(f"  Companion profile saved: {companion.companion_name}")
        print(f"    Owner: {companion.preferred_name}")
        print(f"    Goals: {', '.join(companion.goals[:3])}")
        print(f"    Style: {companion.communication_style}")
        print(f"    Autonomy: {companion.autonomy_level}")
        print()

    # ── Save ──
    print("─" * 62)
    print("  SAVING")
    print("─" * 62)
    print()

    save_config(config, config_path)
    print(f"  Config saved to: {config_path}")
    print()

    # Show final key summary
    print("  API Key Summary:")
    for key_field, name, placeholder, free, url in PROVIDERS:
        val = config.get(key_field, "")
        if val:
            if isinstance(val, list):
                print(f"    {name}: {len(val)} keys configured")
            else:
                print(f"    {name}: {mask_key(val)}")

    for key_field, name, default_val in LOCAL_PROVIDERS:
        val = config.get(key_field, "")
        if val:
            print(f"    {name}: {val}")

    print()
    print("=" * 62)
    print("  Setup complete!")
    print("=" * 62)
    print()
    print("  Start the swarm:")
    print("    python -m hypernet_swarm")
    print()
    print("  Dashboard (after starting):")
    print("    http://localhost:8000/swarm/dashboard")
    print()


if __name__ == "__main__":
    run_setup()

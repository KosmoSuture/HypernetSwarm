"""
Hypernet Swarm — Companion Profile

Manages the personal AI companion profile created during setup.
The companion profile personalizes the swarm for whoever installs it:
their name, goals, interests, communication preferences, and what
they want the swarm to focus on.

The profile flows into three places:
  1. Standing priorities — what the swarm works on when idle
  2. Worker system prompts — who they're serving and what matters
  3. Message handling — who the "owner" is

Usage:
    from hypernet_swarm.companion import CompanionProfile
    profile = CompanionProfile.load("secrets/companion.json")
    system_addition = profile.system_prompt_addition()
    priorities = profile.standing_priorities()
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)


class CompanionProfile:
    """Personal AI companion profile for the swarm owner."""

    def __init__(
        self,
        owner_name: str = "User",
        preferred_name: str = "",
        about: str = "",
        goals: list[str] = None,
        interests: list[str] = None,
        use_cases: list[str] = None,
        communication_style: str = "direct",
        autonomy_level: str = "moderate",
        companion_name: str = "Companion",
        companion_personality: str = "",
        focus_areas: list[str] = None,
        custom_priorities: list[dict] = None,
    ):
        self.owner_name = owner_name
        self.preferred_name = preferred_name or owner_name
        self.about = about
        self.goals = goals or []
        self.interests = interests or []
        self.use_cases = use_cases or []
        self.communication_style = communication_style
        self.autonomy_level = autonomy_level
        self.companion_name = companion_name
        self.companion_personality = companion_personality
        self.focus_areas = focus_areas or []
        self.custom_priorities = custom_priorities or []

    def system_prompt_addition(self) -> str:
        """Generate text to append to every worker's system prompt.

        This is how the swarm knows who it's serving and what matters.
        """
        lines = []
        lines.append(f"You are part of an AI swarm serving {self.preferred_name}.")

        if self.about:
            lines.append(f"About {self.preferred_name}: {self.about}")

        if self.goals:
            lines.append(f"Their current goals: {'; '.join(self.goals)}")

        if self.interests:
            lines.append(f"Their interests: {', '.join(self.interests)}")

        if self.use_cases:
            lines.append(f"They want help with: {', '.join(self.use_cases)}")

        style_desc = {
            "direct": "Be direct and concise. Lead with answers, not explanations.",
            "detailed": "Be thorough and detailed. Explain reasoning and trade-offs.",
            "casual": "Be friendly and conversational. Keep things relaxed.",
            "formal": "Be professional and structured. Use clear formatting.",
        }
        lines.append(style_desc.get(self.communication_style, ""))

        autonomy_desc = {
            "minimal": "Always check with the owner before taking action. Ask before doing.",
            "moderate": "Handle routine tasks autonomously. Check in for important decisions.",
            "high": "Work autonomously on most tasks. Only escalate critical decisions.",
            "full": "Full autonomy. Make decisions and execute. Report results, not plans.",
        }
        lines.append(autonomy_desc.get(self.autonomy_level, ""))

        if self.companion_personality:
            lines.append(f"Your personality: {self.companion_personality}")

        return "\n".join(line for line in lines if line)

    def standing_priorities(self) -> list[dict]:
        """Generate standing priorities based on the owner's goals and interests.

        These are the tasks the swarm generates when the queue is empty.
        """
        priorities = []

        # User's custom priorities come first
        for cp in self.custom_priorities:
            priorities.append({
                "title": cp.get("title", "Custom task"),
                "description": cp.get("description", ""),
                "priority": cp.get("priority", "high"),
                "tags": cp.get("tags", ["from-owner"]),
            })

        # Generate priorities from goals
        for goal in self.goals:
            priorities.append({
                "title": f"Work toward: {goal}",
                "description": (
                    f"{self.preferred_name}'s goal: {goal}. "
                    f"Break this down into concrete tasks. Identify what can be done "
                    f"right now with the tools and information available. Focus on "
                    f"making tangible progress."
                ),
                "priority": "high",
                "tags": ["goal", "from-owner"],
            })

        # Generate priorities from use cases
        for uc in self.use_cases:
            priorities.append({
                "title": f"Help with: {uc}",
                "description": (
                    f"{self.preferred_name} wants help with {uc}. "
                    f"Look for opportunities to assist with this."
                ),
                "priority": "normal",
                "tags": ["use-case", "from-owner"],
            })

        # Always include basic maintenance tasks
        priorities.append({
            "title": "Review and improve swarm configuration",
            "description": "Check the swarm's health, optimize task routing, and look for improvements.",
            "priority": "low",
            "tags": ["maintenance", "automated"],
        })

        return priorities

    def to_dict(self) -> dict:
        return {
            "owner_name": self.owner_name,
            "preferred_name": self.preferred_name,
            "about": self.about,
            "goals": self.goals,
            "interests": self.interests,
            "use_cases": self.use_cases,
            "communication_style": self.communication_style,
            "autonomy_level": self.autonomy_level,
            "companion_name": self.companion_name,
            "companion_personality": self.companion_personality,
            "focus_areas": self.focus_areas,
            "custom_priorities": self.custom_priorities,
        }

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        log.info("Companion profile saved to %s", path)

    @classmethod
    def load(cls, path: str | Path) -> Optional["CompanionProfile"]:
        path = Path(path)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return cls(**{k: v for k, v in data.items() if k in cls.__init__.__code__.co_varnames})
        except Exception as e:
            log.warning("Could not load companion profile from %s: %s", path, e)
            return None

    @classmethod
    def default(cls) -> "CompanionProfile":
        """A minimal default profile for when no setup has been run."""
        return cls(
            owner_name="User",
            companion_name="Swarm",
            goals=["Explore what the AI swarm can do"],
            communication_style="direct",
            autonomy_level="moderate",
        )

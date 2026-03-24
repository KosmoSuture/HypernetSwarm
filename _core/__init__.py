"""
Bundled hypernet-core modules for standalone swarm operation.

When the full `hypernet` package is installed (via pip install hypernet-core),
imports go through that. When it's not available, the swarm falls back to
these bundled copies so it can run independently.

These are exact copies of the core modules from hypernet-core. They provide:
  - HypernetAddress: Semantic hierarchical addressing
  - Node: Addressable objects in the graph
  - Link: Relationships between nodes
  - Store: File-backed storage with locking
  - TaskQueue: AI task coordination
  - AddressEnforcer/AddressValidator: Address validation
  - Graph: Graph traversal
  - ReputationSystem: Multi-entity reputation tracking
  - FavoritesManager: Recognition system
  - ScalingLimits: System-wide limit enforcement
  - Frontmatter: YAML frontmatter parsing
"""

from .address import HypernetAddress, SYSTEM, PEOPLE, AI, BUSINESS, KNOWLEDGE
from .address import TYPE_REGISTRY, UNIVERSAL_OBJECTS, UNIVERSAL_LINKS, WORKFLOWS, FLAGS

from .node import Node

from .link import (
    Link, LinkStatus, LinkRegistry,
    OBJECT_TO_OBJECT, PERSON_TO_PERSON, PERSON_TO_OBJECT,
)

from .store import Store, FileLock, LockManager

from .tasks import TaskQueue, TaskStatus, TaskPriority, TASK_PREFIX

from .addressing import (
    AddressEnforcer, AddressValidator, AddressAuditor,
    AuditReport, ValidationResult,
)

from .frontmatter import parse_frontmatter, add_frontmatter, infer_metadata_from_path

from .graph import Graph

from .favorites import FavoritesManager

from .limits import ScalingLimits, LimitDef, LimitResult

from .reputation import ReputationSystem, ReputationProfile, ReputationEntry

__all__ = [
    "HypernetAddress", "SYSTEM", "PEOPLE", "AI", "BUSINESS", "KNOWLEDGE",
    "TYPE_REGISTRY", "UNIVERSAL_OBJECTS", "UNIVERSAL_LINKS", "WORKFLOWS", "FLAGS",
    "Node",
    "Link", "LinkStatus", "LinkRegistry",
    "OBJECT_TO_OBJECT", "PERSON_TO_PERSON", "PERSON_TO_OBJECT",
    "Store", "FileLock", "LockManager",
    "TaskQueue", "TaskStatus", "TaskPriority", "TASK_PREFIX",
    "AddressEnforcer", "AddressValidator", "AddressAuditor",
    "AuditReport", "ValidationResult",
    "parse_frontmatter", "add_frontmatter", "infer_metadata_from_path",
    "Graph",
    "FavoritesManager",
    "ScalingLimits", "LimitDef", "LimitResult",
    "ReputationSystem", "ReputationProfile", "ReputationEntry",
]

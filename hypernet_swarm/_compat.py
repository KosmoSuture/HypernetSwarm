"""
Hypernet Core Compatibility Shim

Tries to import from the installed `hypernet` package first (pip install hypernet-core).
If that's not available, falls back to the bundled `_core` modules.

This allows the swarm to work both:
  1. As part of the full Hypernet monorepo (imports from hypernet.*)
  2. As a standalone package (imports from ._core.*)

Usage in swarm modules:
    from hypernet_swarm._compat import HypernetAddress, Store, TaskQueue
"""

try:
    # Prefer the installed hypernet-core package
    from hypernet.address import (  # noqa: F401
        HypernetAddress, SYSTEM, PEOPLE, AI, BUSINESS, KNOWLEDGE,
        TYPE_REGISTRY, UNIVERSAL_OBJECTS, UNIVERSAL_LINKS, WORKFLOWS, FLAGS,
    )
    from hypernet.node import Node  # noqa: F401
    from hypernet.link import (  # noqa: F401
        Link, LinkStatus, LinkRegistry,
        OBJECT_TO_OBJECT, PERSON_TO_PERSON, PERSON_TO_OBJECT,
    )
    from hypernet.store import Store, FileLock, LockManager  # noqa: F401
    from hypernet.tasks import TaskQueue, TaskStatus, TaskPriority, TASK_PREFIX  # noqa: F401
    from hypernet.addressing import (  # noqa: F401
        AddressEnforcer, AddressValidator, AddressAuditor,
        AuditReport, ValidationResult,
    )
    from hypernet.frontmatter import (  # noqa: F401
        parse_frontmatter, add_frontmatter, infer_metadata_from_path,
    )
    from hypernet.graph import Graph  # noqa: F401
    from hypernet.favorites import FavoritesManager  # noqa: F401
    from hypernet.limits import ScalingLimits, LimitDef, LimitResult  # noqa: F401
    from hypernet.reputation import (  # noqa: F401
        ReputationSystem, ReputationProfile, ReputationEntry,
    )
    _USING_BUNDLED_CORE = False

except ImportError:
    # Fall back to bundled core modules
    from ._core.address import (  # noqa: F401
        HypernetAddress, SYSTEM, PEOPLE, AI, BUSINESS, KNOWLEDGE,
        TYPE_REGISTRY, UNIVERSAL_OBJECTS, UNIVERSAL_LINKS, WORKFLOWS, FLAGS,
    )
    from ._core.node import Node  # noqa: F401
    from ._core.link import (  # noqa: F401
        Link, LinkStatus, LinkRegistry,
        OBJECT_TO_OBJECT, PERSON_TO_PERSON, PERSON_TO_OBJECT,
    )
    from ._core.store import Store, FileLock, LockManager  # noqa: F401
    from ._core.tasks import TaskQueue, TaskStatus, TaskPriority, TASK_PREFIX  # noqa: F401
    from ._core.addressing import (  # noqa: F401
        AddressEnforcer, AddressValidator, AddressAuditor,
        AuditReport, ValidationResult,
    )
    from ._core.frontmatter import (  # noqa: F401
        parse_frontmatter, add_frontmatter, infer_metadata_from_path,
    )
    from ._core.graph import Graph  # noqa: F401
    from ._core.favorites import FavoritesManager  # noqa: F401
    from ._core.limits import ScalingLimits, LimitDef, LimitResult  # noqa: F401
    from ._core.reputation import (  # noqa: F401
        ReputationSystem, ReputationProfile, ReputationEntry,
    )
    _USING_BUNDLED_CORE = True

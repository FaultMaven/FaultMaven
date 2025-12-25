"""
Investigation engines for milestone-based orchestration.

This package contains the core investigation framework engines ported from
FaultMaven-Mono. These engines implement the sophisticated investigation logic
that was missing from the initial migration.

Engines:
- milestone_engine: Main orchestration engine for turn processing
- hypothesis_manager: Hypothesis confidence and lifecycle management
- ooda_engine: OODA loop execution and adaptive intensity
- memory_manager: Hierarchical memory (hot/warm/cold tiers)
- working_conclusion_generator: Interim conclusion synthesis
- phase_orchestrator: Phase progression and loopback detection

Architecture:
- Service Layer (investigation_service.py) delegates to these engines
- Engines contain business logic (no DB access)
- State passed in/out as InvestigationState Pydantic models
"""

from faultmaven.modules.case.engines.milestone_engine import (
    MilestoneEngine,
    MilestoneEngineError,
)
from faultmaven.modules.case.engines.hypothesis_manager import (
    HypothesisManager,
    HypothesisManagerError,
    rank_hypotheses_by_likelihood,
)
from faultmaven.modules.case.engines.ooda_engine import (
    OODAEngine,
    OODAEngineError,
    AdaptiveIntensityController,
    create_ooda_engine,
)

__all__ = [
    # Core engines (Phase 2)
    "MilestoneEngine",
    "MilestoneEngineError",
    "HypothesisManager",  # Phase 2.2 ✅
    "HypothesisManagerError",
    "rank_hypotheses_by_likelihood",
    "OODAEngine",  # Phase 2.3 ✅
    "OODAEngineError",
    "AdaptiveIntensityController",
    "create_ooda_engine",
    # Supporting engines (Phase 3)
    # "MemoryManager",
    # "WorkingConclusionGenerator",
    # "PhaseOrchestrator",
]

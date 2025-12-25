"""
Hierarchical Memory Manager for Investigation Context

Implements hot/warm/cold memory tiers to optimize token usage while
maintaining investigation context across turns.

Token Budget: ~1,600 tokens total (vs 4,500+ unmanaged, 64% reduction)
- Hot Memory: ~500 tokens (last 2-3 turns, full fidelity)
- Warm Memory: ~300 tokens (recent turns, summarized)
- Cold Memory: ~100 tokens (archived, key facts only)

Source: FaultMaven-Mono memory_manager.py (lines 1-590)
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from faultmaven.modules.case.investigation import (
    InvestigationState,
    HierarchicalMemory,
    MemorySnapshot,
    TurnRecord,
    HypothesisModel,
    EvidenceItem,
)
from faultmaven.modules.case.enums import HypothesisStatus

logger = logging.getLogger(__name__)


class MemoryManagerError(Exception):
    """Base exception for MemoryManager errors."""
    pass


class MemoryManager:
    """
    Manages hierarchical investigation memory (hot/warm/cold tiers).

    Responsibilities:
    - Organize turn history into memory tiers
    - Compress older turns to save tokens
    - Promote/demote content between tiers
    - Provide context for turn processing

    Source: FaultMaven-Mono memory_manager.py lines 160-340
    """

    def __init__(self, llm_provider=None):
        """
        Initialize MemoryManager.

        Args:
            llm_provider: Optional LLM provider for summarization
        """
        self.llm_provider = llm_provider
        self.logger = logging.getLogger(__name__)

    def organize_memory(
        self,
        inv_state: InvestigationState,
    ) -> HierarchicalMemory:
        """
        Organize investigation state into hot/warm/cold memory tiers.

        Hot Memory: Last 2-3 turns (full fidelity)
        Warm Memory: Recent context (summarized)
        Cold Memory: Archived key facts

        Args:
            inv_state: Current investigation state

        Returns:
            HierarchicalMemory with organized content

        Source: FaultMaven-Mono lines 170-220
        """
        memory = HierarchicalMemory()

        # Hot memory: Last 3 turns (full detail)
        recent_turns = inv_state.turn_history[-3:] if inv_state.turn_history else []
        memory.hot_memory = [
            self._create_snapshot_from_turn(turn, tier="hot")
            for turn in recent_turns
        ]

        # Warm memory: Active hypotheses + recent evidence
        active_hypotheses = inv_state.get_active_hypotheses()
        if active_hypotheses:
            warm_snapshot = self._create_hypothesis_snapshot(
                active_hypotheses,
                inv_state.evidence,
                tier="warm"
            )
            memory.warm_memory = [warm_snapshot]

        # Cold memory: Refuted/validated hypotheses (archived)
        archived_hypotheses = [
            h for h in inv_state.hypotheses
            if h.status in [HypothesisStatus.REFUTED, HypothesisStatus.VALIDATED]
        ]
        if archived_hypotheses:
            cold_snapshot = self._create_hypothesis_snapshot(
                archived_hypotheses,
                [],
                tier="cold"
            )
            memory.cold_memory = [cold_snapshot]

        return memory

    def _create_snapshot_from_turn(
        self,
        turn: TurnRecord,
        tier: str = "hot"
    ) -> MemorySnapshot:
        """
        Create memory snapshot from turn record.

        Args:
            turn: Turn record to snapshot
            tier: Memory tier ("hot", "warm", "cold")

        Returns:
            MemorySnapshot

        Source: FaultMaven-Mono lines 240-280
        """
        return MemorySnapshot(
            snapshot_id=f"turn_{turn.turn_number}",
            turn_range=(turn.turn_number, turn.turn_number),
            tier=tier,
            content_summary=f"Turn {turn.turn_number}: {turn.user_input_summary or 'User input'} → {turn.outcome.value}",
            key_insights=[
                f"Phase: {turn.phase.value}",
                f"Progress made: {turn.progress_made}",
            ],
            evidence_ids=turn.evidence_collected,
            hypothesis_updates=turn.hypotheses_updated,
            confidence_delta=0.0,  # Could compute from hypothesis changes
            token_count_estimate=200,  # Estimate for a turn
            created_at=datetime.now(),
        )

    def _create_hypothesis_snapshot(
        self,
        hypotheses: List[HypothesisModel],
        evidence: List[EvidenceItem],
        tier: str = "warm"
    ) -> MemorySnapshot:
        """
        Create memory snapshot from hypotheses.

        Args:
            hypotheses: List of hypotheses to snapshot
            evidence: List of evidence items
            tier: Memory tier

        Returns:
            MemorySnapshot

        Source: FaultMaven-Mono lines 290-330
        """
        # Extract key insights from hypotheses
        insights = []
        hypothesis_ids = []

        for hyp in hypotheses:
            hypothesis_ids.append(hyp.hypothesis_id)
            insights.append(
                f"{hyp.statement} ({hyp.status.value}, {hyp.likelihood:.2f})"
            )

        return MemorySnapshot(
            snapshot_id=f"hypotheses_{tier}",
            turn_range=(0, 0),  # Not turn-specific
            tier=tier,
            content_summary=f"{len(hypotheses)} hypotheses",
            key_insights=insights[:5],  # Limit to top 5
            evidence_ids=[e.evidence_id for e in evidence[:5]],  # Top 5 evidence
            hypothesis_updates=hypothesis_ids,
            confidence_delta=0.0,
            token_count_estimate=len(hypotheses) * 50,  # ~50 tokens per hypothesis
            created_at=datetime.now(),
        )

    def compress_memory(
        self,
        memory: HierarchicalMemory,
        max_hot: int = 3,
        max_warm: int = 5,
        max_cold: int = 10,
    ) -> HierarchicalMemory:
        """
        Compress memory tiers to stay within token limits.

        Strategies:
        1. Keep only last N hot memories
        2. Merge oldest warm memories into cold
        3. Drop oldest cold memories if exceeding limit

        Args:
            memory: Current memory state
            max_hot: Maximum hot memory snapshots
            max_warm: Maximum warm memory snapshots
            max_cold: Maximum cold memory snapshots

        Returns:
            Compressed HierarchicalMemory

        Source: FaultMaven-Mono lines 350-410
        """
        compressed = HierarchicalMemory()

        # Hot memory: Keep last max_hot snapshots
        compressed.hot_memory = memory.hot_memory[-max_hot:]

        # Warm memory: Keep last max_warm, demote older to cold
        if len(memory.warm_memory) > max_warm:
            # Demote oldest warm to cold
            to_demote = memory.warm_memory[:-max_warm]
            compressed.warm_memory = memory.warm_memory[-max_warm:]
            compressed.cold_memory.extend(to_demote)
        else:
            compressed.warm_memory = memory.warm_memory

        # Cold memory: Merge with any demoted warm, then limit
        compressed.cold_memory.extend(memory.cold_memory)
        compressed.cold_memory = compressed.cold_memory[-max_cold:]

        return compressed

    def get_context_for_prompt(
        self,
        memory: HierarchicalMemory,
        max_tokens: int = 1600,
    ) -> str:
        """
        Format memory into context string for LLM prompt.

        Args:
            memory: Hierarchical memory
            max_tokens: Maximum tokens to use

        Returns:
            Formatted context string

        Source: FaultMaven-Mono lines 420-470
        """
        sections = []

        # Hot memory (highest priority)
        if memory.hot_memory:
            hot_text = "## Recent Turns (Hot Memory)\n"
            for snapshot in memory.hot_memory:
                hot_text += f"- {snapshot.content_summary}\n"
                if snapshot.key_insights:
                    for insight in snapshot.key_insights[:3]:
                        hot_text += f"  • {insight}\n"
            sections.append(hot_text)

        # Warm memory (medium priority)
        if memory.warm_memory:
            warm_text = "## Active Investigation Context (Warm Memory)\n"
            for snapshot in memory.warm_memory:
                warm_text += f"- {snapshot.content_summary}\n"
                if snapshot.key_insights:
                    for insight in snapshot.key_insights[:2]:
                        warm_text += f"  • {insight}\n"
            sections.append(warm_text)

        # Cold memory (lowest priority, only if space)
        if memory.cold_memory:
            cold_text = "## Archived Facts (Cold Memory)\n"
            for snapshot in memory.cold_memory[:5]:  # Limit to 5 snapshots
                cold_text += f"- {snapshot.content_summary}\n"
            sections.append(cold_text)

        return "\n\n".join(sections)

    def should_trigger_compression(
        self,
        inv_state: InvestigationState,
        compression_frequency: int = 3,
    ) -> bool:
        """
        Determine if memory compression should be triggered.

        Compression is triggered every N turns to prevent memory bloat.

        Args:
            inv_state: Current investigation state
            compression_frequency: Trigger compression every N turns

        Returns:
            True if compression should be triggered

        Source: FaultMaven-Mono lines 480-510
        """
        # Trigger every N turns
        if inv_state.current_turn % compression_frequency == 0:
            return True

        # Trigger if hot memory exceeds threshold
        if inv_state.memory and len(inv_state.memory.hot_memory) > 5:
            return True

        return False

    async def compress_with_llm(
        self,
        snapshots: List[MemorySnapshot],
        target_tokens: int = 300,
    ) -> MemorySnapshot:
        """
        Compress multiple snapshots using LLM summarization.

        This is an advanced feature that uses LLM to intelligently
        summarize multiple turns into a concise snapshot.

        Args:
            snapshots: Snapshots to compress
            target_tokens: Target token count for summary

        Returns:
            Compressed MemorySnapshot

        Source: FaultMaven-Mono lines 520-580
        """
        if not self.llm_provider:
            # Fallback: Simple concatenation
            return self._merge_snapshots_simple(snapshots)

        # Extract content to summarize
        content_parts = []
        for snapshot in snapshots:
            content_parts.append(snapshot.content_summary)
            content_parts.extend(snapshot.key_insights)

        content_to_summarize = " | ".join(content_parts)

        # LLM summarization prompt
        prompt = f"""Summarize the following investigation context into {target_tokens} tokens or less.
Focus on key facts, decisions, and confidence changes.

Context:
{content_to_summarize}

Summary (max {target_tokens} tokens):"""

        try:
            summary = await self.llm_provider.generate(prompt=prompt)

            # Create compressed snapshot
            return MemorySnapshot(
                snapshot_id=f"compressed_{snapshots[0].snapshot_id}_{snapshots[-1].snapshot_id}",
                turn_range=(
                    snapshots[0].turn_range[0],
                    snapshots[-1].turn_range[1]
                ),
                tier="warm",
                content_summary=summary[:500],  # Limit summary length
                key_insights=[],  # Insights already in summary
                evidence_ids=[],
                hypothesis_updates=[],
                confidence_delta=0.0,
                token_count_estimate=target_tokens,
                created_at=datetime.now(),
            )
        except Exception as e:
            self.logger.warning(f"LLM compression failed, using fallback: {e}")
            return self._merge_snapshots_simple(snapshots)

    def _merge_snapshots_simple(
        self,
        snapshots: List[MemorySnapshot]
    ) -> MemorySnapshot:
        """
        Simple snapshot merge (no LLM).

        Args:
            snapshots: Snapshots to merge

        Returns:
            Merged MemorySnapshot
        """
        if not snapshots:
            raise MemoryManagerError("Cannot merge empty snapshot list")

        # Combine all insights
        all_insights = []
        for snapshot in snapshots:
            all_insights.extend(snapshot.key_insights)

        return MemorySnapshot(
            snapshot_id=f"merged_{len(snapshots)}_snapshots",
            turn_range=(
                snapshots[0].turn_range[0],
                snapshots[-1].turn_range[1]
            ),
            tier="warm",
            content_summary=f"Merged {len(snapshots)} turns",
            key_insights=all_insights[:10],  # Top 10 insights
            evidence_ids=[],
            hypothesis_updates=[],
            confidence_delta=0.0,
            token_count_estimate=len(all_insights) * 20,
            created_at=datetime.now(),
        )

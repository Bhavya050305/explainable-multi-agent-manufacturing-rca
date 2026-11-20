"""
ManuMind AI — LangGraph Multi-Agent Reducers
Deterministic, immutable reducer functions for merging shared state updates
across the Supervisor, Anomaly Detection, and Root Cause Analysis agents.
"""

from copy import deepcopy
import re
from typing import Any, Dict, List, Optional, Set, Union
from backend.app.agents.enums import (
    AgentName,
    HumanApprovalStatus,
    VerificationStatus,
)
from backend.app.agents.schemas import (
    AgentExecutionRecord,
    CandidateRootCause,
    EvidenceItem,
    HumanApprovalDetails,
    RootCauseVerificationDecision,
    _sanitize_string,
)


def sanitize_error_message(msg: Optional[str]) -> Optional[str]:
    """Exposes string sanitization utility to prevent credential exposure in state."""
    return _sanitize_string(msg)


def overwrite_supervisor_field(current: Any, update: Any) -> Any:
    """
    Explicit overwrite semantics for supervisor-owned scalar fields.
    If update is not None, update replaces current; otherwise current is preserved.
    """
    if update is not None:
        return update
    return current


def merge_unique_strings(
    current: Optional[List[str]],
    update: Union[List[str], str, None]
) -> List[str]:
    """
    Deterministic reducer for string identifier lists.
    Preserves original discovery order and deduplicates entries.
    Does not mutate current or update.
    """
    result: List[str] = list(current) if current else []

    if update is None:
        return result

    updates = [update] if isinstance(update, str) else list(update)
    seen = set(result)

    for item in updates:
        if item and item not in seen:
            result.append(item)
            seen.add(item)

    return result


def merge_rag_citations(
    current: Optional[List[str]],
    update: Union[List[str], str, None]
) -> List[str]:
    """
    Deterministic reducer for RAG citation identifiers (e.g. '[CIT-1]').
    Preserves discovery order and deduplicates.
    """
    return merge_unique_strings(current, update)


def merge_errors(
    current: Optional[List[str]],
    update: Union[List[str], str, None]
) -> List[str]:
    """
    Deterministic reducer for sanitized workflow error logs.
    Sanitizes all error messages against credential leakage.
    """
    result: List[str] = list(current) if current else []

    if update is None:
        return result

    updates = [update] if isinstance(update, str) else list(update)
    for err in updates:
        sanitized = sanitize_error_message(err)
        if sanitized:
            result.append(sanitized)

    return result


def merge_evidence(
    current: Optional[List[EvidenceItem]],
    update: Union[List[EvidenceItem], EvidenceItem, None]
) -> List[EvidenceItem]:
    """
    Deterministic reducer for EvidenceItem collections.
    
    Invariants:
    1. Input immutability: current and update are never mutated.
    2. Deduplication: Exact identical items with the same evidence_id are deduplicated.
    3. Conflict preservation: If an update item shares an evidence_id with an existing item
       but differs in content (description, source_reference, source_agent, etc.), both items
       are preserved. The conflicting item is appended with a conflict suffix (__conflict_N)
       to guarantee provenance visibility without silent overwriting.
    """
    result: List[EvidenceItem] = list(current) if current else []

    if update is None:
        return result

    update_items: List[EvidenceItem] = [update] if isinstance(update, EvidenceItem) else list(update)

    for item in update_items:
        # Check for existing item with same evidence_id
        existing_matches = [e for e in result if e.evidence_id == item.evidence_id]

        if not existing_matches:
            # New unique evidence item
            result.append(item)
        else:
            existing = existing_matches[0]
            # Check if identical
            if existing == item:
                # Exact duplicate: do not duplicate
                continue
            else:
                # Conflicting evidence with same ID: PRESERVE BOTH
                # Generate disambiguated conflict ID
                conflict_index = 1
                conflict_id = f"{item.evidence_id}__conflict_{conflict_index}"
                existing_ids = {e.evidence_id for e in result}
                while conflict_id in existing_ids:
                    conflict_index += 1
                    conflict_id = f"{item.evidence_id}__conflict_{conflict_index}"

                conflict_item = item.model_copy(
                    update={"evidence_id": conflict_id}
                )
                result.append(conflict_item)

    return result


def merge_candidate_root_causes(
    current: Optional[List[CandidateRootCause]],
    update: Union[List[CandidateRootCause], CandidateRootCause, None]
) -> List[CandidateRootCause]:
    """
    Deterministic reducer for CandidateRootCause collections.
    
    Invariants:
    1. Input immutability: current and update are never mutated.
    2. Deduplication: Exact identical candidate causes with same cause_id are deduplicated.
    3. Conflict preservation: If an update candidate shares cause_id but has differing
       diagnoses, hypotheses, or confidence, both candidates are preserved with a disambiguated
       cause_id (__alt_N) to ensure competing agent hypotheses are not discarded.
    """
    result: List[CandidateRootCause] = list(current) if current else []

    if update is None:
        return result

    update_items: List[CandidateRootCause] = [update] if isinstance(update, CandidateRootCause) else list(update)

    for item in update_items:
        existing_matches = [c for c in result if c.cause_id == item.cause_id]

        if not existing_matches:
            result.append(item)
        else:
            existing = existing_matches[0]
            if existing == item:
                # Exact duplicate: ignore
                continue
            else:
                # Conflicting candidate root cause: PRESERVE BOTH
                alt_index = 1
                alt_id = f"{item.cause_id}__alt_{alt_index}"
                existing_ids = {c.cause_id for c in result}
                while alt_id in existing_ids:
                    alt_index += 1
                    alt_id = f"{item.cause_id}__alt_{alt_index}"

                alt_item = item.model_copy(
                    update={"cause_id": alt_id}
                )
                result.append(alt_item)

    return result


def merge_agent_executions(
    current: Optional[List[AgentExecutionRecord]],
    update: Union[List[AgentExecutionRecord], AgentExecutionRecord, None]
) -> List[AgentExecutionRecord]:
    """
    Deterministic reducer for AgentExecutionRecord audit history.
    
    Invariants:
    1. Input immutability: current and update are never mutated.
    2. Chronological preservation: preserves execution order.
    3. Lifecycle updates: If an execution record in update matches an existing record_id,
       the record is updated in place in the new list (e.g., transition from RUNNING to COMPLETED).
    4. New records are appended chronologically.
    """
    result: List[AgentExecutionRecord] = list(current) if current else []

    if update is None:
        return result

    update_items: List[AgentExecutionRecord] = [update] if isinstance(update, AgentExecutionRecord) else list(update)

    for item in update_items:
        match_idx = -1
        for idx, rec in enumerate(result):
            if rec.record_id == item.record_id:
                match_idx = idx
                break

        if match_idx >= 0:
            # Update existing record in place
            result[match_idx] = item
        else:
            # Append new execution record
            result.append(item)

    # Sort result chronologically by started_at
    result.sort(key=lambda x: x.started_at)
    return result


def merge_verification_decisions(
    current: Optional[List[Union[RootCauseVerificationDecision, Dict[str, Any]]]],
    update: Union[List[Union[RootCauseVerificationDecision, Dict[str, Any]]], RootCauseVerificationDecision, Dict[str, Any], None]
) -> List[RootCauseVerificationDecision]:
    """
    Deterministic reducer for RootCauseVerificationDecision collections.
    
    Invariants:
    1. Input immutability: current and update are never mutated.
    2. Deduplication: Exact identical decisions with the same decision_id are deduplicated.
    3. Conflict preservation: If an update decision shares a decision_id with an existing decision
       but has differing attributes, both are preserved with a disambiguated decision_id (__alt_N).
    4. Chronological ordering: Decisions are sorted chronologically by verified_at timestamp.
    """
    result: List[RootCauseVerificationDecision] = []
    if current:
        for c in current:
            result.append(
                c if isinstance(c, RootCauseVerificationDecision)
                else RootCauseVerificationDecision.model_validate(c)
            )

    if update is None:
        return result

    raw_updates = [update] if isinstance(update, (RootCauseVerificationDecision, dict)) else list(update)
    update_items: List[RootCauseVerificationDecision] = [
        item if isinstance(item, RootCauseVerificationDecision)
        else RootCauseVerificationDecision.model_validate(item)
        for item in raw_updates
    ]

    for item in update_items:
        existing_matches = [d for d in result if d.decision_id == item.decision_id]

        if not existing_matches:
            result.append(item)
        else:
            existing = existing_matches[0]
            if existing == item:
                # Exact duplicate: do not duplicate
                continue
            else:
                # Conflicting decision with same decision_id: PRESERVE BOTH
                alt_index = 1
                alt_id = f"{item.decision_id}__alt_{alt_index}"
                existing_ids = {d.decision_id for d in result}
                while alt_id in existing_ids:
                    alt_index += 1
                    alt_id = f"{item.decision_id}__alt_{alt_index}"

                alt_item = item.model_copy(update={"decision_id": alt_id})
                result.append(alt_item)

    # Sort chronologically by verified_at
    result.sort(key=lambda d: d.verified_at)
    return result


def merge_human_approval(
    current: Union[HumanApprovalDetails, Dict[str, Any], None],
    update: Union[HumanApprovalDetails, Dict[str, Any], None]
) -> HumanApprovalDetails:
    """
    Deterministic reducer for HumanApprovalDetails state channel.
    
    Invariants:
    1. If update is None, current is preserved.
    2. If current is None or uninitialized, update is accepted.
    3. Enforces valid lifecycle transitions via current.validate_transition_to(update.approval_status).
    4. Prevents illegal transitions from terminal states (APPROVED, REJECTED, EXPIRED).
    """
    current_obj: Optional[HumanApprovalDetails] = None
    if current is not None:
        current_obj = (
            current if isinstance(current, HumanApprovalDetails)
            else HumanApprovalDetails.model_validate(current)
        )

    if update is None:
        return current_obj if current_obj is not None else HumanApprovalDetails()

    update_obj: HumanApprovalDetails = (
        update if isinstance(update, HumanApprovalDetails)
        else HumanApprovalDetails.model_validate(update)
    )

    if current_obj is None:
        return update_obj

    # Enforce lifecycle transition rules
    current_obj.validate_transition_to(update_obj.approval_status)

    return update_obj


FORBIDDEN_WORKER_FIELDS: Set[str] = {
    "human_approval",
    "verification_decisions",
    "workflow_status",
}


def validate_agent_state_update(
    agent_name: AgentName,
    update: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Enforces write-boundary governance across multi-agent state channels.
    
    Security Invariants:
    - Worker agents (ANOMALY_DETECTION, ROOT_CAUSE_ANALYSIS) are strictly forbidden
      from directly modifying:
      1. human_approval (cannot self-approve maintenance tickets or alter gate status)
      2. verification_decisions (cannot self-verify hypotheses; only Supervisor corroboration engine may verify)
      3. workflow_status (cannot terminate or bypass workflow lifecycle)
    
    Raises:
        PermissionError: If a worker agent attempts to write to a restricted field.
    """
    if not isinstance(update, dict):
        return update

    worker_agents = {AgentName.ANOMALY_DETECTION, AgentName.ROOT_CAUSE_ANALYSIS}
    if agent_name in worker_agents:
        forbidden_present = set(update.keys()) & FORBIDDEN_WORKER_FIELDS
        if forbidden_present:
            sorted_fields = sorted(list(forbidden_present))
            raise PermissionError(
                f"Security Write-Boundary Violation: Worker agent '{agent_name.value}' is not permitted "
                f"to write to restricted state field(s): {sorted_fields}. "
                f"These fields are reserved for the Supervisor or Human Operator."
            )

    return update

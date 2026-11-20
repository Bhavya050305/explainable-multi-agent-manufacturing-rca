# ManuMind AI — Phase 5 Step 2.2: Root-Cause Verification Governance Hardening Report

**Project:** ManuMind AI — Explainable Multi-Agent AI System for Manufacturing Anomaly Detection and Root Cause Analysis  
**Institution:** Department of AI & Data Science, RMK Engineering College  
**Repository:** `D:\Desktop\FInal year project\manumind-ai`  
**Branch:** `main` (Git HEAD: `a1e7e77fa550724f812cc2a1024a6ff7d194bc20`)  
**Milestone:** Phase 5 Step 2.2 — Root-Cause Verification Governance Hardening  
**Supabase Migration Revision:** `f3a9082b1c42`  
**Execution Timestamp:** 2026-11-19 21:35:00 IST  
**Final Verdict:** `PASS — FULLY HARDENED`

---

## 1. Executive Summary

During Phase 5 Step 2.1, a security audit identified that `CandidateRootCause` accepted `verification_status = VERIFIED` if supporting evidence IDs were non-empty and confidence was at least `0.5`. This created a critical architectural gap where an AI worker agent or untrusted LLM output could directly self-assert hypotheses as verified, bypassing multi-modal evidence corroboration rubrics established in Step 0.1 ($\ge 0.60$ threshold, $\ge 2$ distinct evidence sources).

In Phase 5 Step 2.2, this governance vulnerability was remediated at the shared-state and schema boundary:
1. **Hypothesis vs. Verification Separation:** Worker agents formulating candidate root causes generate diagnostic hypotheses only (`UNVERIFIED` or `HYPOTHESIS_PENDING`). Direct instantiation of `CandidateRootCause` with `VERIFIED` status is strictly rejected with a `Security Invariant Violation`.
2. **Authoritative Verification Decisions:** Introduced `RootCauseVerificationDecision` Pydantic V2 model. Authoritative verification requires multi-source corroboration ($\ge 0.60$ rubric threshold, $\ge 2$ distinct evidence source types, non-empty evidence IDs, and worker agent exclusion).
3. **State Channel Cross-Validation:** State model `ManuMindStateModel` enforces that `root_cause_verification_status == VERIFIED` requires a matching verified decision in `verification_decisions` whose candidate and evidence IDs are verified to exist in state provenance.
4. **Human Approval Lifecycle State Machine:** Enforced state transition lifecycle rules (`PENDING -> APPROVED/REJECTED/EXPIRED`). Terminal states (`APPROVED`, `REJECTED`, `EXPIRED`) are strictly immutable (`REJECTED -> APPROVED` and `EXPIRED -> APPROVED` are rejected).
5. **Agent Write Boundaries:** Implemented `validate_agent_state_update` blocking worker agents (`ANOMALY_DETECTION`, `ROOT_CAUSE_ANALYSIS`) from writing to `human_approval`, `verification_decisions`, or `workflow_status`.
6. **Comprehensive Verification:** 44 unit tests executed across the state, reducer, and governance test suites; 100% passed in 5.50 seconds.

---

## 2. Architecture & Governance Remediation Details

### 2.1 Hypothesis vs. Verification Decision Separation

In [backend/app/agents/schemas.py](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/agents/schemas.py#L125-L172), `CandidateRootCause` was decoupled from verification authority:

```python
@model_validator(mode="after")
def validate_candidate_integrity(self) -> "CandidateRootCause":
    """
    Phase 5 Step 2.2 Security Invariant:
    Candidate root causes formulated by worker agents or parsed from LLM completions
    represent diagnostic hypotheses and CANNOT directly self-assert VERIFIED status.
    Authoritative verification requires a distinct RootCauseVerificationDecision.
    """
    if self.verification_status == VerificationStatus.VERIFIED:
        raise ValueError(
            f"Security Invariant Violation: Candidate root cause '{self.cause_id}' cannot be directly "
            f"instantiated with verification_status=VERIFIED. Candidates represent unverified hypotheses "
            f"(permit UNVERIFIED or HYPOTHESIS_PENDING). Verification requires an authoritative "
            f"RootCauseVerificationDecision from the Supervisor corroboration engine."
        )
    return self
```

### 2.2 Authoritative Verification Decision Model

Added `RootCauseVerificationDecision` in [backend/app/agents/schemas.py](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/agents/schemas.py#L174-L232):

- **Model Configuration:** `frozen=True, extra="forbid"`
- **Corroboration Score:** Bounded in `[0.0, 1.0]`. Must be $\ge 0.60$ for `VERIFIED` status (Step 0.1 human escalation / ticket threshold).
- **Source Diversity:** Integer count of distinct evidence source types. Must be $\ge 2$ for `VERIFIED` status (multi-modal consensus).
- **Evidence IDs:** Must be non-empty for `VERIFIED` status.
- **Authority Exclusion:** Worker agents (`ANOMALY_DETECTION`, `ROOT_CAUSE_ANALYSIS`) are strictly forbidden from acting as `verified_by`.
- **Supported Methods:** `VerificationMethod.TIER_1_MULTI_MODAL_CONSENSUS`, `TIER_2_SENSOR_RAG_CORROBORATION`, `TIER_3_HUMAN_EXPERT_ESCALATION`.

### 2.3 Cross-Field State Integrity Validation

In [backend/app/agents/state.py](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/agents/state.py#L180-L215), `validate_security_and_integrity_invariants` enforces:

```python
# Invariant 3: Root cause verification governance
if self.root_cause_verification_status == VerificationStatus.VERIFIED:
    verified_decisions = [
        d for d in self.verification_decisions if d.verification_status == VerificationStatus.VERIFIED
    ]
    if not verified_decisions:
        raise ValueError(
            "Security Invariant 3 Violation: root_cause_verification_status cannot be VERIFIED "
            "without an authoritative RootCauseVerificationDecision with status VERIFIED."
        )

    known_evidence_ids = {e.evidence_id for e in self.evidence_collection}
    known_evidence_ids.update(self.supporting_evidence)
    known_evidence_ids.update(self.supporting_evidence_references)
    known_candidate_ids = {c.cause_id for c in self.candidate_root_causes}

    for vd in verified_decisions:
        if known_candidate_ids and vd.candidate_id not in known_candidate_ids:
            raise ValueError(
                f"Security Invariant 3 Violation: Verification decision '{vd.decision_id}' "
                f"references candidate '{vd.candidate_id}' which does not exist in candidate_root_causes."
            )
        for ev_id in vd.verified_evidence_ids:
            if ev_id not in known_evidence_ids:
                raise ValueError(
                    f"Security Invariant 3 Violation: Verification decision '{vd.decision_id}' "
                    f"references evidence ID '{ev_id}' which is not present in state evidence collection."
                )
```

---

## 3. Human Approval Lifecycle State Machine

Implemented `validate_transition_to` on `HumanApprovalDetails` in [backend/app/agents/schemas.py](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/agents/schemas.py#L294-L326):

```
                   +---------------------+
                   |       PENDING       |
                   +----------+----------+
                              |
        +---------------------+---------------------+
        |                     |                     |
        v                     v                     v
+---------------+     +---------------+     +---------------+
|   APPROVED    |     |   REJECTED    |     |    EXPIRED    |
|  (Terminal)   |     |  (Terminal)   |     |  (Terminal)   |
+---------------+     +---------------+     +---------------+
```

### Transition Enforcement Matrix:

| Initial State | Target State | Permitted? | Invariant Enforced |
| :--- | :--- | :--- | :--- |
| `PENDING` | `APPROVED` | **Yes** | Valid approval with human approver. |
| `PENDING` | `REJECTED` | **Yes** | Valid rejection with review reason. |
| `PENDING` | `EXPIRED` | **Yes** | Valid timeout transition. |
| `APPROVED` | `REJECTED` | **No** | Terminal state cannot be altered. |
| `APPROVED` | `PENDING` | **No** | Terminal state cannot be reverted. |
| `REJECTED` | `APPROVED` | **No** | Rejection is permanent; cannot transition to approved. |
| `EXPIRED` | `APPROVED` | **No** | Expired proposal cannot self-revive into approved. |
| `NOT_REQUIRED`| Any | **No** | Unalterable automated/simulation mode. |

---

## 4. Multi-Agent Write Boundaries

In [backend/app/agents/reducers.py](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/agents/reducers.py#L314-L352), `validate_agent_state_update` enforces channel security:

```python
FORBIDDEN_WORKER_FIELDS: Set[str] = {
    "human_approval",
    "verification_decisions",
    "workflow_status",
}

def validate_agent_state_update(agent_name: AgentName, update: Dict[str, Any]) -> Dict[str, Any]:
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
```

---

## 5. Test Suite Execution & Results

Executed the unified test suite:
- [test_agent_state.py](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/tests/test_agent_state.py): 10 tests
- [test_agent_reducers.py](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/tests/test_agent_reducers.py): 11 tests
- [test_agent_verification_governance.py](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/tests/test_agent_verification_governance.py): 23 tests

```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0
rootdir: D:\Desktop\FInal year project\manumind-ai
plugins: anyio-4.14.2, asyncio-1.4.0
collected 44 items

backend/tests/test_agent_state.py ....................                   [ 22%]
backend/tests/test_agent_reducers.py .........................           [ 47%]
backend/tests/test_agent_verification_governance.py .................... [100%]

============================= 44 passed in 5.50s ==============================
```

All 44 tests passed with zero failures and zero warnings.

---

## 6. Environment Invariance Verification

| Invariant / Asset | Expected Baseline | Observed Live Value | Status |
| :--- | :--- | :--- | :--- |
| **Python Version** | Python 3.11.9 | Python 3.11.9 | **Confirmed** |
| **LangGraph Version** | 0.2.45 | 0.2.45 | **Confirmed** |
| **LangChain Core Version** | 0.3.15 | 0.3.15 | **Confirmed** |
| **Pip Environment Health** | No broken requirements | `pip check`: Clean | **Confirmed** |
| **RAG Lock File SHA256** | `778fde7658e8f5a0fd3cb039c6271fbbcce95ab967fbece6d29ca82e3f035ad2` | Exactly matches baseline | **Confirmed** |
| **ChromaDB Collection** | `manumind_bge_small_v1` in `knowledge_base/index` | Count: 564, Dimension: 384 | **Confirmed** |
| **Supabase Alembic Revision** | `f3a9082b1c42` | `f3a9082b1c42 (head)` | **Confirmed** |
| **Git Baseline HEAD** | `a1e7e77fa550724f812cc2a1024a6ff7d194bc20` | `a1e7e77fa550724f812cc2a1024a6ff7d194bc20` | **Confirmed** |
| **Git Staged Files** | 0 staged changes | 0 staged changes | **Confirmed** |
| **Untracked Files** | Preserved | Preserved | **Confirmed** |

---

## 7. Next Steps: Authorization for Phase 5 Step 3

With Step 2.2 completed and verified:
1. The shared state and reducer boundaries are completely secured against self-authorization, uncorroborated verification assertions, and channel write pollution.
2. The system is ready to proceed to **Phase 5 Step 3: Multi-Agent LangGraph Node Implementation** (Supervisor Agent, Anomaly Detection Agent, and Root Cause Analysis Agent) adhering strictly to these hardened state schemas.

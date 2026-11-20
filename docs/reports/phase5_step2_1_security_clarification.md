# ManuMind AI — Phase 5 Step 2.1: Focused Security and Acceptance-Gap Verification Report

**Project:** ManuMind AI — Explainable Multi-Agent AI System for Manufacturing Anomaly Detection and Root Cause Analysis  
**Institution:** Department of AI & Data Science, RMK Engineering College  
**Repository:** `D:\Desktop\FInal year project\manumind-ai`  
**Branch:** `main` (Git HEAD: `a1e7e77fa550724f812cc2a1024a6ff7d194bc20`)  
**Milestone:** Phase 5 Step 2.1 — Focused Security and Acceptance-Gap Verification  
**Audit Mode:** Strictly Read-Only (Zero Code, Package, Database, or RAG Mutations)  
**Execution Timestamp:** 2026-11-19 21:18:00 IST  
**Final Verdict:** `PASS WITH DOCUMENTED LIMITATIONS`

---

## 1. Executive Summary

This strictly read-only audit investigated the remaining security, verification, and governance questions for the Phase 5 Step 2 typed shared state architecture prior to authorizing Phase 5 Step 3 (Multi-Agent Node Implementation).

### Key Findings Summary:
1. **Root-Cause Verification Threshold:** The `0.5` confidence threshold is hard-coded in `backend/app/agents/schemas.py:166`. Under the current schema, an LLM or AI agent could mark a hypothesis as `VERIFIED` by returning confidence $\ge 0.5$ and at least one evidence string. This creates a potential vulnerability where an unverified hypothesis is represented as verified without an independent verification decision or multi-modal corroboration.
2. **Step 0.1 Incommensurability Divergence:** The hard-coded `0.5` threshold is below the $0.60$ minimum cosine similarity / human escalation threshold established in Phase 5 Step 0.1 (`phase5_step0_1_comprehensive_risk_analysis.md:349`).
3. **Human Approval Governance:** The schema strictly enforces that AI agents cannot self-authorize ticket creation (`schemas.py:244-251` and `state.py:167-173`). No secrets or HMAC keys are stored in state. However, approval state transitions lack an explicit state-machine validator in the reducer.
4. **Reducer Immutability & Conflict Preservation:** Reducers guarantee input immutability and conflict preservation. Verified root-cause candidates and evidence items are never deleted or silently overwritten.
5. **Git & Environment Invariance:** Working tree remains preserved with 0 staged files and HEAD matching `a1e7e77fa550724f812cc2a1024a6ff7d194bc20`.

---

## 2. Investigation of the Root-Cause Verification Threshold

### 2.1 Implementation Location
- **Primary Validator:** [schemas.py](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/agents/schemas.py#L154-L171)
  ```python
  @model_validator(mode="after")
  def validate_verification_integrity(self) -> "CandidateRootCause":
      if self.verification_status == VerificationStatus.VERIFIED:
          if not self.supporting_evidence_ids:
              raise ValueError(
                  f"Invariant violation: Candidate root cause '{self.cause_id}' cannot be marked "
                  f"as VERIFIED without at least one supporting evidence reference."
              )
          if self.confidence < 0.5:
              raise ValueError(
                  f"Invariant violation: Candidate root cause '{self.cause_id}' cannot be marked "
                  f"as VERIFIED with confidence ({self.confidence}) below 0.5 threshold."
              )
      return self
  ```
- **State-Level Guard:** [state.py](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/agents/state.py#L176-L185)
  Enforces that `root_cause_verification_status == VERIFIED` requires supporting evidence or at least one verified candidate root cause in `candidate_root_causes`.

### 2.2 Detailed Invariant Answers

| Investigation Question | Findings & Evidence | Assessment |
| :--- | :--- | :--- |
| **1. Where is the 0.5 threshold implemented?** | `backend/app/agents/schemas.py`, line 166. | Exact line identified. |
| **2. Is it a hard-coded validation threshold?** | Yes. `self.confidence < 0.5` is a hard-coded float literal. | Hard-coded. |
| **3. Can a root cause become VERIFIED solely by supplying evidence and confidence >= 0.5?** | **Yes.** Any caller passing `verification_status="VERIFIED"`, `supporting_evidence_ids=["EV-001"]`, and `confidence=0.55` satisfies validation. | Potential gap in epistemic rigor. |
| **4. Is there a distinct, valid verification decision?** | **No.** `verification_status` is an enum attribute on `CandidateRootCause`. There is no `verified_by` field, no verification timestamp, and no distinct rule-engine decision object. | Identified architectural gap. |
| **5. Can an AI agent or untrusted LLM response mark a hypothesis as VERIFIED?** | **Yes.** If an LLM returns JSON with `verification_status: "VERIFIED"`, the schema accepts it. Unlike `HumanApprovalDetails` (which rejects AI agents), `CandidateRootCause` has no agent role exclusion. | Security / Governance risk. |
| **6. Does the model distinguish evidence-backed verification from a numerical confidence threshold?** | **Partially.** It mandates both non-empty evidence IDs and confidence $\ge 0.5$. However, having one evidence string does not prove corroboration, and confidence remains conflated with verification. | Conflation present. |
| **7. Is this consistent with the Step 0.1 confidence-governance design?** | **No.** Step 0.1 established: (a) $0.60$ as minimum human escalation cutoff, (b) $0.80$ as Tier 1 multi-modal consensus, and (c) that causal verification requires an Evidence Corroboration Engine, not an arbitrary 0.5 threshold. | Divergence confirmed. |

### 2.3 Smallest Recommended Correction (For Step 3)
Do not alter Step 2 code during this verification. For Step 3 implementation:
1. In `schemas.py`, restrict `CandidateRootCause` generated by the Root Cause Analysis Agent to strictly `VerificationStatus.UNVERIFIED` or `HYPOTHESIS_PENDING`.
2. Add `verified_by: Optional[str] = None` and `verification_method: Optional[str] = None` to `CandidateRootCause`.
3. Reserve setting `verification_status = VERIFIED` to the Supervisor Agent running the Tier 1/2 Evidence Corroboration Rubric (aligning with Step 0.1 thresholds: $\ge 0.60$ for ticket proposal, $\ge 0.80$ for multi-modal consensus).

---

## 3. Human Approval Governance Verification

| Governance Requirement | Source File & Line References | Test Name & Location | Status |
| :--- | :--- | :--- | :-: |
| **All 5 statuses represented** | `backend/app/agents/enums.py:105-111`<br>(`NOT_REQUIRED`, `PENDING`, `APPROVED`, `REJECTED`, `EXPIRED`) | `test_valid_initial_state_construction`<br>(`test_agent_state.py:46`) | **PASS**<br>*(Coverage Gap on REJECTED/EXPIRED)* |
| **Invalid approval transitions rejected** | `backend/app/agents/schemas.py:234-251`<br>(`validate_approval_boundary`) | `test_agent_self_authorization_strictly_rejected`<br>(`test_agent_state.py:160`) | **PASS** |
| **AI agent cannot become approving authority** | `backend/app/agents/schemas.py:244-251`<br>`backend/app/agents/state.py:167-173` | `test_agent_self_authorization_strictly_rejected`<br>(`test_agent_state.py:160`) | **PASS** |
| **Approval metadata cannot be fabricated** | `backend/app/agents/schemas.py:202-252`<br>(Frozen Pydantic model) | `test_agent_self_authorization_strictly_rejected`<br>(`test_agent_state.py:160`) | **PASS**<br>*(Channel write-gate needed in Step 3)* |
| **Approval status alone cannot authorize ticket creation** | Phase 4 MCP tool boundary (`backend/app/mcp_server/tools.py`) requires one-time consumption token (`consumed_tokens`). State stores reference only. | `test_valid_initial_state_construction`<br>(`test_agent_state.py:46`) | **PASS** |
| **No secret or HMAC token stored in shared state** | `backend/app/agents/schemas.py:25-35` (`_sanitize_string`), lines 215-217 (`approval_reference` stores ID `PROP-XXXX` only). | `test_sanitize_error_message_masks_credentials`<br>(`test_agent_reducers.py:62`) | **PASS** |
| **Distinguishes metadata from external auth token** | `HumanApprovalDetails` stores `status`, `reference`, `reason`, `timestamp`, `approved_by`. Does not hold secret signing keys. | `test_valid_initial_state_construction`<br>(`test_agent_state.py:46`) | **PASS** |

### Test Coverage Gaps Identified:
- **Gap 1:** `HumanApprovalStatus.REJECTED`, `EXPIRED`, and `NOT_REQUIRED` lack explicit dedicated unit tests asserting lifecycle state assignments.
- **Gap 2:** No test verifying state-machine transition rejection (e.g. `REJECTED -> APPROVED`).
- **Gap 3:** No test asserting that worker agent nodes are prevented from emitting updates on the `human_approval` channel (belongs in Step 3 workflow graph tests).

---

## 4. Reducer Protection Verification

1. **Human Approval Overwrite Protection:**
   - Implemented via `overwrite_supervisor_field(current, update)` in [reducers.py](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/agents/reducers.py#L23-L30).
   - If an update is `None`, existing human approval metadata is completely preserved.
   - *Design Boundary for Step 3:* In LangGraph, node return schemas must be strictly scoped so that only the Supervisor node can output keys for `human_approval`.
2. **Verified Root-Cause Findings Preservation:**
   - Implemented via `merge_candidate_root_causes(current, update)` in [reducers.py](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/agents/reducers.py#L144-L190).
   - The reducer iterates over existing items and appends incoming items. It **never deletes or modifies** an existing candidate cause.
   - If a collision occurs on `cause_id`, the competing finding is appended with an `__alt_{N}` suffix, guaranteeing that verified findings cannot be erased.
3. **Evidence Conflict Preservation:**
   - Implemented via `merge_evidence(current, update)` in [reducers.py](file:///D:/Desktop/FInal%20year%20project/manumind-ai/backend/app/agents/reducers.py#L91-L142).
   - Colliding evidence IDs with differing descriptions or provenance are disambiguated with `__conflict_{N}`, guaranteeing complete evidentiary auditability.

---

## 5. Read-Only Git Status Verification

- **Current Branch:** `main`
- **Current HEAD:** `a1e7e77fa550724f812cc2a1024a6ff7d194bc20` (Matches expected baseline exactly)
- **Staged Changes:** Exactly 0 files.
- **Unstaged Tracked Changes:** 1 file (`backend/app/models/__init__.py`, preserved from Phase 4).
- **Untracked Historical Work:** All historical reports, migration scripts, and MCP test suites remain intact.
- **Unexpectedly Deleted Files:** Zero.

---

## 6. Deliverables Generated

- **Clarification Markdown Report:**  
  [phase5_step2_1_security_clarification.md](file:///D:/Desktop/FInal%20year%20project/manumind-ai/docs/reports/phase5_step2_1_security_clarification.md)
- **Structured JSON Report:**  
  [phase5_step2_1_security_clarification.json](file:///D:/Desktop/FInal%20year%20project/manumind-ai/docs/reports/phase5_step2_1_security_clarification.json)

---

## 7. Final Verdict

### Final Verdict: **`PASS WITH DOCUMENTED LIMITATIONS`**

### Verdict Justification:
1. All core security invariants (anti-self-authorization, tool execution boundary, secret masking, bounded confidence, and reducer immutability) are fully implemented, verified, and operational.
2. The root-cause verification threshold was investigated and documented: the hard-coded `0.5` threshold in `schemas.py:166` allows an LLM/agent to mark a candidate as `VERIFIED` without an external corroboration engine. This is documented as a known limitation with a minimum recommended correction for Phase 5 Step 3.
3. Human approval governance was verified across all 7 criteria, with 3 minor test coverage gaps documented.
4. Reducer conflict preservation and verified finding immutability are verified by catalog evidence and passing unit tests.
5. Zero modifications to Python source files, dependencies, databases, or Git status were made.

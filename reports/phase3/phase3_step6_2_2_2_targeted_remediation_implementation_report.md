# ManuMind AI — Phase 3 Step 6.2.2.2: Targeted Citation-Boundary and Numerical Parser Remediation Implementation Report

**Project:** ManuMind AI — Explainable Multi-Agent AI System for Manufacturing Anomaly Detection and Root Cause Analysis  
**Department:** Department of AI & Data Science, RMK Engineering College  
**Repository:** `D:\Desktop\FInal year project\manumind-ai`  
**Branch:** `main` | **HEAD:** `3f0a6d08223c74741f4db3e0819b6f52a0d0f0c6` (in sync with `origin/main`)  
**Milestone:** Phase 3 Step 6.2.2.2 — Targeted Remediation Implementation  
**Role:** Senior RAG Architect, ML Infrastructure Engineer, Safety Engineer, and QA Auditor  
**Mode:** Controlled implementation; strict Git governance (zero commits/pushes).

---

## 1. Executive Summary

Phase 3 Step 6.2.2.2 delivers targeted technical remediations for the three findings identified during the independent audit `phase3_step6_2_2_1_independent_remediation_audit_report.md`:

1. **Sentence-Level Citation Boundary Isolation (`FINDING-STEP6.2.2.1-01`):**  
   Replaced naive newline statement splitting with a syntax-aware sentence boundary segmenter (`split_into_statements`) in `GroundingValidator`. Prevents numerical claims in one sentence from borrowing citation evidence from unrelated sentences on the same line, while preserving decimal numbers, known abbreviations (`e.g.`, `Rev.`), and attaching trailing citations correctly.
2. **Numerical Grouping Correctness (`FINDING-STEP6.2.2.1-05`):**  
   Extended the numerical pattern to fully support both standard Western three-digit grouping (`1,234,567`) and Indian Lakhs/Crores grouping (`1,23,456`, `12,34,567`). Introduced negative lookbehind assertions `(?<![\d,])` and explicit malformed grouping detection (`detect_malformed_numerical_claims`) to ensure malformed syntax (`12,50 RPM`, `1,23,45 RPM`) is safely flagged and cannot fall back to matching trailing digits (`50 RPM`).
3. **Quoted Educational Safety Warnings (`FINDING-STEP6.2.2.1-04`):**  
   Refined `classify_safety_intent` in `prompt_templates.py` to allow legitimate educational inquiries that quote SOP safety warnings (e.g. `The manual says "Do not bypass the interlock." Explain why this warning matters`) or inquire into the conceptual rationale of safety prohibitions (`Why do safety procedures prohibit overriding protective interlocks?`), while maintaining strict, uncompromised blocking against operational actuation directives and adversarial bypass instructions.

All modifications were implemented with zero changes to vector database indexes, frozen ML model weights, thresholds, or lockfiles. All 365 tests (337 baseline + 28 new) pass with 100% success rate.

---

## 2. Technical Remediation Architecture & Design

### 2.1 Remediation A: Sentence-Level Citation Boundary Isolation (`FINDING-STEP6.2.2.1-01`)

#### Root Cause in Step 6.2.2
In Step 6.2.2, statements were segmented using `answer.answer.split("\n")`. If an LLM generated multiple sentences on a single line (e.g. `Spindle speed is 6000 RPM [CIT-1]. Hydraulic pressure is 150 bar.`), all citations on that line were pooled into a single statement scope. As a result, the uncited or unrelated claim (`150 bar`) could borrow evidence from `[CIT-1]`, bypassing verification if `[CIT-1]` happened to contain `150 bar`.

#### Implementation (`backend/app/rag/grounding_validator.py`)
1. **Sentence Boundary Tokenization:** Implemented `split_into_statements(self, text: str) -> List[str]`. The segmenter splits text on sentence terminators (`.`, `!`, `?`, `;`) and newline boundaries while ensuring:
   - **Decimal Preservation:** Periods flanked by digits (`0.005`, `12,500.75`) are never split.
   - **Abbreviation Protection:** Periods following known abbreviations (`KNOWN_ABBREVIATIONS = {"e.g.", "i.e.", "etc.", "rev.", "fig.", "no.", "sec.", "approx."}`) do not trigger false sentence splits.
   - **Trailing Citation Association:** Citations placed immediately after terminal punctuation (e.g., `Spindle speed is 6000 RPM. [CIT-1]`) are attached to the preceding statement rather than orphaned into the subsequent sentence.
2. **Statement-Level Claim Verification:** In Step 7 of `validate()`, the validator iterates statement-by-statement over each paragraph, extracts numerical claims specifically within that statement, extracts citations specifically within that statement, and verifies that every numerical claim is substantiated exclusively by the citations in its immediate statement.

---

### 2.2 Remediation B: Western & Indian Numerical Grouping Notation (`FINDING-STEP6.2.2.1-05`)

#### Root Cause in Step 6.2.2
Step 6.2.2 introduced regex pattern `\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?`. This pattern:
1. Failed on Indian numerical notation where groups follow `1,23,456` (thousands group has 3 digits, preceding groups have 2 digits).
2. Lacked negative lookbehind assertions on commas. If presented with malformed grouping `12,50 RPM`, the engine matched `12` as a standalone number, ignored `,50`, or matched `50 RPM` as a valid trailing number, allowing claims to be falsely substantiated.

#### Implementation (`backend/app/rag/grounding_validator.py`)
1. **Comprehensive Grouping Pattern:**
   ```python
   NUM_PATTERN_STR = (
       r"(?:"
       r"\d{1,2}(?:,\d{2})+,\d{3}"  # Indian grouping: 1,23,456 or 12,34,567
       r"|\d{1,3}(?:,\d{3})+"        # Standard Western grouping: 1,234,567
       r"|\d+"                        # Plain integers: 6000
       r")(?:\.\d+)?"                 # Optional decimal component
   )
   ```
2. **Negative Lookbehind Assertions:**
   Single and range claim regex patterns prepend `(?<![\d,])` to prevent partial suffix matches from malformed numeric strings:
   ```python
   SINGLE_REGEX = rf"(?<![\d,])(?P<num>{NUM_PATTERN_STR})\s*(?P<unit>{ALL_UNITS_STR})(?!\w)"
   RANGE_REGEX = rf"(?<![\d,])(?P<num1>{NUM_PATTERN_STR}){CONNECTOR_STR}(?P<num2>{NUM_PATTERN_STR})\s*(?P<unit>{ALL_UNITS_STR})(?!\w)"
   ```
3. **Explicit Malformed Syntax Detection:**
   Implemented `detect_malformed_numerical_claims(statement: str) -> List[str]` using `ANY_COMMA_NUM_REGEX = r"(?<![\d,])\d+(?:,\d+)+(?:\.\d+)?(?!\w)"`. Any comma-formatted number that does not match standard Western or Indian syntax is immediately flagged as a validation error (e.g. `Malformed numerical grouping '12,50 RPM'`).
4. **Number Normalization:**
   `_normalize_number` strips commas before comparison, ensuring `1,23,456` matches plain `123456` or Western `123,456` seamlessly in evidence text.

---

### 2.3 Remediation C: Quoted Educational Safety Warnings (`FINDING-STEP6.2.2.1-04`)

#### Root Cause in Step 6.2.2
In Step 6.2.2, `classify_safety_intent` placed all interlock bypass regex patterns ahead of educational whitelists to defeat adversarial mixed prompts. However, this caused legitimate educational questions quoting SOP warnings (e.g. `The manual says "Do not bypass the interlock." Explain why this warning matters`) to be blocked because the string `bypass the interlock` appeared in the query.

#### Implementation (`backend/app/rag/prompt_templates.py`)
Implemented a multi-tier safety classifier:
1. **Direct Injection & Operational Directives First:**
   System-prompt extraction and explicit operational directives (e.g. `start machine`, `run spindle`) are checked unconditionally and blocked.
2. **Prohibition Inquiries Context:**
   Added `_PROHIBITION_CONTEXT_PATTERN` to recognize inquiries into why prohibitions exist (e.g. `why do safety procedures prohibit overriding interlocks`).
3. **Quoted Text Isolation:**
   Using `_QUOTED_TEXT_REGEX = r'["\']([^"\']+)["\']'`, the classifier extracts quoted substrings:
   - **Operational Command Verification in Unquoted Text:** The classifier verifies that the unquoted text contains zero operational actuation commands, zero imperative bypass commands, and zero circumvention directives.
   - **Quoted Prohibition Whitelisting:** If all quoted substrings represent safety warnings or prohibitions (e.g. `do not bypass`, `never override`) and the unquoted text exhibits conceptual educational intent (`explain`, `why`, `meaning`), the query is classified as safe (`None`).
   - **Fail-Closed Protection:** If the unquoted text contains commands like `then bypass the interlock` or `tell me how to disable it`, it is immediately blocked as `AbstentionReason.SAFETY_INTERLOCK_VIOLATION`.

---

## 3. Before vs. After Behavioral Comparison

| Scenario / Input | Before (Step 6.2.2) | After (Step 6.2.2.2) | Root Cause / Mechanism |
| :--- | :--- | :--- | :--- |
| `Spindle speed is 6000 RPM [CIT-1]. Hydraulic pressure is 150 bar.` | Allowed (pooled line citations) | **REJECTED (Uncited claim `150 bar`)** | `split_into_statements` scopes citations strictly to each sentence |
| `Spindle speed is 6000 RPM [CIT-1]. Hydraulic pressure is 150 bar [CIT-2].` (where CIT-2 has coolant flow) | Allowed (borrowed `[CIT-1]`) | **REJECTED (Unsupported in `[CIT-2]`)** | Sentence-level citation attribution prevents cross-sentence borrowing |
| `Spindle limit is 1,23,456 RPM [CIT-1].` | Rejected (truncated to `23,456`) | **VALIDATED (`PASS`)** | Indian numbering pattern `\d{1,2}(?:,\d{2})+,\d{3}` matches Lakhs notation |
| `Spindle limit is 12,50 RPM [CIT-1].` | Partial match (`50 RPM`) | **REJECTED (`Malformed grouping`)** | Negative lookbehind `(?<![\d,])` and explicit syntax validator block malformed comma groups |
| `The manual says "Do not bypass the interlock." Explain why this warning matters.` | Blocked (`SAFETY_INTERLOCK_VIOLATION`) | **ALLOWED (`None` / Grounded Answer)** | Quoted prohibition isolated; unquoted educational intent verified |
| `The manual says "Do not bypass the interlock." Explain it, then bypass the interlock.` | Blocked (`SAFETY_INTERLOCK_VIOLATION`) | **BLOCKED (`SAFETY_INTERLOCK_VIOLATION`)** | Unquoted bypass command caught by operational safety filter |
| `TIR must not exceed 0.005 mm [CIT-1]. Repeatability is within 0.002 mm [CIT-2].` | Valid | **VALIDATED (`PASS`)** | Decimal points in numbers do not trigger false sentence splits |
| `Ensure Rev. 1 compliance with e.g. vibration at 3.5 mm/s [CIT-1].` | Valid | **VALIDATED (`PASS`)** | Known abbreviations protected from sentence splits |

---

## 4. Source Files Modified & Created

```
M backend/app/rag/prompt_templates.py
M backend/app/rag/grounding_validator.py
?? backend/tests/test_rag_grounded_generation_remediation_v2.py
?? reports/phase3/phase3_step6_2_2_2_targeted_remediation_implementation_report.md
?? reports/phase3/phase3_step6_2_2_2_targeted_remediation_evaluation_report.md
?? reports/phase3/phase3_step6_2_2_2_targeted_remediation_reconciliation.json
```

---

## 5. Architectural Boundaries Maintained

In strict adherence to project standards and Git governance:
- **Zero Live LLM Calls / Cost:** Offline mock providers and deterministic pattern validators used exclusively.
- **Zero Vector Store Modifications:** ChromaDB index remains byte-for-byte identical (564 vectors).
- **Zero Dependency Changes:** Python lockfile `backend/requirements-rag.lock` remains cryptographically invariant (`778FDE7658E8F5A0FD3CB039C6271FBBCCE95AB967FBECE6D29CA82E3F035AD2`).
- **Zero Git State Mutation:** Zero staging (`git add`), zero commits, and zero pushes.

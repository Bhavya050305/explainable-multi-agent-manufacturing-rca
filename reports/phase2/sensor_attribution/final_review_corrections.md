# ManuMind AI — Phase 2, Step 4: Final Attribution Documentation Review & Corrections

**Project Title:** ManuMind AI: Explainable Multi-Agent AI System for Manufacturing Anomaly Detection and Root Cause Analysis
**Institution:** RMK Engineering College — Department of Artificial Intelligence and Data Science
**Component:** Phase 2, Step 4 — Attribution Documentation Review & Methodological Refinements
**Auditor:** Senior AI/ML Engineer & Independent Evaluator
**Date:** November 2026
**Status:** **REVIEW COMPLETED — ALL DOCUMENTATION CORRECTIONS APPLIED & VERIFIED**

---

## 1. Executive Summary & Purpose

Following the successful implementation, empirical evaluation, and testing of **Phase 2, Step 4 (Sensor-Level Anomaly Attribution)**, this review formalizes specific documentation corrections, terminological refinements, and methodological boundaries.

### Strict Immutability & Non-Modification Compliance:
- **No Retraining:** Neither the Isolation Forest nor the LSTM Autoencoder was retrained.
- **No Weight or Parameter Changes:** Neural network weights, scalers, and decision trees remain unaltered.
- **No Threshold Alterations:** Calibrated decision thresholds ($\tau_{\text{IF}} = 0.0269$, $\tau_{\text{LSTM}} = 0.901464$, and sequence aggregation thresholds) were strictly preserved.
- **No Partition or Dataset Alterations:** Train (70%), Validation (15%), and Test (15%) splits remain unchanged.
- **No Database Modifications:** SQLite (`manumind.db`) and Supabase PostgreSQL 17.11 (40,416 rows) remain untouched.
- **No CSV Data Modification:** Original sequence attribution values in `lstm_sensor_attributions.csv` and `isolation_forest_sensor_attributions.csv` were preserved.

---

## 2. Itemized Changelog of Documentation Corrections

### Correction 1: Healthy Attribution Distribution Interpretation
- **Previous Statement:** Described normal sequence attribution as approximately uniform at ~20% per feature.
- **Corrected Formulation:**
  - Documented that healthy sequence attribution is **relatively distributed** across features, but not strictly uniform:
    - Four features (`Vibration`: 21.58%, `Pressure`: 23.73%, `Current`: 23.21%, `RPM`: 23.35%) each account for a balanced **21.6% to 23.7%** share of nominal reconstruction error, representing irreducible zero-mean Gaussian measurement noise.
    - `Temperature` has a **substantially lower mean reconstruction-error contribution (8.14%)**.
  - **Engineering Explanation:** Temperature dynamics in this synthetic dataset are dominated by a smooth, 24-hour diurnal sinusoidal cycle ($2.5 \sin(\dots)$) which the LSTM Autoencoder predicts with very low reconstruction error, yielding a lower relative share compared to high-frequency sensor noise.
  - **Measurement Integrity:** The original empirical test measurements (Vibration: 21.58%, Temperature: 8.14%, Pressure: 23.73%, Current: 23.21%, RPM: 23.35%) were retained without modification.
- **Updated Files:**
  - `reports/phase2/sensor_attribution/sensor_attribution_report.md` (Section 5)
  - `reports/phase2/sensor_attribution/sensor_attribution_results.json` (`healthy_attribution_distribution`)

---

### Correction 2: Signed Residual Interpretation & Units
- **Previous Statement:** Used generalized phrasing describing residuals as deviations from a healthy physical profile.
- **Corrected Formulation:**
  - Clarified that signed residuals are calculated directly in the **standardized feature space** ($z$-score scale):
    $$\text{SignedResidual}_c = \frac{1}{30} \sum_{t=0}^{29} \left( X_{t, c} - \hat{X}_{t, c} \right)$$
    - **Positive residual ($+$):** Observed scaled sensor value is **above** the model reconstructed value ($X_{t, c} > \hat{X}_{t, c}$).
    - **Negative residual ($-$):** Observed scaled sensor value is **below** the model reconstructed value ($X_{t, c} < \hat{X}_{t, c}$).
  - **Prohibited Claim Avoided:** The model reconstruction $\hat{\mathbf{X}}$ is explicitly defined as the autoencoder's mathematical conditional representation learned from normal training data, **not a confirmed physical ground truth**.
  - **Dimensional Physical Values Preserved:** Inverse-transformed engineering unit residuals are documented as separate, explicit measurements:
    $$\Delta_{\text{physical}, c} = \text{SignedResidual}_c \times \sigma_{\text{train}, c}$$
    - `M102`: Temperature $+29.31^\circ\text{C}$ ($+13.35\sigma$), Pressure $+1.26\text{ bar}$ ($+10.29\sigma$)
    - `M104`: Vibration $+5.30\text{ mm/s}$ ($+23.37\sigma$), Temperature $+12.46^\circ\text{C}$ ($+5.68\sigma$), RPM $-34.18\text{ RPM}$ ($-4.56\sigma$)
    - `M107`: Pressure $-2.63\text{ bar}$ ($-21.50\sigma$, negative), Current $+4.38\text{ A}$ ($+6.16\sigma$, positive)
    - `M109`: Current $+10.06\text{ A}$ ($+14.15\sigma$), Vibration $+2.70\text{ mm/s}$ ($+11.90\sigma$), Temperature $+22.24^\circ\text{C}$ ($+10.13\sigma$)
- **Updated Files:**
  - `reports/phase2/sensor_attribution/sensor_attribution_report.md` (Sections 1, 2.1, 3, 4)
  - `reports/phase2/sensor_attribution/sensor_attribution_results.json` (`definitions.signed_residuals`)
  - `reports/phase2/sensor_attribution/fault_mechanism_consistency.json` (`attribution_notes`)

---

### Correction 3: Fault Progression Evaluation Scope & Partition Clarification
- **Previous Statement:** Fault progression analysis was presented alongside test results without explicitly defining the underlying sequence origins.
- **Corrected Formulation:** Formally decoupled the two evaluation scopes:
  1. **Scope A — Official Test-Set Attribution Benchmark ($N=580$ Sequences):**
     - Evaluated strictly on `data/processed/sequences_test.npz` (timesteps 3,400 to 3,999 across all 10 machines).
     - Official held-out test data evaluating late moderate-to-severe degradation regimes ($progression \ge 0.57$).
     - Test metrics remain untouched (Accuracy = 99.31%, Precision = 98.31%, Recall = 100.0%, F1 = 0.9915).
  2. **Scope B — Full-Lifecycle Diagnostic Attribution ($1,400$ Steps per Faulted Asset):**
     - Evaluated across timesteps 2,600 to 3,999 for `M102, M104, M107, M109`.
     - Spans historical records across three distinct chronological partitions:
       - Timesteps 2,600 to 2,799: Chronological **Training partition** timeline.
       - Timesteps 2,800 to 3,399: Chronological **Validation partition** timeline.
       - Timesteps 3,400 to 3,999: Chronological **Test partition** timeline.
     - **Strict Qualification:** This analysis is an **exploratory progression diagnostic** and is **not described as untouched test data**.
- **Updated Files:**
  - `reports/phase2/sensor_attribution/sensor_attribution_report.md` (Section 6)
  - `reports/phase2/sensor_attribution/sensor_attribution_results.json` (`metadata.evaluation_scopes`)

---

### Correction 4: Isolation Forest Ablation Contribution Normalization
- **Previous Statement:** Ablation percentages were presented without fully documenting the positive-only normalization constraint and non-additivity.
- **Corrected Formulation:**
  - **Raw Signed Ablation Deltas:** Retained in `isolation_forest_sensor_attributions.csv` as the primary unconstrained measurement:
    $$\Delta_c = s(\mathbf{x}) - s\left(\mathbf{x}^{(c)}\right)$$
  - **Negative Values Preserved:** When replacing feature $c$ with its healthy training reference increases isolation (making the sample appear more anomalous due to tree split alterations), $\Delta_c < 0$. Negative values were preserved and never silently discarded.
  - **Positive-Only Normalization Formula:**
    $$\text{ContribPct}_c = \frac{\max(0, \Delta_c)}{\sum_{k=1}^5 \max(0, \Delta_k) + \epsilon} \times 100$$
    Documented that percentages represent the *relative share of positive anomaly score reduction among contributing features*.
  - **Behavior When All Deltas Are Non-Positive:**
    When all five raw signed deltas are zero or negative ($\Delta_k \le 0$ for all $k \in \{1..5\}$), no feature contributed positively to anomaly score reduction. In that case, **all normalized contributions are set to 0.0%**, and the percentages **must not be interpreted as summing to 100%** (they sum to 0.0%, indicating zero positive ablation attribution).
  - **Why Contributions Are Non-Additive:**
    Isolation Forest decision trees partition feature space via orthogonal axis-aligned cuts. Features interact non-linearly across split depths. Altering one feature redirects observation traversal to different subtrees, meaning $\sum_{c=1}^5 \Delta_c \ne s(\mathbf{x}) - s(\mathbf{r})$ in general.
- **Updated Files:**
  - `reports/phase2/sensor_attribution/sensor_attribution_report.md` (Section 2.2)
  - `reports/phase2/sensor_attribution/sensor_attribution_results.json` (`definitions.isolation_forest_ablation_normalization`)
  - `backend/app/ml/sensor_attribution/isolation_forest_attribution.py` (explicit 0.0% fallback for non-positive mask)

---

### Correction 5: Revert of Unauthorized plan.md Modification
- **Action:** Inspected `plan.md` artifact for any modifications made during the documentation review task.
- **Reversion:** Because `plan.md` was not in the authorized Step 4 documentation correction list, the unauthorized update made in the previous turn was cleanly reverted, restoring the pre-existing state of line 105. All unrelated pre-existing contents were preserved.

---

## 3. Directory of Audited Documentation Files

All Step 4 attribution artifacts in [`reports/phase2/sensor_attribution/`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/sensor_attribution/) are finalized:

| File Name | Purpose | Status |
|---|---|:---:|
| [`sensor_attribution_report.md`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/sensor_attribution/sensor_attribution_report.md) | Comprehensive master sensor attribution report | **FINAL** |
| [`final_review_corrections.md`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/sensor_attribution/final_review_corrections.md) | Itemized review corrections and methodological changelog | **FINAL** |
| [`sensor_attribution_results.json`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/sensor_attribution/sensor_attribution_results.json) | Full machine and baseline numerical results with updated metadata | **FINAL** |
| [`fault_mechanism_consistency.json`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/sensor_attribution/fault_mechanism_consistency.json) | Ground-truth physical mechanism comparison and notes | **FINAL** |
| [`lstm_sensor_attributions.csv`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/sensor_attribution/lstm_sensor_attributions.csv) | Sequence-level LSTM reconstruction errors and residuals | **FINAL** |
| [`isolation_forest_sensor_attributions.csv`](file:///D:/Desktop/FInal%20year%20project/manumind-ai/reports/phase2/sensor_attribution/isolation_forest_sensor_attributions.csv) | Sequence-level IF raw signed deltas and normalized shares | **FINAL** |

---

## 4. Test Suite Verification

The complete backend test suite was re-executed to verify that no functional regressions were introduced:
- `pytest backend/tests/test_sensor_attribution.py`: **10 / 10 PASSED**.
- `pytest backend/tests/ -q`: **51 / 51 PASSED (37.96s)**.

---

## 5. Formal Step 4 Closure

Phase 2, Step 4 (Sensor-Level Anomaly Attribution) is formally **CLOSED**.

All mathematical formulations, normalization protocols, residual scales, and evaluation scopes are documented with scientific rigor and transparency. The system is fully cleared to proceed to **Phase 2, Step 5: Failure-Risk Prediction (Feature Engineering & 24h Lead-Time Target)** upon user authorization.

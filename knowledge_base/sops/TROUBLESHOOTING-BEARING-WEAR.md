---
document_id: "DOC-TRB-BEARING-001"
document_name: "Troubleshooting Guide: Spindle and Rotary Bearing Wear"
document_type: "TROUBLESHOOTING"
document_version: "1.0.0"
fault_category: "bearing_wear"
target_machine: "M104 (Demonstration Asset); General Mechanical Assets (M101, M103 Healthy Reference)"
source_type: "SYNTHETIC_DEMONSTRATION"
source_name: "ManuMind AI Phase 3 Synthetic Demonstration Suite"
source_record_id: null
is_synthetic: true
generation_method: "domain_expert_templated_synthesis"
created_at: "2026-11-09T15:00:00+05:30"
review_status: "ACADEMIC_DEMONSTRATION_ONLY"
operational_disclaimer: "SYNTHETIC DEMONSTRATION MATERIAL — NOT AN APPROVED OPERATIONAL PROCEDURE. DO NOT USE IN REAL FACTORY ENVIRONMENTS."
---

> **SAFETY NOTICE: SYNTHETIC DEMONSTRATION MATERIAL — NOT AN APPROVED OPERATIONAL PROCEDURE. DO NOT USE IN REAL FACTORY ENVIRONMENTS.**

# Troubleshooting Guide: Spindle and Rotary Bearing Wear

## 1. Scope & Applicable Assets
- **Document Identifier:** `DOC-TRB-BEARING-001`
- **Primary Fault Category:** `bearing_wear`
- **Applicable Asset Scope:** M104 (Demonstration Asset); General Mechanical Assets (M101, M103 Healthy Reference)
- **Document Status:** Synthetic Technical Demonstration Guide (Version 1.0.0)

---

## 2. Observable Symptoms & Plant Impact
- High-frequency acoustic whistling or metallic grinding noise.
- Elevated vibration RMS velocity in radial/axial planes.
- Increased spindle drive motor current required to sustain target RPM.
- Workpiece surface micro-cracks or circular waviness marks.

---

## 3. Indicative Sensor & Telemetry Signatures
When this failure mode initiates, telemetry indicators diverge from normal baseline distributions:
- **Vibration (mm/s):** Escalates significantly above baseline (> 5.0 mm/s; baseline ~2.2 mm/s).
- **Current (A):** Modest increase due to mechanical friction drag.
- **Temperature (°C):** Secondary elevation in proximity to bearing housing.
- **RPM:** Micro-speed fluctuations during high-load cutting passes.

---

## 4. Engineering Hypotheses vs. Confirmed Physical Causes
The AI anomaly detection subsystem identifies mathematical deviations, not mechanical proof. Consider the following candidate hypotheses:
1. Raceways micro-spalling or surface fatigue from cyclic contact stress.
2. Inadequate air-oil or grease lubrication starvation.
3. Particulate contamination inside bearing cavity.
4. Spindle belt misalignment or unbalanced tooling holder.

---

## 5. Phased Physical Inspection Workflow
Follow this disciplined physical inspection sequence before undertaking component disassembly:
1. **Tooling & Holder Check:** Remove cutting tool holder and run spindle uncoupled to rule out tool unbalance.
2. **Hand Rotation Feel:** De-energize spindle, engage LOTO `[SPEC_REQUIRED: Site-approved lockout/tagout procedure]`, and rotate spindle shaft by hand to detect roughness or notchiness.
3. **Taper Runout Measurement:** Mount dial indicator with magnetic base and measure radial runout at spindle nose taper (tolerance `[SPEC_REQUIRED: Maximum Permissible Spindle Runout]`).
4. **Vibration FFT Analysis:** Capture high-speed frequency spectrum to identify bearing defect frequencies (BPFO, BPFI, BSF, FTF).
5. **Borescopic Inspection:** Inspect bearing outer raceway with borescopic camera where optical ports permit.

---

## 6. Engineering Non-Causality Principle
> [!IMPORTANT]
> **Engineering Non-Causality Principle:** A statistical anomaly score or mathematical feature attribution (e.g., from Isolation Forest, LSTM Autoencoder, or Kernel SHAP) indicates a discrepancy between observed telemetry and a healthy baseline model. **Attribution does NOT prove physical mechanical causation.** Physical verification (e.g., acoustic emissions, micrometer measurements, fluid analysis, borescopic examination) is mandatory before assigning a definitive root cause or executing invasive component replacements.

---

## 7. Evidence Required Prior to Root Cause Assignment
> [!IMPORTANT]
> Physical verification of bearing raceway flaking, micrometer measurement of excessive radial play, or acoustic emission confirmation. A vibration attribution alone does NOT justify spindle disassembly.

---

## 8. Corrective Action Categories
- Routine: Inspect and flush air-oil lubrication supply lines; verify nozzle delivery.
- Corrective: Replace hybrid ceramic angular contact bearing set in cleanroom environment.
- Preventive: Recalibrate spindle dynamic balance and verify tool clamping drawbar force.

---

## 9. Dataset Consistency & Project Boundaries
CRITICAL PROJECT CONSISTENCY NOTICE: M104 is the primary bearing-wear demonstration asset in ManuMind AI. M103 is verified as healthy and must NOT be diagnosed with historical bearing-wear failure.

---

## 10. Missing Engineering Specifications & Placeholders
- `[SPEC_REQUIRED: Site-approved lockout/tagout procedure]`
- `[SPEC_REQUIRED: Certified OEM component clearance tolerance]`
- `[SPEC_REQUIRED: Maximum Permissible Vibration / Temperature Limit]`
- `[SPEC_REQUIRED: Certified torque specification]`

---

## 11. Document Provenance
| Revision | Date | Author / Role | Scope of Revision |
| :---: | :---: | :---: | :--- |
| `1.0.0` | 2026-11-09 | Synthetic Knowledge Engineer | Initial standardized troubleshooting guide. |

*End of Guide — DOC-TRB-BEARING-001*

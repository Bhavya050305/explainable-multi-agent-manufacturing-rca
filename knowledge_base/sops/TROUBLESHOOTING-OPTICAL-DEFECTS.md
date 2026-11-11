---
document_id: "DOC-TRB-OPT-001"
document_name: "Troubleshooting Guide: Workpiece Optical Defect Remediation"
document_type: "TROUBLESHOOTING"
document_version: "1.0.0"
fault_category: "optical_surface_defects"
target_machine: "General Machining Assets (M101-M110 Workpiece Inspection)"
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

# Troubleshooting Guide: Workpiece Optical Defect Remediation

## 1. Scope & Applicable Assets
- **Document Identifier:** `DOC-TRB-OPT-001`
- **Primary Fault Category:** `optical_surface_defects`
- **Applicable Asset Scope:** General Machining Assets (M101-M110 Workpiece Inspection)
- **Document Status:** Synthetic Technical Demonstration Guide (Version 1.0.0)

---

## 2. Observable Symptoms & Plant Impact
- Vision inspection camera detects anomalous workpiece surface patterns.
- Surface Micro-Cracks (`surface_crack`): Longitudinal or transverse fissures.
- Surface Spalling (`spalling`): Flaking, cratering, or localized material pitting.
- Surface Dents (`dent`): Mechanical impression, gouge, or tool impact crater.
- Normal Workpiece (`normal_surface`): Clean ground/turned surface meeting roughness specs.

---

## 3. Indicative Sensor & Telemetry Signatures
When this failure mode initiates, telemetry indicators diverge from normal baseline distributions:
- Vision Model Softmax Score: Uncalibrated probability distribution across 4 classes.
- Correlation with Sensor Telemetry: Machine vibration or current spikes during cutting pass often precede workpiece damage.

---

## 4. Engineering Hypotheses vs. Confirmed Physical Causes
The AI anomaly detection subsystem identifies mathematical deviations, not mechanical proof. Consider the following candidate hypotheses:
1. `surface_crack`: Thermal cracking from inadequate cutting fluid delivery or excessive feed rate inducing thermal shock.
2. `spalling`: Extreme contact shear stress, subsurface metallurgical defect, or severely worn tooling insert.
3. `dent`: Foreign object debris in chuck jaws, robotic gripper dropping workpiece, or chip entrapment.
4. `normal_surface`: Baseline workpiece meeting dimensional and visual inspection tolerances.

---

## 5. Phased Physical Inspection Workflow
Follow this disciplined physical inspection sequence before undertaking component disassembly:
1. **Image Verification:** Inspect raw workpiece BMP image crop to confirm lighting consistency and camera focus.
2. **Physical Part Examination:** Clean workpiece surface with solvent and inspect under 10x optical stereomicroscope.
3. **Non-Destructive Testing (NDT):** For suspected cracks, apply dye-penetrant inspection (PT) or magnetic particle testing (MT) to confirm fissure depth.
4. **Tooling Insert Inspection:** Inspect cutting insert edge with toolmaker's microscope for flank wear, chipping, or built-up edge (BUE).
5. **Coolant Nozzle Aim:** Verify flood coolant nozzles are targeted directly at tool-workpiece shear interface.

---

## 6. Engineering Non-Causality Principle
> [!IMPORTANT]
> **Engineering Non-Causality Principle:** A statistical anomaly score or mathematical feature attribution (e.g., from Isolation Forest, LSTM Autoencoder, or Kernel SHAP) indicates a discrepancy between observed telemetry and a healthy baseline model. **Attribution does NOT prove physical mechanical causation.** Physical verification (e.g., acoustic emissions, micrometer measurements, fluid analysis, borescopic examination) is mandatory before assigning a definitive root cause or executing invasive component replacements.

---

## 7. Evidence Required Prior to Root Cause Assignment
> [!IMPORTANT]
> Microscopic or dye-penetrant confirmation of physical surface defect on actual workpiece. The ResNet Softmax output is an uncalibrated classification on synthetic crops and does not replace certified quality inspection.

---

## 8. Corrective Action Categories
- Routine: Index or replace worn cutting tool insert; clean fixture clamping surfaces.
- Corrective: Quarantine affected production batch number; adjust feed rate and coolant flow.
- Preventive: Implement tool life management cycle counting based on machining cut minutes.

---

## 9. Dataset Consistency & Project Boundaries
Optical defect classifications in ManuMind AI are based on the 600-image dataset (150 images per class). Defect classification provides visual evidence to complement telemetry anomaly detection.

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

*End of Guide — DOC-TRB-OPT-001*

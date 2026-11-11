---
document_id: "DOC-TRB-PRESS-001"
document_name: "Troubleshooting Guide: Pneumatic and Compressor Line Pressure Drop"
document_type: "TROUBLESHOOTING"
document_version: "1.0.0"
fault_category: "pressure_drop"
target_machine: "M107 (Demonstration Asset); General Pneumatic Utilities"
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

# Troubleshooting Guide: Pneumatic and Compressor Line Pressure Drop

## 1. Scope & Applicable Assets
- **Document Identifier:** `DOC-TRB-PRESS-001`
- **Primary Fault Category:** `pressure_drop`
- **Applicable Asset Scope:** M107 (Demonstration Asset); General Pneumatic Utilities
- **Document Status:** Synthetic Technical Demonstration Guide (Version 1.0.0)

---

## 2. Observable Symptoms & Plant Impact
- Inability to maintain main supply air pressure during peak factory demand.
- Actuators stalling or cycle times extending across connected production cells.
- Compressor drive motor operating at maximum RPM continuously without unloading.
- Excessive condensate accumulation in air dryers and header drains.

---

## 3. Indicative Sensor & Telemetry Signatures
When this failure mode initiates, telemetry indicators diverge from normal baseline distributions:
- **Pressure (bar):** Primary indicator; drops steadily below acceptable operating threshold (< 5.0 bar; baseline 6.2-7.0 bar).
- **Current (A):** Operates at near-full-load current continuously.
- **RPM:** Main motor maintains elevated RPM trying to satisfy demand.
- **Vibration (mm/s):** Transient surges during aerodynamic guide vane hunting.

---

## 4. Engineering Hypotheses vs. Confirmed Physical Causes
The AI anomaly detection subsystem identifies mathematical deviations, not mechanical proof. Consider the following candidate hypotheses:
1. Severe compressed air distribution header leak or ruptured flexible hose.
2. Variable Inlet Guide Vane (IGV) actuator linkage binding or position sensor calibration loss.
3. Intake suction air filter element completely clogged with ambient airborne particulate.
4. Minimum pressure check valve or condensate drain valve stuck wide open.

---

## 5. Phased Physical Inspection Workflow
Follow this disciplined physical inspection sequence before undertaking component disassembly:
1. **Acoustic Ultrasound Leak Survey:** Scan main distribution header and drop lines using directional ultrasonic leak detector.
2. **Suction Filter Differential Pressure:** Check manometer reading across intake air filter housing.
3. **IGV Linkage Inspection:** De-energize compressor, perform LOTO `[SPEC_REQUIRED: Site-approved lockout/tagout procedure]`, and manually inspect guide vane pivot pins for mechanical binding.
4. **Drain Valve Verification:** Check automated timer moisture drains to confirm they close tightly after purging.
5. **Intercooler Pressure Check:** Verify stage 1 to stage 2 intercooler pressure to determine if pressure drop is internal to compressor stages.

---

## 6. Engineering Non-Causality Principle
> [!IMPORTANT]
> **Engineering Non-Causality Principle:** A statistical anomaly score or mathematical feature attribution (e.g., from Isolation Forest, LSTM Autoencoder, or Kernel SHAP) indicates a discrepancy between observed telemetry and a healthy baseline model. **Attribution does NOT prove physical mechanical causation.** Physical verification (e.g., acoustic emissions, micrometer measurements, fluid analysis, borescopic examination) is mandatory before assigning a definitive root cause or executing invasive component replacements.

---

## 7. Evidence Required Prior to Root Cause Assignment
> [!IMPORTANT]
> Demonstrated acoustic leak signature, physical binding in IGV mechanical linkage, or verified manometer differential pressure exceeding maximum filter allowable loss.

---

## 8. Corrective Action Categories
- Routine: Replace clogged primary air intake filter panel cartridges.
- Corrective: Re-align and lubricate IGV actuator linkages; recalibrate 4-20 mA position feedback loop.
- Preventive: Repair header pipe flanged connections and replace damaged push-to-connect air fittings.

---

## 9. Dataset Consistency & Project Boundaries
M107 is the designated pressure-drop demonstration asset in project datasets. Pressure attribution highlights pneumatic flow restrictions and control linkage degradation.

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

*End of Guide — DOC-TRB-PRESS-001*

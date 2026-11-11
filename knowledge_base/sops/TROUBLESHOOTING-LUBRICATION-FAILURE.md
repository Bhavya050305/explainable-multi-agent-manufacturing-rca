---
document_id: "DOC-TRB-LUB-001"
document_name: "Troubleshooting Guide: Gearbox and Powertrain Lubrication Failure"
document_type: "TROUBLESHOOTING"
document_version: "1.0.0"
fault_category: "lubrication_failure"
target_machine: "M109 (Demonstration Asset); General Powertrain Assets"
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

# Troubleshooting Guide: Gearbox and Powertrain Lubrication Failure

## 1. Scope & Applicable Assets
- **Document Identifier:** `DOC-TRB-LUB-001`
- **Primary Fault Category:** `lubrication_failure`
- **Applicable Asset Scope:** M109 (Demonstration Asset); General Powertrain Assets
- **Document Status:** Synthetic Technical Demonstration Guide (Version 1.0.0)

---

## 2. Observable Symptoms & Plant Impact
- Significant elevation in gearbox casing temperature across bearing housings.
- Chattering, gear mesh growl, or cyclic tooth impact acoustic emissions.
- Loss of forced circulating oil pressure on primary supply manifold gauge.
- Heavy metal particle accumulation on magnetic oil sump drain plug.

---

## 3. Indicative Sensor & Telemetry Signatures
When this failure mode initiates, telemetry indicators diverge from normal baseline distributions:
- **Pressure (bar):** Severe drop in circulating lubrication supply pressure.
- **Temperature (°C):** Escalates sharply due to metal-to-metal boundary friction.
- **Vibration (mm/s):** Broad-spectrum vibration escalation with gear mesh harmonics.
- **Current (A):** Increased motor current reflecting mechanical drag.

---

## 4. Engineering Hypotheses vs. Confirmed Physical Causes
The AI anomaly detection subsystem identifies mathematical deviations, not mechanical proof. Consider the following candidate hypotheses:
1. Auxiliary lubrication pump motor electrical failure or pump coupling shear.
2. Suction oil strainer blocked by sludge, oxidation varnish, or wear debris.
3. Lubrication oil foaming due to air entrainment or wrong lubricant grade.
4. Oil delivery nozzle orifice clogged, starving individual helical gear mesh points.

---

## 5. Phased Physical Inspection Workflow
Follow this disciplined physical inspection sequence before undertaking component disassembly:
1. **Lube Pump Visual Inspection:** Verify circulation pump electric motor is running and rotation direction is correct.
2. **Suction Strainer Inspection:** Isolate lube circuit, pull suction basket strainer, and inspect for metallic debris.
3. **Oil Quality & Level Check:** Inspect oil level through casing sight glass; check for milky emulsification (water) or black burnt discoloration.
4. **Delivery Nozzle Flow Check:** Open inspection hatch and visually confirm oil spray curtain over gear mesh.
5. **Borescopic Gear Tooth Scan:** Inspect gear teeth for adhesive wear, scuffing, micro-pitting, or discoloration from frictional heat.

---

## 6. Engineering Non-Causality Principle
> [!IMPORTANT]
> **Engineering Non-Causality Principle:** A statistical anomaly score or mathematical feature attribution (e.g., from Isolation Forest, LSTM Autoencoder, or Kernel SHAP) indicates a discrepancy between observed telemetry and a healthy baseline model. **Attribution does NOT prove physical mechanical causation.** Physical verification (e.g., acoustic emissions, micrometer measurements, fluid analysis, borescopic examination) is mandatory before assigning a definitive root cause or executing invasive component replacements.

---

## 7. Evidence Required Prior to Root Cause Assignment
> [!IMPORTANT]
> Physical confirmation of zero oil pressure at manifold, clogged suction screen with metallic debris, or borescopic confirmation of gear tooth scuffing. Model anomaly score indicates telemetry divergence only.

---

## 8. Corrective Action Categories
- Routine: Clean suction basket strainer and replace spin-on 10-micron oil filter elements.
- Corrective: Replace failed lubrication pump unit; flush gearbox sump and refill with fresh ISO VG gear oil.
- Preventive: Implement scheduled oil sampling for wear metals (Fe, Cu) and water contamination.

---

## 9. Dataset Consistency & Project Boundaries
M109 is the designated lubrication-failure demonstration asset in project datasets. Compound telemetry excursions reflect loss of hydrodynamic lubricating film.

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

*End of Guide — DOC-TRB-LUB-001*

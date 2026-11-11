---
document_id: "DOC-TRB-HEAT-001"
document_name: "Troubleshooting Guide: Hydraulic and Mechanical Overheating"
document_type: "TROUBLESHOOTING"
document_version: "1.0.0"
fault_category: "overheating"
target_machine: "M102 (Demonstration Asset); General Thermal Subsystems"
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

# Troubleshooting Guide: Hydraulic and Mechanical Overheating

## 1. Scope & Applicable Assets
- **Document Identifier:** `DOC-TRB-HEAT-001`
- **Primary Fault Category:** `overheating`
- **Applicable Asset Scope:** M102 (Demonstration Asset); General Thermal Subsystems
- **Document Status:** Synthetic Technical Demonstration Guide (Version 1.0.0)

---

## 2. Observable Symptoms & Plant Impact
- Rapid temperature rise in hydraulic fluid reservoir or machine casing.
- Burnt hydraulic oil odor or fluid darkening.
- Sluggish cylinder motion and reduced stamping/clamping force.
- Accelerated deterioration of elastomer seals and O-rings.

---

## 3. Indicative Sensor & Telemetry Signatures
When this failure mode initiates, telemetry indicators diverge from normal baseline distributions:
- **Temperature (°C):** Primary diagnostic indicator; rises continuously above normal operating ceiling (> 65°C; baseline: 45-55°C).
- **Pressure (bar):** Fluid pressure drop or erratic regulation due to thinned oil viscosity.
- **Current (A):** Increased motor current under severe thermal binding.

---

## 4. Engineering Hypotheses vs. Confirmed Physical Causes
The AI anomaly detection subsystem identifies mathematical deviations, not mechanical proof. Consider the following candidate hypotheses:
1. Fouling or sediment buildup in shell-and-tube heat exchanger water passages.
2. Insufficient cooling water flow rate or elevated cooling tower water supply temperature.
3. Main proportional relief valve stuck in bypass or internal valve leakage creating friction heat.
4. Hydraulic fluid viscosity breakdown or severe oxidation (varnish accumulation).

---

## 5. Phased Physical Inspection Workflow
Follow this disciplined physical inspection sequence before undertaking component disassembly:
1. **Cooling Water Flow Verification:** Check cooling water supply pressure and flow meter at heat exchanger inlet.
2. **Heat Exchanger Delta-T:** Measure temperature difference between oil inlet/outlet and water inlet/outlet.
3. **Relief Valve Thermal Scan:** Use calibrated thermal imaging camera to detect localized valve block hot spots indicating internal leakage.
4. **Fluid Quality Testing:** Sample hydraulic fluid from reservoir midpoint; inspect color and perform patch test for varnish deposits.
5. **Reservoir Suction Strainer:** Inspect pump inlet suction strainer for blockage restricting circulation.

---

## 6. Engineering Non-Causality Principle
> [!IMPORTANT]
> **Engineering Non-Causality Principle:** A statistical anomaly score or mathematical feature attribution (e.g., from Isolation Forest, LSTM Autoencoder, or Kernel SHAP) indicates a discrepancy between observed telemetry and a healthy baseline model. **Attribution does NOT prove physical mechanical causation.** Physical verification (e.g., acoustic emissions, micrometer measurements, fluid analysis, borescopic examination) is mandatory before assigning a definitive root cause or executing invasive component replacements.

---

## 7. Evidence Required Prior to Root Cause Assignment
> [!IMPORTANT]
> Confirmed cooling flow restriction below specification, thermal camera verification of valve blow-by, or laboratory oil analysis proving fluid oxidation index exceeds limits.

---

## 8. Corrective Action Categories
- Routine: Descale water-side heat exchanger tubes with biodegradable descaling agent.
- Corrective: Rebuild or replace leaking proportional relief valve; restore cooling water flow rate.
- Preventive: Perform electrostatic oil purification and replenish antioxidant additive package.

---

## 9. Dataset Consistency & Project Boundaries
M102 is the designated overheating demonstration asset in project datasets. Thermal telemetry escalation reflects cooling circuit inefficiency or bypass throttling.

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

*End of Guide — DOC-TRB-HEAT-001*

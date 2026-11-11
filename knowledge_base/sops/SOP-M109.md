---
document_id: "DOC-SOP-M109-001"
document_name: "Standard Operating Procedure: Heavy Industrial Gearbox 09 (M109)"
document_type: "SOP"
document_version: "1.0.0"
machine_id: "M109"
machine_type: "Gearbox"
criticality: 5
production_impact: 4
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

# Standard Operating Procedure: Heavy Industrial Gearbox 09 (`M109`)

## 1. Document Control & Metadata
- **Document Identifier:** `DOC-SOP-M109-001`
- **Target Machine:** `M109` — Heavy Industrial Gearbox 09 (Gearbox)
- **Asset Criticality Level:** Level 5 / 5 (Production Impact: 4 / 5)
- **Demonstration Role:** **Lubrication Failure Demonstration Asset**
- **Primary Subsystem Focus:** Multi-Stage Helical Reduction Gear Train & Forced Pressure Lubrication
- **Effective Date:** November 9, 2026 (Version 1.0.0)

---

## 2. Asset Specifications & Telemetry Overview
### 2.1 Asset Functional Overview
Heavy-duty helical parallel-shaft speed reduction gearbox coupling a 250 kW drive motor to primary plant heavy manufacturing equipment.

### 2.2 Continuous Sensor Monitoring Inventory
The asset is instrumented with 5 continuous industrial sensors sampled at regular intervals:
1. **Vibration Transducer (RMS velocity, mm/s):** Mounted on main bearing housing/drive casing.
2. **Temperature Thermocouple (°C):** Measures bulk fluid/casing surface operating temperature.
3. **Pressure Transmitter (bar):** Measures process hydraulic/pneumatic supply pressure.
4. **Current Transducer (Amperes):** Measures main drive motor 3-phase current load.
5. **Rotational Speed Tachometer (RPM):** Measures primary spindle/output shaft speed.

**Nominal Telemetry Envelope:**
Compound vibration and temperature escalation. Demonstrates progressive lubrication starvation (Lube pressure decay, elevated gear mesh temperature).

---

## 3. Routine Pre-Operational & Inspection Checklist
Prior to authorized production operation, technicians must complete the following checks:
- Inspect forced lubrication electric circulating pump discharge pressure gauge.
- Check dual in-line oil filter differential pressure pop-up indicators.
- Verify magnetic drain plug for excessive ferrous particulate accumulation.
- Monitor gear casing surface temperatures across high-speed input and low-speed output bearings.
- Inspect input and output shaft labyrinth oil seals for leakage.

> [!NOTE]
> All inspections must be logged in the digital maintenance log. If any observed parameter exceeds nominal operational limits, initiate the standard escalation workflow.

---

## 4. Operational Guidelines & Baseline Signatures
- **Startup Protocol:** Energize primary auxiliary pumps and wait until system achieves nominal standby pressure `[SPEC_REQUIRED: Minimum Operating Standby Pressure]`.
- **Steady-State Envelope:** Maintain operating speeds within nominal range `[SPEC_REQUIRED: OEM Permissible Speed Band]`.
- **Shutdown Protocol:** Complete active processing cycle, park motion axes in designated home position, and initiate controlled spin-down.

---

## 5. Maintenance Procedures & Inspection Protocols
### 5.1 Preventive Maintenance Cadence
- Daily: Record lube oil circulation pressure and oil sump sight-glass temperature.
- Weekly: Clean motor-driven oil pump suction basket strainer.
- Monthly: Send gearbox oil sample for ISO 4406 particle count and Karl Fischer water content.
- Corrective (Lubrication Failure Anomaly): Shut down gearbox immediately; replace clogged oil filter cartridges; flush contaminated oil; inspect helical gear teeth for scuffing and micro-pitting.

### 5.2 Corrective Intervention Protocols
When abnormal telemetry or physical symptoms arise:
1. **Safety Isolation:** Implement site Lockout/Tagout procedures `[SPEC_REQUIRED: Site-approved lockout/tagout procedure]`.
2. **De-energization:** Verify zero kinetic, electrical, and pneumatic/hydraulic energy state before removing protective guards.
3. **Targeted Inspection:** Follow the relevant component troubleshooting guide referenced in Section 6.

---

## 6. Failure Mode Differentiation & Non-Causality Principle
### 6.1 Demonstration Guidance for Machine M109
In Phase 1/Phase 2 datasets, M109 demonstrates severe lubrication starvation leading to compound vibration and thermal degradation. Sequence reconstruction error spikes due to friction. Always inspect oil pump circulation and strainer clogging before suspecting catastrophic gear tooth shear.

### 6.2 Non-Causality Principle
> [!IMPORTANT]
> **Engineering Non-Causality Principle:** A statistical anomaly score or mathematical feature attribution (e.g., from Isolation Forest, LSTM Autoencoder, or Kernel SHAP) indicates a discrepancy between observed telemetry and a healthy baseline model. **Attribution does NOT prove physical mechanical causation.** Physical verification (e.g., acoustic emissions, micrometer measurements, fluid analysis, borescopic examination) is mandatory before assigning a definitive root cause or executing invasive component replacements.

---

## 7. Escalation Criteria & Human-in-the-Loop Governance
Automated AI recommendations generated by ManuMind AI are purely advisory. Formal escalation to a certified mechanical maintenance engineer is required under any of the following conditions:
1. Multi-modal consensus indicates elevated anomaly confidence across independent sensor and visual inspection layers.
2. Anomaly persistence exceeds 3 consecutive sampling windows.
3. Rapid thermal escalation $> 5°C / 	ext<built-in function min>$ or severe acoustic rattling is detected.
4. **Mandatory Sign-off:** No work order involving major sub-assembly replacement (such as spindle bearings, hydraulic cylinders, or gear sets) may be executed without explicit human supervisor authorization.

---

## 8. Missing Engineering Specifications & Placeholders
The following authoritative engineering values are intentionally withheld in this synthetic demonstration SOP:
- `[SPEC_REQUIRED: Certified OEM electrical isolation procedure]`
- `[SPEC_REQUIRED: Approved hydraulic pressure limit]`
- `[SPEC_REQUIRED: Site-approved lockout/tagout procedure]`
- `[SPEC_REQUIRED: OEM operating temperature limit]`
- `[SPEC_REQUIRED: Certified torque specification]`
- `[SPEC_REQUIRED: OEM Permissible Speed Band]`

---

## 9. Document Revision History & Provenance
| Revision | Date | Author / Role | Scope of Revision |
| :---: | :---: | :---: | :--- |
| `1.0.0` | 2026-11-09 | Synthetic Knowledge Engineer | Initial standardized synthetic demonstration SOP creation. |

*End of Procedure — DOC-SOP-M109-001*

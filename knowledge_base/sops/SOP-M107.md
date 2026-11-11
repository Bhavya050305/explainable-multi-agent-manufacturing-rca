---
document_id: "DOC-SOP-M107-001"
document_name: "Standard Operating Procedure: Centrifugal Compressor 07 (M107)"
document_type: "SOP"
document_version: "1.0.0"
machine_id: "M107"
machine_type: "Compressor"
criticality: 4
production_impact: 5
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

# Standard Operating Procedure: Centrifugal Compressor 07 (`M107`)

## 1. Document Control & Metadata
- **Document Identifier:** `DOC-SOP-M107-001`
- **Target Machine:** `M107` — Centrifugal Compressor 07 (Compressor)
- **Asset Criticality Level:** Level 4 / 5 (Production Impact: 5 / 5)
- **Demonstration Role:** **Pressure Drop Demonstration Asset**
- **Primary Subsystem Focus:** Two-Stage Centrifugal Impeller & Variable Inlet Guide Vanes (IGV)
- **Effective Date:** November 9, 2026 (Version 1.0.0)

---

## 2. Asset Specifications & Telemetry Overview
### 2.1 Asset Functional Overview
Central plant utility compressor delivering continuous clean, oil-free compressed air to pneumatic actuators across the manufacturing facility.

### 2.2 Continuous Sensor Monitoring Inventory
The asset is instrumented with 5 continuous industrial sensors sampled at regular intervals:
1. **Vibration Transducer (RMS velocity, mm/s):** Mounted on main bearing housing/drive casing.
2. **Temperature Thermocouple (°C):** Measures bulk fluid/casing surface operating temperature.
3. **Pressure Transmitter (bar):** Measures process hydraulic/pneumatic supply pressure.
4. **Current Transducer (Amperes):** Measures main drive motor 3-phase current load.
5. **Rotational Speed Tachometer (RPM):** Measures primary spindle/output shaft speed.

**Nominal Telemetry Envelope:**
High pressure sensitivity. Demonstrates progressive pneumatic line pressure loss (Pressure drops < 5.0 bar; baseline: 6.2-7.0 bar).

---

## 3. Routine Pre-Operational & Inspection Checklist
Prior to authorized production operation, technicians must complete the following checks:
- Monitor primary discharge compressed air line pressure gauge.
- Inspect inlet air filter differential pressure manometer.
- Check variable inlet guide vane (IGV) actuator linkage and position feedback transducer.
- Verify intercooler condensate moisture auto-drain valve discharging cycle.
- Inspect main compressor drive shaft flexible coupling and guard.

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
- Daily: Record discharge air pressure, interstage pressure, and cooling water delta-T.
- Weekly: Purge air filter pre-cleaner bins and inspect acoustic attenuation panels.
- Monthly: Calibrate pneumatic pressure transmitters against laboratory deadweight tester.
- Corrective (Pressure Drop Anomaly): Perform ultrasonic compressed air leak survey; inspect IGV linkage for mechanical binding; replace clogged intake filter elements.

### 5.2 Corrective Intervention Protocols
When abnormal telemetry or physical symptoms arise:
1. **Safety Isolation:** Implement site Lockout/Tagout procedures `[SPEC_REQUIRED: Site-approved lockout/tagout procedure]`.
2. **De-energization:** Verify zero kinetic, electrical, and pneumatic/hydraulic energy state before removing protective guards.
3. **Targeted Inspection:** Follow the relevant component troubleshooting guide referenced in Section 6.

---

## 6. Failure Mode Differentiation & Non-Causality Principle
### 6.1 Demonstration Guidance for Machine M107
In Phase 1/Phase 2 datasets, M107 represents the ground-truth pressure drop degradation scenario. Pressure drop attribution corresponds to intake guide vane hunting, clogged suction filters, or distribution line seal rupture. Verify pneumatic line leakage before replacing expensive impeller stages.

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

*End of Procedure — DOC-SOP-M107-001*

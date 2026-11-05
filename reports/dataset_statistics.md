# ManuMind AI — Expanded Dataset Statistics & Quality Audit

## 1. Executive Summary

- **Total Sensor Readings:** 40,000 (across 10 machines)
- **Total Sequence Windows:** 3,980 (window size: 30 steps, stride: 10)
- **Total Maintenance Records:** 400 (spanning 24 months)
- **Total Defect Images:** 600 (4 balanced classes, 128x128 BMP)
- **Data Leakage Check:** PASSED (Zero Temporal Overlap)
- **Data Integrity:** 0 missing values, 0 duplicate records across all tables

## 2. Sensor Telemetry Distribution

| Machine ID | Asset Name | Criticality | Impact | Fault Mode | Reading Count | Normal | Abnormal |
|---|---|---|---|---|---|---|---|
| M101 | Machine M101 | 3-5 | 2-5 | `normal` | 4,000 | 4,000 | 0 |
| M102 | Machine M102 | 3-5 | 2-5 | `overheating` | 4,000 | 2,600 | 1,400 |
| M103 | Machine M103 | 3-5 | 2-5 | `normal` | 4,000 | 4,000 | 0 |
| M104 | Machine M104 | 3-5 | 2-5 | `bearing_wear` | 4,000 | 2,600 | 1,400 |
| M105 | Machine M105 | 3-5 | 2-5 | `normal` | 4,000 | 4,000 | 0 |
| M106 | Machine M106 | 3-5 | 2-5 | `normal` | 4,000 | 4,000 | 0 |
| M107 | Machine M107 | 3-5 | 2-5 | `pressure_drop` | 4,000 | 2,600 | 1,400 |
| M108 | Machine M108 | 3-5 | 2-5 | `normal` | 4,000 | 4,000 | 0 |
| M109 | Machine M109 | 3-5 | 2-5 | `lubrication_failure` | 4,000 | 2,600 | 1,400 |
| M110 | Machine M110 | 3-5 | 2-5 | `normal` | 4,000 | 4,000 | 0 |

### Fault Categories Breakdown

| Fault Category | Reading Count | Percentage |
|---|---|---|
| `normal` | 34,400 | 86.00% |
| `overheating` | 1,400 | 3.50% |
| `bearing_wear` | 1,400 | 3.50% |
| `pressure_drop` | 1,400 | 3.50% |
| `lubrication_failure` | 1,400 | 3.50% |

### Chronological Partitions

- **Train (70%):** 28,000 readings
- **Validation (15%):** 6,000 readings
- **Test (15%):** 6,000 readings

## 3. Maintenance Records Distribution

| Machine ID | Work Order Count |
|---|---|
| M101 | 35 |
| M102 | 42 |
| M103 | 36 |
| M104 | 35 |
| M105 | 46 |
| M106 | 39 |
| M107 | 28 |
| M108 | 48 |
| M109 | 49 |
| M110 | 42 |

## 4. Defect Image Dataset Distribution

| Defect Class | Train (70%) | Val (15%) | Test (15%) | Total |
|---|---|---|---|---|
| `surface_crack` | 105 | 22 | 23 | 150 |
| `spalling` | 105 | 22 | 23 | 150 |
| `dent` | 105 | 22 | 23 | 150 |
| `normal_surface` | 105 | 22 | 23 | 150 |

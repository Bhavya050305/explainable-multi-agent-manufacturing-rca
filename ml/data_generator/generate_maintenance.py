"""
ManuMind AI - Enhanced Maintenance History Generator
Generates realistic industrial work orders (~300–500 records) across M101-M110 spanning the past 2 years.
Features targeted historical precedents for M104 (spindle bearing degradation, vibration escalation,
SKF bearing replacement, Klüber Isoflex greasing) to ground Root Cause RAG retrieval.
"""

import argparse
import json
import os
import random
from datetime import datetime, timedelta
from typing import List, Dict
import pandas as pd

# Rich domain templates per machine family
ISSUE_TEMPLATES = [
    # Bearing & Spindle (Targeted for CNCs: M103, M104, M101)
    {
        "types": ["CNC Milling", "CNC Lathe"],
        "issues": [
            "Elevated radial vibration detected during high-speed finishing cycle (spindle front bearing)",
            "Audible high-pitch chatter and harmonic vibration around 1800 RPM in main spindle",
            "Spindle bearing thermal run-up during continuous 4-axis roughing operation",
            "Excessive axial play (0.04mm) measured on toolholder interface after vibration alarm",
            "Lubrication starvation in inner bearing race caused micro-pitting on roller balls",
            "Spindle drawbar retention force dropped below safety limit (14.2 kN measured)",
            "Acoustic emission sensor registered high-frequency friction spikes on spindle housing",
            "Collet clamping mechanism sticking due to fine swarf ingress in drawbar sleeve",
            "Spindle motor drive belt micro-cracking and tension slackening after 2000 hours"
        ],
        "actions": [
            "Replaced spindle angular contact bearing set (SKF 7014 CD/P4A). Packed with Klüber Isoflex NBU 15 grease.",
            "Flushed spindle lubrication cartridge, purged degraded oil, installed new micro-filter and balanced shaft.",
            "Replaced front and rear spindle support bearings, performed dynamic balancing to ISO G1.0 tolerance.",
            "Dismantled spindle cartridge, verified run-out, replaced damaged needle bearings and retorqued preload nut.",
            "Emergency shutdown inspection: replaced worn bearing cage and recalibrated acoustic vibration sensor.",
            "Overhauled drawbar disc spring stack (Belleville washers replaced) and restored clamp force to 18 kN.",
            "Ultrasonically cleaned spindle taper, reground drive dogs, and measured runout (< 0.003 mm).",
            "Replaced pneumatic cylinder seal on automatic tool changer gripper and verified arm swing timing.",
            "Installed new high-durability Optibelt poly-V spindle drive belt and adjusted tension to 520 N."
        ],
        "outcomes": ["Resolved", "Resolved", "Resolved", "Monitoring", "Resolved", "Resolved", "Resolved", "Resolved", "Resolved"]
    },
    # Hydraulic & Press (M102)
    {
        "types": ["Hydraulic Press"],
        "issues": [
            "Main hydraulic manifold pressure fluctuation exceeding +/- 12 bar tolerance",
            "Proportional servo valve sticking due to particulate contamination in oil circuit",
            "Hydraulic fluid operating temperature exceeded 68°C under continuous stamping",
            "Piston rod seal leakage observed on primary cylinder gland packing",
            "Accumulator bladder nitrogen pre-charge dropped below 45 bar threshold",
            "Severe hydraulic shock hammer noise upon press decompression cycle",
            "Proportional pressure relief valve solenoid coil open circuit error",
            "Oil analysis indicated high oxidation and varnish buildup (MPC index > 35)"
        ],
        "actions": [
            "Replaced proportional directional control valve and flushed reservoir to ISO 4406 clean class 16/14/11.",
            "Replaced cylinder polyurethane U-cup seal and wear rings; cleaned chrome plating surface.",
            "Descaled water-cooled heat exchanger tube bundle, restored cooling flow rate to 45 L/min.",
            "Recharged hydraulic accumulator with dry nitrogen to 60 bar; replaced gas charging valve core.",
            "Replaced offline fine filter elements (3 micron absolute) and replenished Shell Tellus S2 MX 46.",
            "Adjusted decompression ramp timing on proportional valve controller to dampen hydraulic shock.",
            "Replaced Rexroth 24V DC solenoid valve coil assembly and validated continuity.",
            "Performed electrostatic oil purification treatment and added antioxidant additive package."
        ],
        "outcomes": ["Resolved", "Resolved", "Resolved", "Monitoring", "Resolved", "Resolved", "Resolved", "Resolved"]
    },
    # Compressor (M107)
    {
        "types": ["Compressor"],
        "issues": [
            "Interstage discharge pressure drop with surging oscillations on 2nd stage impeller",
            "Oil foaming and carryover into pneumatic main header",
            "Acoustic inspection identified dry gas seal buffer pressure leakage",
            "Intake air guide vane actuator hunting and losing position feedback",
            "High motor winding temperature due to clogged ventilation louvers",
            "Intercooler moisture separator automatic drain trap valve stuck open",
            "Check valve chatter at compressor discharge nozzle during load modulation"
        ],
        "actions": [
            "Replaced carbon face dry gas seal and inspected labyrinth sleeves for scoring.",
            "Overhauled inlet guide vane pneumatic positioner; calibrated LVDT stroke feedback.",
            "Replaced oil-air coalescing separator element and scavenging check valve.",
            "Cleaned drive motor cooling ducts with dry ice blasting and verified RTD resistance readings.",
            "Replaced suction air intake HEPA cartridge filters and verified delta-P manometer.",
            "Disassembled and rebuilt electronic zero-loss condensate drain valve assembly.",
            "Replaced wafer dual-plate discharge check valve and replaced return spring."
        ],
        "outcomes": ["Resolved", "Resolved", "Monitoring", "Resolved", "Resolved", "Resolved", "Resolved"]
    },
    # Gearbox (M109)
    {
        "types": ["Gearbox"],
        "issues": [
            "High iron particulate count in oil lab analysis (Fe > 140 ppm) from intermediate pinion",
            "Low oil pressure trip on forced circulation lubrication circuit",
            "Gear teeth flank micro-pitting and scuffing detected during borescopic inspection",
            "Output shaft labyrinth oil seal weeping onto mounting plinth",
            "Severe torsional vibration during heavy torque reversal cycles",
            "Magnetic drain plug accumulated heavy metallic sludge within 500 operating hours",
            "Lube oil circulation pump cavitation noise under cold morning startup"
        ],
        "actions": [
            "Drained gearbox sump, flushed wear debris, refilled with Mobilgear 600 XP 220 synthetic oil.",
            "Replaced positive displacement lube oil pump and suction strainer basket.",
            "Replaced mechanical face seal and ground shaft sleeve sealing surface.",
            "Replaced intermediate helical gear set and reset backlash to 0.18 mm.",
            "Realigned motor-to-gearbox flexible coupling using laser alignment kit (offset < 0.03 mm).",
            "Installed continuous magnetic filtration bypass loop on return lube line.",
            "Fitted tank immersion heater setpoint at 35°C to avoid cold viscosity suction cavitation."
        ],
        "outcomes": ["Resolved", "Resolved", "Monitoring", "Resolved", "Resolved", "Resolved", "Resolved"]
    },
    # Robotics & Automation (M105, M106, M108, M110)
    {
        "types": ["Robotic Welder", "Conveyor", "Injection Molding", "Packaging"],
        "issues": [
            "Periodic encoder communication loss on axis 3 servo amplifier",
            "Wear on polyurethane drive timing belt with tooth shearing",
            "Nozzle heater band thermal runaway due to thermocouple loose connection",
            "Pneumatic gripper cylinder stroke sensor magnet detached",
            "Conveyor roller bearing seizure causing motor overload trip",
            "Welding torch cable bundle insulation chaffing on robot wrist casting",
            "Mold clamping platen tie-bar elongation mismatch detected during tonnage calibration",
            "Packaging carton feeder suction cup vacuum loss due to cracked silicone cup"
        ],
        "actions": [
            "Replaced flexible drag-chain harness cable assembly and re-zeroed absolute encoder.",
            "Fitted new steel-reinforced AT10 timing belt and adjusted tension to 450 N with sonic meter.",
            "Replaced ceramic band heater and installed new Type K ungrounded thermocouple probe.",
            "Replaced magnetic reed switch cylinder and re-taught robot pick-and-place positions.",
            "Replaced seized sealed roller bearings with NSK high-durability grease-packed units.",
            "Replaced robotic torch dress package with high-flex corrugated conduit sheath.",
            "Adjusted tie-bar nut preload using hydraulic tensioning unit; verified tonnage equality within 2%.",
            "Replaced entire suction cup manifold array with oil-resistant fluorosilicone cups."
        ],
        "outcomes": ["Resolved", "Resolved", "Resolved", "Resolved", "Resolved", "Resolved", "Resolved", "Resolved"]
    }
]

MACHINES = [
    ("M101", "CNC Lathe Alpha", "CNC Lathe"),
    ("M102", "Hydraulic Stamping Press 02", "Hydraulic Press"),
    ("M103", "5-Axis Milling Center 03", "CNC Milling"),
    ("M104", "High-Speed Spindle Center 04", "CNC Milling"),
    ("M105", "Robotic Spot Welder 05", "Robotic Welder"),
    ("M106", "Heavy Transfer Palletizer 06", "Conveyor"),
    ("M107", "Centrifugal Compressor 07", "Compressor"),
    ("M108", "Injection Molding Machine 08", "Injection Molding"),
    ("M109", "Heavy Industrial Gearbox 09", "Gearbox"),
    ("M110", "High-Throughput Packaging Line 10", "Packaging"),
]


def generate_maintenance_records(target_count: int = 400, seed: int = 42) -> pd.DataFrame:
    """Generate ~400 realistic maintenance history records over 24 months."""
    random.seed(seed)
    records = []

    end_date = datetime(2026, 11, 4, 18, 0, 0)
    start_date = end_date - timedelta(days=730)  # 2 years

    # Specific anchor historical work orders for M104 for the viva demonstration
    m104_special_cases = [
        {
            "machine_id": "M104",
            "date": end_date - timedelta(days=38),
            "issue": "Spindle bearing high vibration alarm (6.4 mm/s RMS). Audible high-frequency whine at 1800 RPM. Suspected inner race spalling.",
            "action": "Conducted borescopic vibration audit. Replaced SKF 7014 high-precision ceramic hybrid bearing assembly. Applied Klüber Isoflex synthetic grease, run-in test 4 hours.",
            "outcome": "Resolved"
        },
        {
            "machine_id": "M104",
            "date": end_date - timedelta(days=115),
            "issue": "Scheduled preventive spindle overhaul. Minor raceway fretting corrosion detected on front bearing set.",
            "action": "Cleaned spindle housing taper, ultrasonically cleaned collet clamp, replaced secondary grease seal cartridge.",
            "outcome": "Resolved"
        },
        {
            "machine_id": "M104",
            "date": end_date - timedelta(days=265),
            "issue": "Vibration sensor transient warning during heavy facing cut on Titanium Grade 5 workpiece.",
            "action": "Checked spindle drawbar retention force (measured 18.5 kN, nominal). Torqued spindle retention studs and recalibrated vibration baseline.",
            "outcome": "Resolved"
        },
        {
            "machine_id": "M104",
            "date": end_date - timedelta(days=410),
            "issue": "Spindle thermal sensor reading 62°C under standard finishing cycle; slight harmonic hum.",
            "action": "Purged contaminated grease from spindle front labyrinth. Re-greased with Klüber NBU 15. Verified thermal stabilization at 46°C.",
            "outcome": "Resolved"
        },
        {
            "machine_id": "M104",
            "date": end_date - timedelta(days=580),
            "issue": "Annual machine geometry qualification: Spindle axial runout measured 0.007 mm (limit 0.005 mm).",
            "action": "Reground spindle nose taper on-machine with high-precision grinding quill. Restored runout to 0.002 mm TIR.",
            "outcome": "Resolved"
        }
    ]
    records.extend(m104_special_cases)

    # Generate remaining records across all 10 machines
    remaining = target_count - len(records)
    for _ in range(remaining):
        machine_id, machine_name, machine_type = random.choice(MACHINES)

        # Match domain template
        matched = [t for t in ISSUE_TEMPLATES if machine_type in t["types"]]
        if not matched:
            matched = [ISSUE_TEMPLATES[-1]]
        template = random.choice(matched)

        idx = random.randint(0, len(template["issues"]) - 1)
        issue = template["issues"][idx]
        action = template["actions"][idx]
        outcome = template["outcomes"][idx]

        random_days = random.randint(2, 725)
        record_date = end_date - timedelta(days=random_days, hours=random.randint(0, 23), minutes=random.randint(0, 59))

        records.append({
            "machine_id": machine_id,
            "date": record_date,
            "issue": issue,
            "action": action,
            "outcome": outcome
        })

    df = pd.DataFrame(records)
    df = df.sort_values(by="date").reset_index(drop=True)
    return df


def generate_and_save_maintenance(output_dir: str = "data/raw", count: int = 400, seed: int = 42) -> pd.DataFrame:
    """Generate and save maintenance history dataset to CSV."""
    os.makedirs(output_dir, exist_ok=True)
    df = generate_maintenance_records(target_count=count, seed=seed)
    out_path = os.path.join(output_dir, "maintenance_history.csv")
    df.to_csv(out_path, index=False)
    print(f"[Maintenance Generator] Generated {len(df)} records across {len(MACHINES)} machines -> {out_path}")
    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic maintenance history records.")
    parser.add_argument("--count", type=int, default=400, help="Number of records to generate (default: 400)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--out-dir", type=str, default="data/raw", help="Output directory path")
    args = parser.parse_args()

    generate_and_save_maintenance(output_dir=args.out_dir, count=args.count, seed=args.seed)

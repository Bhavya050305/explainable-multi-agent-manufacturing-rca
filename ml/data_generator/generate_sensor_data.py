"""
ManuMind AI - Enhanced Industrial Sensor Telemetry Generator
Generates realistic multi-channel time-series data for manufacturing equipment (M101-M110)
supporting large-scale dataset generation (30,000–50,000 readings), realistic operational
shift cycles, ambient temperature dynamics, and progressive fault degradation.
"""

import argparse
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd

# Machine Profiles with realistic industrial metadata
MACHINE_PROFILES = [
    {"id": "M101", "name": "CNC Lathe Alpha", "type": "CNC Lathe", "criticality": 3, "production_impact": 3, "fault": "none"},
    {"id": "M102", "name": "Hydraulic Stamping Press 02", "type": "Hydraulic Press", "criticality": 4, "production_impact": 4, "fault": "overheating"},
    {"id": "M103", "name": "5-Axis Milling Center 03", "type": "CNC Milling", "criticality": 4, "production_impact": 3, "fault": "none"},
    {"id": "M104", "name": "High-Speed Spindle Center 04", "type": "CNC Milling", "criticality": 5, "production_impact": 5, "fault": "bearing_wear"},
    {"id": "M105", "name": "Robotic Spot Welder 05", "type": "Robotic Welder", "criticality": 3, "production_impact": 4, "fault": "none"},
    {"id": "M106", "name": "Heavy Transfer Palletizer 06", "type": "Conveyor", "criticality": 2, "production_impact": 2, "fault": "none"},
    {"id": "M107", "name": "Centrifugal Compressor 07", "type": "Compressor", "criticality": 4, "production_impact": 5, "fault": "pressure_drop"},
    {"id": "M108", "name": "Injection Molding Machine 08", "type": "Injection Molding", "criticality": 3, "production_impact": 3, "fault": "none"},
    {"id": "M109", "name": "Heavy Industrial Gearbox 09", "type": "Gearbox", "criticality": 5, "production_impact": 4, "fault": "lubrication_failure"},
    {"id": "M110", "name": "High-Throughput Packaging Line 10", "type": "Packaging", "criticality": 2, "production_impact": 3, "fault": "none"},
]


def generate_machine_telemetry(profile: dict, steps: int = 4000, step_minutes: int = 5, seed: int = 42) -> pd.DataFrame:
    """
    Generate high-fidelity time-series sensor readings for one machine.
    Features:
    - Circadian/ambient thermal cycle (24-hour periodicity)
    - 3-shift factory operation modulation (Day/Evening/Night load variations)
    - Deterministic random seed per machine for absolute reproducibility
    - Smooth progressive degradation regimes for faulted assets
    """
    mach_seed = seed + int(hashlib_seed(profile["id"]))
    rng = np.random.RandomState(mach_seed)

    end_time = datetime(2026, 11, 5, 12, 0, 0)
    start_time = end_time - timedelta(minutes=steps * step_minutes)
    timestamps = [start_time + timedelta(minutes=i * step_minutes) for i in range(steps)]

    # Time representations (in hours)
    hours = np.array([(t.hour + t.minute / 60.0) for t in timestamps])

    # 1. Factory shift cycle factor: Day (0.05), Evening (0.0), Night (-0.05)
    shift_factor = np.where((hours >= 8) & (hours < 16), 0.08,
                   np.where((hours >= 16) & (hours < 24), 0.02, -0.06))

    # 2. Ambient diurnal thermal curve (peaks around 14:00)
    ambient_thermal = 2.5 * np.sin((hours - 8.0) * (2 * np.pi / 24.0))

    # Base nominal sensor channels
    vibration = 1.8 + 0.22 * rng.randn(steps) + 0.15 * shift_factor
    temperature = 48.0 + 1.2 * rng.randn(steps) + ambient_thermal + 1.5 * shift_factor
    pressure = 6.2 + 0.12 * rng.randn(steps) + 0.1 * shift_factor
    current = 14.5 + 0.7 * rng.randn(steps) + 1.2 * shift_factor
    rpm = 1800.0 + 7.5 * rng.randn(steps)

    is_anomaly = np.zeros(steps, dtype=int)
    failure_risk = np.zeros(steps, dtype=float)
    fault_severity = np.zeros(steps, dtype=float)
    fault_type = ["normal"] * steps

    fault = profile["fault"]

    # Fault timeline configuration:
    # 0 to 65% normal baseline; 65% to 80% incipient degradation; 80% to 100% severe progressive failure
    if fault != "none":
        fault_start = int(steps * 0.65)
        fault_len = steps - fault_start
        progression = np.linspace(0.0, 1.0, fault_len)

        if fault == "bearing_wear":
            # M104 Primary Demo: Inner race spalling -> escalating vibration and cage chatter
            # Incipient phase (subtle vibration rise) + Severe phase (exponential acceleration)
            vib_rise = (progression ** 2.2) * 7.5 + (progression * 1.2)
            temp_rise = (progression ** 1.5) * 16.5
            rpm_drop = (progression ** 2.0) * 55.0

            vibration[fault_start:] += vib_rise + rng.normal(0, 0.35, fault_len)
            temperature[fault_start:] += temp_rise + rng.normal(0, 0.4, fault_len)
            rpm[fault_start:] -= rpm_drop + rng.normal(0, 10.0, fault_len)
            current[fault_start:] += (progression ** 1.8) * 2.5

            is_anomaly[fault_start:] = 1
            fault_severity[fault_start:] = np.clip(progression, 0.0, 1.0)
            failure_risk[fault_start:] = np.clip(0.15 + (progression ** 1.4) * 0.75, 0.0, 0.96)
            for i in range(fault_start, steps):
                fault_type[i] = "bearing_wear"

        elif fault == "overheating":
            # M102: Hydraulic cooler failure / radiator clog
            temp_rise = (progression ** 1.3) * 45.0
            press_rise = (progression ** 1.6) * 1.9

            temperature[fault_start:] += temp_rise + rng.normal(0, 0.6, fault_len)
            pressure[fault_start:] += press_rise + rng.normal(0, 0.08, fault_len)

            is_anomaly[fault_start:] = 1
            fault_severity[fault_start:] = np.clip(progression, 0.0, 1.0)
            failure_risk[fault_start:] = np.clip(0.12 + (progression ** 1.2) * 0.72, 0.0, 0.90)
            for i in range(fault_start, steps):
                fault_type[i] = "overheating"

        elif fault == "pressure_drop":
            # M107: Main compressor pneumatic seal blowout
            press_drop = (progression ** 1.4) * 3.8
            curr_rise = (progression ** 1.2) * 6.5  # motor tries to maintain head

            pressure[fault_start:] -= press_drop + rng.normal(0, 0.09, fault_len)
            current[fault_start:] += curr_rise + rng.normal(0, 0.25, fault_len)

            is_anomaly[fault_start:] = 1
            fault_severity[fault_start:] = np.clip(progression, 0.0, 1.0)
            failure_risk[fault_start:] = np.clip(0.10 + (progression ** 1.3) * 0.75, 0.0, 0.88)
            for i in range(fault_start, steps):
                fault_type[i] = "pressure_drop"

        elif fault == "lubrication_failure":
            # M109: Industrial gearbox boundary dry friction
            vib_rise = (progression ** 1.7) * 4.2
            curr_rise = (progression ** 1.5) * 15.5
            temp_rise = (progression ** 1.4) * 32.0

            vibration[fault_start:] += vib_rise + rng.normal(0, 0.3, fault_len)
            current[fault_start:] += curr_rise + rng.normal(0, 0.5, fault_len)
            temperature[fault_start:] += temp_rise + rng.normal(0, 0.5, fault_len)

            is_anomaly[fault_start:] = 1
            fault_severity[fault_start:] = np.clip(progression, 0.0, 1.0)
            failure_risk[fault_start:] = np.clip(0.15 + (progression ** 1.3) * 0.75, 0.0, 0.93)
            for i in range(fault_start, steps):
                fault_type[i] = "lubrication_failure"

    else:
        # Healthy machines: benign transient operational pulses (e.g. tool changes or pallet load)
        pulse_indices = rng.choice(steps, size=max(2, steps // 800), replace=False)
        for p_idx in pulse_indices:
            vibration[p_idx:p_idx+2] += rng.uniform(0.6, 1.1)
        failure_risk[:] = np.clip(0.02 + rng.uniform(0.0, 0.06, steps), 0.0, 0.15)

    df = pd.DataFrame({
        "machine_id": profile["id"],
        "timestamp": timestamps,
        "vibration": np.round(vibration, 3),
        "temperature": np.round(temperature, 2),
        "pressure": np.round(pressure, 2),
        "current": np.round(current, 2),
        "rpm": np.round(rpm, 1),
        "is_anomaly": is_anomaly,
        "fault_type": fault_type,
        "fault_severity": np.round(fault_severity, 3),
        "failure_risk": np.round(failure_risk, 3)
    })
    return df


def hashlib_seed(val: str) -> int:
    """Deterministic integer hash from string."""
    import hashlib
    return int(hashlib.md5(val.encode("utf-8")).hexdigest()[:8], 16) % 100000


def generate_all_sensor_data(output_dir: str = "data/raw", steps: int = 4000, seed: int = 42) -> pd.DataFrame:
    """
    Generate telemetry for all 10 machines.
    Default 4000 steps * 10 machines = 40,000 total sensor readings.
    """
    os.makedirs(output_dir, exist_ok=True)
    dfs = []
    for profile in MACHINE_PROFILES:
        df_mach = generate_machine_telemetry(profile, steps=steps, seed=seed)
        dfs.append(df_mach)

    full_df = pd.concat(dfs, ignore_index=True)
    raw_path = os.path.join(output_dir, "sensor_readings.csv")
    full_df.to_csv(raw_path, index=False)
    print(f"[Sensor Generator] Generated {len(full_df)} telemetry rows across {len(MACHINE_PROFILES)} machines -> {raw_path}")
    return full_df


def split_sensor_dataset(df: pd.DataFrame, output_dir: str = "data/processed", train_pct: float = 0.70, val_pct: float = 0.15, test_pct: float = 0.15) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Leakage-free chronological dataset splitting.
    For each machine, readings are split chronologically:
    - First 70%: Training Set
    - Next 15%: Validation Set
    - Final 15%: Test Set (Strictly held-out)
    Zero future information leaks into training or validation.
    """
    os.makedirs(output_dir, exist_ok=True)
    train_dfs, val_dfs, test_dfs = [], [], []

    for mach_id, m_df in df.groupby("machine_id", sort=False):
        m_df_sorted = m_df.sort_values(by="timestamp").reset_index(drop=True)
        n = len(m_df_sorted)
        train_idx = int(n * train_pct)
        val_idx = int(n * (train_pct + val_pct))

        train_dfs.append(m_df_sorted.iloc[:train_idx])
        val_dfs.append(m_df_sorted.iloc[train_idx:val_idx])
        test_dfs.append(m_df_sorted.iloc[val_idx:])

    train_df = pd.concat(train_dfs, ignore_index=True)
    val_df = pd.concat(val_dfs, ignore_index=True)
    test_df = pd.concat(test_dfs, ignore_index=True)

    train_path = os.path.join(output_dir, "sensor_train.csv")
    val_path = os.path.join(output_dir, "sensor_val.csv")
    test_path = os.path.join(output_dir, "sensor_test.csv")

    train_df.to_csv(train_path, index=False)
    val_df.to_csv(val_path, index=False)
    test_df.to_csv(test_path, index=False)

    print(f"[Dataset Split] Sensor Splits Saved:")
    print(f"  - Train: {len(train_df)} rows ({len(train_df)/len(df)*100:.1f}%) -> {train_path}")
    print(f"  - Val:   {len(val_df)} rows ({len(val_df)/len(df)*100:.1f}%) -> {val_path}")
    print(f"  - Test:  {len(test_df)} rows ({len(test_df)/len(df)*100:.1f}%) -> {test_path}")

    return train_df, val_df, test_df


def generate_labelled_windows(df: pd.DataFrame, output_dir: str = "data/processed", window_size: int = 30, stride: int = 10) -> pd.DataFrame:
    """
    Generate fixed-length time-series sequence windows for LSTM Autoencoder / Anomaly classifiers.
    Window size: 30 steps (2.5 hours at 5m resolution).
    """
    os.makedirs(output_dir, exist_ok=True)
    windows = []

    features = ["vibration", "temperature", "pressure", "current", "rpm"]

    for mach_id, m_df in df.groupby("machine_id", sort=False):
        m_df_sorted = m_df.sort_values(by="timestamp").reset_index(drop=True)
        n = len(m_df_sorted)

        for start in range(0, n - window_size + 1, stride):
            end = start + window_size
            chunk = m_df_sorted.iloc[start:end]

            # Anomaly label for window: 1 if >= 30% of steps are abnormal
            anomaly_ratio = chunk["is_anomaly"].mean()
            is_win_anomaly = int(anomaly_ratio >= 0.3)

            # Determine predominant fault type
            fault_types = chunk["fault_type"].value_counts()
            dominant_fault = fault_types.index[0] if fault_types.index[0] != "normal" else (fault_types.index[1] if len(fault_types) > 1 else "normal")

            win_meta = {
                "window_id": f"WIN_{mach_id}_{start:05d}",
                "machine_id": mach_id,
                "start_time": chunk["timestamp"].iloc[0],
                "end_time": chunk["timestamp"].iloc[-1],
                "mean_vibration": round(float(chunk["vibration"].mean()), 3),
                "max_vibration": round(float(chunk["vibration"].max()), 3),
                "mean_temperature": round(float(chunk["temperature"].mean()), 2),
                "max_temperature": round(float(chunk["temperature"].max()), 2),
                "mean_pressure": round(float(chunk["pressure"].mean()), 2),
                "mean_current": round(float(chunk["current"].mean()), 2),
                "mean_rpm": round(float(chunk["rpm"].mean()), 1),
                "anomaly_ratio": round(float(anomaly_ratio), 3),
                "is_anomaly": is_win_anomaly,
                "fault_type": dominant_fault,
                "mean_failure_risk": round(float(chunk["failure_risk"].mean()), 3)
            }
            windows.append(win_meta)

    win_df = pd.DataFrame(windows)
    win_path = os.path.join(output_dir, "sensor_windows.csv")
    win_df.to_csv(win_path, index=False)
    print(f"[Window Generator] Created {len(win_df)} labelled sequence windows -> {win_path}")
    return win_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic industrial sensor telemetry.")
    parser.add_argument("--steps", type=int, default=4000, help="Number of telemetry time steps per machine (default: 4000 -> 40,000 total rows)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--out-dir", type=str, default="data/raw", help="Output directory path")
    args = parser.parse_args()

    full_df = generate_all_sensor_data(output_dir=args.out_dir, steps=args.steps, seed=args.seed)
    split_sensor_dataset(full_df, output_dir="data/processed")
    generate_labelled_windows(full_df, output_dir="data/processed")

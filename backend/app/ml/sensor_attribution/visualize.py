"""
ManuMind AI — Sensor Attribution Visualizations Gallery
Department of AI & Data Science — RMK Engineering College

Generates publication-grade analytical visualizations for sensor-level anomaly attribution:
1. sensor_contribution_bar_chart.png
2. attribution_heatmap.png
3. sensor_contribution_over_time.png
4. lstm_vs_if_attribution_comparison.png
5. normal_vs_anomalous_distributions.png
6. fault_progression_vs_dominant_sensor.png
"""

import os
import tempfile
from typing import Dict, List, Tuple, Any, Optional

# Set non-interactive backend and writable cache before importing pyplot
os.environ.setdefault("MPLCONFIGDIR", os.path.join(tempfile.gettempdir(), "matplotlib_manumind"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd

from backend.app.ml.sensor_attribution.config import (
    FEATURE_COLUMNS,
    FEATURE_UNITS,
    SYNTHETIC_FAULT_MAPPING
)

# Professional visual palette
PALETTE = {
    "vibration": "#2b5c8f",     # Deep Steel Blue
    "temperature": "#c0392b",   # Crimson / Thermal Red
    "pressure": "#27ae60",      # Emerald Green
    "current": "#f39c12",       # Amber / Industrial Yellow
    "rpm": "#8e44ad"            # Purple
}
FEATURE_COLORS = [PALETTE[f] for f in FEATURE_COLUMNS]


def plot_sensor_contribution_bars(
    lstm_df: pd.DataFrame,
    output_path: str
):
    """
    Figure 1: Sensor contribution bar chart for each faulted machine (M102, M104, M107, M109).
    Shows mean percentage contribution across anomalous test sequences with standard error bars.
    """
    fig, axes = plt.subplots(2, 2, figsize=(14, 10), sharey=True)
    axes = axes.flatten()

    faulted_machines = ["M102", "M104", "M107", "M109"]

    for i, m_id in enumerate(faulted_machines):
        ax = axes[i]
        meta = SYNTHETIC_FAULT_MAPPING.get(m_id, {})
        m_name = meta.get("name", m_id)
        fault_name = meta.get("fault", "Unknown")

        sub = lstm_df[(lstm_df["machine_id"] == m_id) & (lstm_df["is_anomaly"] == 1)]
        pct_cols = [f"{f}_pct" for f in FEATURE_COLUMNS]

        means = sub[pct_cols].mean().values
        stds = sub[pct_cols].std().values

        bars = ax.bar(
            FEATURE_COLUMNS,
            means,
            yerr=stds,
            capsize=5,
            color=FEATURE_COLORS,
            alpha=0.88,
            edgecolor="black",
            linewidth=1.0
        )

        # Highlight dominant sensor with label
        dom_idx = int(np.argmax(means))
        ax.annotate(
            f"Dominant: {FEATURE_COLUMNS[dom_idx].capitalize()}\n({means[dom_idx]:.1f}%)",
            xy=(dom_idx, means[dom_idx] + stds[dom_idx] + 2),
            xytext=(dom_idx, min(95, means[dom_idx] + stds[dom_idx] + 15)),
            ha="center",
            fontsize=10,
            fontweight="bold",
            color=FEATURE_COLORS[dom_idx],
            arrowprops=dict(arrowstyle="->", color=FEATURE_COLORS[dom_idx], lw=1.5)
        )

        ax.set_title(f"{m_id}: {m_name}\nFault: {fault_name.replace('_', ' ').title()}", fontsize=12, fontweight="bold", pad=8)
        ax.set_ylabel("Contribution (%)", fontsize=10, fontweight="bold")
        ax.set_ylim(0, 105)
        ax.grid(axis="y", linestyle="--", alpha=0.4)
        ax.tick_params(axis="x", rotation=15)

    plt.suptitle("LSTM Reconstruction Error Sensor Attribution Across Faulted Assets\n(Evaluated on Anomalous Test Sequences, N=58 per Machine)", fontsize=14, fontweight="bold", y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=300)
    plt.close()


def plot_attribution_heatmap(
    lstm_df: pd.DataFrame,
    output_path: str
):
    """
    Figure 2: Five-feature heatmap of attribution across anomalous sequences.
    Visualizes individual sequence-level attribution percentages grouped by faulted machine.
    """
    anom_df = lstm_df[lstm_df["is_anomaly"] == 1].sort_values(by=["machine_id", "window_id"]).reset_index(drop=True)
    pct_cols = [f"{f}_pct" for f in FEATURE_COLUMNS]

    data_matrix = anom_df[pct_cols].values  # (232, 5)

    plt.figure(figsize=(10, 12))
    ax = sns.heatmap(
        data_matrix,
        cmap="YlOrRd",
        cbar_kws={"label": "Reconstruction Error Contribution (%)"},
        xticklabels=[f.capitalize() for f in FEATURE_COLUMNS],
        yticklabels=False,
        vmin=0,
        vmax=100
    )

    # Add machine group boundary lines and annotations
    machines = anom_df["machine_id"].values
    unique_m, idxs = np.unique(machines, return_index=True)
    sorted_order = np.argsort(idxs)
    unique_m = unique_m[sorted_order]
    idxs = idxs[sorted_order]

    for j, (m_id, start_idx) in enumerate(zip(unique_m, idxs)):
        end_idx = idxs[j + 1] if j + 1 < len(idxs) else len(anom_df)
        mid_idx = (start_idx + end_idx) / 2.0

        if j > 0:
            ax.axhline(start_idx, color="black", linewidth=1.5, linestyle="--")

        meta = SYNTHETIC_FAULT_MAPPING.get(m_id, {})
        fault_name = meta.get("fault", "Fault").replace("_", " ").title()
        ax.text(
            -0.2, mid_idx,
            f"{m_id}\n({fault_name})",
            va="center", ha="right",
            fontsize=10, fontweight="bold",
            transform=ax.get_yaxis_transform()
        )

    plt.title("Sensor-Level Anomaly Attribution Heatmap\n(All 232 Anomalous Test Sequences Grouped by Asset)", fontsize=13, fontweight="bold", pad=12)
    plt.xlabel("Monitored Sensor Channel", fontsize=11, fontweight="bold")
    plt.ylabel("Test Sequence Windows (Chronological per Asset)", fontsize=11, fontweight="bold")

    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=300)
    plt.close()


def plot_sensor_contribution_over_time(
    lstm_df: pd.DataFrame,
    output_path: str
):
    """
    Figure 3: Sensor contribution over time for M102, M104, M107, and M109.
    Tracks progression of sensor contribution percentages across all test sequence windows (normal to severe).
    """
    fig, axes = plt.subplots(4, 1, figsize=(14, 14), sharex=True)
    faulted_machines = ["M102", "M104", "M107", "M109"]

    for i, m_id in enumerate(faulted_machines):
        ax = axes[i]
        meta = SYNTHETIC_FAULT_MAPPING.get(m_id, {})
        m_name = meta.get("name", m_id)
        fault_name = meta.get("fault", "Unknown").replace("_", " ").title()

        sub = lstm_df[lstm_df["machine_id"] == m_id].sort_values(by="window_id").reset_index(drop=True)
        x_steps = np.arange(len(sub))

        for feat in FEATURE_COLUMNS:
            ax.plot(
                x_steps,
                sub[f"{feat}_pct"],
                label=f"{feat.capitalize()}",
                color=PALETTE[feat],
                linewidth=2.2,
                alpha=0.9
            )

        # Mark anomaly onset boundary if present
        anom_indices = np.where(sub["is_anomaly"] == 1)[0]
        if len(anom_indices) > 0 and anom_indices[0] > 0:
            ax.axvline(anom_indices[0], color="red", linestyle=":", linewidth=2, label="Anomaly Window Onset")

        ax.set_title(f"{m_id}: {m_name} — Fault: {fault_name}", fontsize=11, fontweight="bold", pad=4)
        ax.set_ylabel("Contribution (%)", fontsize=10, fontweight="bold")
        ax.set_ylim(-2, 102)
        ax.grid(True, linestyle="--", alpha=0.4)
        if i == 0:
            ax.legend(loc="upper right", ncol=6, fontsize=9, framealpha=0.95)

    axes[-1].set_xlabel("Test Sequence Window Index (Chronological Stride 10)", fontsize=11, fontweight="bold")
    plt.suptitle("Sensor Attribution Trajectories Over Test Partition Timeline\n(Tracking Multi-Sensor Contributions Across Operating Sequences)", fontsize=14, fontweight="bold", y=0.99)
    plt.tight_layout(rect=[0, 0, 1, 0.97])
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=300)
    plt.close()


def plot_lstm_vs_if_attribution_comparison(
    lstm_df: pd.DataFrame,
    if_df: pd.DataFrame,
    output_path: str
):
    """
    Figure 4: Comparison of LSTM attribution and Isolation Forest ablation results.
    Direct head-to-head comparison of normalized contribution percentages across all 5 sensors.
    """
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    axes = axes.flatten()

    faulted_machines = ["M102", "M104", "M107", "M109"]
    x = np.arange(len(FEATURE_COLUMNS))
    width = 0.38

    for i, m_id in enumerate(faulted_machines):
        ax = axes[i]
        meta = SYNTHETIC_FAULT_MAPPING.get(m_id, {})
        fault_name = meta.get("fault", "Unknown").replace("_", " ").title()

        l_sub = lstm_df[(lstm_df["machine_id"] == m_id) & (lstm_df["is_anomaly"] == 1)]
        i_sub = if_df[(if_df["machine_id"] == m_id) & (if_df["is_anomaly"] == 1)]

        l_means = [l_sub[f"{f}_pct"].mean() for f in FEATURE_COLUMNS]
        i_means = [i_sub[f"{f}_contrib_pct"].mean() for f in FEATURE_COLUMNS]

        rects1 = ax.bar(x - width/2, l_means, width, label="LSTM Reconstruction Error", color="#1f77b4", alpha=0.85, edgecolor="black")
        rects2 = ax.bar(x + width/2, i_means, width, label="Isolation Forest Feature Ablation", color="#ff7f0e", alpha=0.85, edgecolor="black")

        ax.set_title(f"{m_id} ({fault_name})", fontsize=12, fontweight="bold", pad=6)
        ax.set_ylabel("Attribution Share (%)", fontsize=10, fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels([f.capitalize() for f in FEATURE_COLUMNS], fontsize=10)
        ax.set_ylim(0, 105)
        ax.grid(axis="y", linestyle="--", alpha=0.4)
        if i == 0:
            ax.legend(loc="upper right", fontsize=9, framealpha=0.95)

    plt.suptitle("Methodological Cross-Comparison: LSTM Reconstruction vs. Isolation Forest Ablation\n(Average Sensor Attribution Share on Anomalous Test Sequences)", fontsize=14, fontweight="bold", y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=300)
    plt.close()


def plot_normal_vs_anomalous_distributions(
    lstm_df: pd.DataFrame,
    output_path: str
):
    """
    Figure 5: Normal versus anomalous sensor contribution distributions.
    Shows box plots contrasting the dispersed baseline attribution of healthy sequences
    against the sharp channel-specific concentration of anomalous sequences.
    """
    normal_sub = lstm_df[lstm_df["is_anomaly"] == 0]
    anom_sub = lstm_df[lstm_df["is_anomaly"] == 1]

    plot_records = []
    for f in FEATURE_COLUMNS:
        col = f"{f}_pct"
        for val in normal_sub[col]:
            plot_records.append({"Feature": f.capitalize(), "Attribution (%)": val, "Condition": "Normal Sequences (Healthy Fleet)"})
        for val in anom_sub[col]:
            plot_records.append({"Feature": f.capitalize(), "Attribution (%)": val, "Condition": "Anomalous Sequences (Faulted Assets)"})

    dist_df = pd.DataFrame(plot_records)

    plt.figure(figsize=(13, 7))
    sns.boxplot(
        data=dist_df,
        x="Feature",
        y="Attribution (%)",
        hue="Condition",
        palette=["#2ecc71", "#e74c3c"],
        width=0.6,
        fliersize=2
    )

    # Reference uniform baseline line (20%)
    plt.axhline(20.0, color="gray", linestyle="--", linewidth=1.5, label="Uniform Nominal Baseline (20%)")

    plt.title("Attribution Distribution: Normal Sequences vs. Anomalous Sequences\n(Highlighting Peak Concentration on Defective Channels)", fontsize=13, fontweight="bold", pad=10)
    plt.xlabel("Sensor Feature", fontsize=11, fontweight="bold")
    plt.ylabel("Reconstruction Error Attribution (%)", fontsize=11, fontweight="bold")
    plt.ylim(-2, 102)
    plt.grid(axis="y", linestyle="--", alpha=0.4)
    plt.legend(loc="upper right", fontsize=10, framealpha=0.95)

    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=300)
    plt.close()


def plot_fault_progression_vs_dominant_sensor(
    progression_df: pd.DataFrame,
    output_path: str
):
    """
    Figure 6: Fault progression versus dominant sensor contribution.
    Visualizes how the attribution percentage of the candidate sensor evolves
    from Stage 1 (Incipient) through Stage 2 (Moderate) to Stage 3 (Severe).
    """
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.flatten()

    faulted_machines = ["M102", "M104", "M107", "M109"]

    for i, m_id in enumerate(faulted_machines):
        ax = axes[i]
        meta = SYNTHETIC_FAULT_MAPPING.get(m_id, {})
        prim_sensor = meta.get("primary_expected", "vibration")
        fault_name = meta.get("fault", "Unknown").replace("_", " ").title()

        sub = progression_df[progression_df["machine_id"] == m_id].sort_values(by="progression_step").reset_index(drop=True)

        if len(sub) > 0 and "dominant_pct" in sub.columns:
            ax.plot(
                sub["progression_step"],
                sub["dominant_pct"],
                marker="o",
                markersize=4,
                color=PALETTE[prim_sensor],
                linewidth=2.2,
                label=f"Candidate Sensor: {prim_sensor.capitalize()}"
            )

            # Shade progression stages
            ax.axvspan(0, 600, color="#f9e79f", alpha=0.3, label="Stage 1: Incipient")
            ax.axvspan(600, 1000, color="#f5b041", alpha=0.3, label="Stage 2: Moderate")
            ax.axvspan(1000, 1400, color="#ec7063", alpha=0.3, label="Stage 3: Severe")

        ax.set_title(f"{m_id} ({fault_name}) — Sensor: {prim_sensor.capitalize()}", fontsize=11, fontweight="bold", pad=6)
        ax.set_xlabel("Fault Progression Steps (0 = Onset at Step 2600)", fontsize=10, fontweight="bold")
        ax.set_ylabel("Attribution Share (%)", fontsize=10, fontweight="bold")
        ax.set_ylim(0, 105)
        ax.grid(True, linestyle="--", alpha=0.4)
        if i == 0:
            ax.legend(loc="lower right", fontsize=8, framealpha=0.95)

    plt.suptitle("Dominant Sensor Attribution Stability Across Fault Progression Stages\n(Evaluated Across Full 1,400 Injected Fault Timesteps)", fontsize=14, fontweight="bold", y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=300)
    plt.close()


def generate_all_visualizations(
    lstm_df: pd.DataFrame,
    if_df: pd.DataFrame,
    progression_df: pd.DataFrame,
    output_dir: str
) -> Dict[str, str]:
    """Generates and saves all 6 required analytical attribution figures."""
    os.makedirs(output_dir, exist_ok=True)

    fig1_path = os.path.join(output_dir, "sensor_contribution_bar_chart.png")
    fig2_path = os.path.join(output_dir, "attribution_heatmap.png")
    fig3_path = os.path.join(output_dir, "sensor_contribution_over_time.png")
    fig4_path = os.path.join(output_dir, "lstm_vs_if_attribution_comparison.png")
    fig5_path = os.path.join(output_dir, "normal_vs_anomalous_distributions.png")
    fig6_path = os.path.join(output_dir, "fault_progression_vs_dominant_sensor.png")

    plot_sensor_contribution_bars(lstm_df, fig1_path)
    plot_attribution_heatmap(lstm_df, fig2_path)
    plot_sensor_contribution_over_time(lstm_df, fig3_path)
    plot_lstm_vs_if_attribution_comparison(lstm_df, if_df, fig4_path)
    plot_normal_vs_anomalous_distributions(lstm_df, fig5_path)
    plot_fault_progression_vs_dominant_sensor(progression_df, fig6_path)

    return {
        "sensor_contribution_bar_chart": fig1_path,
        "attribution_heatmap": fig2_path,
        "sensor_contribution_over_time": fig3_path,
        "lstm_vs_if_attribution_comparison": fig4_path,
        "normal_vs_anomalous_distributions": fig5_path,
        "fault_progression_vs_dominant_sensor": fig6_path
    }

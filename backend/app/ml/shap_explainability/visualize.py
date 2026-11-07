"""
ManuMind AI — SHAP Anomaly Attribution Visualization Engine
Department of AI & Data Science — RMK Engineering College

Publication-grade visualizers for local waterfall explanations, global feature importance,
and beeswarm distribution plots for the Isolation Forest Kernel SHAP explainer.
All plots explicitly preserve dimensional integrity and avoid misleading physical-unit labels.
"""

import os
from typing import Any, Dict, List, Optional, Tuple, Union

import matplotlib
matplotlib.use("Agg")  # Non-interactive headless backend
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from backend.app.ml.shap_explainability.config import FEATURE_COLUMNS, FEATURE_UNITS


def plot_waterfall(
    explanation: Dict[str, Any],
    save_path: str,
    feature_values: Optional[Union[np.ndarray, List[float], Dict[str, float]]] = None,
    scaled: bool = True,
    title: Optional[str] = None
) -> str:
    """
    Renders a publication-grade waterfall plot for an individual observation.

    Illustrates how each sensor feature drives the continuous anomaly score from
    the healthy baseline expectation E[f(X)] to the observed anomaly score f(X).

    Args:
        explanation: Dictionary returned by IsolationForestShapExplainer.explain_observation.
        save_path: Destination path for the saved graphic (PNG).
        feature_values: Optional sensor values for display alongside feature names.
        scaled: Whether feature_values are in standardized space (z-score) or original units.
        title: Optional custom plot title.

    Returns:
        Absolute or relative path to the saved plot image.
    """
    os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)

    attributions = explanation.get("feature_attributions", {})
    base_val = float(explanation.get("base_value", 0.0))
    anomaly_score = float(explanation.get("anomaly_score", 0.0))
    machine_id = explanation.get("machine_id", "Unknown")
    step = explanation.get("step", "N/A")

    features = list(attributions.keys())
    values = [float(attributions[f]) for f in features]

    # Sort features by absolute attribution magnitude descending
    sorted_pairs = sorted(zip(features, values), key=lambda x: abs(x[1]), reverse=True)
    sorted_features = [p[0] for p in sorted_pairs]
    sorted_values = [p[1] for p in sorted_pairs]

    fig, ax = plt.subplots(figsize=(10, 5.5), dpi=300)

    y_pos = np.arange(len(sorted_features))

    # Determine colors: red/coral for positive (pushes toward anomaly), steelblue for negative (anchors to health)
    colors = ["#d9534f" if v > 0 else "#337ab7" for v in sorted_values]

    bars = ax.barh(y_pos, sorted_values, height=0.6, color=colors, edgecolor="black", linewidth=0.8, alpha=0.9)

    ax.set_yticks(y_pos)
    ytick_labels = []
    for f in sorted_features:
        f_label = f"{f}"
        if feature_values is not None:
            if isinstance(feature_values, dict) and f in feature_values:
                val_str = f" ({feature_values[f]:+.2f}σ)" if scaled else f" ({feature_values[f]:.2f} {FEATURE_UNITS.get(f, '')})"
                f_label += val_str
        ytick_labels.append(f_label)

    ax.set_yticklabels(ytick_labels, fontsize=11, fontweight="bold")
    ax.invert_yaxis()  # Largest on top

    ax.axvline(0, color="black", linestyle="-", linewidth=1.0, alpha=0.7)

    # Value text annotations on bars
    x_max = max(abs(min(sorted_values)), abs(max(sorted_values)), 0.01) * 1.35
    ax.set_xlim(-x_max, x_max)

    for bar, val in zip(bars, sorted_values):
        offset = x_max * 0.03
        if val >= 0:
            ax.text(val + offset, bar.get_y() + bar.get_height() / 2.0, f"+{val:.4f}",
                    va="center", ha="left", fontsize=9.5, fontweight="bold", color="#a94442")
        else:
            ax.text(val - offset, bar.get_y() + bar.get_height() / 2.0, f"{val:.4f}",
                    va="center", ha="right", fontsize=9.5, fontweight="bold", color="#245269")

    # Annotate baseline and anomaly score
    plot_title = title or f"SHAP Local Waterfall Attribution — Machine {machine_id} (Step {step})"
    ax.set_title(plot_title, fontsize=13, fontweight="bold", pad=15)
    ax.set_xlabel("Attribution Force Δf(X) [Dimensionless Anomaly Intensity Delta]", fontsize=10.5, labelpad=10)

    # Subtitle annotation box
    subtitle = (
        f"Baseline E[f(X)] = {base_val:+.4f}  |  Anomaly Score f(X) = {anomaly_score:+.4f}  |  "
        f"Sum Δf = {sum(sorted_values):+.4f}  |  Share of Positive Top Contributor = {explanation.get('share_of_positive_attribution_pct')}%"
    )
    plt.figtext(0.5, 0.01, subtitle, ha="center", fontsize=8.5, style="italic",
                 bbox=dict(boxstyle="round,pad=0.4", facecolor="#f8f9fa", edgecolor="#cccccc"))

    ax.grid(axis="x", linestyle="--", alpha=0.5)
    plt.tight_layout(rect=[0, 0.04, 1, 1])

    plt.savefig(save_path, bbox_inches="tight")
    plt.close(fig)
    return save_path


def plot_global_feature_importance(
    explanations: List[Dict[str, Any]],
    save_path: str,
    title: Optional[str] = None
) -> str:
    """
    Renders global mean absolute SHAP feature importance across a cohort of observations.

    Importance_j = (1 / N) * sum_k |phi_k,j|

    Args:
        explanations: List of explanation dictionaries.
        save_path: Destination path for graphic (PNG).
        title: Optional custom plot title.

    Returns:
        Path to saved graphic.
    """
    os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)

    if not explanations:
        raise ValueError("Cannot plot feature importance from empty explanations list.")

    features = FEATURE_COLUMNS
    abs_matrix = np.zeros((len(explanations), len(features)), dtype=np.float64)

    for i, exp in enumerate(explanations):
        attr = exp.get("feature_attributions", {})
        for j, feat in enumerate(features):
            abs_matrix[i, j] = abs(float(attr.get(feat, 0.0)))

    mean_abs_importance = np.mean(abs_matrix, axis=0)

    # Sort descending
    sorted_indices = np.argsort(mean_abs_importance)[::-1]
    sorted_features = [features[idx] for idx in sorted_indices]
    sorted_importance = [mean_abs_importance[idx] for idx in sorted_indices]

    fig, ax = plt.subplots(figsize=(9, 5), dpi=300)
    y_pos = np.arange(len(sorted_features))

    bars = ax.barh(y_pos, sorted_importance, height=0.55, color="#2b5c8f", edgecolor="black", linewidth=0.8)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(sorted_features, fontsize=11, fontweight="bold")
    ax.invert_yaxis()

    max_val = max(sorted_importance) * 1.25
    ax.set_xlim(0, max_val)

    for bar, val in zip(bars, sorted_importance):
        ax.text(val + max_val * 0.02, bar.get_y() + bar.get_height() / 2.0, f"{val:.4f}",
                va="center", ha="left", fontsize=9.5, fontweight="bold")

    plot_title = title or f"Global SHAP Feature Importance (Mean |Δf(X)|, N={len(explanations)})"
    ax.set_title(plot_title, fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("Mean Absolute Attribution Force E[|Δf(X)|] [Dimensionless]", fontsize=10.5, labelpad=10)

    ax.grid(axis="x", linestyle="--", alpha=0.5)
    plt.tight_layout()

    plt.savefig(save_path, bbox_inches="tight")
    plt.close(fig)
    return save_path


def plot_beeswarm(
    explanations: List[Dict[str, Any]],
    raw_feature_matrix: np.ndarray,
    save_path: str,
    title: Optional[str] = None
) -> str:
    """
    Renders a publication-grade beeswarm distribution plot showing attribution distribution
    and feature value gradient (standardized deviation) across observations.

    Args:
        explanations: List of explanation dictionaries.
        raw_feature_matrix: Matrix of shape (N, 5) containing standardized feature values.
        save_path: Destination path for graphic (PNG).
        title: Optional custom plot title.

    Returns:
        Path to saved graphic.
    """
    os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)

    features = FEATURE_COLUMNS
    N = len(explanations)
    shap_matrix = np.zeros((N, len(features)), dtype=np.float64)

    for i, exp in enumerate(explanations):
        attr = exp.get("feature_attributions", {})
        for j, feat in enumerate(features):
            shap_matrix[i, j] = float(attr.get(feat, 0.0))

    # Sort features by mean absolute SHAP
    mean_abs = np.mean(np.abs(shap_matrix), axis=0)
    sorted_order = np.argsort(mean_abs)[::-1]

    fig, ax = plt.subplots(figsize=(10, 6), dpi=300)

    cmap = plt.get_cmap("coolwarm")
    y_pos = np.arange(len(sorted_order))

    # Deterministic jitter for beeswarm scatter
    rng = np.random.RandomState(42)

    for plot_idx, feat_idx in enumerate(sorted_order):
        feat_shaps = shap_matrix[:, feat_idx]
        feat_vals = raw_feature_matrix[:, feat_idx]

        # Normalize feature values to [0, 1] for colormap
        v_min, v_max = np.percentile(feat_vals, 5), np.percentile(feat_vals, 95)
        if v_max > v_min:
            norm_vals = np.clip((feat_vals - v_min) / (v_max - v_min), 0.0, 1.0)
        else:
            norm_vals = np.full_like(feat_vals, 0.5)

        jitter = rng.normal(0, 0.08, size=N)
        y_scatter = plot_idx + jitter

        scatter = ax.scatter(
            feat_shaps,
            y_scatter,
            c=norm_vals,
            cmap=cmap,
            s=22,
            alpha=0.75,
            edgecolors="none"
        )

    ax.axvline(0, color="gray", linestyle="--", linewidth=1.0, alpha=0.7)
    ax.set_yticks(y_pos)
    ax.set_yticklabels([features[idx] for idx in sorted_order], fontsize=11, fontweight="bold")
    ax.invert_yaxis()

    plot_title = title or f"SHAP Summary Beeswarm Distribution (N={N} Observations)"
    ax.set_title(plot_title, fontsize=13, fontweight="bold", pad=15)
    ax.set_xlabel("SHAP Attribution Force Δf(X) [Dimensionless Anomaly Delta]", fontsize=10.5, labelpad=10)

    # Add colorbar
    cbar = plt.colorbar(scatter, ax=ax, orientation="vertical", pad=0.02, fraction=0.03)
    cbar.set_ticks([0.0, 1.0])
    cbar.set_ticklabels(["Low (Nominal)", "High (Deviated)"])
    cbar.set_label("Feature Value (Standardized)", fontsize=9.5, fontweight="bold")

    ax.grid(axis="x", linestyle="--", alpha=0.4)
    plt.tight_layout()

    plt.savefig(save_path, bbox_inches="tight")
    plt.close(fig)
    return save_path

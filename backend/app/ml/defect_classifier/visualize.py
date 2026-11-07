"""
ManuMind AI — ResNet Defect Classifier Visualization Suite
Department of AI & Data Science — RMK Engineering College

Generates 300 DPI publication-grade figures:
1. training_curves.png: Epoch loss & accuracy trajectories with best-checkpoint marker.
2. confusion_matrix.png: 4x4 normalized contingency heatmap with counts & percentages.
3. roc_curves.png: Multi-class One-vs-Rest ROC curves with per-class and macro AUC.
4. sample_predictions_grid.png: Workpiece visual grid with confidence percentages.
"""

import os
import tempfile
from typing import Any, Dict, List, Optional, Tuple

# Enforce writable matplotlib cache before importing pyplot
os.environ.setdefault("MPLCONFIGDIR", tempfile.gettempdir())

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from backend.app.ml.defect_classifier.config import (
    CLASS_DISPLAY_NAMES,
    CLASS_NAMES,
    INT_TO_LABEL,
    DefectClassifierConfig,
)
from backend.app.ml.defect_classifier.dataset import (
    load_manifest,
    load_partition_arrays,
)


def plot_training_curves(
    history: Dict[str, List[float]],
    output_path: str,
    dpi: int = 300
) -> str:
    """Plot training and validation loss and accuracy curves."""
    epochs = range(1, len(history["loss"]) + 1)
    val_losses = history.get("val_loss", [])
    best_epoch = int(np.argmin(val_losses)) + 1 if val_losses else 1

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5), dpi=dpi)

    # Subplot 1: Loss
    ax1.plot(epochs, history["loss"], "o-", color="#2563eb", linewidth=2, label="Train Loss", markersize=4)
    if "val_loss" in history:
        ax1.plot(epochs, history["val_loss"], "s-", color="#dc2626", linewidth=2, label="Val Loss", markersize=4)
        ax1.axvline(best_epoch, color="#16a34a", linestyle="--", linewidth=1.5,
                    label=f"Best Checkpoint (Epoch {best_epoch})")
        ax1.scatter([best_epoch], [val_losses[best_epoch - 1]], color="#16a34a", s=80, zorder=5)

    ax1.set_title("Categorical Cross-Entropy Loss (Label Smoothing = 0.05)", fontsize=12, fontweight="bold", pad=10)
    ax1.set_xlabel("Epoch", fontsize=11)
    ax1.set_ylabel("Loss", fontsize=11)
    ax1.grid(True, linestyle=":", alpha=0.6)
    ax1.legend(loc="upper right", frameon=True, facecolor="#ffffff", framealpha=0.9)

    # Subplot 2: Accuracy
    ax2.plot(epochs, history["accuracy"], "o-", color="#2563eb", linewidth=2, label="Train Accuracy", markersize=4)
    if "val_accuracy" in history:
        ax2.plot(epochs, history["val_accuracy"], "s-", color="#dc2626", linewidth=2, label="Val Accuracy", markersize=4)
        val_accs = history["val_accuracy"]
        best_acc = val_accs[best_epoch - 1]
        ax2.axvline(best_epoch, color="#16a34a", linestyle="--", linewidth=1.5,
                    label=f"Val Acc at Best: {best_acc:.2%}")
        ax2.scatter([best_epoch], [best_acc], color="#16a34a", s=80, zorder=5)

    ax2.set_title("Classification Accuracy Trajectory", fontsize=12, fontweight="bold", pad=10)
    ax2.set_xlabel("Epoch", fontsize=11)
    ax2.set_ylabel("Accuracy", fontsize=11)
    ax2.set_ylim(-0.02, 1.05)
    ax2.grid(True, linestyle=":", alpha=0.6)
    ax2.legend(loc="lower right", frameon=True, facecolor="#ffffff", framealpha=0.9)

    plt.suptitle("Compact ResNet-18 Defect Classifier — Training Convergence",
                 fontsize=14, fontweight="bold", y=1.02)
    plt.tight_layout()

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.savefig(output_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    return output_path


def plot_confusion_matrix(
    cm_dict: Dict[str, Any],
    output_path: str,
    partition_name: str = "Validation",
    dpi: int = 300
) -> str:
    """Plot normalized 4x4 contingency matrix heatmap with counts & percentages."""
    raw = np.array(cm_dict["raw_counts"], dtype=int)
    norm = np.array(cm_dict["normalized_percentages"], dtype=float)
    classes = [CLASS_DISPLAY_NAMES.get(c, c) for c in cm_dict["classes"]]
    n_classes = len(classes)

    fig, ax = plt.subplots(figsize=(8, 7), dpi=dpi)
    cax = ax.imshow(norm, interpolation="nearest", cmap="Blues", vmin=0.0, vmax=1.0)
    cbar = fig.colorbar(cax, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("Classification Rate (Normalized)", fontsize=10)

    # Labels
    tick_marks = np.arange(n_classes)
    ax.set_xticks(tick_marks)
    ax.set_yticks(tick_marks)
    ax.set_xticklabels(classes, rotation=25, ha="right", fontsize=10, fontweight="bold")
    ax.set_yticklabels(classes, fontsize=10, fontweight="bold")

    # Annotate each cell
    thresh = 0.5
    for i in range(n_classes):
        for j in range(n_classes):
            pct_val = norm[i, j]
            count_val = raw[i, j]
            text_color = "white" if pct_val > thresh else "#1e293b"
            cell_text = f"{pct_val:.1%}\n({count_val})"
            ax.text(j, i, cell_text, ha="center", va="center",
                    color=text_color, fontsize=10, fontweight="bold")

    ax.set_title(f"Compact ResNet-18 — {partition_name} Confusion Matrix",
                 fontsize=13, fontweight="bold", pad=15)
    ax.set_ylabel("Ground Truth Class", fontsize=11, fontweight="bold")
    ax.set_xlabel("Predicted Defect Class", fontsize=11, fontweight="bold")
    plt.tight_layout()

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.savefig(output_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    return output_path


def plot_roc_curves(
    roc_dict: Dict[str, Any],
    output_path: str,
    macro_auc: float,
    partition_name: str = "Validation",
    dpi: int = 300
) -> str:
    """Plot multi-class One-vs-Rest ROC curves."""
    fig, ax = plt.subplots(figsize=(8, 7), dpi=dpi)

    colors = {
        "surface_crack": "#dc2626",
        "spalling": "#d97706",
        "dent": "#2563eb",
        "normal_surface": "#16a34a",
    }

    for cname, roc_data in roc_dict.items():
        disp_name = CLASS_DISPLAY_NAMES.get(cname, cname)
        color = colors.get(cname, "#64748b")
        auc_val = roc_data["auc"]
        fpr = roc_data["fpr"]
        tpr = roc_data["tpr"]
        ax.plot(fpr, tpr, color=color, linewidth=2,
                label=f"{disp_name} (AUC = {auc_val:.4f})")

    # Chance baseline
    ax.plot([0, 1], [0, 1], "k--", linewidth=1.2, alpha=0.6, label="Random Chance (AUC = 0.5000)")

    ax.set_title(f"One-vs-Rest ROC Curves — {partition_name} Partition (Macro AUC = {macro_auc:.4f})",
                 fontsize=13, fontweight="bold", pad=15)
    ax.set_xlabel("False Positive Rate (1 - Specificity)", fontsize=11)
    ax.set_ylabel("True Positive Rate (Sensitivity / Recall)", fontsize=11)
    ax.set_xlim([-0.02, 1.02])
    ax.set_ylim([-0.02, 1.05])
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(loc="lower right", frameon=True, facecolor="#ffffff", framealpha=0.9, fontsize=9.5)
    plt.tight_layout()

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.savefig(output_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    return output_path


def plot_sample_predictions_grid(
    records: List[Dict[str, Any]],
    pred_probs: np.ndarray,
    output_path: str,
    repo_root: Optional[str] = None,
    grid_size: Tuple[int, int] = (4, 4),
    dpi: int = 300
) -> str:
    """
    Render 4x4 visual inspection grid showing workpiece images,
    ground-truth annotations, predicted labels, and confidence bars.
    """
    n_display = grid_size[0] * grid_size[1]
    # Sample balanced across classes
    indices_by_class: Dict[str, List[int]] = {c: [] for c in CLASS_NAMES}
    for i, r in enumerate(records):
        indices_by_class[r["defect_type"]].append(i)

    selected_indices: List[int] = []
    samples_per_class = n_display // len(CLASS_NAMES)
    for cname in CLASS_NAMES:
        c_inds = indices_by_class[cname][:samples_per_class]
        selected_indices.extend(c_inds)

    fig, axes = plt.subplots(grid_size[0], grid_size[1], figsize=(14, 14), dpi=dpi)
    axes_flat = axes.flatten()

    for idx, sample_idx in enumerate(selected_indices):
        ax = axes_flat[idx]
        rec = records[sample_idx]
        probs = pred_probs[sample_idx]
        pred_class_idx = int(np.argmax(probs))
        pred_label = INT_TO_LABEL[pred_class_idx]
        conf = float(probs[pred_class_idx])
        true_label = rec["defect_type"]
        is_correct = bool(pred_label == true_label)

        # Load original image for visualization
        from backend.app.ml.defect_classifier.dataset import resolve_image_path
        abs_img_path = resolve_image_path(rec["filepath"], repo_root)
        from PIL import Image
        with Image.open(abs_img_path) as img:
            img_arr = np.array(img.convert("RGB"))

        ax.imshow(img_arr)
        ax.set_xticks([])
        ax.set_yticks([])

        # Color-coded border
        border_color = "#16a34a" if is_correct else "#dc2626"
        for spine in ax.spines.values():
            spine.set_edgecolor(border_color)
            spine.set_linewidth(3.0)

        true_disp = CLASS_DISPLAY_NAMES.get(true_label, true_label)
        pred_disp = CLASS_DISPLAY_NAMES.get(pred_label, pred_label)
        title_text = f"True: {true_disp}\nPred: {pred_disp} ({conf:.1%})"
        ax.set_title(title_text, fontsize=9, fontweight="bold",
                     color="#15803d" if is_correct else "#b91c1c", pad=5)

    plt.suptitle("Workpiece Defect Inspection — Sample Visual Predictions Grid",
                 fontsize=15, fontweight="bold", y=0.99)
    plt.tight_layout()

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.savefig(output_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    return output_path


def generate_all_visualizations(
    results_dict: Dict[str, Any],
    history_dict: Optional[Dict[str, Any]] = None,
    config: Optional[DefectClassifierConfig] = None,
    repo_root: Optional[str] = None
) -> List[str]:
    """Generate the complete set of 4 analytical PNG graphics."""
    if config is None:
        config = DefectClassifierConfig()

    graphs_dir = config.resolve_path(config.graphs_dir)
    os.makedirs(graphs_dir, exist_ok=True)
    generated_files: List[str] = []

    # 1. Training curves
    if history_dict and "loss" in history_dict:
        tc_path = os.path.join(graphs_dir, "training_curves.png")
        plot_training_curves(history_dict, tc_path)
        generated_files.append(tc_path)

    # Determine which metrics partition to plot (Validation or Test)
    target_partition_name = "Test" if "test_metrics" in results_dict else "Validation"
    metrics_to_plot = results_dict.get("test_metrics", results_dict.get("validation_metrics", {}))

    # 2. Confusion matrix
    if "confusion_matrix" in metrics_to_plot:
        cm_path = os.path.join(graphs_dir, "confusion_matrix.png")
        plot_confusion_matrix(metrics_to_plot["confusion_matrix"], cm_path,
                              partition_name=target_partition_name)
        generated_files.append(cm_path)

    # 3. ROC curves
    if "roc_curves" in metrics_to_plot:
        roc_path = os.path.join(graphs_dir, "roc_curves.png")
        plot_roc_curves(metrics_to_plot["roc_curves"], roc_path,
                        macro_auc=metrics_to_plot.get("macro_roc_auc", 1.0),
                        partition_name=target_partition_name)
        generated_files.append(roc_path)

    # 4. Sample predictions grid
    try:
        from keras import models
        model_path = config.resolve_path(config.model_save_path)
        if os.path.exists(model_path):
            model = models.load_model(model_path)
            partitions = load_manifest(
                manifest_path=config.resolve_path(config.manifest_path),
                repo_root=repo_root
            )
            # Use test if evaluated, else val
            eval_split = "test" if "test_metrics" in results_dict else "val"
            recs = partitions[eval_split]
            X, _, _, _ = load_partition_arrays(recs, repo_root=repo_root)
            pred_probs = model.predict(X, batch_size=config.batch_size, verbose=0)
            grid_path = os.path.join(graphs_dir, "sample_predictions_grid.png")
            plot_sample_predictions_grid(recs, pred_probs, grid_path, repo_root=repo_root)
            generated_files.append(grid_path)
    except Exception as e:
        print(f"[Visualize] Warning: Sample grid generation skipped: {e}")

    return generated_files

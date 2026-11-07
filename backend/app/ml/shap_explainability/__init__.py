"""
ManuMind AI — Isolation Forest SHAP Explainability Package
Department of AI & Data Science — RMK Engineering College

Public exports for Kernel SHAP model explainability.
"""

from backend.app.ml.shap_explainability.config import (
    ShapExplainerConfig,
    FEATURE_COLUMNS,
    FEATURE_UNITS,
    STRATIFIED_MACHINE_IDS,
    SAMPLES_PER_MACHINE,
    TOTAL_BACKGROUND_SAMPLES,
    RANDOM_SEED,
    SHAP_NSAMPLES,
    ADDITIVITY_TOLERANCE,
    ATTRIBUTION_UNITS
)
from backend.app.ml.shap_explainability.explainer import IsolationForestShapExplainer
from backend.app.ml.shap_explainability.visualize import (
    plot_waterfall,
    plot_global_feature_importance,
    plot_beeswarm
)
from backend.app.ml.shap_explainability.evaluate import ShapEvaluationPipeline

__all__ = [
    "ShapExplainerConfig",
    "IsolationForestShapExplainer",
    "ShapEvaluationPipeline",
    "FEATURE_COLUMNS",
    "FEATURE_UNITS",
    "STRATIFIED_MACHINE_IDS",
    "SAMPLES_PER_MACHINE",
    "TOTAL_BACKGROUND_SAMPLES",
    "RANDOM_SEED",
    "SHAP_NSAMPLES",
    "ADDITIVITY_TOLERANCE",
    "ATTRIBUTION_UNITS",
    "plot_waterfall",
    "plot_global_feature_importance",
    "plot_beeswarm"
]

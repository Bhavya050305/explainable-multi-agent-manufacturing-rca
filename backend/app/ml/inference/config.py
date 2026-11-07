"""
ManuMind AI — Unified Inference Service Configuration
Department of AI & Data Science — RMK Engineering College

Centralizes canonical feature ordering, frozen decision thresholds, artifact paths,
cryptographic baseline hashes, model identifiers, and timeout semantics.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

# Root directory resolution
INFERENCE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = INFERENCE_DIR.parent.parent.parent
BASE_DIR = BACKEND_DIR.parent
MODELS_STORE_DIR = BASE_DIR / "ml" / "models_store"

# Canonical feature ordering: Strictly enforced and permutation-resistant
CANONICAL_FEATURES: List[str] = [
    "vibration",
    "temperature",
    "pressure",
    "current",
    "rpm"
]

FEATURE_UNITS: Dict[str, str] = {
    "vibration": "mm/s",
    "temperature": "°C",
    "pressure": "bar",
    "current": "A",
    "rpm": "RPM"
}

SEQUENCE_LENGTH: int = 30
N_FEATURES: int = 5

# Frozen Decision Thresholds (Derived during validation calibration; strictly immutable)
ISOLATION_FOREST_FROZEN_THRESHOLD: float = 0.0269
LSTM_AUTOENCODER_FROZEN_THRESHOLD: float = 0.901464

# Workpiece Vision Defect Classes
DEFECT_CLASSES: List[str] = [
    "normal_surface",
    "dent",
    "surface_crack",
    "spalling"
]

CLASS_DISPLAY_NAMES: Dict[str, str] = {
    "normal_surface": "Normal Surface",
    "dent": "Surface Dent",
    "surface_crack": "Surface Micro-Crack",
    "spalling": "Surface Spalling / Pitting"
}

DEFECT_RECOMMENDATIONS: Dict[str, str] = {
    "normal_surface": "Component verified healthy. Normal operation authorized.",
    "dent": "Mechanical impact suspected. Inspect workpiece alignment and fixturing.",
    "surface_crack": "Thermal/cyclic fatigue suspected. Initiate NDT dye-penetrant inspection immediately.",
    "spalling": "Advanced subsurface fatigue / severe shear wear. Replace tooling/insert immediately."
}

# Model Identifiers
MODEL_ID_IF: str = "isolation_forest_v1"
MODEL_ID_LSTM: str = "lstm_autoencoder_v1"
MODEL_ID_RESNET: str = "compact_resnet18_v1"
MODEL_ID_SHAP: str = "shap_kernel_explainer_v1"
MODEL_ID_ATTRIBUTION: str = "lstm_mse_attribution_v1"

# Cryptographically Verified Baseline SHA-256 Hashes
EXPECTED_ARTIFACT_HASHES: Dict[str, str] = {
    "sensor_scaler.joblib": "f21f0899cd3af4d807e54f98b4627d5512650f08cad35ba17a6cd80268398faf",
    "isolation_forest.joblib": "afdf397336f01cfe32c6d4660b3f0094bec01869ab3f8ec276a4d34ca8ac52a2",
    "isolation_forest_metadata.json": "bbb05f4447d52c5ae0f4444649e2e59bf5f282aceb1cfd028e6309b86e8ed3d5",
    "lstm_autoencoder.keras": "b1cae16de57b556f13b3f96e12a8c451d05f3bdd9887a65172817cd99e30e0b5",
    "lstm_autoencoder_metadata.json": "d679e55a2b9935c2e8820d5b117a7c8fc8f84b94cd6565252255168f82fda0c1",
    "resnet_defect_classifier.keras": "aac4b1c2d8c7ba47cef2e31b73d27ad6ff9b8be9352d6e3850c2e201e3195a98",
    "resnet_defect_classifier_metadata.json": "e7e95b8037efceade0a8d19d0a14ecff86868d887e081ac306d1cb36573c8d73",
}


@dataclass
class InferenceConfig:
    """Configuration container for the Unified Inference Service."""
    models_dir: Path = MODELS_STORE_DIR
    base_dir: Path = BASE_DIR
    canonical_features: List[str] = field(default_factory=lambda: list(CANONICAL_FEATURES))
    sequence_length: int = SEQUENCE_LENGTH
    n_features: int = N_FEATURES

    # Thresholds
    if_threshold: float = ISOLATION_FOREST_FROZEN_THRESHOLD
    lstm_threshold: float = LSTM_AUTOENCODER_FROZEN_THRESHOLD

    # Timeouts (Request deadlines in seconds)
    default_inference_timeout: float = 10.0
    shap_timeout: float = 30.0

    # Image shape for Defect Classifier
    image_shape: tuple = (128, 128, 3)

    # Hashes
    expected_hashes: Dict[str, str] = field(default_factory=lambda: dict(EXPECTED_ARTIFACT_HASHES))

    def resolve_artifact_path(self, filename: str) -> Path:
        """Resolves full filesystem path for a model store artifact."""
        return self.models_dir / filename

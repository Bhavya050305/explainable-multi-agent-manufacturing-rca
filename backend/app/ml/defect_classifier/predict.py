"""
ManuMind AI — ResNet Defect Classifier Inference Service
Department of AI & Data Science — RMK Engineering College

Provides real-time single-image and batch inference for visual defect inspection.
Compatible with backend Pydantic DefectInspectionResponse schema.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
from PIL import Image
import tensorflow as tf
from keras import models, Model

from backend.app.ml.defect_classifier.config import (
    CLASS_DISPLAY_NAMES,
    CLASS_NAMES,
    INT_TO_LABEL,
    LABEL_TO_INT,
    MACHINE_BATCH_LOOKUP,
    RECOMMENDATIONS,
    DefectClassifierConfig,
)
from backend.app.ml.defect_classifier.dataset import load_single_image


class DefectClassifierInferenceService:
    """
    Production inference service wrapping the trained Compact ResNet-18 model.
    Accepts filepaths, PIL Images, or raw numpy tensors and returns
    structured defect diagnoses compatible with DefectInspectionResponse.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        config: Optional[DefectClassifierConfig] = None
    ) -> None:
        self.config = config or DefectClassifierConfig()
        if model_path is None:
            model_path = self.config.resolve_path(self.config.model_save_path)
        elif not os.path.isabs(model_path):
            model_path = self.config.resolve_path(model_path)

        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Defect classifier model artifact not found at: {model_path}. "
                "Ensure model is trained before running inference."
            )

        self.model_path = model_path
        self.model: Model = models.load_model(model_path)
        self.target_shape = (self.config.image_height, self.config.image_width)

    def _preprocess_input(
        self,
        image_input: Union[str, Path, Image.Image, np.ndarray]
    ) -> Tuple[np.ndarray, str]:
        """Convert heterogeneous image inputs into standardized (1, 128, 128, 3) tensor."""
        image_name = "sample_image.bmp"

        if isinstance(image_input, (str, Path)):
            filepath = str(image_input)
            image_name = os.path.basename(filepath)
            norm_arr = load_single_image(filepath, target_shape=self.target_shape)
            return np.expand_dims(norm_arr, axis=0), image_name

        elif isinstance(image_input, Image.Image):
            rgb_img = image_input.convert("RGB")
            if rgb_img.size != (self.target_shape[1], self.target_shape[0]):
                rgb_img = rgb_img.resize(
                    (self.target_shape[1], self.target_shape[0]),
                    Image.Resampling.BILINEAR
                )
            arr = np.array(rgb_img, dtype=np.float32)
            norm_arr = (arr / 127.5) - 1.0
            return np.expand_dims(norm_arr, axis=0), image_name

        elif isinstance(image_input, np.ndarray):
            arr = image_input.astype(np.float32)
            # If shape is (128, 128), replicate to 3 channels
            if arr.ndim == 2:
                arr = np.stack([arr] * 3, axis=-1)
            # If values in [0, 255], normalize to [-1, 1]
            if np.max(arr) > 1.0:
                arr = (arr / 127.5) - 1.0
            if arr.ndim == 3:
                arr = np.expand_dims(arr, axis=0)
            if arr.shape[1:4] != (*self.target_shape, 3):
                raise ValueError(
                    f"Expected tensor shape (1, {self.target_shape[0]}, {self.target_shape[1]}, 3), "
                    f"got {arr.shape}"
                )
            return arr, image_name

        else:
            raise TypeError(f"Unsupported image input type: {type(image_input)}")

    def predict_image(
        self,
        image_input: Union[str, Path, Image.Image, np.ndarray],
        image_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run inference on a single workpiece image.

        Returns dictionary formatted for DefectInspectionResponse schema.
        """
        tensor, detected_name = self._preprocess_input(image_input)
        final_image_name = image_name or detected_name

        # Forward pass
        probs = self.model(tensor, training=False).numpy()[0]
        pred_idx = int(np.argmax(probs))
        defect_class = INT_TO_LABEL[pred_idx]
        confidence = float(probs[pred_idx])

        # Lookup domain attributes
        machine_meta = MACHINE_BATCH_LOOKUP.get(defect_class, {
            "machine_id": "UNKNOWN",
            "batch_number": "UNKNOWN"
        })
        recommendation = RECOMMENDATIONS.get(
            defect_class,
            "Inspect workpiece manually against engineering standards."
        )

        return {
            "image_name": final_image_name,
            "defect_type": CLASS_DISPLAY_NAMES.get(defect_class, defect_class),
            "confidence": round(confidence, 4),
            "affected_machine_id": machine_meta["machine_id"],
            "batch_number": machine_meta["batch_number"],
            "recommendation": recommendation,
            # Diagnostic extensions
            "is_defective": bool(defect_class != "normal_surface"),
            "raw_defect_class": defect_class,
            "class_probabilities": {
                cname: round(float(probs[i]), 4) for i, cname in enumerate(CLASS_NAMES)
            }
        }

    def predict_batch(
        self,
        images: List[Union[str, Path, Image.Image, np.ndarray]]
    ) -> List[Dict[str, Any]]:
        """Run batch inference over a list of images."""
        return [self.predict_image(img) for img in images]

    def to_pydantic(self, result_dict: Dict[str, Any]):
        """Convert output dictionary to backend DefectInspectionResponse Pydantic model."""
        from backend.app.schemas.chat import DefectInspectionResponse
        return DefectInspectionResponse(
            image_name=result_dict["image_name"],
            defect_type=result_dict["defect_type"],
            confidence=result_dict["confidence"],
            affected_machine_id=result_dict.get("affected_machine_id"),
            batch_number=result_dict.get("batch_number"),
            recommendation=result_dict["recommendation"],
        )

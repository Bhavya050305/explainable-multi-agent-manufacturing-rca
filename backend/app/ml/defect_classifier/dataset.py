"""
ManuMind AI — Defect Image Dataset Loader & Augmentation Pipeline
Department of AI & Data Science — RMK Engineering College

Provides manifest-only dataset loading, partition isolation, deterministic
normalization to [-1.0, 1.0], and training-only data augmentation.
"""

import json
import os
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image
import tensorflow as tf
from keras import layers, utils

from backend.app.ml.defect_classifier.config import (
    CLASS_NAMES,
    LABEL_TO_INT,
    DefectClassifierConfig,
)


def resolve_image_path(filepath_from_manifest: str, repo_root: Optional[str] = None) -> str:
    """
    Resolve image filepath specified in manifest to an absolute path.
    Handles mixed Windows/POSIX path separators.
    """
    if repo_root is None:
        cfg = DefectClassifierConfig()
        repo_root = cfg.resolve_path("")

    # Normalize manifest path separators
    clean_rel = filepath_from_manifest.replace("\\", os.sep).replace("/", os.sep)
    abs_path = os.path.normpath(os.path.join(repo_root, clean_rel))
    return abs_path


def load_manifest(
    manifest_path: Optional[str] = None,
    repo_root: Optional[str] = None
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Load authoritative defect image manifest and partition into Train, Val, Test.
    Strictly queries defect_manifest.json and ignores unmanifested disk files.

    Returns:
        Dict with keys 'train', 'val', 'test', each mapping to record dictionaries.
    """
    cfg = DefectClassifierConfig()
    if manifest_path is None:
        manifest_path = cfg.resolve_path(cfg.manifest_path)
    elif not os.path.isabs(manifest_path):
        manifest_path = cfg.resolve_path(manifest_path)

    if not os.path.exists(manifest_path):
        raise FileNotFoundError(f"Defect manifest not found at: {manifest_path}")

    with open(manifest_path, "r", encoding="utf-8") as f:
        records: List[Dict[str, Any]] = json.load(f)

    if len(records) != 600:
        raise ValueError(
            f"Expected exactly 600 manifest records, found {len(records)} in {manifest_path}"
        )

    partitions: Dict[str, List[Dict[str, Any]]] = {
        "train": [],
        "val": [],
        "test": []
    }

    for rec in records:
        split = rec.get("split")
        if split not in partitions:
            raise ValueError(f"Unknown split '{split}' in record: {rec.get('sample_id')}")
        partitions[split].append(rec)

    # Verify partition counts
    if len(partitions["train"]) != 420:
        raise ValueError(f"Expected 420 train records, got {len(partitions['train'])}")
    if len(partitions["val"]) != 88:
        raise ValueError(f"Expected 88 validation records, got {len(partitions['val'])}")
    if len(partitions["test"]) != 92:
        raise ValueError(f"Expected 92 test records, got {len(partitions['test'])}")

    return partitions


def load_single_image(
    image_path: str,
    target_shape: Tuple[int, int] = (128, 128)
) -> np.ndarray:
    """
    Load, resize, and normalize a single BMP/RGB image to [-1.0, 1.0].

    Args:
        image_path: Absolute or relative path to image file.
        target_shape: Expected (height, width).

    Returns:
        np.ndarray of shape (height, width, 3), dtype float32, bounded in [-1.0, 1.0].
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file does not exist: {image_path}")

    with Image.open(image_path) as img:
        img_rgb = img.convert("RGB")
        if img_rgb.size != (target_shape[1], target_shape[0]):
            img_rgb = img_rgb.resize((target_shape[1], target_shape[0]), Image.Resampling.BILINEAR)
        arr = np.array(img_rgb, dtype=np.float32)

    # Scale from [0.0, 255.0] to [-1.0, 1.0]
    norm_arr = (arr / 127.5) - 1.0
    return norm_arr


def load_partition_arrays(
    records: List[Dict[str, Any]],
    repo_root: Optional[str] = None,
    target_shape: Tuple[int, int] = (128, 128)
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, List[Dict[str, Any]]]:
    """
    Load all images and encoded labels for a given partition.

    Args:
        records: List of manifest records for this partition.
        repo_root: Repository root path.
        target_shape: Image (height, width).

    Returns:
        Tuple of:
            X: np.ndarray shape (N, 128, 128, 3), float32 in [-1.0, 1.0]
            y_one_hot: np.ndarray shape (N, 4), float32
            y_int: np.ndarray shape (N,), int32
            records: List of manifest records
    """
    n_samples = len(records)
    X = np.empty((n_samples, target_shape[0], target_shape[1], 3), dtype=np.float32)
    y_int = np.empty((n_samples,), dtype=np.int32)

    for i, rec in enumerate(records):
        filepath = resolve_image_path(rec["filepath"], repo_root)
        X[i] = load_single_image(filepath, target_shape=target_shape)
        defect_type = rec["defect_type"]
        if defect_type not in LABEL_TO_INT:
            raise KeyError(f"Unknown defect type '{defect_type}' in record: {rec}")
        y_int[i] = LABEL_TO_INT[defect_type]

    y_one_hot = utils.to_categorical(y_int, num_classes=len(CLASS_NAMES)).astype(np.float32)
    return X, y_one_hot, y_int, records


def build_augmentation_layer(
    seed: int = 42,
    rotation_factor: float = 15.0 / 360.0,
    brightness_factor: float = 0.08
) -> tf.keras.Sequential:
    """
    Build training-only Keras augmentation pipeline:
    - Random horizontal & vertical flips
    - Random subtle rotation (+/- 15 degrees)
    - Random subtle brightness modulation (+/- 8%) within [-1.0, 1.0]

    Validation and test pipelines remain strictly unaugmented.
    """
    aug = tf.keras.Sequential([
        layers.RandomFlip("horizontal_and_vertical", seed=seed, name="aug_flip"),
        layers.RandomRotation(rotation_factor, fill_mode="nearest", seed=seed, name="aug_rot"),
        layers.RandomBrightness(brightness_factor, value_range=(-1.0, 1.0), seed=seed, name="aug_bright"),
    ], name="data_augmentation")
    return aug


def create_tf_dataset(
    X: np.ndarray,
    y: np.ndarray,
    batch_size: int = 32,
    is_training: bool = False,
    augment_layer: Optional[tf.keras.Sequential] = None,
    shuffle: bool = True,
    seed: int = 42
) -> tf.data.Dataset:
    """
    Construct an optimized tf.data.Dataset from numpy arrays.

    Args:
        X: Feature tensor (N, 128, 128, 3)
        y: Target tensor (N, 4) one-hot
        batch_size: Mini-batch size
        is_training: If True, applies data augmentation and shuffling
        augment_layer: Keras Sequential augmentation layer
        shuffle: Whether to shuffle
        seed: Shuffling seed

    Returns:
        tf.data.Dataset yielding (batch_X, batch_y)
    """
    ds = tf.data.Dataset.from_tensor_slices((X, y))

    if is_training and shuffle:
        ds = ds.shuffle(buffer_size=len(X), seed=seed, reshuffle_each_iteration=True)

    ds = ds.batch(batch_size)

    if is_training and augment_layer is not None:
        ds = ds.map(
            lambda img_batch, lbl_batch: (augment_layer(img_batch, training=True), lbl_batch),
            num_parallel_calls=tf.data.AUTOTUNE
        )

    ds = ds.prefetch(buffer_size=tf.data.AUTOTUNE)
    return ds

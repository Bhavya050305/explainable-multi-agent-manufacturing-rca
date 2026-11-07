"""
ManuMind AI — ResNet Defect Classifier Training Pipeline
Department of AI & Data Science — RMK Engineering College

Executes training from scratch on the 420-sample training partition with:
- Strict seed determinism (seed 42)
- Training-only data augmentation
- Validation-based Early Stopping, LR reduction, and Best-Checkpoint selection
- Freezes the test partition completely (unobserved during training)
"""

import hashlib
import json
import os
import random
import time
from typing import Any, Dict, Optional, Tuple

import numpy as np
import tensorflow as tf
from keras import losses, optimizers, callbacks, Model

from backend.app.ml.defect_classifier.config import (
    CLASS_NAMES,
    DefectClassifierConfig,
)
from backend.app.ml.defect_classifier.dataset import (
    build_augmentation_layer,
    create_tf_dataset,
    load_manifest,
    load_partition_arrays,
)
from backend.app.ml.defect_classifier.model import (
    build_compact_resnet18,
    get_model_parameter_counts,
)


def set_determinism(seed: int = 42) -> None:
    """Enforce reproducibility across all random number generators."""
    random.seed(seed)
    np.random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    tf.keras.utils.set_random_seed(seed)


def compute_file_sha256(filepath: str) -> str:
    """Calculate the cryptographic SHA-256 checksum of a file."""
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest()


def train_defect_classifier(
    config: Optional[DefectClassifierConfig] = None,
    repo_root: Optional[str] = None,
    verbose: int = 1
) -> Tuple[Model, Dict[str, Any], Dict[str, Any]]:
    """
    Train Compact ResNet-18 classifier from scratch on Train partition (N=420)
    and validate on Validation partition (N=88).

    The test partition (N=92) is strictly FROZEN and ignored during this process.

    Returns:
        Tuple of (trained_model, training_history_dict, metadata_dict).
    """
    if config is None:
        config = DefectClassifierConfig()

    set_determinism(config.random_seed)

    # 1. Load Train and Validation partitions strictly from manifest
    partitions = load_manifest(
        manifest_path=config.resolve_path(config.manifest_path),
        repo_root=repo_root
    )

    train_records = partitions["train"]  # 420
    val_records = partitions["val"]      # 88
    # Notice: partitions['test'] is completely omitted from the training pipeline

    if verbose:
        print(f"[Train] Loaded manifest: {len(train_records)} Train, {len(val_records)} Val records.")

    # 2. Ingest image tensors and labels
    X_train, y_train_cat, y_train_int, _ = load_partition_arrays(
        train_records, repo_root=repo_root, target_shape=(config.image_height, config.image_width)
    )
    X_val, y_val_cat, y_val_int, _ = load_partition_arrays(
        val_records, repo_root=repo_root, target_shape=(config.image_height, config.image_width)
    )

    if verbose:
        print(f"[Train] Tensors loaded: X_train {X_train.shape}, X_val {X_val.shape}")
        print(f"[Train] Input value bounds: X_train [{np.min(X_train):.2f}, {np.max(X_train):.2f}], "
              f"X_val [{np.min(X_val):.2f}, {np.max(X_val):.2f}]")

    # 3. Create augmentation layer and tf.data pipelines
    aug_layer = build_augmentation_layer(
        seed=config.random_seed,
        rotation_factor=config.rotation_factor,
        brightness_factor=config.brightness_factor
    ) if config.enable_augmentation else None

    train_ds = create_tf_dataset(
        X_train, y_train_cat,
        batch_size=config.batch_size,
        is_training=True,
        augment_layer=aug_layer,
        shuffle=True,
        seed=config.random_seed
    )

    val_ds = create_tf_dataset(
        X_val, y_val_cat,
        batch_size=config.batch_size,
        is_training=False,
        augment_layer=None,
        shuffle=False,
        seed=config.random_seed
    )

    # 4. Construct Compact ResNet-18 model
    model = build_compact_resnet18(
        input_shape=config.input_shape,
        num_classes=config.num_classes,
        l2_reg=config.l2_reg,
        dropout_rate=config.dropout_rate,
        bn_momentum=config.bn_momentum,
        name="compact_resnet18_scratch"
    )

    param_counts = get_model_parameter_counts(model)
    if verbose:
        print(f"[Model] Compact ResNet-18 created with {param_counts['total_parameters']:,} total parameters "
              f"({param_counts['trainable_parameters']:,} trainable).")

    # 5. Compile with Adam, Label Smoothing Categorical Crossentropy
    loss_fn = losses.CategoricalCrossentropy(
        label_smoothing=config.label_smoothing,
        name="categorical_crossentropy"
    )
    optimizer = optimizers.Adam(learning_rate=config.learning_rate)

    model.compile(
        optimizer=optimizer,
        loss=loss_fn,
        metrics=["accuracy"]
    )

    # 6. Configure Callbacks
    model_save_path = config.resolve_path(config.model_save_path)
    os.makedirs(os.path.dirname(model_save_path), exist_ok=True)

    ckpt_cb = callbacks.ModelCheckpoint(
        filepath=model_save_path,
        monitor="val_loss",
        save_best_only=True,
        mode="min",
        verbose=verbose
    )

    early_stop_cb = callbacks.EarlyStopping(
        monitor="val_loss",
        patience=config.early_stopping_patience,
        restore_best_weights=True,
        mode="min",
        verbose=verbose
    )

    reduce_lr_cb = callbacks.ReduceLROnPlateau(
        monitor="val_loss",
        factor=config.reduce_lr_factor,
        patience=config.reduce_lr_patience,
        min_lr=config.min_lr,
        mode="min",
        verbose=verbose
    )

    cb_list = [ckpt_cb, early_stop_cb, reduce_lr_cb]

    # 7. Execute Training
    start_time = time.time()
    history = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=config.epochs,
        callbacks=cb_list,
        verbose=verbose
    )
    elapsed_training_time = time.time() - start_time

    # Best epoch identification
    val_losses = history.history.get("val_loss", [])
    best_epoch = int(np.argmin(val_losses)) + 1
    best_val_loss = float(val_losses[best_epoch - 1])
    best_val_acc = float(history.history.get("val_accuracy", [0.0])[best_epoch - 1])

    if verbose:
        print(f"[Train] Training finished in {elapsed_training_time:.2f}s. "
              f"Best epoch: {best_epoch}/{len(val_losses)} with val_loss={best_val_loss:.4f}, val_acc={best_val_acc:.4f}")

    # Re-verify saved model on disk
    if not os.path.exists(model_save_path):
        # Fallback save if checkpoint didn't trigger for any reason
        model.save(model_save_path)

    model_sha256 = compute_file_sha256(model_save_path)

    # 8. Assemble Metadata
    clean_history = {
        k: [float(v_val) for v_val in v] for k, v in history.history.items()
    }

    metadata = {
        "model_name": "compact_resnet18_scratch",
        "architecture": {
            "type": "Compact ResNet-18",
            "stem_filters": config.stem_filters,
            "stage_channels": config.stage_channels,
            "stage_blocks": config.stage_blocks,
            "input_shape": list(config.input_shape),
            "num_classes": config.num_classes,
            "parameters": param_counts,
        },
        "hyperparameters": {
            "learning_rate": config.learning_rate,
            "batch_size": config.batch_size,
            "epochs_requested": config.epochs,
            "epochs_completed": len(val_losses),
            "best_epoch": best_epoch,
            "l2_reg": config.l2_reg,
            "dropout_rate": config.dropout_rate,
            "label_smoothing": config.label_smoothing,
            "random_seed": config.random_seed,
            "early_stopping_patience": config.early_stopping_patience,
            "reduce_lr_patience": config.reduce_lr_patience,
        },
        "dataset": {
            "train_samples": len(train_records),
            "val_samples": len(val_records),
            "test_samples_frozen": len(partitions["test"]),
            "classes": CLASS_NAMES,
            "samples_per_class_train": 105,
            "samples_per_class_val": 22,
            "manifest_path": config.manifest_path,
        },
        "training_performance": {
            "elapsed_seconds": round(elapsed_training_time, 2),
            "best_val_loss": round(best_val_loss, 6),
            "best_val_accuracy": round(best_val_acc, 6),
            "final_lr": float(clean_history.get("learning_rate", [config.learning_rate])[-1]),
        },
        "history": clean_history,
        "artifact": {
            "model_path": config.model_save_path,
            "sha256": model_sha256,
        }
    }

    metadata_save_path = config.resolve_path(config.metadata_save_path)
    os.makedirs(os.path.dirname(metadata_save_path), exist_ok=True)
    with open(metadata_save_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    if verbose:
        print(f"[Train] Model saved to {model_save_path} (SHA-256: {model_sha256[:16]}...)")
        print(f"[Train] Metadata saved to {metadata_save_path}")

    return model, clean_history, metadata


if __name__ == "__main__":
    train_defect_classifier(verbose=1)

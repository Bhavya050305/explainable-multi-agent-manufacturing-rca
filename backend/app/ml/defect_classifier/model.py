"""
ManuMind AI — ResNet Defect Classifier Functional Architecture Factory
Department of AI & Data Science — RMK Engineering College

Implements custom Compact ResNet-18 trained from scratch (weights=None)
with L2 kernel regularization, Batch Normalization, and Dropout.

Total Parameters: 2,804,708 (2,799,908 trainable, 4,800 non-trainable BN)
"""

from typing import Dict, List, Optional, Tuple

import tensorflow as tf
from keras import layers, regularizers, Model


def residual_basic_block(
    x: tf.Tensor,
    filters: int,
    stride: int = 1,
    reg: Optional[regularizers.Regularizer] = None,
    stage_idx: int = 1,
    block_idx: int = 1,
    bn_momentum: float = 0.85
) -> tf.Tensor:
    """
    Standard ResNet BasicBlock:
        x -> Conv3x3 (stride) -> BN -> ReLU -> Conv3x3 (stride=1) -> BN -> Add(shortcut) -> ReLU

    Projection shortcut with Conv1x1 (stride) -> BN applied when dimension or stride changes.
    """
    shortcut = x
    in_channels = x.shape[-1]

    # Projection shortcut if spatial dimensions decrease or channel count changes
    if stride != 1 or in_channels != filters:
        shortcut = layers.Conv2D(
            filters=filters,
            kernel_size=1,
            strides=stride,
            padding="same",
            use_bias=False,
            kernel_regularizer=reg,
            name=f"stage{stage_idx}_b{block_idx}_proj_conv"
        )(shortcut)
        shortcut = layers.BatchNormalization(
            momentum=bn_momentum,
            name=f"stage{stage_idx}_b{block_idx}_proj_bn"
        )(shortcut)

    # First Conv3x3
    y = layers.Conv2D(
        filters=filters,
        kernel_size=3,
        strides=stride,
        padding="same",
        use_bias=False,
        kernel_regularizer=reg,
        name=f"stage{stage_idx}_b{block_idx}_conv1"
    )(x)
    y = layers.BatchNormalization(
        momentum=bn_momentum,
        name=f"stage{stage_idx}_b{block_idx}_bn1"
    )(y)
    y = layers.ReLU(
        name=f"stage{stage_idx}_b{block_idx}_relu1"
    )(y)

    # Second Conv3x3
    y = layers.Conv2D(
        filters=filters,
        kernel_size=3,
        strides=1,
        padding="same",
        use_bias=False,
        kernel_regularizer=reg,
        name=f"stage{stage_idx}_b{block_idx}_conv2"
    )(y)
    y = layers.BatchNormalization(
        momentum=bn_momentum,
        name=f"stage{stage_idx}_b{block_idx}_bn2"
    )(y)

    # Residual addition and activation
    out = layers.Add(
        name=f"stage{stage_idx}_b{block_idx}_add"
    )([shortcut, y])
    out = layers.ReLU(
        name=f"stage{stage_idx}_b{block_idx}_relu2"
    )(out)

    return out


def build_compact_resnet18(
    input_shape: Tuple[int, int, int] = (128, 128, 3),
    num_classes: int = 4,
    l2_reg: float = 1e-4,
    dropout_rate: float = 0.35,
    bn_momentum: float = 0.85,
    name: str = "compact_resnet18"
) -> Model:
    """
    Build Compact ResNet-18 architecture with stage channels [32, 64, 128, 256].
    Specifically sized for small manufacturing image cohorts (N=420 training).

    Total Parameters: 2,804,708 (2,799,908 trainable).
    """
    reg = regularizers.l2(l2_reg) if l2_reg > 0 else None
    inputs = layers.Input(shape=input_shape, name="workpiece_image_input")

    # Stem: 7x7 Conv, stride 2, 32 filters -> BN -> ReLU -> 3x3 MaxPool, stride 2
    x = layers.Conv2D(
        filters=32,
        kernel_size=7,
        strides=2,
        padding="same",
        use_bias=False,
        kernel_regularizer=reg,
        name="stem_conv"
    )(inputs)
    x = layers.BatchNormalization(momentum=bn_momentum, name="stem_bn")(x)
    x = layers.ReLU(name="stem_relu")(x)
    x = layers.MaxPooling2D(pool_size=3, strides=2, padding="same", name="stem_pool")(x)

    # Residual Stages: [2, 2, 2, 2] blocks with channels [32, 64, 128, 256]
    stage_channels = [32, 64, 128, 256]
    stage_strides = [1, 2, 2, 2]

    for s_idx, (filters, stride) in enumerate(zip(stage_channels, stage_strides)):
        for b_idx in range(2):
            block_stride = stride if b_idx == 0 else 1
            x = residual_basic_block(
                x,
                filters=filters,
                stride=block_stride,
                reg=reg,
                stage_idx=s_idx + 1,
                block_idx=b_idx + 1,
                bn_momentum=bn_momentum
            )

    # Head: Global Average Pooling -> Dropout -> Dense(num_classes, softmax)
    x = layers.GlobalAveragePooling2D(name="global_avg_pool")(x)
    if dropout_rate > 0.0:
        x = layers.Dropout(rate=dropout_rate, name="head_dropout")(x)
    outputs = layers.Dense(
        units=num_classes,
        activation="softmax",
        kernel_regularizer=reg,
        name="classification_head"
    )(x)

    model = Model(inputs=inputs, outputs=outputs, name=name)
    return model


def build_standard_resnet18(
    input_shape: Tuple[int, int, int] = (128, 128, 3),
    num_classes: int = 4,
    l2_reg: float = 1e-4,
    dropout_rate: float = 0.35,
    bn_momentum: float = 0.85,
    name: str = "standard_resnet18"
) -> Model:
    """
    Build Standard ResNet-18 architecture with stage channels [64, 128, 256, 512].
    Total Parameters: 11,188,164 (11,178,564 trainable).
    """
    reg = regularizers.l2(l2_reg) if l2_reg > 0 else None
    inputs = layers.Input(shape=input_shape, name="workpiece_image_input")

    # Stem: 7x7 Conv, stride 2, 64 filters
    x = layers.Conv2D(
        filters=64,
        kernel_size=7,
        strides=2,
        padding="same",
        use_bias=False,
        kernel_regularizer=reg,
        name="stem_conv"
    )(inputs)
    x = layers.BatchNormalization(momentum=bn_momentum, name="stem_bn")(x)
    x = layers.ReLU(name="stem_relu")(x)
    x = layers.MaxPooling2D(pool_size=3, strides=2, padding="same", name="stem_pool")(x)

    stage_channels = [64, 128, 256, 512]
    stage_strides = [1, 2, 2, 2]

    for s_idx, (filters, stride) in enumerate(zip(stage_channels, stage_strides)):
        for b_idx in range(2):
            block_stride = stride if b_idx == 0 else 1
            x = residual_basic_block(
                x,
                filters=filters,
                stride=block_stride,
                reg=reg,
                stage_idx=s_idx + 1,
                block_idx=b_idx + 1,
                bn_momentum=bn_momentum
            )

    x = layers.GlobalAveragePooling2D(name="global_avg_pool")(x)
    if dropout_rate > 0.0:
        x = layers.Dropout(rate=dropout_rate, name="head_dropout")(x)
    outputs = layers.Dense(
        units=num_classes,
        activation="softmax",
        kernel_regularizer=reg,
        name="classification_head"
    )(x)

    model = Model(inputs=inputs, outputs=outputs, name=name)
    return model


def get_model_parameter_counts(model: Model) -> Dict[str, int]:
    """Calculate exact total, trainable, and non-trainable parameter counts."""
    total_params = model.count_params()
    trainable_params = sum(p.numpy().size for p in model.trainable_variables)
    non_trainable_params = total_params - trainable_params
    return {
        "total_parameters": int(total_params),
        "trainable_parameters": int(trainable_params),
        "non_trainable_parameters": int(non_trainable_params),
    }

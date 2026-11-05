"""
ManuMind AI — LSTM Autoencoder Model Architecture
Department of AI & Data Science — RMK Engineering College

Encoder-Decoder architecture for multivariate temporal sequence reconstruction.
Input: (batch_size, 30, 5) -> Latent representation (32) -> Output: (batch_size, 30, 5)
"""

import os
from typing import Tuple, List

import keras
from keras import layers


def build_lstm_autoencoder(
    input_shape: Tuple[int, int] = (30, 5),
    encoder_units: List[int] = None,
    decoder_units: List[int] = None,
    learning_rate: float = 0.001
) -> keras.Model:
    """
    Builds and compiles an LSTM Encoder-Decoder Autoencoder for multivariate sequence reconstruction.
    """
    if encoder_units is None:
        encoder_units = [64, 32]
    if decoder_units is None:
        decoder_units = [32, 64]

    timesteps, n_features = input_shape

    # Input Layer
    inputs = layers.Input(shape=input_shape, name="sequence_input")

    # Encoder
    x = layers.LSTM(
        encoder_units[0],
        activation="tanh",
        return_sequences=True,
        name="encoder_lstm_1"
    )(inputs)
    x = layers.Dropout(0.1, name="encoder_dropout_1")(x)

    # Latent bottleneck representation
    latent = layers.LSTM(
        encoder_units[1],
        activation="tanh",
        return_sequences=False,
        name="encoder_lstm_2_latent"
    )(x)

    # Decoder: Repeat latent vector across sequence timesteps
    x = layers.RepeatVector(timesteps, name="repeat_vector")(latent)

    x = layers.LSTM(
        decoder_units[0],
        activation="tanh",
        return_sequences=True,
        name="decoder_lstm_1"
    )(x)
    x = layers.Dropout(0.1, name="decoder_dropout_1")(x)

    x = layers.LSTM(
        decoder_units[1],
        activation="tanh",
        return_sequences=True,
        name="decoder_lstm_2"
    )(x)

    # Output Layer: TimeDistributed Dense to reconstruct 5 sensor features per timestep
    outputs = layers.TimeDistributed(
        layers.Dense(n_features),
        name="reconstructed_sequence"
    )(x)

    model = keras.Model(inputs=inputs, outputs=outputs, name="LSTM_Autoencoder_ManuMind")

    # Compile with Adam optimizer and Mean Squared Error loss
    optimizer = keras.optimizers.Adam(learning_rate=learning_rate)
    model.compile(optimizer=optimizer, loss="mse", metrics=["mae"])

    return model

"""
ManuMind AI - Enhanced Defect Image Generator
Generates high-fidelity 24-bit bitmap test samples for industrial quality inspection
with labeled defect categories (surface_crack, spalling, dent, normal_surface)
scaled to ~600 images (150 per class) with leak-free Train/Val/Test partitions.
"""

import argparse
import json
import math
import os
import random
import struct
from typing import List, Dict, Tuple


def create_bmp_file(width: int, height: int, pixels: List[List[Tuple[int, int, int]]], output_path: str):
    """
    Pure Python 24-bit uncompressed BMP image writer.
    Generates standard valid binary image files without external dependencies.
    """
    row_bytes = width * 3
    pad = (4 - (row_bytes % 4)) % 4
    row_stride = row_bytes + pad
    image_data_size = row_stride * height
    file_size = 54 + image_data_size

    # BMP Header (14 bytes)
    header = b'BM' + struct.pack('<IHHI', file_size, 0, 0, 54)
    # DIB Header - BITMAPINFOHEADER (40 bytes)
    dib = struct.pack('<IIIHHIIIIII', 40, width, height, 1, 24, 0, image_data_size, 2835, 2835, 0, 0)

    data = bytearray()
    for y in reversed(range(height)):
        for x in range(width):
            r, g, b = pixels[y][x]
            r = max(0, min(255, int(r)))
            g = max(0, min(255, int(g)))
            b = max(0, min(255, int(b)))
            data.extend([b, g, r])
        data.extend([0] * pad)

    with open(output_path, "wb") as f:
        f.write(header + dib + data)


def generate_defect_sample(defect_type: str, width: int = 128, height: int = 128, seed: int = 42) -> List[List[Tuple[int, int, int]]]:
    """
    Render realistic synthetic metallic surface texture and inject class-specific defect morphologies.
    Variations:
    - Background: Machined grain frequency, surface roughness level, subtle directional lighting.
    - Defect location, orientation, scale, depth, and edge transitions.
    """
    rng = random.Random(seed)

    # Base metallic background texture (brushed steel gray ~ 180-210)
    grain_period = rng.uniform(0.2, 0.6)
    base_luminance = rng.randint(188, 202)
    lighting_tilt = rng.uniform(-0.08, 0.08)

    grid = []
    for y in range(height):
        row = []
        for x in range(width):
            noise = rng.randint(-7, 7)
            grain = int(6 * math.sin(x * grain_period))
            tilt = int(lighting_tilt * (x + y - width))
            val = base_luminance + noise + grain + tilt
            row.append((val, val, val))
        grid.append(row)

    if defect_type == "surface_crack":
        # Jagged branched crack propagating through workpiece surface
        start_x = rng.randint(20, width - 40)
        curr_x = float(start_x)
        start_y = rng.randint(15, 30)
        length = rng.randint(45, 80)
        angle_bias = rng.uniform(-0.4, 0.4)
        branch_at = rng.randint(25, 40)
        has_branch = rng.random() > 0.35

        for i in range(length):
            y = min(height - 1, start_y + i)
            curr_x += angle_bias + rng.choice([-0.8, -0.4, 0.0, 0.4, 0.8])
            cx = max(2, min(width - 3, int(curr_x)))

            # Crack core (very dark)
            grid[y][cx] = (25, 25, 30)
            # Penumbra shadow & micro-spall edge
            if cx + 1 < width:
                grid[y][cx + 1] = (65, 65, 70)
            if cx - 1 >= 0:
                grid[y][cx - 1] = (95, 95, 100)

            # Secondary fork branch
            if has_branch and i >= branch_at:
                bx = max(2, min(width - 3, cx + int((i - branch_at) * 0.7)))
                grid[y][bx] = (40, 40, 45)
                if bx + 1 < width:
                    grid[y][bx + 1] = (85, 85, 90)

    elif defect_type == "spalling":
        # Cluster of irregular dark pitted craters (fatigue spall on bearing raceway)
        center_x = rng.randint(35, width - 35)
        center_y = rng.randint(35, height - 35)
        num_pits = rng.randint(20, 45)
        cluster_spread = rng.uniform(8.0, 16.0)

        for _ in range(num_pits):
            px = center_x + int(rng.gauss(0, cluster_spread))
            py = center_y + int(rng.gauss(0, cluster_spread))
            if 0 <= px < width and 0 <= py < height:
                radius = rng.randint(2, 6)
                pit_depth = rng.randint(25, 65)
                for dy in range(-radius, radius + 1):
                    for dx in range(-radius, radius + 1):
                        nx, ny = px + dx, py + dy
                        if 0 <= nx < width and 0 <= ny < height and dx*dx + dy*dy <= radius*radius:
                            fade = math.sqrt(dx*dx + dy*dy) / radius
                            val = int(pit_depth + fade * (140 - pit_depth))
                            grid[ny][nx] = (val, val + 4, val + 7)

    elif defect_type == "dent":
        # Elliptical mechanical impact dent with shaded crater and raised specular lip
        cx = rng.randint(35, width - 35)
        cy = rng.randint(35, height - 35)
        rx = rng.randint(15, 28)
        ry = rng.randint(12, 24)
        depth_scale = rng.uniform(80, 130)

        for y in range(height):
            for x in range(width):
                dist = ((x - cx) ** 2) / (rx ** 2) + ((y - cy) ** 2) / (ry ** 2)
                if dist <= 1.0:
                    shadow = (1.0 - math.sqrt(dist)) * depth_scale
                    val = max(15, int(base_luminance - shadow))
                    grid[y][x] = (val, val, val + 4)
                elif 1.0 < dist <= 1.28:
                    # Raised plastic deformation rim (specular reflection)
                    highlight = int(242 + rng.randint(0, 10))
                    grid[y][x] = (min(255, highlight), min(255, highlight), min(255, highlight + 3))

    elif defect_type == "normal_surface":
        # Pristine machined ground surface with nominal uniform grain
        pass

    return grid


def generate_defect_dataset(
    output_dir: str = "data/defect_images",
    num_samples_per_class: int = 150,
    seed: int = 42,
    train_pct: float = 0.70,
    val_pct: float = 0.15,
    test_pct: float = 0.15
) -> List[Dict]:
    """
    Generate scaled defect dataset across 4 classes (~600 images total)
    with strict leak-free Train/Val/Test partitions and complete metadata manifest.
    """
    os.makedirs(output_dir, exist_ok=True)
    classes = ["surface_crack", "spalling", "dent", "normal_surface"]
    manifest = []

    machines_lookup = {
        "surface_crack": ("M104", "B-8821", "Spindle bearing raceway crack candidate"),
        "spalling": ("M104", "B-8821", "Bearing roller fatigue spalling"),
        "dent": ("M102", "B-7740", "Die impact indentation dent"),
        "normal_surface": ("M101", "B-9910", "Nominal workpiece surface finish")
    }

    n_train = int(num_samples_per_class * train_pct)
    n_val = int(num_samples_per_class * val_pct)

    sample_counter = 0
    for cls in classes:
        mach_id, batch_num, desc = machines_lookup[cls]
        for i in range(1, num_samples_per_class + 1):
            # Assign partition
            if i <= n_train:
                split = "train"
            elif i <= n_train + n_val:
                split = "val"
            else:
                split = "test"

            filename = f"{mach_id}_{cls}_{i:03d}.bmp"
            filepath = os.path.join(output_dir, filename)

            # Unique deterministic seed per image
            sample_seed = seed + sample_counter * 53 + i * 17
            pixels = generate_defect_sample(cls, width=128, height=128, seed=sample_seed)
            create_bmp_file(128, 128, pixels, filepath)

            manifest.append({
                "sample_id": f"IMG_{sample_counter:04d}",
                "filename": filename,
                "filepath": filepath,
                "defect_type": cls,
                "split": split,
                "machine_id": mach_id,
                "batch_number": batch_num,
                "description": desc,
                "is_defective": (cls != "normal_surface"),
                "is_synthetic": True,
                "resolution": "128x128",
                "format": "BMP-24bit"
            })
            sample_counter += 1

    manifest_path = os.path.join(output_dir, "defect_manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"[Defect Generator] Generated {len(manifest)} image samples -> {output_dir}")
    print(f"  - Classes: {classes}")
    print(f"  - Per Class: {num_samples_per_class}")
    print(f"  - Train: {sum(1 for m in manifest if m['split'] == 'train')}")
    print(f"  - Val:   {sum(1 for m in manifest if m['split'] == 'val')}")
    print(f"  - Test:  {sum(1 for m in manifest if m['split'] == 'test')}")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic visual defect inspection samples.")
    parser.add_argument("--per-class", type=int, default=150, help="Number of samples per defect class (default: 150 -> 600 total)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--out-dir", type=str, default="data/defect_images", help="Output directory path")
    args = parser.parse_args()

    generate_defect_dataset(output_dir=args.out_dir, num_samples_per_class=args.per_class, seed=args.seed)

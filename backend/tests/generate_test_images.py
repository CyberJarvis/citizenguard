#!/usr/bin/env python3
"""
Test Image Generator for CoastGuardians
Generates synthetic test images for each hazard type.
"""

import os
import sys
from pathlib import Path

# Try to import PIL, provide helpful message if not available
try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("Warning: Pillow not installed. Install with: pip install Pillow")
    print("Generating placeholder metadata files instead of actual images.\n")

import json
import random
from datetime import datetime


# =============================================================================
# CONFIGURATION
# =============================================================================

OUTPUT_DIR = Path(__file__).parent / "fixtures" / "images"

# Color schemes for different hazard types (RGB)
HAZARD_COLORS = {
    "tsunami": {
        "primary": (30, 60, 100),      # Deep ocean blue
        "secondary": (180, 200, 220),   # Foam/spray
        "accent": (50, 80, 120)         # Wave
    },
    "cyclone": {
        "primary": (60, 60, 70),        # Dark storm clouds
        "secondary": (100, 100, 110),   # Lighter clouds
        "accent": (150, 150, 160)       # Rain streaks
    },
    "high_waves": {
        "primary": (50, 100, 150),      # Ocean blue
        "secondary": (200, 220, 240),   # White caps
        "accent": (70, 130, 180)        # Wave body
    },
    "flooded_coastline": {
        "primary": (120, 90, 60),       # Muddy brown water
        "secondary": (80, 130, 80),     # Vegetation
        "accent": (100, 110, 80)        # Mixed debris
    },
    "rip_current": {
        "primary": (60, 120, 180),      # Blue water
        "secondary": (40, 100, 160),    # Darker channel
        "accent": (200, 220, 240)       # Foam lines
    },
    "beached_animal": {
        "primary": (220, 200, 170),     # Sandy beach
        "secondary": (80, 80, 90),      # Animal (whale/dolphin)
        "accent": (70, 130, 180)        # Water edge
    },
    "ship_wreck": {
        "primary": (50, 90, 130),       # Ocean
        "secondary": (100, 80, 60),     # Rusted ship
        "accent": (30, 30, 30)          # Dark hull
    },
    "marine_debris": {
        "primary": (220, 200, 170),     # Beach
        "secondary": (150, 150, 160),   # Plastic debris
        "accent": (100, 180, 100)       # Tangled nets
    },
    "oil_spill": {
        "primary": (50, 90, 130),       # Ocean blue
        "secondary": (20, 20, 25),      # Oil black
        "accent": (80, 60, 100)         # Oil sheen purple
    },
    "other": {
        "primary": (100, 150, 200),     # Generic water
        "secondary": (180, 180, 180),   # Unknown object
        "accent": (220, 200, 170)       # Beach
    }
}

# Image characteristics
IMAGE_SIZES = {
    "standard": (1920, 1080),
    "mobile_portrait": (1080, 1920),
    "mobile_landscape": (1280, 720),
    "square": (1080, 1080),
    "low_res": (640, 480),
    "high_res": (3840, 2160)
}


# =============================================================================
# IMAGE GENERATION FUNCTIONS
# =============================================================================

def create_gradient_background(size: tuple, color1: tuple, color2: tuple) -> Image.Image:
    """Create a gradient background."""
    img = Image.new('RGB', size)
    draw = ImageDraw.Draw(img)

    for y in range(size[1]):
        ratio = y / size[1]
        r = int(color1[0] * (1 - ratio) + color2[0] * ratio)
        g = int(color1[1] * (1 - ratio) + color2[1] * ratio)
        b = int(color1[2] * (1 - ratio) + color2[2] * ratio)
        draw.line([(0, y), (size[0], y)], fill=(r, g, b))

    return img


def add_noise(img: Image.Image, intensity: int = 10) -> Image.Image:
    """Add random noise to image for realism."""
    pixels = img.load()
    width, height = img.size

    for x in range(0, width, 2):
        for y in range(0, height, 2):
            if x < width and y < height:
                r, g, b = pixels[x, y]
                noise = random.randint(-intensity, intensity)
                pixels[x, y] = (
                    max(0, min(255, r + noise)),
                    max(0, min(255, g + noise)),
                    max(0, min(255, b + noise))
                )

    return img


def add_text_overlay(img: Image.Image, text: str, position: str = "bottom") -> Image.Image:
    """Add text overlay to image."""
    draw = ImageDraw.Draw(img)

    # Use default font
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
    except:
        font = ImageFont.load_default()

    # Calculate position
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    if position == "bottom":
        x = (img.width - text_width) // 2
        y = img.height - text_height - 20
    elif position == "top":
        x = (img.width - text_width) // 2
        y = 20
    else:
        x = (img.width - text_width) // 2
        y = (img.height - text_height) // 2

    # Draw text with background
    padding = 5
    draw.rectangle(
        [x - padding, y - padding, x + text_width + padding, y + text_height + padding],
        fill=(0, 0, 0, 128)
    )
    draw.text((x, y), text, fill=(255, 255, 255), font=font)

    return img


def generate_hazard_image(
    hazard_type: str,
    size_name: str = "standard",
    quality: str = "good",
    add_label: bool = True
) -> Image.Image:
    """Generate a test image for a specific hazard type."""

    if not PIL_AVAILABLE:
        return None

    size = IMAGE_SIZES.get(size_name, IMAGE_SIZES["standard"])
    colors = HAZARD_COLORS.get(hazard_type, HAZARD_COLORS["other"])

    # Create base gradient
    img = create_gradient_background(size, colors["primary"], colors["secondary"])
    draw = ImageDraw.Draw(img)

    # Add hazard-specific elements
    if hazard_type == "tsunami":
        # Draw large wave
        for i in range(3):
            y_offset = size[1] // 2 + i * 50
            points = []
            for x in range(0, size[0], 20):
                y = y_offset + int(100 * abs(((x / 100) % 2) - 1))
                points.append((x, y))
            points.extend([(size[0], size[1]), (0, size[1])])
            draw.polygon(points, fill=colors["accent"])

    elif hazard_type == "cyclone":
        # Draw spiral pattern
        center_x, center_y = size[0] // 2, size[1] // 2
        for r in range(50, min(size) // 2, 30):
            draw.arc([center_x - r, center_y - r, center_x + r, center_y + r],
                    0, 270, fill=colors["accent"], width=3)

    elif hazard_type == "high_waves":
        # Draw multiple wave crests
        for wave_num in range(5):
            y_base = size[1] // 3 + wave_num * 80
            for x in range(0, size[0], 10):
                y = y_base + int(30 * ((x / 50) % 2))
                draw.ellipse([x, y, x + 20, y + 40], fill=colors["accent"])

    elif hazard_type == "flooded_coastline":
        # Draw flooded area
        draw.rectangle([0, size[1] // 2, size[0], size[1]], fill=colors["primary"])
        # Add debris
        for _ in range(20):
            x = random.randint(0, size[0])
            y = random.randint(size[1] // 2, size[1])
            draw.rectangle([x, y, x + 10, y + 5], fill=colors["accent"])

    elif hazard_type == "beached_animal":
        # Draw beach and animal shape
        draw.rectangle([0, size[1] * 2 // 3, size[0], size[1]], fill=colors["primary"])
        # Whale shape
        whale_x = size[0] // 3
        whale_y = size[1] * 3 // 4
        draw.ellipse([whale_x, whale_y - 30, whale_x + 200, whale_y + 50], fill=colors["secondary"])

    elif hazard_type == "ship_wreck":
        # Draw tilted ship
        points = [
            (size[0] // 3, size[1] // 2),
            (size[0] * 2 // 3, size[1] // 3),
            (size[0] * 2 // 3, size[1] * 2 // 3),
            (size[0] // 3, size[1] * 2 // 3)
        ]
        draw.polygon(points, fill=colors["secondary"])

    elif hazard_type == "marine_debris":
        # Draw scattered debris
        for _ in range(50):
            x = random.randint(0, size[0])
            y = random.randint(size[1] // 2, size[1])
            debris_size = random.randint(5, 20)
            draw.rectangle([x, y, x + debris_size, y + debris_size // 2],
                          fill=colors["secondary"])

    elif hazard_type == "oil_spill":
        # Draw oil slick
        for _ in range(10):
            x = random.randint(size[0] // 4, size[0] * 3 // 4)
            y = random.randint(size[1] // 4, size[1] * 3 // 4)
            rx = random.randint(50, 150)
            ry = random.randint(30, 80)
            draw.ellipse([x - rx, y - ry, x + rx, y + ry], fill=colors["secondary"])

    elif hazard_type == "rip_current":
        # Draw channel pattern
        channel_x = size[0] // 2
        draw.rectangle([channel_x - 30, 0, channel_x + 30, size[1]], fill=colors["secondary"])
        # Foam lines
        for y in range(0, size[1], 50):
            draw.line([(channel_x - 40, y), (channel_x + 40, y)],
                     fill=colors["accent"], width=3)

    # Add noise for realism
    if quality in ["good", "excellent"]:
        img = add_noise(img, intensity=5)
    elif quality == "poor":
        img = add_noise(img, intensity=30)
        img = img.filter(ImageFilter.BLUR)

    # Add label if requested
    if add_label:
        label = f"TEST: {hazard_type.replace('_', ' ').title()}"
        img = add_text_overlay(img, label)

    return img


def generate_all_hazard_images():
    """Generate test images for all hazard types."""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    generated = []

    for hazard_type in HAZARD_COLORS.keys():
        for size_name in ["standard", "mobile_portrait", "low_res"]:
            for quality in ["good", "poor"]:
                filename = f"{hazard_type}_{size_name}_{quality}.jpg"
                filepath = OUTPUT_DIR / filename

                if PIL_AVAILABLE:
                    img = generate_hazard_image(hazard_type, size_name, quality)
                    if img:
                        img.save(filepath, "JPEG", quality=85)
                        generated.append(str(filepath))
                        print(f"Generated: {filename}")
                else:
                    # Create metadata file instead
                    metadata = {
                        "hazard_type": hazard_type,
                        "size": IMAGE_SIZES.get(size_name),
                        "quality": quality,
                        "generated_at": datetime.now().isoformat(),
                        "note": "Placeholder - Pillow not installed"
                    }
                    meta_path = filepath.with_suffix('.json')
                    with open(meta_path, 'w') as f:
                        json.dump(metadata, f, indent=2)
                    generated.append(str(meta_path))
                    print(f"Generated metadata: {meta_path.name}")

    return generated


def generate_edge_case_images():
    """Generate edge case images for testing."""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    edge_cases = []

    if PIL_AVAILABLE:
        # Very small image
        tiny = Image.new('RGB', (100, 100), (128, 128, 128))
        tiny.save(OUTPUT_DIR / "edge_tiny.jpg")
        edge_cases.append("edge_tiny.jpg")

        # Very large image
        large = Image.new('RGB', (4000, 3000), (100, 150, 200))
        large.save(OUTPUT_DIR / "edge_large.jpg", quality=70)
        edge_cases.append("edge_large.jpg")

        # Black image
        black = Image.new('RGB', (800, 600), (0, 0, 0))
        black.save(OUTPUT_DIR / "edge_black.jpg")
        edge_cases.append("edge_black.jpg")

        # White image
        white = Image.new('RGB', (800, 600), (255, 255, 255))
        white.save(OUTPUT_DIR / "edge_white.jpg")
        edge_cases.append("edge_white.jpg")

        # Heavily blurred
        blurred = generate_hazard_image("tsunami", "standard", "poor", False)
        if blurred:
            blurred = blurred.filter(ImageFilter.GaussianBlur(radius=10))
            blurred.save(OUTPUT_DIR / "edge_blurred.jpg")
            edge_cases.append("edge_blurred.jpg")

        # Very dark
        dark = Image.new('RGB', (800, 600), (20, 20, 25))
        dark.save(OUTPUT_DIR / "edge_dark.jpg")
        edge_cases.append("edge_dark.jpg")

        print(f"Generated {len(edge_cases)} edge case images")
    else:
        # Create metadata for edge cases
        edge_case_specs = [
            ("edge_tiny.json", {"size": (100, 100), "type": "tiny"}),
            ("edge_large.json", {"size": (4000, 3000), "type": "large"}),
            ("edge_black.json", {"size": (800, 600), "type": "black"}),
            ("edge_white.json", {"size": (800, 600), "type": "white"}),
            ("edge_blurred.json", {"size": (1920, 1080), "type": "blurred"}),
            ("edge_dark.json", {"size": (800, 600), "type": "dark"})
        ]

        for filename, spec in edge_case_specs:
            filepath = OUTPUT_DIR / filename
            with open(filepath, 'w') as f:
                json.dump({**spec, "generated_at": datetime.now().isoformat()}, f, indent=2)
            edge_cases.append(filename)

        print(f"Generated {len(edge_cases)} edge case metadata files")

    return edge_cases


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("CoastGuardians Test Image Generator")
    print("=" * 50)
    print(f"Output directory: {OUTPUT_DIR}")
    print()

    # Generate main hazard images
    print("Generating hazard type images...")
    hazard_images = generate_all_hazard_images()
    print(f"Total: {len(hazard_images)} images\n")

    # Generate edge cases
    print("Generating edge case images...")
    edge_images = generate_edge_case_images()
    print()

    # Summary
    print("=" * 50)
    print("Summary:")
    print(f"  Hazard images: {len(hazard_images)}")
    print(f"  Edge cases: {len(edge_images)}")
    print(f"  Total: {len(hazard_images) + len(edge_images)}")
    print(f"\nImages saved to: {OUTPUT_DIR}")

    if not PIL_AVAILABLE:
        print("\nNote: Install Pillow for actual image generation:")
        print("  pip install Pillow")

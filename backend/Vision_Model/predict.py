"""
Vision Model Prediction Module
For backend integration with CoastGuardians hazard classification system.
"""

import json
from pathlib import Path
import numpy as np
import tensorflow as tf

# ---------- CONFIG ----------
# Get the directory where this script is located
SCRIPT_DIR = Path(__file__).resolve().parent

# Use absolute paths relative to the script location
MODEL_PATH = SCRIPT_DIR / "base_model.keras"
THRESH_PATH = SCRIPT_DIR / "thresholds.json"

# Label columns matching the model output order
LABEL_COLS = ['trash', 'oil_spill', 'marine_animal', 'shipwreck', 'clean']

IMG_SIZE = 224
APPLY_DERIVED_CLEAN = True
APPLY_EXIF_TRANSPOSE = True  # Handle mobile image orientation
# ----------------------------

# Global model cache
_loaded_model = None


def load_model_(model_path=None, custom_objects=None):
    """
    Load a Keras model. Uses cached model if already loaded.

    Args:
        model_path: Path to the model file (defaults to MODEL_PATH)
        custom_objects: Custom objects for model loading if needed

    Returns:
        Loaded TensorFlow/Keras model
    """
    global _loaded_model

    if _loaded_model is not None:
        return _loaded_model

    if model_path is None:
        model_path = MODEL_PATH

    model_path_str = str(model_path)
    print(f"Loading Vision Model from: {model_path_str}")

    if not Path(model_path_str).exists():
        raise FileNotFoundError(f"Model file not found: {model_path_str}")

    _loaded_model = tf.keras.models.load_model(model_path_str, compile=False, custom_objects=custom_objects)
    print("Vision Model loaded successfully!")
    return _loaded_model


def load_thresholds_(path=None):
    """
    Load thresholds from JSON file. Falls back to defaults if missing.

    Args:
        path: Path to thresholds.json file

    Returns:
        numpy array of thresholds for each label
    """
    # Default thresholds (from thresholds.json)
    defaults = np.array([0.096, 0.6265, 0.495, 0.005, 0.173], dtype=float)

    if path is None:
        path = THRESH_PATH

    p = Path(path)
    if not p.exists():
        print(f"Thresholds file not found at {p}, using defaults")
        return defaults

    try:
        with open(p, "r") as f:
            d = json.load(f)
        return np.array([float(d[c]) for c in LABEL_COLS], dtype=float)
    except Exception as e:
        print(f"Error loading thresholds: {e}, using defaults")
        return defaults


def apply_exif_transpose(image_path):
    """
    Apply EXIF orientation to image pixels using PIL.

    Mobile devices record images in landscape orientation and use EXIF
    Orientation tag (0x0112) to indicate how the image should be displayed.
    This function burns the rotation into the pixel data.

    Args:
        image_path: Path to the image file

    Returns:
        numpy array of the correctly oriented image (RGB, uint8), or None if failed
    """
    try:
        from PIL import Image, ImageOps

        # Open image with PIL to handle EXIF
        img = Image.open(str(image_path))

        # Apply EXIF transpose - this rotates the pixels based on EXIF orientation
        img = ImageOps.exif_transpose(img)

        # Convert to RGB if needed (handles RGBA, grayscale, etc.)
        if img.mode != 'RGB':
            img = img.convert('RGB')

        # Convert to numpy array
        return np.array(img, dtype=np.uint8)

    except ImportError:
        print("PIL not available for EXIF transpose, using TensorFlow directly")
        return None
    except Exception as e:
        print(f"EXIF transpose failed: {e}, using TensorFlow directly")
        return None


def preprocess_image_(path, img_size=IMG_SIZE):
    """
    Load and preprocess image into model-ready tensor.

    Handles EXIF orientation from mobile devices to ensure images
    are correctly oriented before classification.

    Args:
        path: Path to the image file
        img_size: Target image size (default 224)

    Returns:
        Preprocessed image tensor ready for model input
    """
    # First try EXIF transpose with PIL (handles mobile orientation)
    if APPLY_EXIF_TRANSPOSE:
        img_array = apply_exif_transpose(path)
        if img_array is not None:
            # Convert numpy array to tensor
            img = tf.convert_to_tensor(img_array, dtype=tf.float32)
            img = tf.image.resize(img, (img_size, img_size))
            img = tf.keras.applications.resnet_v2.preprocess_input(img)
            return img

    # Fallback: Use TensorFlow directly (no EXIF handling)
    img_bytes = tf.io.read_file(str(path))

    # Decode JPEG if possible (faster), else fall back
    try:
        img = tf.image.decode_jpeg(img_bytes, channels=3)
    except:
        img = tf.image.decode_image(img_bytes, channels=3, expand_animations=False)

    img = tf.image.resize(img, (img_size, img_size))
    img = tf.cast(img, tf.float32)
    img = tf.keras.applications.resnet_v2.preprocess_input(img)
    return img


def predict(image_path):
    """
    Run prediction on an image and return classification results.

    Args:
        image_path: Path to the image file

    Returns:
        Dictionary with:
        - image: path to the image
        - thresholds: per-class thresholds used
        - probs: per-class probabilities from model
        - preds: per-class binary predictions (0 or 1)
    """
    path = Path(image_path)
    if not path.exists():
        print(f"Image not found: {path}")
        return None

    # Load model (uses cache if already loaded)
    model = load_model_()

    # Load thresholds
    thresholds = load_thresholds_()

    # Preprocess image
    img = preprocess_image_(path)
    batch = tf.expand_dims(img, axis=0)

    # Run prediction
    probs = model.predict(batch, verbose=0).squeeze(0)
    preds = (probs >= thresholds).astype(int)

    # Derived-clean logic: if no hazards detected, set clean=1
    if APPLY_DERIVED_CLEAN:
        hazards = preds[:-1]  # All except 'clean'
        preds[-1] = 1 if not hazards.any() else 0

    # Build result dictionary
    result = {
        "image": str(path),
        "thresholds": dict(zip(LABEL_COLS, thresholds.tolist())),
        "probs": {LABEL_COLS[i]: float(probs[i]) for i in range(len(LABEL_COLS))},
        "preds": {LABEL_COLS[i]: int(preds[i]) for i in range(len(LABEL_COLS))}
    }

    return result


def get_model_info():
    """
    Get information about the Vision Model configuration.

    Returns:
        Dictionary with model configuration details
    """
    return {
        "model_path": str(MODEL_PATH),
        "model_exists": MODEL_PATH.exists(),
        "thresholds_path": str(THRESH_PATH),
        "thresholds_exists": THRESH_PATH.exists(),
        "label_columns": LABEL_COLS,
        "image_size": IMG_SIZE,
        "exif_transpose_enabled": APPLY_EXIF_TRANSPOSE,
        "derived_clean_enabled": APPLY_DERIVED_CLEAN
    }


# For testing when run directly
if __name__ == "__main__":
    print("Vision Model Configuration:")
    print(json.dumps(get_model_info(), indent=2))

    # Test model loading
    try:
        model = load_model_()
        print(f"\nModel loaded: {type(model)}")
        print(f"Model input shape: {model.input_shape}")
        print(f"Model output shape: {model.output_shape}")
    except Exception as e:
        print(f"\nError loading model: {e}")

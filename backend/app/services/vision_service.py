"""
Vision Model Service
Layer 4: Image classification wrapper for the Vision_Model system.
Validates that uploaded images match reported hazard types.

Enhanced with:
- Face detection to reject selfies and portrait images
- Skin tone analysis to detect non-hazard images
- More aggressive "clean" detection when probabilities are low
- Color palette analysis for coastal/marine context
"""

import logging
import os
import sys
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path

from app.models.verification import (
    LayerResult, LayerStatus, LayerName, ImageLayerData,
    VisionClassificationResult
)

logger = logging.getLogger(__name__)


class VisionService:
    """
    Vision Model integration service for image-based hazard validation.

    Wraps the existing Vision_Model/predict.py system to classify
    images and validate against reported hazard types.
    """

    # Hazard types that require image validation
    APPLICABLE_HAZARDS = [
        "Beached Aquatic Animal",
        "Ship Wreck",
        "Plastic Pollution",  # Maps to trash/marine debris
        "Oil Spill",
    ]

    # Mapping from Vision Model output to system hazard types
    VISION_TO_HAZARD_MAP = {
        "trash": ["Plastic Pollution", "Marine Debris"],
        "oil_spill": ["Oil Spill", "Chemical Spill"],
        "marine_animal": ["Beached Aquatic Animal"],
        "shipwreck": ["Ship Wreck"],
        "clean": []  # No hazard detected
    }

    # Reverse mapping: system hazard type to Vision Model class
    HAZARD_TO_VISION_MAP = {
        "Plastic Pollution": "trash",
        "Marine Debris": "trash",
        "Oil Spill": "oil_spill",
        "Chemical Spill": "oil_spill",
        "Beached Aquatic Animal": "marine_animal",
        "Ship Wreck": "shipwreck",
    }

    # Vision Model labels
    LABEL_COLS = ['trash', 'oil_spill', 'marine_animal', 'shipwreck', 'clean']

    def __init__(self):
        """Initialize vision service."""
        self._initialized = False
        self._model = None
        self._thresholds = None
        self._vision_model_path = None
        self._initialize()

    def _initialize(self):
        """Initialize the Vision Model."""
        try:
            # Find the Vision_Model directory
            # It should be at backend/Vision_Model relative to this file
            current_file = Path(__file__).resolve()
            backend_dir = current_file.parent.parent.parent  # app/services -> app -> backend
            self._vision_model_path = backend_dir / "Vision_Model"

            if not self._vision_model_path.exists():
                logger.warning(f"Vision_Model directory not found at {self._vision_model_path}")
                self._initialized = False
                return

            # Add Vision_Model to path for imports
            sys.path.insert(0, str(self._vision_model_path))

            # Load model lazily (will be loaded on first prediction)
            self._initialized = True
            logger.info(f"VisionService initialized. Model path: {self._vision_model_path}")

        except Exception as e:
            logger.error(f"Failed to initialize VisionService: {e}")
            self._initialized = False

    def _load_model_if_needed(self):
        """Lazy load the Keras model."""
        if self._model is not None:
            return True

        try:
            # Use standalone keras for Keras 3.x models (not tf.keras)
            import keras
            logger.info(f"Keras imported successfully (version: {keras.__version__})")

            if not self._initialized or self._vision_model_path is None:
                logger.error("VisionService not initialized - vision_model_path is None")
                return False

            model_path = self._vision_model_path / "base_model.keras"
            logger.info(f"Checking model at: {model_path}")

            if not model_path.exists():
                logger.error(f"Model file not found: {model_path}")
                return False

            logger.info(f"Loading Vision Model from {model_path}...")

            # Suppress TensorFlow warnings during load
            import os
            os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

            # Use standalone keras.models.load_model for Keras 3.x saved models
            self._model = keras.models.load_model(str(model_path), compile=False)
            logger.info(f"Model loaded! Input shape: {self._model.input_shape}, Output shape: {self._model.output_shape}")

            # Load thresholds from the Vision_Model directory
            # First try thresholds.json directly, then model_export subfolder
            thresh_path = self._vision_model_path / "thresholds.json"
            if not thresh_path.exists():
                thresh_path = self._vision_model_path / "model_export" / "thresholds.json"
            self._thresholds = self._load_thresholds(thresh_path)
            logger.info(f"Loaded thresholds from {thresh_path}: {self._thresholds}")

            logger.info("Vision Model loaded successfully and ready for predictions")
            return True

        except ImportError as e:
            logger.error(f"TensorFlow import failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to load Vision Model: {e}", exc_info=True)
            return False

    def _load_thresholds(self, path: Path) -> Dict[str, float]:
        """Load classification thresholds from JSON file."""
        import json
        import numpy as np

        # Default thresholds (updated from thresholds.json)
        defaults = {
            "trash": 0.096,
            "oil_spill": 0.6265,
            "marine_animal": 0.495,
            "shipwreck": 0.005,
            "clean": 0.173
        }

        if not path.exists():
            logger.warning(f"Thresholds file not found, using defaults: {path}")
            return defaults

        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load thresholds: {e}, using defaults")
            return defaults

    def _detect_faces(self, image_path: str) -> Tuple[bool, int, float]:
        """
        Detect faces in image using OpenCV's Haar Cascade classifier.

        Args:
            image_path: Path to the image file

        Returns:
            Tuple of (faces_detected, face_count, face_area_ratio)
        """
        try:
            import cv2
            import numpy as np

            # Read image
            img = cv2.imread(image_path)
            if img is None:
                return False, 0, 0.0

            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Load face cascade classifier
            face_cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            face_cascade = cv2.CascadeClassifier(face_cascade_path)

            # Detect faces
            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30)
            )

            if len(faces) == 0:
                return False, 0, 0.0

            # Calculate face area ratio
            img_area = img.shape[0] * img.shape[1]
            total_face_area = sum(w * h for (x, y, w, h) in faces)
            face_ratio = total_face_area / img_area

            logger.info(f"Face detection: {len(faces)} face(s), area ratio: {face_ratio:.2%}")
            return True, len(faces), face_ratio

        except ImportError:
            logger.warning("OpenCV not available for face detection")
            return False, 0, 0.0
        except Exception as e:
            logger.warning(f"Face detection error: {e}")
            return False, 0, 0.0

    def _analyze_skin_tones(self, image_path: str) -> Tuple[float, bool]:
        """
        Analyze image for skin tone prevalence using HSV color space.

        Selfies and portrait images typically have high skin tone ratios.

        Args:
            image_path: Path to the image file

        Returns:
            Tuple of (skin_ratio, is_likely_portrait)
        """
        try:
            import cv2
            import numpy as np

            # Read image
            img = cv2.imread(image_path)
            if img is None:
                return 0.0, False

            # Convert to HSV
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

            # Define skin tone ranges in HSV
            # Lower and upper bounds for skin tone detection
            lower_skin = np.array([0, 20, 70], dtype=np.uint8)
            upper_skin = np.array([20, 255, 255], dtype=np.uint8)

            # Create mask for skin tones
            mask = cv2.inRange(hsv, lower_skin, upper_skin)

            # Calculate ratio
            total_pixels = img.shape[0] * img.shape[1]
            skin_pixels = cv2.countNonZero(mask)
            skin_ratio = skin_pixels / total_pixels

            # Portrait images typically have 15%+ skin tone
            is_likely_portrait = skin_ratio > 0.15

            logger.info(f"Skin tone analysis: ratio={skin_ratio:.2%}, likely_portrait={is_likely_portrait}")
            return skin_ratio, is_likely_portrait

        except ImportError:
            logger.warning("OpenCV not available for skin tone analysis")
            return 0.0, False
        except Exception as e:
            logger.warning(f"Skin tone analysis error: {e}")
            return 0.0, False

    def _analyze_color_palette(self, image_path: str) -> Dict[str, Any]:
        """
        Analyze image color palette for coastal/marine context.

        Marine hazard images typically contain blues, greens, browns.
        Selfies typically have different color distributions.

        Args:
            image_path: Path to the image file

        Returns:
            Dictionary with color analysis results
        """
        try:
            import cv2
            import numpy as np

            # Read image
            img = cv2.imread(image_path)
            if img is None:
                return {"valid": False}

            # Convert to HSV for color analysis
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

            # Define color ranges for marine context
            # Blue (water)
            lower_blue = np.array([100, 50, 50])
            upper_blue = np.array([130, 255, 255])
            blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)
            blue_ratio = cv2.countNonZero(blue_mask) / (img.shape[0] * img.shape[1])

            # Green/Brown (algae, debris)
            lower_green = np.array([35, 50, 50])
            upper_green = np.array([85, 255, 255])
            green_mask = cv2.inRange(hsv, lower_green, upper_green)
            green_ratio = cv2.countNonZero(green_mask) / (img.shape[0] * img.shape[1])

            # Brown/tan (beach, sand)
            lower_brown = np.array([10, 50, 50])
            upper_brown = np.array([30, 255, 200])
            brown_mask = cv2.inRange(hsv, lower_brown, upper_brown)
            brown_ratio = cv2.countNonZero(brown_mask) / (img.shape[0] * img.shape[1])

            # Dark (oil spill)
            lower_dark = np.array([0, 0, 0])
            upper_dark = np.array([180, 255, 50])
            dark_mask = cv2.inRange(hsv, lower_dark, upper_dark)
            dark_ratio = cv2.countNonZero(dark_mask) / (img.shape[0] * img.shape[1])

            # Coastal context score
            coastal_score = blue_ratio + green_ratio * 0.5 + brown_ratio * 0.3 + dark_ratio * 0.2

            return {
                "valid": True,
                "blue_ratio": blue_ratio,
                "green_ratio": green_ratio,
                "brown_ratio": brown_ratio,
                "dark_ratio": dark_ratio,
                "coastal_score": coastal_score,
                "is_likely_coastal": coastal_score > 0.15
            }

        except ImportError:
            return {"valid": False, "error": "opencv_not_available"}
        except Exception as e:
            return {"valid": False, "error": str(e)}

    def _perform_pre_classification_checks(
        self,
        image_path: str,
        reported_hazard_type: str
    ) -> Optional[LayerResult]:
        """
        Perform pre-classification checks to detect obvious non-hazard images.

        This catches selfies, portraits, and clearly irrelevant images BEFORE
        running the expensive CNN classification.

        Args:
            image_path: Path to the image file
            reported_hazard_type: The hazard type reported by user

        Returns:
            LayerResult if image should be rejected, None to continue with CNN
        """
        rejection_reasons = []
        rejection_score = 0.0

        # Check 1: Face detection
        faces_detected, face_count, face_ratio = self._detect_faces(image_path)
        if faces_detected:
            if face_ratio > 0.10:  # Face covers >10% of image
                rejection_reasons.append(f"Human face detected covering {face_ratio:.1%} of image")
                rejection_score += 0.4
            if face_count >= 2:
                rejection_reasons.append(f"Multiple people detected ({face_count} faces)")
                rejection_score += 0.2

        # Check 2: Skin tone analysis
        skin_ratio, is_portrait = self._analyze_skin_tones(image_path)
        if is_portrait and skin_ratio > 0.20:
            rejection_reasons.append(f"High skin tone ratio ({skin_ratio:.1%}) suggests portrait/selfie")
            rejection_score += 0.3

        # Check 3: Color palette analysis
        color_analysis = self._analyze_color_palette(image_path)
        if color_analysis.get("valid") and not color_analysis.get("is_likely_coastal", True):
            # Low coastal colors suggest non-marine image
            coastal_score = color_analysis.get("coastal_score", 0)
            if coastal_score < 0.05:
                rejection_reasons.append(f"Image lacks coastal/marine color palette (score: {coastal_score:.2%})")
                rejection_score += 0.2

        # If strong rejection indicators, reject early
        if rejection_score >= 0.5 or (faces_detected and face_ratio > 0.15):
            return LayerResult(
                layer_name=LayerName.IMAGE,
                status=LayerStatus.FAIL,
                score=0.0,
                confidence=0.9,
                weight=0.20,
                reasoning=(
                    f"Image rejected: Not a valid {reported_hazard_type} image. "
                    f"Detected issues: {'; '.join(rejection_reasons)}. "
                    f"Please upload a clear photo of the actual hazard."
                ),
                data={
                    "hazard_type": reported_hazard_type,
                    "rejection_type": "pre_classification_check",
                    "faces_detected": faces_detected,
                    "face_count": face_count,
                    "face_area_ratio": face_ratio,
                    "skin_ratio": skin_ratio,
                    "is_portrait": is_portrait,
                    "color_analysis": color_analysis,
                    "rejection_reasons": rejection_reasons,
                    "rejection_score": rejection_score
                },
                processed_at=datetime.now(timezone.utc)
            )

        return None  # Continue with CNN classification

    def _apply_exif_transpose(self, image_path: str) -> Any:
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
            import numpy as np

            # Open image with PIL to handle EXIF
            img = Image.open(image_path)

            # Apply EXIF transpose - this rotates the pixels based on EXIF orientation
            img = ImageOps.exif_transpose(img)

            # Convert to RGB if needed (handles RGBA, grayscale, etc.)
            if img.mode != 'RGB':
                img = img.convert('RGB')

            # Convert to numpy array
            return np.array(img, dtype=np.uint8)

        except Exception as e:
            logger.warning(f"EXIF transpose failed: {e}, using TensorFlow directly")
            return None

    def _preprocess_image(self, image_path: str) -> Any:
        """
        Preprocess image for model input.

        Handles EXIF orientation from mobile devices to ensure images
        are correctly oriented before classification.
        """
        import tensorflow as tf
        import keras

        # First try EXIF transpose with PIL (handles mobile orientation)
        img_array = self._apply_exif_transpose(image_path)
        if img_array is not None:
            # Convert numpy array to tensor
            img = tf.convert_to_tensor(img_array, dtype=tf.float32)
            img = tf.image.resize(img, (224, 224))
            # Use standalone keras for preprocessing (Keras 3.x compatible)
            img = keras.applications.resnet_v2.preprocess_input(img)
            return img

        # Fallback: Use TensorFlow directly (no EXIF handling)
        img_bytes = tf.io.read_file(image_path)

        # Try JPEG first (faster), fall back to generic decode
        try:
            img = tf.image.decode_jpeg(img_bytes, channels=3)
        except:
            img = tf.image.decode_image(img_bytes, channels=3, expand_animations=False)

        img = tf.image.resize(img, (224, 224))
        img = tf.cast(img, tf.float32)
        # Use standalone keras for preprocessing (Keras 3.x compatible)
        img = keras.applications.resnet_v2.preprocess_input(img)

        return img

    def is_applicable_hazard(self, hazard_type: str) -> bool:
        """
        Check if the hazard type requires image validation.

        Args:
            hazard_type: The reported hazard type

        Returns:
            True if image validation applies to this hazard type
        """
        return hazard_type in self.HAZARD_TO_VISION_MAP

    async def classify_image(
        self,
        image_path: str,
        reported_hazard_type: str
    ) -> LayerResult:
        """
        Classify an image and validate against reported hazard type.

        Enhanced verification pipeline:
        1. Pre-classification checks (face detection, skin tones, color palette) - ALWAYS RUN
        2. CNN model classification (only for applicable hazard types)
        3. Hazard type matching

        Args:
            image_path: Path to the image file
            reported_hazard_type: The hazard type reported by the user

        Returns:
            LayerResult with classification outcome
        """
        try:
            import tensorflow as tf
            import numpy as np
            tensorflow_available = True
        except ImportError as e:
            tensorflow_available = False
            logger.warning(f"TensorFlow not available: {e}. Image layer will use fallback analysis.")

        # Check if image exists FIRST (before any analysis)
        if not os.path.exists(image_path):
            return LayerResult(
                layer_name=LayerName.IMAGE,
                status=LayerStatus.FAIL,
                score=0.0,
                confidence=0.0,
                weight=0.20,
                reasoning=f"Image file not found: {image_path}",
                data={"error": "file_not_found", "path": image_path},
                processed_at=datetime.now(timezone.utc)
            )

        # STEP 1: Pre-classification checks for obvious non-hazard images
        # ALWAYS RUN these checks regardless of hazard type!
        # This catches selfies, portraits, and irrelevant images BEFORE CNN
        logger.info(f"Running pre-classification checks for: {image_path}")
        pre_check_result = self._perform_pre_classification_checks(image_path, reported_hazard_type)
        if pre_check_result is not None:
            logger.info(f"Image rejected by pre-classification: {pre_check_result.reasoning}")
            return pre_check_result

        # STEP 2: Check if hazard type requires CNN model validation
        # Some hazard types (like cyclone, flood) can't be validated by the CNN model
        if not self.is_applicable_hazard(reported_hazard_type):
            # Image passed pre-classification checks but CNN not applicable
            return LayerResult(
                layer_name=LayerName.IMAGE,
                status=LayerStatus.PASS,  # PASS because pre-checks passed
                score=0.7,  # Give reasonable score since image looks valid
                confidence=0.6,
                weight=0.20,
                reasoning=(
                    f"Image passed basic quality checks (no faces/selfies detected). "
                    f"CNN classification not applicable for hazard type: {reported_hazard_type}. "
                    f"Image appears to be a legitimate environmental photo."
                ),
                data={
                    "hazard_type": reported_hazard_type,
                    "reason": "cnn_not_applicable",
                    "pre_checks_passed": True
                },
                processed_at=datetime.now(timezone.utc)
            )

        # If TensorFlow not available, use fallback image analysis
        if not tensorflow_available:
            return await self._fallback_image_analysis(image_path, reported_hazard_type)

        try:
            # STEP 3: Load model if needed for CNN classification
            logger.info(f"Starting CNN classification for: {image_path}")
            if not self._load_model_if_needed():
                logger.error("Model load failed - returning 50% score fallback")
                return LayerResult(
                    layer_name=LayerName.IMAGE,
                    status=LayerStatus.FAIL,
                    score=0.5,  # Give partial score since model failure isn't user's fault
                    confidence=0.0,
                    weight=0.20,
                    reasoning="Vision Model could not be loaded - check server logs for details",
                    data={"error": "model_load_failure"},
                    processed_at=datetime.now(timezone.utc)
                )

            # Preprocess and predict
            logger.info(f"Preprocessing image: {image_path}")
            img = self._preprocess_image(image_path)
            batch = tf.expand_dims(img, axis=0)
            logger.info("Running model prediction...")
            probs = self._model.predict(batch, verbose=0).squeeze(0)
            logger.info(f"Prediction complete. Probabilities: {dict(zip(self.LABEL_COLS, probs.tolist()))}")

            # Apply thresholds
            threshold_array = np.array([
                self._thresholds.get(label, 0.5)
                for label in self.LABEL_COLS
            ])
            preds = (probs >= threshold_array).astype(int)

            # Apply derived-clean logic
            hazards = preds[:-1]  # All except 'clean'
            preds[-1] = 1 if not hazards.any() else 0

            # Build predictions dictionary
            predictions = {
                self.LABEL_COLS[i]: {
                    "probability": float(probs[i]),
                    "predicted": int(preds[i])
                }
                for i in range(len(self.LABEL_COLS))
            }

            # Find the expected Vision Model class for the reported hazard
            expected_vision_class = self.HAZARD_TO_VISION_MAP.get(reported_hazard_type, None)

            # Determine if prediction matches reported hazard
            if expected_vision_class:
                # Check if the expected class was detected
                is_match = preds[self.LABEL_COLS.index(expected_vision_class)] == 1
                match_confidence = float(probs[self.LABEL_COLS.index(expected_vision_class)])

                # Find what was actually predicted (highest probability hazard)
                hazard_probs = {
                    label: float(probs[i])
                    for i, label in enumerate(self.LABEL_COLS)
                    if label != 'clean'
                }
                predicted_class = max(hazard_probs, key=hazard_probs.get)
                predicted_confidence = hazard_probs[predicted_class]

            else:
                is_match = False
                match_confidence = 0.0
                predicted_class = "unknown"
                predicted_confidence = 0.0

            # Calculate score
            if is_match:
                # Match found - hazard type was correctly detected
                # Score is based on the detection being successful, not raw probability
                # Since the model's thresholds are already calibrated, passing the threshold
                # means the detection is valid. We scale the score to reflect confidence levels:
                # - Above 2x threshold: high confidence (0.9-1.0)
                # - At threshold: medium confidence (0.7)
                # - Just above threshold: lower confidence (0.5-0.7)
                threshold = self._thresholds.get(expected_vision_class, 0.5)
                if threshold > 0:
                    # How many times above threshold is the probability?
                    ratio = match_confidence / threshold
                    if ratio >= 2.0:
                        score = 0.9 + min(0.1, (ratio - 2.0) * 0.05)  # 0.9-1.0
                    elif ratio >= 1.5:
                        score = 0.8 + (ratio - 1.5) * 0.2  # 0.8-0.9
                    else:
                        score = 0.6 + (ratio - 1.0) * 0.4  # 0.6-0.8
                else:
                    score = 0.7  # Default if no threshold

                status = LayerStatus.PASS
                reasoning = (
                    f"Image classification matches reported hazard. "
                    f"Detected: {expected_vision_class} (confidence: {match_confidence:.1%}, threshold: {threshold:.1%})."
                )
            elif preds[-1] == 1:  # Clean detected
                # Image shows no hazard
                score = 0.0
                status = LayerStatus.FAIL
                reasoning = (
                    f"Image shows clean/normal conditions, not {reported_hazard_type}. "
                    f"No hazard detected in the image."
                )
            else:
                # Hazard detected but doesn't match reported type
                # Higher confidence in wrong hazard = lower score (more suspicious)
                score = max(0.0, 0.3 * (1.0 - predicted_confidence))  # Low score for high-confidence mismatch
                status = LayerStatus.FAIL
                reasoning = (
                    f"Image shows {predicted_class} ({predicted_confidence:.1%}), "
                    f"but {reported_hazard_type} was reported. Possible wrong image or misclassification."
                )

            # Build layer data
            layer_data = ImageLayerData(
                image_path=image_path,
                reported_hazard_type=reported_hazard_type,
                predicted_class=predicted_class,
                prediction_confidence=predicted_confidence,
                is_match=is_match,
                all_predictions={
                    label: float(probs[i])
                    for i, label in enumerate(self.LABEL_COLS)
                }
            )

            return LayerResult(
                layer_name=LayerName.IMAGE,
                status=status,
                score=max(0.0, min(1.0, score)),
                confidence=match_confidence if is_match else predicted_confidence,
                weight=0.20,
                reasoning=reasoning,
                data=layer_data.model_dump(),
                processed_at=datetime.now(timezone.utc)
            )

        except Exception as e:
            logger.error(f"Vision classification error: {e}")
            return LayerResult(
                layer_name=LayerName.IMAGE,
                status=LayerStatus.FAIL,
                score=0.5,  # Partial score for system error
                confidence=0.0,
                weight=0.20,
                reasoning=f"Image classification failed: {str(e)}",
                data={"error": str(e), "image_path": image_path},
                processed_at=datetime.now(timezone.utc)
            )

    async def get_classification(self, image_path: str) -> Optional[VisionClassificationResult]:
        """
        Get raw classification result for an image.

        Args:
            image_path: Path to the image file

        Returns:
            VisionClassificationResult or None if classification fails
        """
        import tensorflow as tf
        import numpy as np

        try:
            if not os.path.exists(image_path):
                return None

            if not self._load_model_if_needed():
                return None

            # Preprocess and predict
            img = self._preprocess_image(image_path)
            batch = tf.expand_dims(img, axis=0)
            probs = self._model.predict(batch, verbose=0).squeeze(0)

            # Apply thresholds
            threshold_array = np.array([
                self._thresholds.get(label, 0.5)
                for label in self.LABEL_COLS
            ])
            preds = (probs >= threshold_array).astype(int)

            # Apply derived-clean logic
            hazards = preds[:-1]
            preds[-1] = 1 if not hazards.any() else 0

            # Find primary predicted class
            if preds[-1] == 1:
                predicted_class = "clean"
            else:
                hazard_probs = {
                    label: float(probs[i])
                    for i, label in enumerate(self.LABEL_COLS)
                    if label != 'clean' and preds[i] == 1
                }
                if hazard_probs:
                    predicted_class = max(hazard_probs, key=hazard_probs.get)
                else:
                    # Find highest probability hazard
                    hazard_probs_all = {
                        label: float(probs[i])
                        for i, label in enumerate(self.LABEL_COLS)
                        if label != 'clean'
                    }
                    predicted_class = max(hazard_probs_all, key=hazard_probs_all.get)

            return VisionClassificationResult(
                trash=int(preds[0]),
                oil_spill=int(preds[1]),
                marine_animal=int(preds[2]),
                shipwreck=int(preds[3]),
                clean=int(preds[4]),
                confidence_scores={
                    self.LABEL_COLS[i]: float(probs[i])
                    for i in range(len(self.LABEL_COLS))
                },
                predicted_class=predicted_class,
                processed_at=datetime.now(timezone.utc)
            )

        except Exception as e:
            logger.error(f"Vision classification error: {e}")
            return None


    async def _fallback_image_analysis(
        self,
        image_path: str,
        reported_hazard_type: str
    ) -> LayerResult:
        """
        Fallback image analysis when TensorFlow is not available.
        Uses Ollama with LLaVA vision model for image classification.

        Args:
            image_path: Path to the image file
            reported_hazard_type: The hazard type reported by the user

        Returns:
            LayerResult with analysis outcome
        """
        import base64
        import httpx

        # ALWAYS run pre-classification checks first (face detection, etc.)
        # This catches selfies even when TensorFlow is not available
        logger.info(f"Running pre-classification checks (fallback mode) for: {image_path}")
        pre_check_result = self._perform_pre_classification_checks(image_path, reported_hazard_type)
        if pre_check_result is not None:
            pre_check_result.data["fallback"] = True
            logger.info(f"Image rejected by pre-classification (fallback): {pre_check_result.reasoning}")
            return pre_check_result

        # Check if hazard type requires image validation
        if not self.is_applicable_hazard(reported_hazard_type):
            return LayerResult(
                layer_name=LayerName.IMAGE,
                status=LayerStatus.PASS,  # PASS because pre-checks passed
                score=0.7,
                confidence=0.6,
                weight=0.20,
                reasoning=(
                    f"Image passed basic quality checks (no faces/selfies detected). "
                    f"CNN classification not applicable for hazard type: {reported_hazard_type}. "
                    f"Image appears to be a legitimate environmental photo."
                ),
                data={
                    "hazard_type": reported_hazard_type,
                    "reason": "cnn_not_applicable",
                    "pre_checks_passed": True,
                    "fallback": True
                },
                processed_at=datetime.now(timezone.utc)
            )

        # Check if image exists (should have been checked by pre-classification)
        if not os.path.exists(image_path):
            return LayerResult(
                layer_name=LayerName.IMAGE,
                status=LayerStatus.FAIL,
                score=0.0,
                confidence=0.0,
                weight=0.20,
                reasoning=f"Image file not found: {image_path}",
                data={"error": "file_not_found", "path": image_path, "fallback": True},
                processed_at=datetime.now(timezone.utc)
            )

        # Try Ollama with LLaVA for vision analysis
        try:
            # Read and encode image
            with open(image_path, "rb") as f:
                image_data = f.read()
            image_base64 = base64.b64encode(image_data).decode("utf-8")

            # Create prompt for vision analysis
            prompt = f"""Analyze this image and determine if it shows any of the following coastal/marine hazards:
1. Oil spill - dark oil slicks on water, petroleum contamination
2. Trash/Plastic pollution - marine debris, plastic waste in water or on beach
3. Beached/stranded marine animal - dolphins, whales, sea turtles on shore
4. Shipwreck - damaged or wrecked vessels

The user reported this as: "{reported_hazard_type}"

Respond in this exact format:
DETECTED: [hazard type or "none"]
CONFIDENCE: [low/medium/high]
MATCHES_REPORT: [yes/no]
DESCRIPTION: [brief description of what you see]"""

            # Call Ollama API with LLaVA
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": "llava",
                        "prompt": prompt,
                        "images": [image_base64],
                        "stream": False
                    }
                )

                if response.status_code == 200:
                    result = response.json()
                    llm_response = result.get("response", "")

                    # Parse the response
                    detected = "unknown"
                    confidence = "medium"
                    matches_report = False
                    description = ""

                    for line in llm_response.split("\n"):
                        line = line.strip()
                        if line.startswith("DETECTED:"):
                            detected = line.replace("DETECTED:", "").strip().lower()
                        elif line.startswith("CONFIDENCE:"):
                            confidence = line.replace("CONFIDENCE:", "").strip().lower()
                        elif line.startswith("MATCHES_REPORT:"):
                            matches_report = "yes" in line.lower()
                        elif line.startswith("DESCRIPTION:"):
                            description = line.replace("DESCRIPTION:", "").strip()

                    # Calculate score based on response
                    confidence_scores = {"low": 0.4, "medium": 0.6, "high": 0.85}
                    base_confidence = confidence_scores.get(confidence, 0.5)

                    if matches_report:
                        score = 0.7 + (base_confidence * 0.3)  # 0.7-1.0
                        status = LayerStatus.PASS
                        reasoning = f"LLaVA vision analysis confirms {reported_hazard_type}. {description}"
                    elif detected == "none" or detected == "clean":
                        score = 0.3
                        status = LayerStatus.FAIL
                        reasoning = f"LLaVA vision analysis found no hazard in image. Expected: {reported_hazard_type}. {description}"
                    else:
                        score = 0.4
                        status = LayerStatus.FAIL
                        reasoning = f"LLaVA detected '{detected}' but report claims '{reported_hazard_type}'. {description}"

                    return LayerResult(
                        layer_name=LayerName.IMAGE,
                        status=status,
                        score=max(0.0, min(1.0, score)),
                        confidence=base_confidence,
                        weight=0.20,
                        reasoning=reasoning,
                        data={
                            "hazard_type": reported_hazard_type,
                            "detected": detected,
                            "matches_report": matches_report,
                            "llm_confidence": confidence,
                            "description": description,
                            "fallback": True,
                            "method": "ollama_llava"
                        },
                        processed_at=datetime.now(timezone.utc)
                    )
                else:
                    raise Exception(f"Ollama API returned {response.status_code}")

        except Exception as e:
            logger.warning(f"Ollama LLaVA fallback failed: {e}. Using basic image validation.")

        # Final fallback: Basic image validation (file exists, reasonable size, valid format)
        try:
            from PIL import Image

            # Open and validate image
            img = Image.open(image_path)
            width, height = img.size
            file_size = os.path.getsize(image_path)
            format_type = img.format

            # Basic quality checks
            checks_passed = 0
            total_checks = 4
            issues = []

            # Check 1: Valid image format
            if format_type in ["JPEG", "PNG", "JPG"]:
                checks_passed += 1
            else:
                issues.append(f"Unusual format: {format_type}")

            # Check 2: Reasonable dimensions (not too small)
            if width >= 100 and height >= 100:
                checks_passed += 1
            else:
                issues.append(f"Image too small: {width}x{height}")

            # Check 3: Reasonable file size (10KB - 20MB)
            if 10000 <= file_size <= 20000000:
                checks_passed += 1
            else:
                issues.append(f"Unusual file size: {file_size} bytes")

            # Check 4: Color image (not grayscale for most hazards)
            if img.mode in ["RGB", "RGBA"]:
                checks_passed += 1
            else:
                issues.append(f"Not RGB: {img.mode}")

            score = 0.5 + (checks_passed / total_checks) * 0.3  # 0.5 to 0.8

            if checks_passed == total_checks:
                status = LayerStatus.PASS
                reasoning = f"Basic image validation passed. Format: {format_type}, Size: {width}x{height}, File: {file_size/1024:.1f}KB. Unable to verify hazard content (TensorFlow unavailable)."
            else:
                status = LayerStatus.PASS  # Still pass but with lower confidence
                reasoning = f"Basic image validation: {checks_passed}/{total_checks} checks passed. Issues: {', '.join(issues)}. Unable to verify hazard content."

            return LayerResult(
                layer_name=LayerName.IMAGE,
                status=status,
                score=score,
                confidence=0.3,  # Low confidence for basic validation
                weight=0.20,
                reasoning=reasoning,
                data={
                    "hazard_type": reported_hazard_type,
                    "image_format": format_type,
                    "image_dimensions": f"{width}x{height}",
                    "file_size_kb": round(file_size / 1024, 1),
                    "checks_passed": checks_passed,
                    "total_checks": total_checks,
                    "issues": issues,
                    "fallback": True,
                    "method": "basic_validation"
                },
                processed_at=datetime.now(timezone.utc)
            )

        except Exception as e:
            logger.error(f"Basic image validation failed: {e}")
            return LayerResult(
                layer_name=LayerName.IMAGE,
                status=LayerStatus.PASS,
                score=0.5,
                confidence=0.1,
                weight=0.20,
                reasoning=f"Image validation could not be performed. Assigning neutral score. Error: {str(e)}",
                data={
                    "hazard_type": reported_hazard_type,
                    "error": str(e),
                    "fallback": True,
                    "method": "error_fallback"
                },
                processed_at=datetime.now(timezone.utc)
            )


# Singleton instance
_vision_service: Optional[VisionService] = None


def get_vision_service() -> VisionService:
    """Get or create vision service singleton."""
    global _vision_service
    if _vision_service is None:
        _vision_service = VisionService()
    return _vision_service

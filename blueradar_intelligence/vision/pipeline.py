"""
BlueRadar - Complete Vision Pipeline
Image classification for hazard detection using ViT
"""

import io
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass

from utils.logging_config import setup_logging
from config import vision_config, IMAGES_DIR, IMAGE_CLASSIFICATION_LABELS

logger = setup_logging("vision_pipeline")

# Check available libraries
TORCH_AVAILABLE = False
PIL_AVAILABLE = False
DEVICE = "cpu"

try:
    import torch
    import torchvision.transforms as transforms
    TORCH_AVAILABLE = True
    
    if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        DEVICE = torch.device("mps")
    elif torch.cuda.is_available():
        DEVICE = torch.device("cuda")
    else:
        DEVICE = torch.device("cpu")
    
    logger.info(f"PyTorch available for vision, device: {DEVICE}")
except ImportError:
    logger.warning("PyTorch not available for vision")

try:
    from PIL import Image, ImageStat, ExifTags
    PIL_AVAILABLE = True
except ImportError:
    logger.warning("Pillow not available")

try:
    from transformers import ViTImageProcessor, ViTForImageClassification, pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logger.warning("Transformers not available for vision")


@dataclass
class ImageClassification:
    label: str
    confidence: float
    is_hazard_related: bool
    category: str


@dataclass
class ImageAnalysis:
    path: str
    dimensions: Dict[str, int]
    file_size: int
    format: str
    hash_md5: str
    hash_perceptual: str
    classifications: List[ImageClassification]
    hazard_score: int
    damage_level: Optional[str]
    is_relevant: bool
    color_analysis: Dict
    exif_data: Dict
    authenticity_flags: List[str]


class VisionPipeline:
    """
    Image classification pipeline:
    1. Download/load images
    2. Basic image analysis (size, format, colors)
    3. ViT-based classification
    4. Hazard relevance scoring
    5. Damage assessment
    6. Authenticity checking
    """
    
    # ImageNet classes related to hazards
    HAZARD_CLASS_MAPPING = {
        # Water/flood related
        "seashore": "flood",
        "lakeside": "flood",
        "dam": "flood",
        "breakwater": "rough_sea",
        "sandbar": "coastal",
        "promontory": "coastal",
        
        # Weather related
        "volcano": "disaster",
        "alp": "landscape",
        "valley": "landscape",
        "geyser": "natural",
        
        # Vehicle/rescue
        "lifeboat": "rescue",
        "aircraft_carrier": "rescue",
        "speedboat": "vessel",
        "container_ship": "vessel",
        "wreck": "damage",
        
        # Structures
        "suspension_bridge": "infrastructure",
        "steel_arch_bridge": "infrastructure",
        "pier": "coastal",
        "dock": "coastal",
        "boathouse": "coastal",
    }
    
    HAZARD_KEYWORDS = [
        "water", "sea", "ocean", "wave", "flood", "storm", "rain",
        "ship", "boat", "rescue", "bridge", "coast", "beach",
        "damage", "wreck", "debris"
    ]
    
    def __init__(self, use_ml: bool = True, device: str = "auto"):
        self.use_ml = use_ml and TORCH_AVAILABLE and PIL_AVAILABLE
        self.device = DEVICE if device == "auto" else torch.device(device)
        
        self.model = None
        self.processor = None
        self.models_loaded = False
        
        # Image transforms
        self.transform = None
        if TORCH_AVAILABLE:
            self.transform = transforms.Compose([
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225]
                )
            ])
        
        if self.use_ml and TRANSFORMERS_AVAILABLE:
            self._load_models()
    
    def _load_models(self):
        """Load vision models"""
        try:
            logger.info("Loading vision models...")
            
            model_name = "google/vit-base-patch16-224"
            
            self.processor = ViTImageProcessor.from_pretrained(model_name)
            self.model = ViTForImageClassification.from_pretrained(model_name)
            self.model.to(self.device)
            self.model.eval()
            
            self.models_loaded = True
            logger.info("✓ Vision models loaded")
            
        except Exception as e:
            logger.error(f"Error loading vision models: {e}")
            self.use_ml = False
    
    def process(self, posts: List[Dict]) -> List[Dict]:
        """Process images from posts"""
        logger.info(f"Processing images from {len(posts)} posts")
        
        processed_count = 0
        
        for post in posts:
            try:
                local_paths = post.get("media", {}).get("local_paths", [])
                
                if not local_paths:
                    post["vision"] = self._get_default_result()
                    continue
                
                # Process each image
                image_results = []
                for path in local_paths[:5]:  # Max 5 images
                    result = self._analyze_image(path)
                    if result:
                        image_results.append(result)
                
                # Aggregate results
                post["vision"] = self._aggregate_results(image_results)
                processed_count += 1
                
            except Exception as e:
                logger.debug(f"Error processing images: {e}")
                post["vision"] = self._get_default_result()
        
        logger.info(f"✓ Processed {processed_count} posts with images")
        return posts
    
    def _analyze_image(self, image_path: str) -> Optional[Dict]:
        """Analyze a single image"""
        try:
            path = Path(image_path)
            if not path.exists():
                return None
            
            # Load image
            image = Image.open(path)
            
            # Convert to RGB if needed
            if image.mode != "RGB":
                image = image.convert("RGB")
            
            # Basic info
            width, height = image.size
            file_size = path.stat().st_size
            
            # Generate hashes
            md5_hash = self._get_md5_hash(path)
            perceptual_hash = self._get_perceptual_hash(image)
            
            # Color analysis
            color_analysis = self._analyze_colors(image)
            
            # EXIF data
            exif_data = self._extract_exif(image)
            
            # ML classification
            classifications = []
            hazard_score = 0
            
            if self.use_ml and self.models_loaded:
                classifications = self._ml_classify(image)
                hazard_score = self._calculate_hazard_score(classifications)
            else:
                # Rule-based analysis
                classifications = self._rule_based_classify(color_analysis)
                hazard_score = self._calculate_hazard_score(classifications)
            
            # Authenticity check
            authenticity_flags = self._check_authenticity(image, exif_data)
            
            # Damage assessment
            damage_level = self._assess_damage(classifications, color_analysis)
            
            return {
                "path": str(path),
                "dimensions": {"width": width, "height": height},
                "file_size": file_size,
                "format": image.format or path.suffix.upper(),
                "hash_md5": md5_hash,
                "hash_perceptual": perceptual_hash,
                "classifications": classifications,
                "hazard_score": hazard_score,
                "damage_level": damage_level,
                "is_relevant": hazard_score > 30,
                "color_analysis": color_analysis,
                "exif_data": exif_data,
                "authenticity_flags": authenticity_flags
            }
            
        except Exception as e:
            logger.debug(f"Error analyzing image: {e}")
            return None
    
    def _ml_classify(self, image: Image.Image) -> List[Dict]:
        """ML-based image classification"""
        try:
            # Process image
            inputs = self.processor(images=image, return_tensors="pt")
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Get predictions
            with torch.no_grad():
                outputs = self.model(**inputs)
                probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
            
            # Get top predictions
            top_probs, top_indices = torch.topk(probs, 10)
            
            results = []
            for prob, idx in zip(top_probs[0], top_indices[0]):
                label = self.model.config.id2label[idx.item()]
                confidence = prob.item()
                
                is_hazard = self._is_hazard_related(label)
                category = self._get_category(label)
                
                results.append({
                    "label": label,
                    "confidence": round(confidence, 4),
                    "is_hazard_related": is_hazard,
                    "category": category
                })
            
            return results
            
        except Exception as e:
            logger.debug(f"ML classification error: {e}")
            return []
    
    def _is_hazard_related(self, label: str) -> bool:
        """Check if label is hazard-related"""
        label_lower = label.lower().replace("_", " ")
        
        # Check direct mapping
        if label_lower in self.HAZARD_CLASS_MAPPING:
            return True
        
        # Check keywords
        return any(kw in label_lower for kw in self.HAZARD_KEYWORDS)
    
    def _get_category(self, label: str) -> str:
        """Get category for label"""
        label_lower = label.lower().replace("_", " ")
        
        if label_lower in self.HAZARD_CLASS_MAPPING:
            return self.HAZARD_CLASS_MAPPING[label_lower]
        
        for kw in self.HAZARD_KEYWORDS:
            if kw in label_lower:
                return kw
        
        return "other"
    
    def _calculate_hazard_score(self, classifications: List[Dict]) -> int:
        """Calculate hazard relevance score"""
        if not classifications:
            return 0
        
        score = 0
        
        for cls in classifications[:5]:  # Top 5
            if cls.get("is_hazard_related"):
                score += int(cls.get("confidence", 0) * 100 * 0.5)
        
        return min(100, score)
    
    def _rule_based_classify(self, color_analysis: Dict) -> List[Dict]:
        """Rule-based classification based on colors"""
        results = []
        
        dominant = color_analysis.get("dominant_color", "")
        blue_ratio = color_analysis.get("blue_ratio", 0)
        brightness = color_analysis.get("brightness", 128)
        
        # Blue dominant (water/sky)
        if blue_ratio > 0.4:
            results.append({
                "label": "water_detected",
                "confidence": blue_ratio,
                "is_hazard_related": True,
                "category": "water"
            })
        
        # Dark image (storm/night)
        if brightness < 80:
            results.append({
                "label": "dark_conditions",
                "confidence": 1 - (brightness / 128),
                "is_hazard_related": True,
                "category": "weather"
            })
        
        return results
    
    def _analyze_colors(self, image: Image.Image) -> Dict:
        """Analyze image colors"""
        try:
            # Resize for faster processing
            small = image.resize((100, 100))
            
            # Get statistics
            stat = ImageStat.Stat(small)
            
            r_mean, g_mean, b_mean = stat.mean[:3]
            brightness = (r_mean + g_mean + b_mean) / 3
            
            # Calculate ratios
            total = r_mean + g_mean + b_mean
            blue_ratio = b_mean / total if total > 0 else 0
            
            # Dominant color
            if b_mean > r_mean and b_mean > g_mean:
                dominant = "blue"
            elif g_mean > r_mean:
                dominant = "green"
            else:
                dominant = "red/brown"
            
            return {
                "brightness": round(brightness, 2),
                "dominant_color": dominant,
                "red_mean": round(r_mean, 2),
                "green_mean": round(g_mean, 2),
                "blue_mean": round(b_mean, 2),
                "blue_ratio": round(blue_ratio, 4)
            }
            
        except Exception:
            return {}
    
    def _extract_exif(self, image: Image.Image) -> Dict:
        """Extract EXIF data"""
        try:
            exif = image._getexif()
            if not exif:
                return {}
            
            readable_exif = {}
            for tag_id, value in exif.items():
                tag = ExifTags.TAGS.get(tag_id, tag_id)
                
                if tag in ["DateTime", "DateTimeOriginal", "Make", "Model", "GPSInfo"]:
                    readable_exif[tag] = str(value)[:100]
            
            return readable_exif
            
        except Exception:
            return {}
    
    def _check_authenticity(self, image: Image.Image, exif: Dict) -> List[str]:
        """Check for authenticity issues"""
        flags = []
        
        # Check for EXIF
        if not exif:
            flags.append("no_exif_data")
        
        # Check dimensions
        width, height = image.size
        
        if width == height:
            flags.append("square_crop")  # Might be screenshot
        
        if width < 200 or height < 200:
            flags.append("very_small_image")
        
        return flags
    
    def _assess_damage(self, classifications: List[Dict], colors: Dict) -> Optional[str]:
        """Assess damage level from image"""
        # Simple heuristic
        hazard_classes = [c for c in classifications if c.get("is_hazard_related")]
        
        if not hazard_classes:
            return None
        
        max_conf = max(c.get("confidence", 0) for c in hazard_classes)
        
        if max_conf > 0.8:
            return "severe"
        elif max_conf > 0.5:
            return "moderate"
        elif max_conf > 0.3:
            return "minor"
        
        return "unknown"
    
    def _get_md5_hash(self, path: Path) -> str:
        """Get MD5 hash of file"""
        try:
            with open(path, "rb") as f:
                return hashlib.md5(f.read()).hexdigest()
        except:
            return ""
    
    def _get_perceptual_hash(self, image: Image.Image) -> str:
        """Generate perceptual hash"""
        try:
            small = image.resize((8, 8), Image.Resampling.LANCZOS).convert("L")
            pixels = list(small.getdata())
            avg = sum(pixels) / len(pixels)
            
            bits = "".join("1" if p > avg else "0" for p in pixels)
            return hex(int(bits, 2))[2:].zfill(16)
        except:
            return ""
    
    def _aggregate_results(self, image_results: List[Dict]) -> Dict:
        """Aggregate results from multiple images"""
        if not image_results:
            return self._get_default_result()
        
        avg_score = sum(r.get("hazard_score", 0) for r in image_results) / len(image_results)
        any_relevant = any(r.get("is_relevant") for r in image_results)
        
        # Collect hazard classifications
        hazard_classes = []
        for r in image_results:
            for c in r.get("classifications", []):
                if c.get("is_hazard_related"):
                    hazard_classes.append(c)
        
        return {
            "processed_images": len(image_results),
            "avg_hazard_score": int(avg_score),
            "is_relevant": any_relevant,
            "hazard_classifications": hazard_classes[:10],
            "image_details": image_results,
            "processed_at": datetime.now().isoformat()
        }
    
    def _get_default_result(self) -> Dict:
        """Default result"""
        return {
            "processed_images": 0,
            "avg_hazard_score": 0,
            "is_relevant": False,
            "hazard_classifications": [],
            "image_details": [],
            "processed_at": datetime.now().isoformat()
        }
    
    def classify_single(self, image_path: str) -> Dict:
        """Classify single image"""
        result = self._analyze_image(image_path)
        return result or self._get_default_result()


# Global instance
vision_pipeline = VisionPipeline(use_ml=True)

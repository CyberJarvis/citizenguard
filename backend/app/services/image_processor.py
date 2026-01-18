"""
Image Processing Service
Handles EXIF transposition, metadata extraction, and image optimization.

This service ensures images display correctly regardless of device orientation
by burning EXIF rotation directly into pixel data before stripping metadata.
"""

import logging
import os
import io
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ImageMetadata:
    """Extracted metadata from image before stripping."""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude: Optional[float] = None
    timestamp: Optional[datetime] = None
    device_make: Optional[str] = None
    device_model: Optional[str] = None
    original_orientation: Optional[int] = None
    original_width: Optional[int] = None
    original_height: Optional[int] = None


@dataclass
class ProcessedImage:
    """Result of image processing."""
    image_bytes: bytes
    metadata: ImageMetadata
    final_width: int
    final_height: int
    file_size: int
    format: str
    was_rotated: bool
    compression_applied: bool


class ImageProcessor:
    """
    Image processing service for EXIF transposition and metadata handling.

    Workflow:
    1. Extract GPS and timestamp metadata
    2. Read EXIF Orientation tag (0x0112)
    3. Apply physical rotation to pixel data
    4. Strip all EXIF metadata
    5. Compress/resize for storage
    """

    # EXIF Orientation tag values and their meanings
    ORIENTATION_TRANSFORMS = {
        1: None,  # Normal - no rotation needed
        2: 'FLIP_LEFT_RIGHT',  # Mirror horizontal
        3: 'ROTATE_180',  # Rotate 180
        4: 'FLIP_TOP_BOTTOM',  # Mirror vertical
        5: 'TRANSPOSE',  # Mirror horizontal + rotate 270 CW
        6: 'ROTATE_270',  # Rotate 90 CW (270 CCW)
        7: 'TRANSVERSE',  # Mirror horizontal + rotate 90 CW
        8: 'ROTATE_90',  # Rotate 270 CW (90 CCW)
    }

    # GPS EXIF tag IDs
    GPS_TAGS = {
        'GPSLatitude': 0x0002,
        'GPSLatitudeRef': 0x0001,
        'GPSLongitude': 0x0004,
        'GPSLongitudeRef': 0x0003,
        'GPSAltitude': 0x0006,
        'GPSAltitudeRef': 0x0005,
        'GPSTimeStamp': 0x0007,
        'GPSDateStamp': 0x001D,
    }

    # Default compression settings
    DEFAULT_MAX_DIMENSION = 1920  # Max width/height for storage
    DEFAULT_QUALITY = 85  # JPEG quality (0-100)
    LOW_BANDWIDTH_MAX_DIMENSION = 1280
    LOW_BANDWIDTH_QUALITY = 70

    def __init__(self, low_bandwidth_mode: bool = False):
        """
        Initialize image processor.

        Args:
            low_bandwidth_mode: If True, use more aggressive compression
        """
        self.low_bandwidth_mode = low_bandwidth_mode
        self._pil_available = False
        self._check_dependencies()

    def _check_dependencies(self):
        """Check if PIL/Pillow is available."""
        try:
            from PIL import Image, ImageOps, ExifTags
            self._pil_available = True
            logger.info("ImageProcessor initialized with PIL support")
        except ImportError:
            self._pil_available = False
            logger.warning("PIL not available - image processing will be limited")

    def _convert_gps_to_decimal(self, gps_coords: tuple, ref: str) -> Optional[float]:
        """
        Convert GPS coordinates from EXIF format to decimal degrees.

        EXIF stores GPS as ((degrees, 1), (minutes, 1), (seconds, 100))
        """
        try:
            if not gps_coords:
                return None

            # Handle different EXIF formats
            if isinstance(gps_coords[0], tuple):
                degrees = gps_coords[0][0] / gps_coords[0][1]
                minutes = gps_coords[1][0] / gps_coords[1][1]
                seconds = gps_coords[2][0] / gps_coords[2][1]
            else:
                # Some cameras store as simple floats
                degrees = float(gps_coords[0])
                minutes = float(gps_coords[1])
                seconds = float(gps_coords[2])

            decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)

            # Apply hemisphere
            if ref in ['S', 'W']:
                decimal = -decimal

            return decimal
        except Exception as e:
            logger.warning(f"Failed to convert GPS coordinates: {e}")
            return None

    def _extract_metadata(self, image) -> ImageMetadata:
        """
        Extract important metadata from image before stripping.

        Args:
            image: PIL Image object

        Returns:
            ImageMetadata with extracted values
        """
        from PIL import ExifTags

        metadata = ImageMetadata()
        metadata.original_width = image.width
        metadata.original_height = image.height

        try:
            exif = image._getexif()
            if not exif:
                return metadata

            # Get orientation
            for tag_id, value in exif.items():
                tag = ExifTags.TAGS.get(tag_id, tag_id)

                if tag == 'Orientation':
                    metadata.original_orientation = value
                elif tag == 'Make':
                    metadata.device_make = str(value)
                elif tag == 'Model':
                    metadata.device_model = str(value)
                elif tag == 'DateTime' or tag == 'DateTimeOriginal':
                    try:
                        metadata.timestamp = datetime.strptime(
                            str(value), '%Y:%m:%d %H:%M:%S'
                        ).replace(tzinfo=timezone.utc)
                    except ValueError:
                        pass

            # Extract GPS data
            gps_info = exif.get(34853)  # GPSInfo tag
            if gps_info:
                # Latitude
                lat_coords = gps_info.get(2)  # GPSLatitude
                lat_ref = gps_info.get(1, 'N')  # GPSLatitudeRef
                metadata.latitude = self._convert_gps_to_decimal(lat_coords, lat_ref)

                # Longitude
                lon_coords = gps_info.get(4)  # GPSLongitude
                lon_ref = gps_info.get(3, 'E')  # GPSLongitudeRef
                metadata.longitude = self._convert_gps_to_decimal(lon_coords, lon_ref)

                # Altitude
                altitude = gps_info.get(6)  # GPSAltitude
                if altitude:
                    try:
                        if isinstance(altitude, tuple):
                            metadata.altitude = altitude[0] / altitude[1]
                        else:
                            metadata.altitude = float(altitude)

                        # Check altitude reference (0 = above sea level, 1 = below)
                        alt_ref = gps_info.get(5, 0)
                        if alt_ref == 1:
                            metadata.altitude = -metadata.altitude
                    except Exception:
                        pass

        except Exception as e:
            logger.warning(f"Error extracting EXIF metadata: {e}")

        return metadata

    def _apply_exif_transpose(self, image) -> Tuple[Any, bool]:
        """
        Apply EXIF orientation to image pixels.

        This burns the rotation directly into the pixel data,
        so the image displays correctly even without EXIF tags.

        Args:
            image: PIL Image object

        Returns:
            Tuple of (transposed_image, was_rotated)
        """
        from PIL import ImageOps

        try:
            # Use PIL's built-in exif_transpose which handles all 8 orientations
            transposed = ImageOps.exif_transpose(image)

            # Check if rotation was applied
            was_rotated = (
                transposed.width != image.width or
                transposed.height != image.height or
                id(transposed) != id(image)
            )

            return transposed, was_rotated

        except Exception as e:
            logger.warning(f"EXIF transpose failed: {e}, returning original")
            return image, False

    def _resize_image(self, image, max_dimension: int) -> Any:
        """
        Resize image while maintaining aspect ratio.

        Args:
            image: PIL Image object
            max_dimension: Maximum width or height

        Returns:
            Resized PIL Image
        """
        from PIL import Image

        # Only resize if image is larger than max_dimension
        if image.width <= max_dimension and image.height <= max_dimension:
            return image

        # Calculate new dimensions
        ratio = min(max_dimension / image.width, max_dimension / image.height)
        new_width = int(image.width * ratio)
        new_height = int(image.height * ratio)

        # Use high-quality resize
        return image.resize((new_width, new_height), Image.LANCZOS)

    def _strip_metadata_and_save(
        self,
        image,
        format: str = 'JPEG',
        quality: int = 85
    ) -> bytes:
        """
        Save image without any EXIF metadata.

        Args:
            image: PIL Image object
            format: Output format (JPEG, PNG)
            quality: JPEG quality (0-100)

        Returns:
            Image bytes without metadata
        """
        # Create new image without EXIF by copying pixel data
        # This effectively strips all metadata
        if image.mode in ('RGBA', 'P'):
            # Convert to RGB for JPEG
            image = image.convert('RGB')

        output = io.BytesIO()

        # Save without EXIF
        save_kwargs = {
            'format': format,
            'optimize': True,
        }

        if format.upper() == 'JPEG':
            save_kwargs['quality'] = quality
            save_kwargs['progressive'] = True
        elif format.upper() == 'PNG':
            save_kwargs['compress_level'] = 6

        image.save(output, **save_kwargs)
        return output.getvalue()

    def process_image(
        self,
        image_bytes: bytes,
        filename: Optional[str] = None,
        extract_gps: bool = True,
        apply_rotation: bool = True,
        strip_metadata: bool = True,
        resize: bool = True,
        output_format: Optional[str] = None
    ) -> ProcessedImage:
        """
        Process image with full EXIF handling pipeline.

        Workflow:
        1. Extract GPS and timestamp metadata (before stripping)
        2. Read and apply EXIF orientation
        3. Resize if needed
        4. Strip all metadata
        5. Compress and return

        Args:
            image_bytes: Raw image bytes
            filename: Original filename (for format detection)
            extract_gps: Whether to extract GPS metadata
            apply_rotation: Whether to apply EXIF rotation
            strip_metadata: Whether to strip EXIF data
            resize: Whether to resize large images
            output_format: Force output format (JPEG/PNG)

        Returns:
            ProcessedImage with processed bytes and extracted metadata
        """
        if not self._pil_available:
            raise RuntimeError("PIL not available for image processing")

        from PIL import Image

        # Load image
        input_buffer = io.BytesIO(image_bytes)
        image = Image.open(input_buffer)
        original_format = image.format or 'JPEG'

        # Step 1: Extract metadata BEFORE any processing
        metadata = ImageMetadata()
        if extract_gps:
            metadata = self._extract_metadata(image)

        # Step 2: Apply EXIF rotation to burn orientation into pixels
        was_rotated = False
        if apply_rotation:
            image, was_rotated = self._apply_exif_transpose(image)
            if was_rotated:
                logger.debug(f"Applied EXIF rotation for orientation {metadata.original_orientation}")

        # Step 3: Resize if needed
        compression_applied = False
        if resize:
            max_dim = (
                self.LOW_BANDWIDTH_MAX_DIMENSION
                if self.low_bandwidth_mode
                else self.DEFAULT_MAX_DIMENSION
            )
            original_size = (image.width, image.height)
            image = self._resize_image(image, max_dim)
            if (image.width, image.height) != original_size:
                compression_applied = True

        # Step 4 & 5: Strip metadata and compress
        quality = (
            self.LOW_BANDWIDTH_QUALITY
            if self.low_bandwidth_mode
            else self.DEFAULT_QUALITY
        )

        # Determine output format
        if output_format:
            out_format = output_format.upper()
        elif original_format in ['JPEG', 'JPG']:
            out_format = 'JPEG'
        elif original_format == 'PNG':
            out_format = 'PNG'
        else:
            out_format = 'JPEG'  # Default to JPEG for compression

        if strip_metadata:
            processed_bytes = self._strip_metadata_and_save(
                image,
                format=out_format,
                quality=quality
            )
            compression_applied = True
        else:
            # Save with metadata intact (rarely used)
            output = io.BytesIO()
            image.save(output, format=out_format, quality=quality)
            processed_bytes = output.getvalue()

        return ProcessedImage(
            image_bytes=processed_bytes,
            metadata=metadata,
            final_width=image.width,
            final_height=image.height,
            file_size=len(processed_bytes),
            format=out_format,
            was_rotated=was_rotated,
            compression_applied=compression_applied
        )

    async def process_upload(
        self,
        upload_bytes: bytes,
        filename: Optional[str] = None
    ) -> Tuple[bytes, ImageMetadata]:
        """
        Process an uploaded image file.

        Convenience method for API endpoints.

        Args:
            upload_bytes: Raw uploaded file bytes
            filename: Original filename

        Returns:
            Tuple of (processed_bytes, extracted_metadata)
        """
        result = self.process_image(
            upload_bytes,
            filename=filename,
            extract_gps=True,
            apply_rotation=True,
            strip_metadata=True,
            resize=True
        )

        logger.info(
            f"Image processed: {result.final_width}x{result.final_height}, "
            f"size={result.file_size/1024:.1f}KB, "
            f"rotated={result.was_rotated}, "
            f"gps={'yes' if result.metadata.latitude else 'no'}"
        )

        return result.image_bytes, result.metadata


# Singleton instance
_image_processor: Optional[ImageProcessor] = None


def get_image_processor(low_bandwidth_mode: bool = False) -> ImageProcessor:
    """Get or create image processor singleton."""
    global _image_processor
    if _image_processor is None:
        _image_processor = ImageProcessor(low_bandwidth_mode=low_bandwidth_mode)
    return _image_processor

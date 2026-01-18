"""
AWS S3 Storage Service
Handles file uploads to S3 with presigned URLs for direct browser uploads
"""

import uuid
import logging
from typing import Optional, Dict, Any, Tuple
from datetime import datetime
import mimetypes

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from botocore.config import Config

from app.config import settings

logger = logging.getLogger(__name__)


class S3Service:
    """
    Service for managing S3 file uploads with presigned URLs

    Supports:
    - Presigned URL generation for direct browser uploads
    - File organization by type (hazards, profiles, events, voice-notes)
    - Public read access for uploaded files
    """

    # Allowed file types and their MIME types
    ALLOWED_IMAGE_TYPES = {
        'image/jpeg': '.jpg',
        'image/png': '.png',
        'image/webp': '.webp',
        'image/avif': '.avif',
        'image/heic': '.heic',
        'image/heif': '.heif',
    }

    ALLOWED_VOICE_TYPES = {
        'audio/webm': '.webm',
        'audio/mpeg': '.mp3',
        'audio/wav': '.wav',
        'audio/mp4': '.m4a',
    }

    # Max file sizes (in bytes)
    MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB
    MAX_VOICE_SIZE = 5 * 1024 * 1024   # 5 MB
    MAX_PROFILE_SIZE = 5 * 1024 * 1024  # 5 MB

    # S3 folder structure
    FOLDERS = {
        'hazard_image': 'hazards',
        'hazard_voice': 'voice-notes',
        'profile': 'profiles',
        'event': 'events',
    }

    def __init__(self):
        """Initialize S3 client"""
        self._client = None
        self._initialized = False

    def _get_client(self):
        """Lazy initialization of S3 client"""
        if not self._client and settings.S3_ENABLED:
            try:
                config = Config(
                    region_name=settings.AWS_REGION,
                    signature_version='s3v4',
                    s3={'addressing_style': 'virtual'},
                    retries={'max_attempts': 3, 'mode': 'standard'}
                )

                # Use regional endpoint to avoid redirect issues with CORS
                endpoint_url = f"https://s3.{settings.AWS_REGION}.amazonaws.com"

                self._client = boto3.client(
                    's3',
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                    region_name=settings.AWS_REGION,
                    endpoint_url=endpoint_url,
                    config=config
                )
                self._initialized = True
                logger.info("S3 client initialized successfully")
            except NoCredentialsError:
                logger.error("AWS credentials not configured")
                raise ValueError("AWS credentials not configured")
            except Exception as e:
                logger.error(f"Failed to initialize S3 client: {e}")
                raise

        return self._client

    @property
    def is_enabled(self) -> bool:
        """Check if S3 storage is enabled"""
        return settings.S3_ENABLED

    def _generate_key(self, upload_type: str, filename: str, user_id: Optional[str] = None) -> str:
        """
        Generate a unique S3 key (path) for the file

        Structure:
        - hazards/{year}/{month}/{uuid}.{ext}
        - profiles/{user_id}/{uuid}.{ext}
        - events/{event_id}/{uuid}.{ext}
        - voice-notes/{year}/{month}/{uuid}.{ext}
        """
        now = datetime.utcnow()
        file_id = str(uuid.uuid4())

        # Get file extension
        ext = mimetypes.guess_extension(filename) or ''
        if '.' in filename:
            ext = '.' + filename.rsplit('.', 1)[-1].lower()

        folder = self.FOLDERS.get(upload_type, 'misc')

        if upload_type == 'profile' and user_id:
            return f"{folder}/{user_id}/{file_id}{ext}"
        elif upload_type == 'event' and user_id:  # user_id is event_id in this case
            return f"{folder}/{user_id}/{file_id}{ext}"
        else:
            return f"{folder}/{now.year}/{now.month:02d}/{file_id}{ext}"

    def generate_presigned_url(
        self,
        upload_type: str,
        content_type: str,
        filename: str,
        user_id: Optional[str] = None,
        file_size: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate a presigned URL for direct browser upload to S3

        Args:
            upload_type: Type of upload ('hazard_image', 'hazard_voice', 'profile', 'event')
            content_type: MIME type of the file
            filename: Original filename
            user_id: User ID (for profiles) or Event ID (for events)
            file_size: File size in bytes (for validation)

        Returns:
            Dict with presigned URL, S3 key, and public URL
        """
        if not self.is_enabled:
            raise ValueError("S3 storage is not enabled")

        # Validate content type
        if upload_type in ('hazard_image', 'profile', 'event'):
            if content_type not in self.ALLOWED_IMAGE_TYPES:
                raise ValueError(f"Invalid image type: {content_type}. Allowed: {list(self.ALLOWED_IMAGE_TYPES.keys())}")
            max_size = self.MAX_PROFILE_SIZE if upload_type == 'profile' else self.MAX_IMAGE_SIZE
        elif upload_type == 'hazard_voice':
            if content_type not in self.ALLOWED_VOICE_TYPES:
                raise ValueError(f"Invalid voice type: {content_type}. Allowed: {list(self.ALLOWED_VOICE_TYPES.keys())}")
            max_size = self.MAX_VOICE_SIZE
        else:
            raise ValueError(f"Invalid upload type: {upload_type}")

        # Validate file size
        if file_size and file_size > max_size:
            raise ValueError(f"File too large. Maximum size: {max_size / (1024*1024):.1f} MB")

        # Generate S3 key
        s3_key = self._generate_key(upload_type, filename, user_id)

        try:
            client = self._get_client()

            # Generate presigned URL for PUT operation
            presigned_url = client.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': settings.S3_BUCKET_NAME,
                    'Key': s3_key,
                    'ContentType': content_type,
                },
                ExpiresIn=settings.S3_PRESIGNED_URL_EXPIRY,
                HttpMethod='PUT'
            )

            # Public URL for accessing the file after upload
            public_url = f"{settings.s3_base_url}/{s3_key}"

            logger.info(f"Generated presigned URL for {upload_type}: {s3_key}")

            return {
                'presigned_url': presigned_url,
                's3_key': s3_key,
                'public_url': public_url,
                'expires_in': settings.S3_PRESIGNED_URL_EXPIRY,
                'max_size': max_size,
                'content_type': content_type,
            }

        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise ValueError(f"Failed to generate upload URL: {str(e)}")

    def delete_file(self, s3_key: str) -> bool:
        """
        Delete a file from S3

        Args:
            s3_key: The S3 key (path) of the file to delete

        Returns:
            True if successful, False otherwise
        """
        if not self.is_enabled:
            logger.warning("S3 is not enabled, cannot delete file")
            return False

        try:
            client = self._get_client()
            client.delete_object(
                Bucket=settings.S3_BUCKET_NAME,
                Key=s3_key
            )
            logger.info(f"Deleted S3 file: {s3_key}")
            return True
        except ClientError as e:
            logger.error(f"Failed to delete S3 file {s3_key}: {e}")
            return False

    def file_exists(self, s3_key: str) -> bool:
        """
        Check if a file exists in S3

        Args:
            s3_key: The S3 key (path) of the file

        Returns:
            True if file exists, False otherwise
        """
        if not self.is_enabled:
            return False

        try:
            client = self._get_client()
            client.head_object(
                Bucket=settings.S3_BUCKET_NAME,
                Key=s3_key
            )
            return True
        except ClientError:
            return False

    def get_public_url(self, s3_key: str) -> str:
        """
        Get the public URL for an S3 object

        Args:
            s3_key: The S3 key (path) of the file

        Returns:
            Public URL string
        """
        return f"{settings.s3_base_url}/{s3_key}"

    def extract_key_from_url(self, url: str) -> Optional[str]:
        """
        Extract S3 key from a public URL

        Args:
            url: The public S3 URL

        Returns:
            S3 key or None if not a valid S3 URL
        """
        base_url = settings.s3_base_url
        if url.startswith(base_url):
            return url[len(base_url) + 1:]  # +1 for the /
        return None

    async def upload_file_directly(
        self,
        file_content: bytes,
        upload_type: str,
        content_type: str,
        filename: str,
        user_id: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Upload file directly to S3 (fallback for server-side uploads)

        This is used when presigned URLs are not suitable (e.g., image processing)

        Args:
            file_content: File bytes
            upload_type: Type of upload
            content_type: MIME type
            filename: Original filename
            user_id: User ID or Event ID

        Returns:
            Dict with s3_key and public_url
        """
        if not self.is_enabled:
            raise ValueError("S3 storage is not enabled")

        s3_key = self._generate_key(upload_type, filename, user_id)

        try:
            client = self._get_client()
            client.put_object(
                Bucket=settings.S3_BUCKET_NAME,
                Key=s3_key,
                Body=file_content,
                ContentType=content_type,
            )

            public_url = self.get_public_url(s3_key)
            logger.info(f"Uploaded file directly to S3: {s3_key}")

            return {
                's3_key': s3_key,
                'public_url': public_url,
            }

        except ClientError as e:
            logger.error(f"Failed to upload file to S3: {e}")
            raise ValueError(f"Failed to upload file: {str(e)}")

    def download_file_to_temp(self, s3_key: str) -> Optional[str]:
        """
        Download a file from S3 to a temporary local file.

        Used for image verification where local file access is required.

        Args:
            s3_key: The S3 key (path) of the file to download

        Returns:
            Local temporary file path, or None if download failed
        """
        import tempfile
        import os

        if not self.is_enabled:
            logger.warning("S3 is not enabled, cannot download file")
            return None

        try:
            client = self._get_client()

            # Determine file extension from s3_key
            ext = ''
            if '.' in s3_key:
                ext = '.' + s3_key.rsplit('.', 1)[-1].lower()

            # Create a temporary file with the correct extension
            temp_fd, temp_path = tempfile.mkstemp(suffix=ext, prefix='s3_download_')
            os.close(temp_fd)  # Close the file descriptor, we'll write via boto3

            # Download from S3
            client.download_file(
                Bucket=settings.S3_BUCKET_NAME,
                Key=s3_key,
                Filename=temp_path
            )

            logger.info(f"Downloaded S3 file to temp: {s3_key} -> {temp_path}")
            return temp_path

        except ClientError as e:
            logger.error(f"Failed to download S3 file {s3_key}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error downloading S3 file {s3_key}: {e}")
            return None

    def download_from_url_to_temp(self, s3_url: str) -> Optional[str]:
        """
        Download a file from S3 URL to a temporary local file.

        Convenience method that extracts the key from URL first.

        Args:
            s3_url: The full S3 public URL

        Returns:
            Local temporary file path, or None if download failed
        """
        s3_key = self.extract_key_from_url(s3_url)
        if not s3_key:
            logger.error(f"Invalid S3 URL: {s3_url}")
            return None

        return self.download_file_to_temp(s3_key)


# Global S3 service instance
s3_service = S3Service()

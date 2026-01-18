"""
S3 Migration Script

Migrates existing local file uploads to AWS S3 bucket.
Run this script after configuring S3 credentials in .env

Usage:
    cd backend
    python scripts/migrate_to_s3.py [--dry-run]

Options:
    --dry-run    Show what would be migrated without actually uploading
"""

import os
import sys
import asyncio
import argparse
import mimetypes
from pathlib import Path
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import boto3
from botocore.exceptions import ClientError
from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings


class S3Migrator:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.stats = {
            'hazards': {'found': 0, 'migrated': 0, 'skipped': 0, 'failed': 0},
            'profiles': {'found': 0, 'migrated': 0, 'skipped': 0, 'failed': 0},
            'events': {'found': 0, 'migrated': 0, 'skipped': 0, 'failed': 0},
        }

        # Initialize S3 client
        if not settings.S3_ENABLED:
            print("ERROR: S3 is not enabled. Set S3_ENABLED=true in .env")
            sys.exit(1)

        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        self.bucket = settings.S3_BUCKET_NAME
        self.base_url = settings.s3_base_url

        # MongoDB connection
        self.mongo_client = AsyncIOMotorClient(settings.MONGODB_URL)
        self.db = self.mongo_client[settings.MONGODB_DB_NAME]

    def get_content_type(self, file_path: str) -> str:
        """Get MIME type for file"""
        mime_type, _ = mimetypes.guess_type(file_path)
        return mime_type or 'application/octet-stream'

    def upload_to_s3(self, local_path: str, s3_key: str) -> bool:
        """Upload a file to S3"""
        try:
            content_type = self.get_content_type(local_path)

            if self.dry_run:
                print(f"  [DRY-RUN] Would upload: {local_path} -> s3://{self.bucket}/{s3_key}")
                return True

            self.s3_client.upload_file(
                local_path,
                self.bucket,
                s3_key,
                ExtraArgs={'ContentType': content_type}
            )
            return True
        except Exception as e:
            print(f"  ERROR uploading {local_path}: {e}")
            return False

    def file_exists_on_s3(self, s3_key: str) -> bool:
        """Check if file already exists on S3"""
        try:
            self.s3_client.head_object(Bucket=self.bucket, Key=s3_key)
            return True
        except ClientError:
            return False

    async def migrate_hazard_reports(self):
        """Migrate hazard report images and voice notes"""
        print("\n=== Migrating Hazard Reports ===")

        cursor = self.db.hazard_reports.find({})
        async for report in cursor:
            report_id = report.get('report_id', str(report['_id']))

            # Migrate image
            image_url = report.get('image_url')
            if image_url and image_url.startswith('/uploads/'):
                self.stats['hazards']['found'] += 1
                local_path = image_url.lstrip('/')

                if not os.path.exists(local_path):
                    print(f"  SKIP {report_id}: File not found - {local_path}")
                    self.stats['hazards']['skipped'] += 1
                    continue

                # Generate S3 key
                filename = os.path.basename(local_path)
                created_at = report.get('created_at', datetime.utcnow())
                s3_key = f"hazards/{created_at.year}/{created_at.month:02d}/{filename}"

                # Check if already migrated
                if self.file_exists_on_s3(s3_key):
                    print(f"  SKIP {report_id}: Already on S3 - {s3_key}")
                    self.stats['hazards']['skipped'] += 1
                    continue

                # Upload
                if self.upload_to_s3(local_path, s3_key):
                    new_url = f"{self.base_url}/{s3_key}"

                    if not self.dry_run:
                        # Update database
                        await self.db.hazard_reports.update_one(
                            {'_id': report['_id']},
                            {'$set': {'image_url': new_url}}
                        )

                    print(f"  OK {report_id}: {local_path} -> {s3_key}")
                    self.stats['hazards']['migrated'] += 1
                else:
                    self.stats['hazards']['failed'] += 1

            # Migrate voice note
            voice_url = report.get('voice_note_url')
            if voice_url and voice_url.startswith('/uploads/'):
                local_path = voice_url.lstrip('/')

                if os.path.exists(local_path):
                    filename = os.path.basename(local_path)
                    created_at = report.get('created_at', datetime.utcnow())
                    s3_key = f"voice-notes/{created_at.year}/{created_at.month:02d}/{filename}"

                    if not self.file_exists_on_s3(s3_key):
                        if self.upload_to_s3(local_path, s3_key):
                            new_url = f"{self.base_url}/{s3_key}"
                            if not self.dry_run:
                                await self.db.hazard_reports.update_one(
                                    {'_id': report['_id']},
                                    {'$set': {'voice_note_url': new_url}}
                                )
                            print(f"  OK voice: {local_path} -> {s3_key}")

    async def migrate_profile_pictures(self):
        """Migrate user profile pictures"""
        print("\n=== Migrating Profile Pictures ===")

        cursor = self.db.users.find({'profile_picture': {'$exists': True, '$ne': None}})
        async for user in cursor:
            user_id = user.get('user_id', str(user['_id']))
            picture_url = user.get('profile_picture')

            if picture_url and picture_url.startswith('/uploads/'):
                self.stats['profiles']['found'] += 1
                local_path = picture_url.lstrip('/')

                if not os.path.exists(local_path):
                    print(f"  SKIP {user_id}: File not found - {local_path}")
                    self.stats['profiles']['skipped'] += 1
                    continue

                # Generate S3 key
                filename = os.path.basename(local_path)
                s3_key = f"profiles/{user_id}/{filename}"

                # Check if already migrated
                if self.file_exists_on_s3(s3_key):
                    print(f"  SKIP {user_id}: Already on S3 - {s3_key}")
                    self.stats['profiles']['skipped'] += 1
                    continue

                # Upload
                if self.upload_to_s3(local_path, s3_key):
                    new_url = f"{self.base_url}/{s3_key}"

                    if not self.dry_run:
                        await self.db.users.update_one(
                            {'_id': user['_id']},
                            {'$set': {'profile_picture': new_url}}
                        )

                    print(f"  OK {user_id}: {local_path} -> {s3_key}")
                    self.stats['profiles']['migrated'] += 1
                else:
                    self.stats['profiles']['failed'] += 1

    async def migrate_event_photos(self):
        """Migrate event photos"""
        print("\n=== Migrating Event Photos ===")

        # Check for event_photos collection or embedded photos in events
        cursor = self.db.event_photos.find({})
        async for photo in cursor:
            photo_url = photo.get('photo_url')

            if photo_url and photo_url.startswith('/uploads/'):
                self.stats['events']['found'] += 1
                local_path = photo_url.lstrip('/')

                if not os.path.exists(local_path):
                    self.stats['events']['skipped'] += 1
                    continue

                event_id = photo.get('event_id', 'unknown')
                filename = os.path.basename(local_path)
                s3_key = f"events/{event_id}/{filename}"

                if self.file_exists_on_s3(s3_key):
                    self.stats['events']['skipped'] += 1
                    continue

                if self.upload_to_s3(local_path, s3_key):
                    new_url = f"{self.base_url}/{s3_key}"

                    if not self.dry_run:
                        await self.db.event_photos.update_one(
                            {'_id': photo['_id']},
                            {'$set': {'photo_url': new_url}}
                        )

                    print(f"  OK event photo: {local_path} -> {s3_key}")
                    self.stats['events']['migrated'] += 1
                else:
                    self.stats['events']['failed'] += 1

    def print_summary(self):
        """Print migration summary"""
        print("\n" + "=" * 50)
        print("MIGRATION SUMMARY")
        print("=" * 50)

        if self.dry_run:
            print("(DRY RUN - no actual changes made)")
            print()

        for category, stats in self.stats.items():
            print(f"\n{category.upper()}:")
            print(f"  Found:    {stats['found']}")
            print(f"  Migrated: {stats['migrated']}")
            print(f"  Skipped:  {stats['skipped']}")
            print(f"  Failed:   {stats['failed']}")

        total_found = sum(s['found'] for s in self.stats.values())
        total_migrated = sum(s['migrated'] for s in self.stats.values())
        total_failed = sum(s['failed'] for s in self.stats.values())

        print(f"\nTOTAL: {total_migrated}/{total_found} files migrated, {total_failed} failed")

    async def run(self):
        """Run the migration"""
        print("=" * 50)
        print("CoastGuardian S3 Migration Script")
        print("=" * 50)
        print(f"Bucket: {self.bucket}")
        print(f"Region: {settings.AWS_REGION}")
        print(f"Dry Run: {self.dry_run}")

        try:
            await self.migrate_hazard_reports()
            await self.migrate_profile_pictures()
            await self.migrate_event_photos()
        finally:
            self.mongo_client.close()

        self.print_summary()


async def main():
    parser = argparse.ArgumentParser(description='Migrate local uploads to S3')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be migrated without uploading')
    args = parser.parse_args()

    migrator = S3Migrator(dry_run=args.dry_run)
    await migrator.run()


if __name__ == '__main__':
    asyncio.run(main())

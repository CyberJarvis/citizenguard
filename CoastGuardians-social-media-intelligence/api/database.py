"""
Coast Guardian Database Service
MongoDB integration for social posts and analysis storage
"""

import os
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from pymongo import MongoClient, DESCENDING
from pymongo.collection import Collection
from bson import ObjectId
import json

from api.models import ProcessedPost, SocialMediaPost, DisasterAnalysis, SystemStats

class CoastGuardianDatabase:
    """MongoDB database service for Coast Guardian"""

    def __init__(self):
        self.client = None
        self.db = None
        self.collections = {}
        self.connect()

    def connect(self):
        """Connect to MongoDB Atlas"""
        try:
            mongodb_uri = os.getenv('MONGODB_URI')
            database_name = os.getenv('MONGODB_DATABASE', 'coastaguardian_socailmedia_db')

            if not mongodb_uri:
                raise ValueError("MONGODB_URI not found in environment variables")

            self.client = MongoClient(
                mongodb_uri,
                tlsAllowInvalidCertificates=True,
                serverSelectionTimeoutMS=5000,  # 5 seconds instead of 30
                connectTimeoutMS=5000,  # 5 seconds connection timeout
                socketTimeoutMS=5000    # 5 seconds socket timeout
            )
            self.db = self.client[database_name]

            # Initialize collections
            self.collections = {
                'social_posts': self.db.social_posts,
                'social_analysis': self.db.social_analysis,
                'misinfo_flags': self.db.misinfo_flags,
                'alerts': self.db.alerts,
                'system_stats': self.db.system_stats
            }

            # Create indexes for better performance
            self._create_indexes()

            print("✅ Database connected successfully")

        except Exception as e:
            print(f"❌ Database connection error: {e}")
            raise

    def _create_indexes(self):
        """Create database indexes for performance"""
        try:
            # Social posts indexes
            self.collections['social_posts'].create_index([
                ("timestamp", DESCENDING),
                ("platform", 1),
                ("language", 1)
            ])

            # Analysis indexes
            self.collections['social_analysis'].create_index([
                ("analysis.disaster_type", 1),
                ("analysis.urgency", 1),
                ("analysis.relevance_score", DESCENDING),
                ("processed_at", DESCENDING)
            ])

            # Alerts indexes
            self.collections['alerts'].create_index([
                ("severity", 1),
                ("triggered_at", DESCENDING)
            ])

        except Exception as e:
            print(f"⚠️ Index creation warning: {e}")

    def store_processed_post(self, processed_post: ProcessedPost) -> str:
        """Store processed post and analysis"""
        try:
            # Convert to dict and handle datetime serialization
            post_data = processed_post.model_dump()
            post_data['_id'] = ObjectId()
            post_data['stored_at'] = datetime.now(timezone.utc)

            # Store in social_analysis collection
            result = self.collections['social_analysis'].insert_one(post_data)

            # Also store raw post in social_posts collection
            raw_post_data = processed_post.original_post.model_dump()
            raw_post_data['analysis_id'] = result.inserted_id
            raw_post_data['stored_at'] = datetime.now(timezone.utc)

            self.collections['social_posts'].insert_one(raw_post_data)

            return str(result.inserted_id)

        except Exception as e:
            print(f"❌ Error storing post: {e}")
            raise

    def get_recent_posts(self, limit: int = 50, disaster_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recent analyzed posts"""
        try:
            query = {}
            if disaster_filter and disaster_filter != "all":
                query["analysis.disaster_type"] = disaster_filter

            cursor = self.collections['social_analysis'].find(query).sort("processed_at", DESCENDING).limit(limit)

            posts = []
            for post in cursor:
                post['_id'] = str(post['_id'])  # Convert ObjectId to string
                posts.append(post)

            return posts

        except Exception as e:
            print(f"❌ Error retrieving posts: {e}")
            return []

    def get_disaster_statistics(self, days: int = 7) -> Dict[str, Any]:
        """Get disaster statistics for specified days"""
        try:
            start_date = datetime.now(timezone.utc) - timedelta(days=days)

            # Aggregation pipeline for statistics
            pipeline = [
                {
                    "$match": {
                        "processed_at": {"$gte": start_date}
                    }
                },
                {
                    "$group": {
                        "_id": "$analysis.disaster_type",
                        "count": {"$sum": 1},
                        "avg_relevance": {"$avg": "$analysis.relevance_score"},
                        "max_relevance": {"$max": "$analysis.relevance_score"},
                        "urgency_breakdown": {
                            "$push": "$analysis.urgency"
                        }
                    }
                }
            ]

            results = list(self.collections['social_analysis'].aggregate(pipeline))

            # Process results
            disaster_stats = {}
            for result in results:
                disaster_type = result['_id']
                disaster_stats[disaster_type] = {
                    'count': result['count'],
                    'avg_relevance': round(result['avg_relevance'], 2),
                    'max_relevance': result['max_relevance'],
                    'urgency_breakdown': self._count_urgency_levels(result['urgency_breakdown'])
                }

            return disaster_stats

        except Exception as e:
            print(f"❌ Error getting statistics: {e}")
            return {}

    def _count_urgency_levels(self, urgency_list: List[str]) -> Dict[str, int]:
        """Count urgency levels"""
        counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for urgency in urgency_list:
            if urgency in counts:
                counts[urgency] += 1
        return counts

    def get_platform_statistics(self) -> List[Dict[str, Any]]:
        """Get statistics by platform"""
        try:
            pipeline = [
                {
                    "$group": {
                        "_id": "$original_post.platform",
                        "total_posts": {"$sum": 1},
                        "disaster_posts": {
                            "$sum": {
                                "$cond": [
                                    {"$ne": ["$analysis.disaster_type", "none"]},
                                    1,
                                    0
                                ]
                            }
                        },
                        "avg_relevance": {"$avg": "$analysis.relevance_score"}
                    }
                }
            ]

            results = list(self.collections['social_analysis'].aggregate(pipeline))

            platform_stats = []
            for result in results:
                platform_stats.append({
                    'platform': result['_id'],
                    'total_posts': result['total_posts'],
                    'disaster_posts': result['disaster_posts'],
                    'avg_relevance_score': round(result['avg_relevance'], 2),
                    'disaster_rate': round((result['disaster_posts'] / result['total_posts']) * 100, 1)
                })

            return platform_stats

        except Exception as e:
            print(f"❌ Error getting platform statistics: {e}")
            return []

    def search_posts(self,
                    query: str,
                    disaster_type: Optional[str] = None,
                    limit: int = 20) -> List[Dict[str, Any]]:
        """Search posts by text query"""
        try:
            # Create text index if not exists
            try:
                self.collections['social_analysis'].create_index([("original_post.text", "text")])
            except:
                pass  # Index might already exist

            search_filter = {"$text": {"$search": query}}

            if disaster_type and disaster_type != "all":
                search_filter["analysis.disaster_type"] = disaster_type

            cursor = self.collections['social_analysis'].find(search_filter).limit(limit)

            posts = []
            for post in cursor:
                post['_id'] = str(post['_id'])
                posts.append(post)

            return posts

        except Exception as e:
            print(f"❌ Error searching posts: {e}")
            return []

    def store_alert(self, alert_data: Dict[str, Any]) -> str:
        """Store real-time alert"""
        try:
            alert_data['stored_at'] = datetime.now(timezone.utc)
            result = self.collections['alerts'].insert_one(alert_data)
            return str(result.inserted_id)

        except Exception as e:
            print(f"❌ Error storing alert: {e}")
            raise

    def get_recent_alerts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent alerts"""
        try:
            cursor = self.collections['alerts'].find().sort("triggered_at", DESCENDING).limit(limit)

            alerts = []
            for alert in cursor:
                alert['_id'] = str(alert['_id'])
                alerts.append(alert)

            return alerts

        except Exception as e:
            print(f"❌ Error retrieving alerts: {e}")
            return []

    def get_system_health(self) -> Dict[str, Any]:
        """Get system health metrics"""
        try:
            total_posts = self.collections['social_analysis'].count_documents({})
            total_alerts = self.collections['alerts'].count_documents({})

            # Recent activity (last 24 hours)
            yesterday = datetime.now(timezone.utc) - timedelta(days=1)
            recent_posts = self.collections['social_analysis'].count_documents({
                "processed_at": {"$gte": yesterday}
            })

            return {
                'total_posts_processed': total_posts,
                'total_alerts_generated': total_alerts,
                'last_24h_posts': recent_posts,
                'database_status': 'healthy',
                'collections_count': len(self.collections)
            }

        except Exception as e:
            print(f"❌ Error getting health metrics: {e}")
            return {
                'database_status': 'error',
                'error': str(e)
            }

    def close(self):
        """Close database connection"""
        if self.client:
            self.client.close()
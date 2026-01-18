"""
Analytics Service
Provides aggregated analytics data for the Analyst module.
Handles MongoDB aggregation pipelines for complex queries.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class AnalyticsService:
    """
    Service for computing analytics and aggregations.

    Provides:
    - Report statistics and trends
    - Hazard distribution analysis
    - Geospatial heatmap data
    - NLP insights aggregation
    - Verification metrics
    - Time-series data for charts
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    # =========================================================================
    # DATE RANGE HELPERS
    # =========================================================================

    def get_date_range(self, range_type: str) -> Dict[str, datetime]:
        """
        Convert a range type to start/end dates.

        Args:
            range_type: '7days', '30days', '90days', 'year', 'all'

        Returns:
            Dict with 'start' and 'end' datetime objects
        """
        now = datetime.now(timezone.utc)
        end = now

        if range_type == "7days":
            start = now - timedelta(days=7)
        elif range_type == "30days":
            start = now - timedelta(days=30)
        elif range_type == "90days":
            start = now - timedelta(days=90)
        elif range_type == "year":
            start = now - timedelta(days=365)
        elif range_type == "all":
            start = datetime(2020, 1, 1, tzinfo=timezone.utc)
        else:
            # Default to 7 days
            start = now - timedelta(days=7)

        return {"start": start, "end": end}

    def get_previous_period(self, start: datetime, end: datetime) -> Dict[str, datetime]:
        """Get the previous period of same duration for comparison."""
        duration = end - start
        prev_end = start
        prev_start = prev_end - duration
        return {"start": prev_start, "end": prev_end}

    # =========================================================================
    # DASHBOARD SUMMARY
    # =========================================================================

    async def get_dashboard_summary(self, user_id: str) -> Dict[str, Any]:
        """
        Get summary data for the analyst dashboard.

        Returns:
            Dashboard summary with key metrics
        """
        now = datetime.now(timezone.utc)
        seven_days_ago = now - timedelta(days=7)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # Get total reports
        total_reports = await self.db.hazard_reports.count_documents({})

        # Get reports this week
        reports_this_week = await self.db.hazard_reports.count_documents({
            "created_at": {"$gte": seven_days_ago}
        })

        # Get today's reports
        reports_today = await self.db.hazard_reports.count_documents({
            "created_at": {"$gte": today_start}
        })

        # Get pending verification count
        pending_reports = await self.db.hazard_reports.count_documents({
            "verification_status": "pending"
        })

        # Get verified reports count
        verified_reports = await self.db.hazard_reports.count_documents({
            "verification_status": "verified"
        })

        # Get active alerts count
        active_alerts = await self.db.alerts.count_documents({
            "status": "active"
        })

        # Get critical/high alerts
        critical_alerts = await self.db.alerts.count_documents({
            "status": "active",
            "severity": {"$in": ["critical", "high"]}
        })

        # Get monitored locations count (from ML service data)
        # This would normally come from the ML monitor service
        monitored_locations = 14

        # Calculate verification rate
        verification_rate = 0
        if total_reports > 0:
            verification_rate = round((verified_reports / total_reports) * 100, 1)

        return {
            "total_reports": total_reports,
            "reports_this_week": reports_this_week,
            "reports_today": reports_today,
            "pending_reports": pending_reports,
            "verified_reports": verified_reports,
            "verification_rate": verification_rate,
            "active_alerts": active_alerts,
            "critical_alerts": critical_alerts,
            "monitored_locations": monitored_locations,
            "last_updated": now.isoformat()
        }

    # =========================================================================
    # REPORT ANALYTICS
    # =========================================================================

    async def get_report_analytics(
        self,
        date_range: str = "7days",
        region: Optional[str] = None,
        hazard_type: Optional[str] = None,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive report analytics.

        Args:
            date_range: Time period for analysis
            region: Filter by region
            hazard_type: Filter by hazard type
            status: Filter by verification status

        Returns:
            Analytics data with metrics and distributions
        """
        dates = self.get_date_range(date_range)
        prev_dates = self.get_previous_period(dates["start"], dates["end"])

        # Build match filter - use flexible date filter to include all reports
        match_filter = {}
        if date_range != "all":
            match_filter["created_at"] = {"$gte": dates["start"], "$lte": dates["end"]}

        if region:
            match_filter["$or"] = [
                {"location.region": region},
                {"location.state": region},
                {"location.city": region}
            ]
        if hazard_type:
            match_filter["hazard_type"] = hazard_type
        if status and status != "all":
            match_filter["$or"] = [
                {"verification_status": status},
                {"status": status}
            ]

        # Get total count (no date filter for overall stats)
        total_all = await self.db.hazard_reports.count_documents({})

        # Total reports in period
        total_reports = await self.db.hazard_reports.count_documents(match_filter) if match_filter else total_all

        # Previous period filter for comparison
        prev_match_filter = {}
        if date_range != "all":
            prev_match_filter["created_at"] = {
                "$gte": prev_dates["start"],
                "$lte": prev_dates["end"]
            }
        prev_total = await self.db.hazard_reports.count_documents(prev_match_filter) if prev_match_filter else 0

        # Calculate change percentage
        change_pct = 0
        if prev_total > 0:
            change_pct = round(((total_reports - prev_total) / prev_total) * 100, 1)

        # Reports by verification status (try both field names)
        status_pipeline = [
            {"$match": match_filter} if match_filter else {"$match": {}},
            {"$group": {
                "_id": {"$ifNull": ["$verification_status", "$status"]},
                "count": {"$sum": 1}
            }}
        ]
        status_results = await self.db.hazard_reports.aggregate(status_pipeline).to_list(100)
        by_status = {}
        for item in status_results:
            key = item["_id"] or "unknown"
            by_status[key] = item["count"]

        # Verified and pending counts
        verified_count = by_status.get("verified", 0)
        pending_count = by_status.get("pending", 0)

        # Reports by hazard type
        type_pipeline = [
            {"$match": match_filter} if match_filter else {"$match": {}},
            {"$group": {
                "_id": "$hazard_type",
                "count": {"$sum": 1}
            }},
            {"$sort": {"count": -1}}
        ]
        type_results = await self.db.hazard_reports.aggregate(type_pipeline).to_list(100)
        by_hazard_type = {}
        for item in type_results:
            if item["_id"]:
                by_hazard_type[item["_id"]] = item["count"]

        # Reports by region (top 10) - try multiple location fields
        region_pipeline = [
            {"$match": match_filter} if match_filter else {"$match": {}},
            {"$group": {
                "_id": {"$ifNull": ["$location.state", {"$ifNull": ["$location.region", "$location.city"]}]},
                "count": {"$sum": 1}
            }},
            {"$match": {"_id": {"$ne": None}}},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]
        region_results = await self.db.hazard_reports.aggregate(region_pipeline).to_list(100)
        by_region = {}
        for item in region_results:
            if item["_id"]:
                by_region[item["_id"]] = item["count"]

        # High severity count
        high_severity_pipeline = [
            {"$match": match_filter} if match_filter else {"$match": {}},
            {"$match": {
                "$or": [
                    {"severity": {"$in": ["critical", "high", "severe"]}},
                    {"risk_level": {"$in": ["critical", "high"]}},
                    {"urgency": "immediate"}
                ]
            }},
            {"$count": "count"}
        ]
        high_severity_result = await self.db.hazard_reports.aggregate(high_severity_pipeline).to_list(1)
        high_severity_count = high_severity_result[0]["count"] if high_severity_result else 0

        # Get available regions for filters
        regions_list = await self.db.hazard_reports.distinct("location.state")
        regions_list = [r for r in regions_list if r]
        if not regions_list:
            regions_list = await self.db.hazard_reports.distinct("location.region")
            regions_list = [r for r in regions_list if r]

        return {
            "total_reports": total_reports,
            "verified_reports": verified_count,
            "pending_reports": pending_count,
            "high_severity_count": high_severity_count,
            "change_from_previous": {
                "total": change_pct,
                "verified": 0,
                "pending": 0,
                "high_severity": 0
            },
            "by_status": by_status,
            "by_hazard_type": by_hazard_type,
            "by_region": by_region,
            "available_regions": sorted(regions_list),
            "date_range": {
                "start": dates["start"].isoformat(),
                "end": dates["end"].isoformat(),
                "type": date_range
            }
        }

    # =========================================================================
    # TREND ANALYSIS
    # =========================================================================

    async def get_trend_data(
        self,
        date_range: str = "30days",
        group_by: str = "day",
        hazard_type: Optional[str] = None,
        region: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get time-series trend data for charts.

        Args:
            date_range: Time period
            group_by: Grouping interval ('day', 'week', 'month')
            hazard_type: Optional filter
            region: Optional filter

        Returns:
            Time-series data for trend visualization
        """
        dates = self.get_date_range(date_range)

        # Build match filter
        match_filter = {
            "created_at": {"$gte": dates["start"], "$lte": dates["end"]}
        }
        if hazard_type:
            match_filter["hazard_type"] = hazard_type
        if region:
            match_filter["location.region"] = region

        # Determine date grouping format
        if group_by == "week":
            date_format = "%Y-W%V"
            date_group = {
                "year": {"$year": "$created_at"},
                "week": {"$week": "$created_at"}
            }
        elif group_by == "month":
            date_format = "%Y-%m"
            date_group = {
                "year": {"$year": "$created_at"},
                "month": {"$month": "$created_at"}
            }
        else:  # day
            date_format = "%Y-%m-%d"
            date_group = {
                "year": {"$year": "$created_at"},
                "month": {"$month": "$created_at"},
                "day": {"$dayOfMonth": "$created_at"}
            }

        # Aggregation pipeline for time series
        pipeline = [
            {"$match": match_filter},
            {"$group": {
                "_id": date_group,
                "total": {"$sum": 1},
                "verified": {
                    "$sum": {"$cond": [{"$eq": ["$verification_status", "verified"]}, 1, 0]}
                },
                "pending": {
                    "$sum": {"$cond": [{"$eq": ["$verification_status", "pending"]}, 1, 0]}
                },
                "high_priority": {
                    "$sum": {"$cond": [
                        {"$or": [
                            {"$in": ["$risk_level", ["critical", "high"]]},
                            {"$eq": ["$urgency", "immediate"]}
                        ]},
                        1, 0
                    ]}
                }
            }},
            {"$sort": {"_id.year": 1, "_id.month": 1, "_id.day": 1, "_id.week": 1}}
        ]

        results = await self.db.hazard_reports.aggregate(pipeline).to_list(1000)

        # Format results into chart-friendly structure
        timeline = []
        for item in results:
            # Build date string based on grouping
            if group_by == "week":
                date_str = f"{item['_id']['year']}-W{item['_id']['week']:02d}"
            elif group_by == "month":
                date_str = f"{item['_id']['year']}-{item['_id']['month']:02d}"
            else:
                date_str = f"{item['_id']['year']}-{item['_id']['month']:02d}-{item['_id'].get('day', 1):02d}"

            timeline.append({
                "date": date_str,
                "total": item["total"],
                "verified": item["verified"],
                "pending": item["pending"],
                "high_priority": item["high_priority"]
            })

        return {
            "timeline": timeline,
            "group_by": group_by,
            "date_range": {
                "start": dates["start"].isoformat(),
                "end": dates["end"].isoformat()
            }
        }

    # =========================================================================
    # GEOSPATIAL ANALYTICS
    # =========================================================================

    async def get_geospatial_data(
        self,
        date_range: str = "30days",
        hazard_type: Optional[str] = None,
        min_lat: Optional[float] = None,
        max_lat: Optional[float] = None,
        min_lon: Optional[float] = None,
        max_lon: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Get geospatial data for heatmap visualization.

        Returns report locations aggregated into grid cells for heatmap.
        """
        dates = self.get_date_range(date_range)

        # Build match filter - try multiple coordinate field patterns
        match_filter = {
            "created_at": {"$gte": dates["start"], "$lte": dates["end"]}
        }
        if hazard_type:
            match_filter["hazard_type"] = hazard_type

        # Add bounding box filter if provided
        if all([min_lat, max_lat, min_lon, max_lon]):
            match_filter["$or"] = [
                {
                    "location.latitude": {"$gte": min_lat, "$lte": max_lat},
                    "location.longitude": {"$gte": min_lon, "$lte": max_lon}
                },
                {
                    "location.lat": {"$gte": min_lat, "$lte": max_lat},
                    "location.lng": {"$gte": min_lon, "$lte": max_lon}
                }
            ]

        # Get individual report locations - try multiple field patterns
        pipeline = [
            {"$match": match_filter},
            {"$project": {
                "lat": {"$ifNull": ["$location.latitude", {"$ifNull": ["$location.lat", "$latitude"]}]},
                "lng": {"$ifNull": ["$location.longitude", {"$ifNull": ["$location.lng", "$longitude"]}]},
                "hazard_type": 1,
                "risk_level": {"$ifNull": ["$risk_level", "$severity"]},
                "verification_status": {"$ifNull": ["$verification_status", "$status"]},
                "location_name": {"$ifNull": ["$location.address", {"$ifNull": ["$location.name", "$location.city"]}]}
            }},
            {"$match": {
                "lat": {"$exists": True, "$ne": None},
                "lng": {"$exists": True, "$ne": None}
            }},
            {"$limit": 5000}  # Limit for performance
        ]

        results = await self.db.hazard_reports.aggregate(pipeline).to_list(5000)

        # Format for heatmap - use field names expected by frontend
        report_points = []
        for item in results:
            if item.get("lat") and item.get("lng"):
                # Map risk_level to severity
                risk_level = item.get("risk_level", "medium")
                if risk_level in ["critical", "severe"]:
                    severity = "critical"
                elif risk_level == "high":
                    severity = "high"
                elif risk_level == "medium":
                    severity = "medium"
                else:
                    severity = "low"

                report_points.append({
                    "lat": item["lat"],
                    "lng": item["lng"],  # Frontend expects 'lng' not 'lon'
                    "hazard_type": item.get("hazard_type", "unknown"),
                    "severity": severity,  # Frontend expects 'severity' not 'risk_level'
                    "location": item.get("location_name", "Unknown Location")
                })

        # Get region aggregations
        region_pipeline = [
            {"$match": match_filter},
            {"$group": {
                "_id": {"$ifNull": ["$location.region", {"$ifNull": ["$location.state", "$location.city"]}]},
                "count": {"$sum": 1},
                "avg_lat": {"$avg": {"$ifNull": ["$location.latitude", "$location.lat"]}},
                "avg_lng": {"$avg": {"$ifNull": ["$location.longitude", "$location.lng"]}}
            }},
            {"$match": {"_id": {"$ne": None}}},
            {"$sort": {"count": -1}},
            {"$limit": 20}
        ]
        region_results = await self.db.hazard_reports.aggregate(region_pipeline).to_list(100)

        regions = []
        for item in region_results:
            if item["_id"] and item.get("avg_lat") and item.get("avg_lng"):
                regions.append({
                    "name": item["_id"],
                    "count": item["count"],
                    "center": {
                        "lat": item["avg_lat"],
                        "lng": item["avg_lng"]
                    }
                })

        return {
            "report_points": report_points,
            "regions": regions,
            "total_points": len(report_points),
            "date_range": {
                "start": dates["start"].isoformat(),
                "end": dates["end"].isoformat()
            }
        }

    # =========================================================================
    # NLP INSIGHTS
    # =========================================================================

    async def get_nlp_insights(
        self,
        date_range: str = "30days",
        hazard_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get aggregated NLP insights from reports.

        Returns sentiment analysis, keyword frequencies, and risk scores.
        """
        dates = self.get_date_range(date_range)

        match_filter = {
            "created_at": {"$gte": dates["start"], "$lte": dates["end"]}
        }
        if hazard_type:
            match_filter["hazard_type"] = hazard_type

        # Sentiment distribution
        sentiment_pipeline = [
            {"$match": {**match_filter, "nlp_sentiment": {"$exists": True}}},
            {"$group": {
                "_id": "$nlp_sentiment",
                "count": {"$sum": 1}
            }}
        ]
        sentiment_results = await self.db.hazard_reports.aggregate(sentiment_pipeline).to_list(100)
        sentiment_dist = {item["_id"]: item["count"] for item in sentiment_results if item["_id"]}

        # Average risk score
        risk_pipeline = [
            {"$match": {**match_filter, "nlp_risk_score": {"$exists": True, "$ne": None}}},
            {"$group": {
                "_id": None,
                "avg_risk": {"$avg": "$nlp_risk_score"},
                "max_risk": {"$max": "$nlp_risk_score"},
                "min_risk": {"$min": "$nlp_risk_score"},
                "count": {"$sum": 1}
            }}
        ]
        risk_results = await self.db.hazard_reports.aggregate(risk_pipeline).to_list(1)
        risk_stats = risk_results[0] if risk_results else {"avg_risk": 0, "max_risk": 0, "min_risk": 0, "count": 0}

        # Keyword frequency (aggregate from nlp_keywords arrays)
        keyword_pipeline = [
            {"$match": {**match_filter, "nlp_keywords": {"$exists": True, "$ne": []}}},
            {"$unwind": "$nlp_keywords"},
            {"$group": {
                "_id": "$nlp_keywords",
                "count": {"$sum": 1}
            }},
            {"$sort": {"count": -1}},
            {"$limit": 30}
        ]
        keyword_results = await self.db.hazard_reports.aggregate(keyword_pipeline).to_list(100)
        top_keywords = [{"keyword": item["_id"], "count": item["count"]} for item in keyword_results if item["_id"]]

        # Risk score distribution (buckets)
        risk_dist_pipeline = [
            {"$match": {**match_filter, "nlp_risk_score": {"$exists": True, "$ne": None}}},
            {"$bucket": {
                "groupBy": "$nlp_risk_score",
                "boundaries": [0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.1],
                "default": "other",
                "output": {"count": {"$sum": 1}}
            }}
        ]
        risk_dist_results = await self.db.hazard_reports.aggregate(risk_dist_pipeline).to_list(100)
        risk_distribution = []
        bucket_labels = ["Very Low (0-0.2)", "Low (0.2-0.4)", "Medium (0.4-0.6)", "High (0.6-0.8)", "Critical (0.8-1.0)"]
        for i, item in enumerate(risk_dist_results):
            if item["_id"] != "other" and i < len(bucket_labels):
                risk_distribution.append({
                    "range": bucket_labels[i],
                    "count": item["count"]
                })

        return {
            "sentiment_distribution": sentiment_dist,
            "risk_statistics": {
                "average": round(risk_stats.get("avg_risk", 0) or 0, 3),
                "maximum": round(risk_stats.get("max_risk", 0) or 0, 3),
                "minimum": round(risk_stats.get("min_risk", 0) or 0, 3),
                "reports_analyzed": risk_stats.get("count", 0)
            },
            "top_keywords": top_keywords,
            "risk_distribution": risk_distribution,
            "date_range": {
                "start": dates["start"].isoformat(),
                "end": dates["end"].isoformat()
            }
        }

    # =========================================================================
    # VERIFICATION METRICS
    # =========================================================================

    async def get_verification_metrics(
        self,
        date_range: str = "30days"
    ) -> Dict[str, Any]:
        """
        Get verification performance metrics.

        Returns response times, verification rates, and verifier statistics.
        """
        dates = self.get_date_range(date_range)

        match_filter = {
            "created_at": {"$gte": dates["start"], "$lte": dates["end"]}
        }

        # Total and verified counts
        total = await self.db.hazard_reports.count_documents(match_filter)
        verified = await self.db.hazard_reports.count_documents({
            **match_filter,
            "verification_status": "verified"
        })
        rejected = await self.db.hazard_reports.count_documents({
            **match_filter,
            "verification_status": "rejected"
        })

        # Average response time (verified_at - created_at)
        response_pipeline = [
            {"$match": {
                **match_filter,
                "verification_status": {"$in": ["verified", "rejected"]},
                "verified_at": {"$exists": True}
            }},
            {"$project": {
                "response_time": {
                    "$subtract": ["$verified_at", "$created_at"]
                }
            }},
            {"$group": {
                "_id": None,
                "avg_response_ms": {"$avg": "$response_time"},
                "min_response_ms": {"$min": "$response_time"},
                "max_response_ms": {"$max": "$response_time"}
            }}
        ]
        response_results = await self.db.hazard_reports.aggregate(response_pipeline).to_list(1)
        response_stats = response_results[0] if response_results else {}

        # Convert ms to hours
        avg_response_hours = 0
        if response_stats.get("avg_response_ms"):
            avg_response_hours = round(response_stats["avg_response_ms"] / (1000 * 60 * 60), 1)

        # Top verifiers
        verifier_pipeline = [
            {"$match": {
                **match_filter,
                "verified_by": {"$exists": True, "$ne": None}
            }},
            {"$group": {
                "_id": "$verified_by",
                "count": {"$sum": 1}
            }},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]
        verifier_results = await self.db.hazard_reports.aggregate(verifier_pipeline).to_list(100)
        # Note: We don't expose verifier names (PII) to analysts, just IDs
        top_verifiers = [{"id": item["_id"], "count": item["count"]} for item in verifier_results if item["_id"]]

        # Active reporters (unique users who submitted reports)
        reporter_pipeline = [
            {"$match": match_filter},
            {"$group": {
                "_id": "$user_id"
            }},
            {"$count": "total"}
        ]
        reporter_results = await self.db.hazard_reports.aggregate(reporter_pipeline).to_list(1)
        active_reporters = reporter_results[0]["total"] if reporter_results else 0

        return {
            "total_reports": total,
            "verified_reports": verified,
            "rejected_reports": rejected,
            "pending_reports": total - verified - rejected,
            "verification_rate": round((verified / max(total, 1)) * 100, 1),
            "rejection_rate": round((rejected / max(total, 1)) * 100, 1),
            "avg_response_time_hours": avg_response_hours,
            "active_reporters": active_reporters,
            "top_verifiers": top_verifiers,
            "date_range": {
                "start": dates["start"].isoformat(),
                "end": dates["end"].isoformat()
            }
        }

    # =========================================================================
    # HAZARD TYPE ANALYTICS
    # =========================================================================

    async def get_hazard_type_analytics(
        self,
        date_range: str = "30days"
    ) -> Dict[str, Any]:
        """
        Get detailed analytics by hazard type.
        """
        dates = self.get_date_range(date_range)

        match_filter = {
            "created_at": {"$gte": dates["start"], "$lte": dates["end"]}
        }

        pipeline = [
            {"$match": match_filter},
            {"$group": {
                "_id": "$hazard_type",
                "total": {"$sum": 1},
                "verified": {
                    "$sum": {"$cond": [{"$eq": ["$verification_status", "verified"]}, 1, 0]}
                },
                "high_risk": {
                    "$sum": {"$cond": [{"$in": ["$risk_level", ["critical", "high"]]}, 1, 0]}
                },
                "avg_risk_score": {"$avg": "$nlp_risk_score"}
            }},
            {"$sort": {"total": -1}}
        ]

        results = await self.db.hazard_reports.aggregate(pipeline).to_list(100)

        hazard_types = []
        for item in results:
            if item["_id"]:
                hazard_types.append({
                    "type": item["_id"],
                    "total": item["total"],
                    "verified": item["verified"],
                    "high_risk": item["high_risk"],
                    "verification_rate": round((item["verified"] / max(item["total"], 1)) * 100, 1),
                    "avg_risk_score": round(item["avg_risk_score"] or 0, 3)
                })

        return {
            "hazard_types": hazard_types,
            "date_range": {
                "start": dates["start"].isoformat(),
                "end": dates["end"].isoformat()
            }
        }

    # =========================================================================
    # COMPARISON ANALYTICS
    # =========================================================================

    async def get_period_comparison(
        self,
        current_range: str = "7days",
        hazard_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Compare current period with previous period.
        """
        current_dates = self.get_date_range(current_range)
        previous_dates = self.get_previous_period(current_dates["start"], current_dates["end"])

        async def get_period_stats(start: datetime, end: datetime) -> Dict:
            match_filter = {
                "created_at": {"$gte": start, "$lte": end}
            }
            if hazard_type:
                match_filter["hazard_type"] = hazard_type

            total = await self.db.hazard_reports.count_documents(match_filter)
            verified = await self.db.hazard_reports.count_documents({
                **match_filter, "verification_status": "verified"
            })
            high_priority = await self.db.hazard_reports.count_documents({
                **match_filter,
                "$or": [
                    {"risk_level": {"$in": ["critical", "high"]}},
                    {"urgency": "immediate"}
                ]
            })

            return {
                "total": total,
                "verified": verified,
                "high_priority": high_priority,
                "verification_rate": round((verified / max(total, 1)) * 100, 1)
            }

        current_stats = await get_period_stats(current_dates["start"], current_dates["end"])
        previous_stats = await get_period_stats(previous_dates["start"], previous_dates["end"])

        def calc_change(current: int, previous: int) -> float:
            if previous == 0:
                return 100 if current > 0 else 0
            return round(((current - previous) / previous) * 100, 1)

        return {
            "current_period": {
                "start": current_dates["start"].isoformat(),
                "end": current_dates["end"].isoformat(),
                "stats": current_stats
            },
            "previous_period": {
                "start": previous_dates["start"].isoformat(),
                "end": previous_dates["end"].isoformat(),
                "stats": previous_stats
            },
            "changes": {
                "total": calc_change(current_stats["total"], previous_stats["total"]),
                "verified": calc_change(current_stats["verified"], previous_stats["verified"]),
                "high_priority": calc_change(current_stats["high_priority"], previous_stats["high_priority"])
            }
        }


# Singleton instance helper
_analytics_service: Optional[AnalyticsService] = None


def get_analytics_service(db: AsyncIOMotorDatabase) -> AnalyticsService:
    """Get or create analytics service instance."""
    global _analytics_service
    if _analytics_service is None or _analytics_service.db != db:
        _analytics_service = AnalyticsService(db)
    return _analytics_service


__all__ = [
    'AnalyticsService',
    'get_analytics_service'
]

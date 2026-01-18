"""
Database migrations module
Handles database schema changes and data migrations
"""

from .location_index import fix_location_index

__all__ = ["fix_location_index"]

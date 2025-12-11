"""Data models for AirSight."""

from .air_reading import AirReading
from .location import Location
from .alert import Alert, AlertType
from .query_result import QueryResult

__all__ = [
    "AirReading",
    "Location", 
    "Alert",
    "AlertType",
    "QueryResult",
]


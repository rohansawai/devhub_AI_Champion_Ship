"""
Location data model.
Represents a geographic location with air quality monitoring sensors.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class Location:
    """
    Represents a geographic location for air quality monitoring.
    
    Attributes:
        id: Unique identifier from OpenAQ
        name: Human-readable name of the location
        city: City name
        country: Country name
        latitude: Geographic latitude
        longitude: Geographic longitude
        sensors: List of sensor IDs at this location
        is_mobile: Whether this is a mobile monitoring station
        is_active: Whether the location is currently active
    """
    
    id: int
    name: str
    city: str
    country: str
    latitude: float
    longitude: float
    sensors: List[int] = field(default_factory=list)
    is_mobile: bool = False
    is_active: bool = True
    
    @classmethod
    def from_openaq(cls, data: Dict[str, Any]) -> "Location":
        """
        Create Location from OpenAQ API response.
        
        Args:
            data: Dictionary from OpenAQ /locations endpoint
            
        Returns:
            Location instance
        """
        # Extract coordinates
        coordinates = data.get("coordinates", {})
        latitude = coordinates.get("latitude", 0.0)
        longitude = coordinates.get("longitude", 0.0)
        
        # Extract country name
        country_data = data.get("country", {})
        if isinstance(country_data, dict):
            country = country_data.get("name", "Unknown")
        else:
            country = str(country_data) if country_data else "Unknown"
        
        # Extract sensor IDs
        sensors = []
        for sensor in data.get("sensors", []):
            if isinstance(sensor, dict):
                sensor_id = sensor.get("id")
                if sensor_id:
                    sensors.append(sensor_id)
            elif isinstance(sensor, int):
                sensors.append(sensor)
        
        return cls(
            id=data.get("id", 0),
            name=data.get("name", "Unknown"),
            city=data.get("city", "Unknown") or "Unknown",
            country=country,
            latitude=latitude,
            longitude=longitude,
            sensors=sensors,
            is_mobile=data.get("isMobile", False),
            is_active=data.get("isActive", True),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "city": self.city,
            "country": self.country,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "sensors": self.sensors,
            "is_mobile": self.is_mobile,
            "is_active": self.is_active,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Location":
        """Create Location from dictionary."""
        return cls(
            id=data.get("id", 0),
            name=data.get("name", "Unknown"),
            city=data.get("city", "Unknown"),
            country=data.get("country", "Unknown"),
            latitude=data.get("latitude", 0.0),
            longitude=data.get("longitude", 0.0),
            sensors=data.get("sensors", []),
            is_mobile=data.get("is_mobile", False),
            is_active=data.get("is_active", True),
        )
    
    def distance_to(self, latitude: float, longitude: float) -> float:
        """
        Calculate approximate distance to another point in kilometers.
        
        Uses Haversine formula for spherical distance.
        
        Args:
            latitude: Target latitude
            longitude: Target longitude
            
        Returns:
            Distance in kilometers
        """
        import math
        
        # Earth's radius in kilometers
        R = 6371.0
        
        lat1 = math.radians(self.latitude)
        lat2 = math.radians(latitude)
        dlat = math.radians(latitude - self.latitude)
        dlon = math.radians(longitude - self.longitude)
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def __str__(self) -> str:
        """Human-readable string representation."""
        status = "🟢 Active" if self.is_active else "🔴 Inactive"
        mobile = " (Mobile)" if self.is_mobile else ""
        return f"{self.name}, {self.city}, {self.country}{mobile} | {status} | {len(self.sensors)} sensors"


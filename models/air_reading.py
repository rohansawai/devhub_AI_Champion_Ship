"""
Air quality reading data model.
Represents a single measurement from an air quality sensor.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class AirReading:
    """
    Represents a single air quality measurement.
    
    Attributes:
        location_id: Unique identifier for the monitoring location
        location_name: Human-readable name of the location
        city: City where the measurement was taken
        country: Country where the measurement was taken
        latitude: Geographic latitude
        longitude: Geographic longitude
        pm25: PM2.5 particulate matter (μg/m³)
        pm10: PM10 particulate matter (μg/m³)
        ozone: Ozone O3 (ppm)
        no2: Nitrogen dioxide (ppm)
        co: Carbon monoxide (ppm)
        so2: Sulfur dioxide (ppm)
        timestamp: When the measurement was taken
        aqi: Calculated Air Quality Index
    """
    
    # Location info
    location_id: int
    location_name: str
    city: str
    country: str
    latitude: float
    longitude: float
    
    # Measurements (all optional as not all sensors measure everything)
    pm25: Optional[float] = None
    pm10: Optional[float] = None
    ozone: Optional[float] = None
    no2: Optional[float] = None
    co: Optional[float] = None
    so2: Optional[float] = None
    
    # Metadata
    timestamp: Optional[datetime] = None
    aqi: Optional[int] = None
    
    def __post_init__(self):
        """Calculate AQI if not provided."""
        if self.aqi is None and self.pm25 is not None:
            self.aqi = self.calculate_aqi()
    
    def calculate_aqi(self) -> Optional[int]:
        """
        Calculate Air Quality Index from PM2.5.
        
        Uses US EPA breakpoints for PM2.5 to AQI conversion.
        
        Returns:
            AQI value (0-500+) or None if PM2.5 not available
        """
        if self.pm25 is None:
            return None
        
        pm = self.pm25
        
        # EPA breakpoints for PM2.5 (24-hour average)
        breakpoints = [
            (0.0, 12.0, 0, 50),        # Good
            (12.1, 35.4, 51, 100),     # Moderate
            (35.5, 55.4, 101, 150),    # Unhealthy for Sensitive Groups
            (55.5, 150.4, 151, 200),   # Unhealthy
            (150.5, 250.4, 201, 300),  # Very Unhealthy
            (250.5, 350.4, 301, 400),  # Hazardous
            (350.5, 500.4, 401, 500),  # Hazardous
        ]
        
        for pm_low, pm_high, aqi_low, aqi_high in breakpoints:
            if pm_low <= pm <= pm_high:
                # Linear interpolation
                aqi = ((aqi_high - aqi_low) / (pm_high - pm_low)) * (pm - pm_low) + aqi_low
                return int(round(aqi))
        
        # If PM2.5 > 500.4, return 500+
        if pm > 500.4:
            return 500
        
        return None
    
    def get_health_category(self) -> str:
        """
        Get health category based on AQI.
        
        Returns:
            Human-readable health category
        """
        aqi = self.aqi if self.aqi is not None else self.calculate_aqi()
        
        if aqi is None:
            return "Unknown"
        
        if aqi <= 50:
            return "Good"
        elif aqi <= 100:
            return "Moderate"
        elif aqi <= 150:
            return "Unhealthy for Sensitive Groups"
        elif aqi <= 200:
            return "Unhealthy"
        elif aqi <= 300:
            return "Very Unhealthy"
        else:
            return "Hazardous"
    
    def get_health_color(self) -> str:
        """Get color code for the health category."""
        category = self.get_health_category()
        colors = {
            "Good": "🟢",
            "Moderate": "🟡",
            "Unhealthy for Sensitive Groups": "🟠",
            "Unhealthy": "🔴",
            "Very Unhealthy": "🟣",
            "Hazardous": "🟤",
            "Unknown": "⚪",
        }
        return colors.get(category, "⚪")
    
    def get_health_advice(self) -> str:
        """Get health advice based on AQI level."""
        category = self.get_health_category()
        advice = {
            "Good": "Air quality is satisfactory. Enjoy outdoor activities!",
            "Moderate": "Air quality is acceptable. Unusually sensitive people should consider reducing prolonged outdoor exertion.",
            "Unhealthy for Sensitive Groups": "Members of sensitive groups may experience health effects. General public is less likely to be affected.",
            "Unhealthy": "Everyone may begin to experience health effects. Sensitive groups may experience more serious effects.",
            "Very Unhealthy": "Health alert! Everyone may experience more serious health effects. Avoid outdoor activities.",
            "Hazardous": "Health emergency! Everyone is more likely to be affected. Stay indoors and keep windows closed.",
            "Unknown": "Unable to determine air quality. Check local sources for more information.",
        }
        return advice.get(category, "No advice available.")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/serialization."""
        return {
            "location_id": self.location_id,
            "location_name": self.location_name,
            "city": self.city,
            "country": self.country,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "pm25": self.pm25,
            "pm10": self.pm10,
            "ozone": self.ozone,
            "no2": self.no2,
            "co": self.co,
            "so2": self.so2,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "aqi": self.aqi,
            "health_category": self.get_health_category(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AirReading":
        """Create AirReading from dictionary."""
        timestamp = None
        if data.get("timestamp"):
            if isinstance(data["timestamp"], str):
                timestamp = datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
            elif isinstance(data["timestamp"], datetime):
                timestamp = data["timestamp"]
        
        return cls(
            location_id=data.get("location_id", 0),
            location_name=data.get("location_name", "Unknown"),
            city=data.get("city", "Unknown"),
            country=data.get("country", "Unknown"),
            latitude=data.get("latitude", 0.0),
            longitude=data.get("longitude", 0.0),
            pm25=data.get("pm25"),
            pm10=data.get("pm10"),
            ozone=data.get("ozone"),
            no2=data.get("no2"),
            co=data.get("co"),
            so2=data.get("so2"),
            timestamp=timestamp,
            aqi=data.get("aqi"),
        )
    
    def __str__(self) -> str:
        """Human-readable string representation."""
        aqi_str = f"AQI: {self.aqi}" if self.aqi else "AQI: N/A"
        pm_str = f"PM2.5: {self.pm25:.1f} μg/m³" if self.pm25 else "PM2.5: N/A"
        return f"{self.get_health_color()} {self.location_name}, {self.city} | {pm_str} | {aqi_str} | {self.get_health_category()}"


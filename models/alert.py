"""
Alert data model.
Represents user-defined alerts for air quality thresholds.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, TYPE_CHECKING
from enum import Enum
import uuid

if TYPE_CHECKING:
    from .air_reading import AirReading


class AlertType(Enum):
    """Types of alerts that can be configured."""
    
    PM25_THRESHOLD = "pm25_threshold"
    PM10_THRESHOLD = "pm10_threshold"
    AQI_THRESHOLD = "aqi_threshold"
    OZONE_THRESHOLD = "ozone_threshold"
    ANOMALY = "anomaly"
    
    def get_display_name(self) -> str:
        """Get human-readable name for the alert type."""
        names = {
            AlertType.PM25_THRESHOLD: "PM2.5 Threshold",
            AlertType.PM10_THRESHOLD: "PM10 Threshold",
            AlertType.AQI_THRESHOLD: "AQI Threshold",
            AlertType.OZONE_THRESHOLD: "Ozone Threshold",
            AlertType.ANOMALY: "Anomaly Detection",
        }
        return names.get(self, self.value)


class AlertSeverity(Enum):
    """Severity levels for alerts."""
    
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    
    def get_emoji(self) -> str:
        """Get emoji for the severity level."""
        emojis = {
            AlertSeverity.INFO: "ℹ️",
            AlertSeverity.WARNING: "⚠️",
            AlertSeverity.CRITICAL: "🚨",
        }
        return emojis.get(self, "❓")


@dataclass
class Alert:
    """
    Represents a user-defined alert configuration.
    
    Attributes:
        id: Unique identifier for the alert
        user_id: ID of the user who created the alert
        location_name: Name of the location to monitor
        alert_type: Type of threshold to monitor
        threshold: Threshold value that triggers the alert
        is_active: Whether the alert is currently active
        created_at: When the alert was created
        last_triggered: When the alert was last triggered
        trigger_count: Number of times the alert has been triggered
    """
    
    id: str
    user_id: str
    location_name: str
    alert_type: AlertType
    threshold: float
    is_active: bool = True
    created_at: Optional[datetime] = None
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0
    
    def __post_init__(self):
        """Set default values after initialization."""
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if not self.id:
            self.id = str(uuid.uuid4())
    
    def should_trigger(self, reading: "AirReading") -> bool:
        """
        Check if this alert should trigger for a given reading.
        
        Args:
            reading: Air quality reading to check
            
        Returns:
            True if the alert should trigger
        """
        if not self.is_active:
            return False
        
        if self.alert_type == AlertType.PM25_THRESHOLD:
            return reading.pm25 is not None and reading.pm25 > self.threshold
        
        elif self.alert_type == AlertType.PM10_THRESHOLD:
            return reading.pm10 is not None and reading.pm10 > self.threshold
        
        elif self.alert_type == AlertType.AQI_THRESHOLD:
            aqi = reading.aqi if reading.aqi is not None else reading.calculate_aqi()
            return aqi is not None and aqi > self.threshold
        
        elif self.alert_type == AlertType.OZONE_THRESHOLD:
            return reading.ozone is not None and reading.ozone > self.threshold
        
        return False
    
    def get_severity(self, reading: "AirReading") -> AlertSeverity:
        """
        Determine severity based on how much the threshold is exceeded.
        
        Args:
            reading: Air quality reading
            
        Returns:
            Alert severity level
        """
        value = None
        
        if self.alert_type == AlertType.PM25_THRESHOLD:
            value = reading.pm25
        elif self.alert_type == AlertType.PM10_THRESHOLD:
            value = reading.pm10
        elif self.alert_type == AlertType.AQI_THRESHOLD:
            value = reading.aqi if reading.aqi else reading.calculate_aqi()
        elif self.alert_type == AlertType.OZONE_THRESHOLD:
            value = reading.ozone
        
        if value is None:
            return AlertSeverity.INFO
        
        # Calculate how much the threshold is exceeded
        ratio = value / self.threshold if self.threshold > 0 else 0
        
        if ratio >= 2.0:
            return AlertSeverity.CRITICAL
        elif ratio >= 1.5:
            return AlertSeverity.WARNING
        else:
            return AlertSeverity.INFO
    
    def trigger(self) -> None:
        """Mark the alert as triggered."""
        self.last_triggered = datetime.utcnow()
        self.trigger_count += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/serialization."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "location_name": self.location_name,
            "alert_type": self.alert_type.value,
            "threshold": self.threshold,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_triggered": self.last_triggered.isoformat() if self.last_triggered else None,
            "trigger_count": self.trigger_count,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Alert":
        """Create Alert from dictionary."""
        created_at = None
        if data.get("created_at"):
            created_at = datetime.fromisoformat(data["created_at"])
        
        last_triggered = None
        if data.get("last_triggered"):
            last_triggered = datetime.fromisoformat(data["last_triggered"])
        
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            user_id=data.get("user_id", ""),
            location_name=data.get("location_name", ""),
            alert_type=AlertType(data.get("alert_type", "pm25_threshold")),
            threshold=data.get("threshold", 0.0),
            is_active=data.get("is_active", True),
            created_at=created_at,
            last_triggered=last_triggered,
            trigger_count=data.get("trigger_count", 0),
        )
    
    def format_message(self, reading: "AirReading") -> str:
        """
        Format an alert message for display.
        
        Args:
            reading: The reading that triggered the alert
            
        Returns:
            Formatted alert message
        """
        severity = self.get_severity(reading)
        emoji = severity.get_emoji()
        
        value = None
        unit = ""
        
        if self.alert_type == AlertType.PM25_THRESHOLD:
            value = reading.pm25
            unit = "μg/m³"
        elif self.alert_type == AlertType.PM10_THRESHOLD:
            value = reading.pm10
            unit = "μg/m³"
        elif self.alert_type == AlertType.AQI_THRESHOLD:
            value = reading.aqi if reading.aqi else reading.calculate_aqi()
            unit = ""
        elif self.alert_type == AlertType.OZONE_THRESHOLD:
            value = reading.ozone
            unit = "ppm"
        
        return (
            f"{emoji} **{severity.value.upper()} ALERT**\n\n"
            f"Location: {self.location_name}\n"
            f"Type: {self.alert_type.get_display_name()}\n"
            f"Current Value: {value:.1f} {unit}\n"
            f"Threshold: {self.threshold:.1f} {unit}\n"
            f"Health Category: {reading.get_health_category()}"
        )
    
    def __str__(self) -> str:
        """Human-readable string representation."""
        status = "🟢 Active" if self.is_active else "🔴 Inactive"
        return f"Alert: {self.location_name} | {self.alert_type.get_display_name()} > {self.threshold} | {status}"


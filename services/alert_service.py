"""
Alert Service.
Manages user alerts for air quality thresholds.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

from clients.raindrop_client import RaindropClient
from models.alert import Alert, AlertType, AlertSeverity
from models.air_reading import AirReading
from config.settings import settings


class AlertService:
    """
    Service for managing user alerts.
    
    Responsibilities:
    - Create, update, delete alert configurations
    - Check if readings trigger alerts
    - Store alert configs in SmartMemory
    - Track alert history
    
    Usage:
        service = AlertService(raindrop_client)
        alert = service.create_alert(
            user_id="user1",
            location_name="Delhi",
            alert_type=AlertType.PM25_THRESHOLD,
            threshold=100.0
        )
        triggered = service.check_alerts("user1", readings)
    """
    
    MEMORY_KEY_ALERTS = "alerts"
    MEMORY_KEY_HISTORY = "alert_history"
    
    def __init__(self, raindrop: RaindropClient):
        """
        Initialize the alert service.
        
        Args:
            raindrop: Raindrop client for storage
        """
        self.raindrop = raindrop
    
    # =========================================
    # Alert CRUD Operations
    # =========================================
    
    def create_alert(
        self,
        user_id: str,
        location_name: str,
        alert_type: AlertType,
        threshold: float,
    ) -> Alert:
        """
        Create a new alert for a user.
        
        Args:
            user_id: User identifier
            location_name: Location to monitor (city name)
            alert_type: Type of threshold to monitor
            threshold: Threshold value
            
        Returns:
            Created Alert object
        """
        alert = Alert(
            id=str(uuid.uuid4()),
            user_id=user_id,
            location_name=location_name,
            alert_type=alert_type,
            threshold=threshold,
            is_active=True,
            created_at=datetime.utcnow(),
        )
        
        # Get existing alerts and add new one
        alerts = self.get_user_alerts(user_id)
        alerts.append(alert)
        
        # Store in SmartMemory
        self._save_alerts(user_id, alerts)
        
        if settings.debug:
            print(f"[AlertService] Created alert for {user_id}: {alert}")
        
        return alert
    
    def get_user_alerts(self, user_id: str) -> List[Alert]:
        """
        Get all alerts for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of Alert objects
        """
        alerts_data = self.raindrop.memory.retrieve(
            key=self.MEMORY_KEY_ALERTS,
            user_id=user_id,
        )
        
        if not alerts_data:
            return []
        
        return [Alert.from_dict(a) for a in alerts_data]
    
    def get_alert_by_id(self, user_id: str, alert_id: str) -> Optional[Alert]:
        """
        Get a specific alert by ID.
        
        Args:
            user_id: User identifier
            alert_id: Alert identifier
            
        Returns:
            Alert object or None
        """
        alerts = self.get_user_alerts(user_id)
        for alert in alerts:
            if alert.id == alert_id:
                return alert
        return None
    
    def update_alert(
        self,
        user_id: str,
        alert_id: str,
        threshold: float = None,
        is_active: bool = None,
    ) -> Optional[Alert]:
        """
        Update an existing alert.
        
        Args:
            user_id: User identifier
            alert_id: Alert identifier
            threshold: New threshold (optional)
            is_active: New active status (optional)
            
        Returns:
            Updated Alert or None if not found
        """
        alerts = self.get_user_alerts(user_id)
        updated_alert = None
        
        for alert in alerts:
            if alert.id == alert_id:
                if threshold is not None:
                    alert.threshold = threshold
                if is_active is not None:
                    alert.is_active = is_active
                updated_alert = alert
                break
        
        if updated_alert:
            self._save_alerts(user_id, alerts)
        
        return updated_alert
    
    def delete_alert(self, user_id: str, alert_id: str) -> bool:
        """
        Delete an alert.
        
        Args:
            user_id: User identifier
            alert_id: Alert identifier
            
        Returns:
            True if deleted, False if not found
        """
        alerts = self.get_user_alerts(user_id)
        original_count = len(alerts)
        
        alerts = [a for a in alerts if a.id != alert_id]
        
        if len(alerts) < original_count:
            self._save_alerts(user_id, alerts)
            return True
        
        return False
    
    def toggle_alert(self, user_id: str, alert_id: str) -> Optional[Alert]:
        """
        Toggle an alert's active status.
        
        Args:
            user_id: User identifier
            alert_id: Alert identifier
            
        Returns:
            Updated Alert or None
        """
        alert = self.get_alert_by_id(user_id, alert_id)
        if alert:
            return self.update_alert(user_id, alert_id, is_active=not alert.is_active)
        return None
    
    # =========================================
    # Alert Checking
    # =========================================
    
    def check_alerts(
        self,
        user_id: str,
        readings: List[AirReading],
    ) -> List[Dict[str, Any]]:
        """
        Check if any alerts should trigger for the given readings.
        
        Args:
            user_id: User identifier
            readings: Air quality readings to check
            
        Returns:
            List of triggered alert info dictionaries
        """
        alerts = self.get_user_alerts(user_id)
        triggered = []
        
        for alert in alerts:
            if not alert.is_active:
                continue
            
            for reading in readings:
                # Check if location matches (case-insensitive)
                location_match = (
                    reading.city.lower() == alert.location_name.lower() or
                    reading.location_name.lower() == alert.location_name.lower()
                )
                
                if location_match and alert.should_trigger(reading):
                    # Mark alert as triggered
                    alert.trigger()
                    
                    triggered.append({
                        "alert": alert,
                        "reading": reading,
                        "severity": alert.get_severity(reading),
                        "message": alert.format_message(reading),
                    })
        
        # Save updated alerts (with trigger counts)
        if triggered:
            self._save_alerts(user_id, alerts)
            self._save_to_history(user_id, triggered)
        
        return triggered
    
    def check_city(self, user_id: str, city: str, reading: AirReading) -> List[Dict[str, Any]]:
        """
        Check alerts for a specific city.
        
        Args:
            user_id: User identifier
            city: City name
            reading: Current air quality reading
            
        Returns:
            List of triggered alert info
        """
        return self.check_alerts(user_id, [reading])
    
    # =========================================
    # Alert History
    # =========================================
    
    def get_alert_history(
        self,
        user_id: str,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Get alert trigger history for a user.
        
        Args:
            user_id: User identifier
            limit: Maximum number of entries
            
        Returns:
            List of historical alert triggers
        """
        history = self.raindrop.memory.retrieve(
            key=self.MEMORY_KEY_HISTORY,
            user_id=user_id,
        )
        
        if not history:
            return []
        
        return history[:limit]
    
    def clear_history(self, user_id: str) -> bool:
        """Clear alert history for a user."""
        return self.raindrop.memory.delete(
            key=self.MEMORY_KEY_HISTORY,
            user_id=user_id,
        )
    
    # =========================================
    # Statistics
    # =========================================
    
    def get_alert_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Get alert statistics for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Statistics dictionary
        """
        alerts = self.get_user_alerts(user_id)
        history = self.get_alert_history(user_id, limit=100)
        
        active_alerts = [a for a in alerts if a.is_active]
        
        return {
            "total_alerts": len(alerts),
            "active_alerts": len(active_alerts),
            "inactive_alerts": len(alerts) - len(active_alerts),
            "total_triggers": sum(a.trigger_count for a in alerts),
            "recent_triggers": len(history),
            "most_triggered": max(
                alerts, 
                key=lambda a: a.trigger_count,
                default=None
            ),
            "locations_monitored": list(set(a.location_name for a in alerts)),
        }
    
    # =========================================
    # Preset Alerts
    # =========================================
    
    def create_preset_alerts(
        self,
        user_id: str,
        location: str,
    ) -> List[Alert]:
        """
        Create a set of preset alerts for common thresholds.
        
        Creates alerts for:
        - PM2.5 > 35 (Moderate)
        - PM2.5 > 55 (Unhealthy for Sensitive)
        - PM2.5 > 150 (Unhealthy)
        - AQI > 100 (Moderate)
        - AQI > 150 (Unhealthy)
        
        Args:
            user_id: User identifier
            location: Location to monitor
            
        Returns:
            List of created alerts
        """
        presets = [
            (AlertType.PM25_THRESHOLD, 35.0, "Moderate PM2.5"),
            (AlertType.PM25_THRESHOLD, 55.0, "Unhealthy PM2.5 for Sensitive"),
            (AlertType.PM25_THRESHOLD, 150.0, "Unhealthy PM2.5"),
            (AlertType.AQI_THRESHOLD, 100.0, "Moderate AQI"),
            (AlertType.AQI_THRESHOLD, 150.0, "Unhealthy AQI"),
        ]
        
        created = []
        for alert_type, threshold, _ in presets:
            alert = self.create_alert(
                user_id=user_id,
                location_name=location,
                alert_type=alert_type,
                threshold=threshold,
            )
            created.append(alert)
        
        return created
    
    # =========================================
    # Helper Methods
    # =========================================
    
    def _save_alerts(self, user_id: str, alerts: List[Alert]):
        """Save alerts to SmartMemory."""
        alerts_data = [a.to_dict() for a in alerts]
        self.raindrop.memory.store(
            key=self.MEMORY_KEY_ALERTS,
            value=alerts_data,
            user_id=user_id,
        )
    
    def _save_to_history(self, user_id: str, triggered: List[Dict]):
        """Save triggered alerts to history."""
        history = self.get_alert_history(user_id, limit=100) or []
        
        for item in triggered:
            history.insert(0, {
                "alert_id": item["alert"].id,
                "location": item["alert"].location_name,
                "alert_type": item["alert"].alert_type.value,
                "threshold": item["alert"].threshold,
                "severity": item["severity"].value,
                "reading_pm25": item["reading"].pm25,
                "reading_aqi": item["reading"].aqi,
                "timestamp": datetime.utcnow().isoformat(),
            })
        
        # Keep only last 100 entries
        history = history[:100]
        
        self.raindrop.memory.store(
            key=self.MEMORY_KEY_HISTORY,
            value=history,
            user_id=user_id,
        )


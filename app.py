"""
AirSight - Real-Time Air Quality Intelligence
Main Application Entry Point

This is the main orchestrator that ties together all components:
- OpenAQ Client for data fetching
- Raindrop Client for storage and AI
- Services for business logic

Usage:
    from app import AirSightApp
    
    app = AirSightApp()
    app.initialize()
    
    # Ask questions
    result = app.ask("Is the air safe in Tokyo?")
    print(result)
    
    # Compare cities
    result = app.compare("Tokyo", "Delhi")
    print(result)
    
    # Set alerts
    app.set_alert("user1", "Delhi", threshold=100)
    
    app.close()
"""

from typing import List, Optional, Dict, Any

from clients.openaq_client import OpenAQClient
from clients.raindrop_client import RaindropClient
from services.data_service import DataService
from services.query_service import QueryService
from services.alert_service import AlertService
from models.air_reading import AirReading
from models.alert import Alert, AlertType
from models.query_result import QueryResult
from config.settings import settings
from utils.validators import validate_city_name, validate_question, sanitize_input
from utils.formatters import format_reading, format_readings_table


class AirSightApp:
    """
    Main AirSight Application.
    
    Provides a unified interface for all air quality intelligence features:
    - Natural language Q&A about air quality
    - City comparisons
    - Alert management
    - Historical data analysis
    
    This class orchestrates the interaction between:
    - OpenAQ API (data source)
    - Raindrop Platform (storage, memory, AI)
    - Business logic services
    """
    
    def __init__(
        self,
        openaq_api_key: str = None,
        raindrop_api_key: str = None,
        cerebras_api_key: str = None,
    ):
        """
        Initialize the AirSight application.
        
        Args:
            openaq_api_key: OpenAQ API key (defaults to settings)
            raindrop_api_key: Raindrop API key (defaults to settings)
            cerebras_api_key: Cerebras API key (defaults to settings)
        """
        # Initialize clients
        self.openaq = OpenAQClient(
            api_key=openaq_api_key or settings.openaq_api_key
        )
        self.raindrop = RaindropClient(
            api_key=raindrop_api_key or settings.raindrop_api_key,
            cerebras_api_key=cerebras_api_key or settings.cerebras_api_key,
        )
        
        # Initialize services (will be set up in initialize())
        self.data_service: Optional[DataService] = None
        self.query_service: Optional[QueryService] = None
        self.alert_service: Optional[AlertService] = None
        
        self._initialized = False
    
    def initialize(self) -> bool:
        """
        Initialize all components.
        
        Returns:
            True if initialization successful
        """
        try:
            # Initialize Raindrop components
            self.raindrop.initialize_all()
            
            # Initialize services
            self.data_service = DataService(self.openaq, self.raindrop)
            self.query_service = QueryService(self.raindrop, self.data_service)
            self.alert_service = AlertService(self.raindrop)
            
            self._initialized = True
            print("[AirSight] Application initialized successfully")
            return True
            
        except Exception as e:
            print(f"[AirSight] Initialization failed: {e}")
            return False
    
    def _ensure_initialized(self):
        """Ensure the app is initialized before operations."""
        if not self._initialized:
            self.initialize()
    
    # =========================================
    # Query Methods
    # =========================================
    
    def ask(self, question: str, user_id: str = "default") -> str:
        """
        Ask a natural language question about air quality.
        
        Args:
            question: User's question
            user_id: User identifier for context
            
        Returns:
            Answer string
        
        Examples:
            app.ask("Is the air safe in Tokyo?")
            app.ask("What's the PM2.5 in Delhi?")
            app.ask("Should I go jogging in LA?")
        """
        self._ensure_initialized()
        
        # Validate input
        question = sanitize_input(question)
        is_valid, error = validate_question(question)
        if not is_valid:
            return f"❌ {error}"
        
        # Get answer
        result = self.query_service.ask(question, user_id)
        return result.to_display()
    
    def compare(self, city1: str, city2: str, user_id: str = "default") -> str:
        """
        Compare air quality between two cities.
        
        Args:
            city1: First city name
            city2: Second city name
            user_id: User identifier
            
        Returns:
            Comparison result string
        """
        self._ensure_initialized()
        
        # Validate cities
        for city in [city1, city2]:
            is_valid, error = validate_city_name(city)
            if not is_valid:
                return f"❌ Invalid city name '{city}': {error}"
        
        result = self.query_service.compare(city1, city2, user_id)
        return result.to_display()
    
    def get_health_advice(self, city: str, user_id: str = "default") -> str:
        """
        Get health advice for a city's current air quality.
        
        Args:
            city: City name
            user_id: User identifier
            
        Returns:
            Health advice string
        """
        self._ensure_initialized()
        
        is_valid, error = validate_city_name(city)
        if not is_valid:
            return f"❌ {error}"
        
        result = self.query_service.get_health_advice(city, user_id)
        return result.to_display()
    
    # =========================================
    # Data Methods
    # =========================================
    
    def get_air_quality(self, city: str, limit: int = 10) -> List[AirReading]:
        """
        Get current air quality readings for a city.
        
        Args:
            city: City name
            limit: Maximum readings to return
            
        Returns:
            List of AirReading objects
        """
        self._ensure_initialized()
        return self.data_service.get_air_quality(city, limit)
    
    def get_air_quality_formatted(self, city: str, detailed: bool = False) -> str:
        """
        Get formatted air quality for display.
        
        Args:
            city: City name
            detailed: Whether to show detailed view
            
        Returns:
            Formatted string
        """
        self._ensure_initialized()
        
        readings = self.data_service.get_air_quality(city, limit=10)
        
        if not readings:
            return f"❌ No air quality data found for {city}"
        
        if detailed:
            return "\n\n".join(format_reading(r, detailed=True) for r in readings)
        else:
            return format_readings_table(readings)
    
    def get_city_stats(self, city: str) -> Dict[str, Any]:
        """
        Get statistics for a city.
        
        Args:
            city: City name
            
        Returns:
            Statistics dictionary
        """
        self._ensure_initialized()
        return self.data_service.get_city_stats(city)
    
    # =========================================
    # Alert Methods
    # =========================================
    
    def set_alert(
        self,
        user_id: str,
        location: str,
        threshold: float,
        alert_type: str = "pm25",
    ) -> str:
        """
        Set an air quality alert.
        
        Args:
            user_id: User identifier
            location: Location to monitor
            threshold: Threshold value
            alert_type: Type of alert ("pm25", "aqi", "ozone")
            
        Returns:
            Confirmation message
        """
        self._ensure_initialized()
        
        # Map string to AlertType
        type_map = {
            "pm25": AlertType.PM25_THRESHOLD,
            "pm10": AlertType.PM10_THRESHOLD,
            "aqi": AlertType.AQI_THRESHOLD,
            "ozone": AlertType.OZONE_THRESHOLD,
        }
        
        alert_type_enum = type_map.get(alert_type.lower(), AlertType.PM25_THRESHOLD)
        
        alert = self.alert_service.create_alert(
            user_id=user_id,
            location_name=location,
            alert_type=alert_type_enum,
            threshold=threshold,
        )
        
        return f"✅ Alert created! I'll notify you when {alert_type.upper()} exceeds {threshold} in {location}."
    
    def get_alerts(self, user_id: str) -> List[Alert]:
        """
        Get all alerts for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of Alert objects
        """
        self._ensure_initialized()
        return self.alert_service.get_user_alerts(user_id)
    
    def get_alerts_formatted(self, user_id: str) -> str:
        """
        Get formatted alerts for display.
        
        Args:
            user_id: User identifier
            
        Returns:
            Formatted string
        """
        self._ensure_initialized()
        
        alerts = self.alert_service.get_user_alerts(user_id)
        
        if not alerts:
            return "📭 No alerts configured. Use set_alert() to create one."
        
        lines = ["## Your Alerts", ""]
        for alert in alerts:
            status = "🟢 Active" if alert.is_active else "🔴 Inactive"
            lines.append(
                f"- {status} **{alert.location_name}**: "
                f"{alert.alert_type.get_display_name()} > {alert.threshold} "
                f"(Triggered {alert.trigger_count} times)"
            )
        
        return "\n".join(lines)
    
    def delete_alert(self, user_id: str, alert_id: str) -> str:
        """
        Delete an alert.
        
        Args:
            user_id: User identifier
            alert_id: Alert identifier
            
        Returns:
            Confirmation message
        """
        self._ensure_initialized()
        
        if self.alert_service.delete_alert(user_id, alert_id):
            return "✅ Alert deleted successfully"
        else:
            return "❌ Alert not found"
    
    def check_alerts(self, user_id: str, city: str) -> str:
        """
        Check if any alerts are triggered for a city.
        
        Args:
            user_id: User identifier
            city: City to check
            
        Returns:
            Alert status message
        """
        self._ensure_initialized()
        
        readings = self.data_service.get_air_quality(city, limit=5)
        
        if not readings:
            return f"❌ No data available for {city}"
        
        triggered = self.alert_service.check_alerts(user_id, readings)
        
        if triggered:
            messages = [item["message"] for item in triggered]
            return "\n\n".join(messages)
        else:
            return f"✅ No alerts triggered for {city}. Air quality is within your thresholds."
    
    # =========================================
    # Utility Methods
    # =========================================
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get application status.
        
        Returns:
            Status dictionary
        """
        return {
            "initialized": self._initialized,
            "raindrop_connected": self.raindrop.is_initialized if self.raindrop else False,
            "openaq_base_url": self.openaq.BASE_URL if self.openaq else None,
            "settings": {
                "debug": settings.debug,
                "cache_ttl": settings.cache_ttl_seconds,
            },
        }
    
    def clear_cache(self):
        """Clear all cached data."""
        self._ensure_initialized()
        self.data_service.clear_cache()
        print("[AirSight] Cache cleared")
    
    def close(self):
        """Close all connections and cleanup."""
        if self.openaq:
            self.openaq.close()
        if self.raindrop:
            self.raindrop.close()
        
        self._initialized = False
        print("[AirSight] Application closed")
    
    def __enter__(self):
        self.initialize()
        return self
    
    def __exit__(self, *args):
        self.close()


# =========================================
# Quick Start Functions
# =========================================

def create_app() -> AirSightApp:
    """
    Create and initialize an AirSight application instance.
    
    Returns:
        Initialized AirSightApp
    """
    app = AirSightApp()
    app.initialize()
    return app


def quick_query(question: str) -> str:
    """
    Quick one-off query without managing app lifecycle.
    
    Args:
        question: Question to ask
        
    Returns:
        Answer string
    """
    with AirSightApp() as app:
        return app.ask(question)


# =========================================
# CLI Entry Point
# =========================================

if __name__ == "__main__":
    import sys
    
    print("=" * 50)
    print("🌍 AirSight - Real-Time Air Quality Intelligence")
    print("=" * 50)
    print()
    
    app = AirSightApp()
    app.initialize()
    
    print()
    print("Testing queries...")
    print("-" * 50)
    
    # Test ask
    print("\n📝 Question: 'Is the air safe in Tokyo?'")
    result = app.ask("Is the air safe in Tokyo?")
    print(result)
    
    # Test comparison
    print("\n📝 Comparing Tokyo vs Delhi")
    result = app.compare("Tokyo", "Delhi")
    print(result)
    
    # Test alerts
    print("\n📝 Setting an alert for Delhi")
    result = app.set_alert("demo_user", "Delhi", 100)
    print(result)
    
    print("\n📝 Getting alerts")
    result = app.get_alerts_formatted("demo_user")
    print(result)
    
    app.close()
    
    print()
    print("=" * 50)
    print("✅ All tests completed!")
    print("=" * 50)


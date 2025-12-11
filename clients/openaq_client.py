"""
OpenAQ API Client.
Handles all communication with the OpenAQ air quality data API.
Docs: https://docs.openaq.org/examples/examples
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import httpx

from config.settings import settings
from models.air_reading import AirReading
from models.location import Location


class OpenAQError(Exception):
    """Exception raised for OpenAQ API errors."""
    
    def __init__(self, message: str, status_code: int = None, response: dict = None):
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(self.message)


class OpenAQClient:
    """
    Client for interacting with the OpenAQ API.
    
    Provides methods to:
    - Find air quality monitoring locations
    - Get measurements from sensors
    - Get latest readings for parameters
    - Get historical data for trends
    
    Usage:
        client = OpenAQClient()
        locations = client.get_locations_by_city("Tokyo")
        for loc in locations:
            print(loc)
        client.close()
    
    Or with context manager:
        with OpenAQClient() as client:
            locations = client.get_locations_by_city("Tokyo")
    """
    
    BASE_URL = "https://api.openaq.org/v3"
    
    # Parameter IDs in OpenAQ
    PARAM_PM25 = 2
    PARAM_PM10 = 1
    PARAM_OZONE = 3
    PARAM_NO2 = 7
    PARAM_CO = 4
    PARAM_SO2 = 9
    
    def __init__(self, api_key: str = None):
        """
        Initialize the OpenAQ client.
        
        Args:
            api_key: OpenAQ API key (defaults to settings.openaq_api_key)
        """
        self.api_key = api_key or settings.openaq_api_key
        self._client = httpx.Client(
            base_url=self.BASE_URL,
            headers={"X-API-Key": self.api_key} if self.api_key else {},
            timeout=30.0,
        )
    
    def _request(self, method: str, endpoint: str, params: dict = None) -> dict:
        """
        Make a request to the OpenAQ API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., "/locations")
            params: Query parameters
            
        Returns:
            JSON response as dictionary
            
        Raises:
            OpenAQError: If the request fails
        """
        try:
            response = self._client.request(method, endpoint, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise OpenAQError(
                f"HTTP error: {e.response.status_code}",
                status_code=e.response.status_code,
                response=e.response.json() if e.response.content else None,
            )
        except httpx.RequestError as e:
            raise OpenAQError(f"Request error: {str(e)}")
    
    # =========================================
    # Location Methods
    # =========================================
    
    def get_locations_near(
        self,
        latitude: float,
        longitude: float,
        radius_meters: int = None,
        limit: int = None,
    ) -> List[Location]:
        """
        Find air quality monitoring locations near a point.
        
        Args:
            latitude: Geographic latitude
            longitude: Geographic longitude
            radius_meters: Search radius in meters (default: 25000)
            limit: Maximum number of results (default: 100)
            
        Returns:
            List of Location objects
        """
        params = {
            "coordinates": f"{longitude},{latitude}",
            "radius": radius_meters or settings.default_radius_meters,
            "limit": limit or settings.max_results,
        }
        
        data = self._request("GET", "/locations", params)
        return [Location.from_openaq(loc) for loc in data.get("results", [])]
    
    def get_locations_by_city(self, city: str, limit: int = None) -> List[Location]:
        """
        Find locations in a city.
        
        Args:
            city: City name to search
            limit: Maximum number of results
            
        Returns:
            List of Location objects
        """
        params = {
            "city": city,
            "limit": limit or settings.max_results,
        }
        
        data = self._request("GET", "/locations", params)
        return [Location.from_openaq(loc) for loc in data.get("results", [])]
    
    def get_locations_by_country(self, country: str, limit: int = None) -> List[Location]:
        """
        Find locations in a country.
        
        Args:
            country: Country code (e.g., "US", "IN", "JP")
            limit: Maximum number of results
            
        Returns:
            List of Location objects
        """
        params = {
            "countries_id": country,
            "limit": limit or settings.max_results,
        }
        
        data = self._request("GET", "/locations", params)
        return [Location.from_openaq(loc) for loc in data.get("results", [])]
    
    def get_location_by_id(self, location_id: int) -> Optional[Location]:
        """
        Get a specific location by ID.
        
        Args:
            location_id: OpenAQ location ID
            
        Returns:
            Location object or None if not found
        """
        try:
            data = self._request("GET", f"/locations/{location_id}")
            results = data.get("results", [])
            return Location.from_openaq(results[0]) if results else None
        except OpenAQError:
            return None
    
    # =========================================
    # Measurement Methods
    # =========================================
    
    def get_sensor_measurements(
        self,
        sensor_id: int,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get measurements for a specific sensor.
        
        Args:
            sensor_id: Sensor ID
            limit: Maximum number of results
            
        Returns:
            List of measurement dictionaries
        """
        params = {"limit": limit}
        data = self._request("GET", f"/sensors/{sensor_id}/measurements", params)
        return data.get("results", [])
    
    def get_sensor_daily_averages(
        self,
        sensor_id: int,
        limit: int = 365,
    ) -> List[Dict[str, Any]]:
        """
        Get daily average values for a sensor.
        
        Useful for trend analysis.
        
        Args:
            sensor_id: Sensor ID
            limit: Number of days to retrieve
            
        Returns:
            List of daily average measurements
        """
        params = {"limit": limit}
        data = self._request("GET", f"/sensors/{sensor_id}/days", params)
        return data.get("results", [])
    
    def get_sensor_hourly_averages(
        self,
        sensor_id: int,
        limit: int = 168,  # 7 days
    ) -> List[Dict[str, Any]]:
        """
        Get hourly average values for a sensor.
        
        Args:
            sensor_id: Sensor ID
            limit: Number of hours to retrieve
            
        Returns:
            List of hourly average measurements
        """
        params = {"limit": limit}
        data = self._request("GET", f"/sensors/{sensor_id}/hours", params)
        return data.get("results", [])
    
    # =========================================
    # Latest Data Methods
    # =========================================
    
    def get_latest_by_parameter(
        self,
        parameter_id: int = PARAM_PM25,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """
        Get latest readings for a parameter globally.
        
        Args:
            parameter_id: Parameter ID (default: PM2.5)
            limit: Maximum number of results
            
        Returns:
            List of latest readings
        """
        params = {"limit": limit}
        data = self._request("GET", f"/parameters/{parameter_id}/latest", params)
        return data.get("results", [])
    
    def get_location_latest(self, location_id: int) -> List[Dict[str, Any]]:
        """
        Get latest measurements for a location.
        
        Args:
            location_id: Location ID
            
        Returns:
            List of latest measurements
        """
        data = self._request("GET", f"/locations/{location_id}/latest")
        return data.get("results", [])
    
    # =========================================
    # High-Level Convenience Methods
    # =========================================
    
    def get_air_quality(self, city: str, limit: int = 10) -> List[AirReading]:
        """
        Get current air quality readings for a city.
        
        This is a high-level method that:
        1. Finds locations in the city
        2. Gets the latest measurements
        3. Returns AirReading objects
        
        Args:
            city: City name
            limit: Maximum number of readings
            
        Returns:
            List of AirReading objects
        """
        locations = self.get_locations_by_city(city, limit=limit)
        readings = []
        
        for loc in locations:
            if loc.sensors:
                try:
                    # Get the latest measurement from the first sensor
                    measurements = self.get_sensor_measurements(loc.sensors[0], limit=1)
                    if measurements:
                        reading = self._measurement_to_reading(measurements[0], loc)
                        if reading:
                            readings.append(reading)
                except OpenAQError:
                    continue  # Skip locations with errors
        
        return readings
    
    def get_air_quality_near(
        self,
        latitude: float,
        longitude: float,
        radius_meters: int = None,
        limit: int = 10,
    ) -> List[AirReading]:
        """
        Get current air quality readings near coordinates.
        
        Args:
            latitude: Geographic latitude
            longitude: Geographic longitude
            radius_meters: Search radius in meters
            limit: Maximum number of readings
            
        Returns:
            List of AirReading objects
        """
        locations = self.get_locations_near(latitude, longitude, radius_meters, limit)
        readings = []
        
        for loc in locations:
            if loc.sensors:
                try:
                    measurements = self.get_sensor_measurements(loc.sensors[0], limit=1)
                    if measurements:
                        reading = self._measurement_to_reading(measurements[0], loc)
                        if reading:
                            readings.append(reading)
                except OpenAQError:
                    continue
        
        return readings
    
    def _measurement_to_reading(
        self,
        measurement: Dict[str, Any],
        location: Location,
    ) -> Optional[AirReading]:
        """
        Convert an OpenAQ measurement to an AirReading.
        
        Args:
            measurement: Measurement dictionary from API
            location: Location object
            
        Returns:
            AirReading or None if conversion fails
        """
        try:
            # Extract parameter info
            parameter = measurement.get("parameter", {})
            param_name = parameter.get("name", "").lower() if isinstance(parameter, dict) else ""
            value = measurement.get("value")
            
            # Parse timestamp
            timestamp = None
            datetime_info = measurement.get("datetime", {})
            if datetime_info:
                utc_str = datetime_info.get("utc", "")
                if utc_str:
                    timestamp = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
            
            # Create reading with the appropriate parameter
            reading = AirReading(
                location_id=location.id,
                location_name=location.name,
                city=location.city,
                country=location.country,
                latitude=location.latitude,
                longitude=location.longitude,
                timestamp=timestamp,
            )
            
            # Set the appropriate measurement field
            if "pm25" in param_name or param_name == "pm2.5":
                reading.pm25 = value
            elif "pm10" in param_name:
                reading.pm10 = value
            elif "ozone" in param_name or param_name == "o3":
                reading.ozone = value
            elif "no2" in param_name:
                reading.no2 = value
            elif "co" in param_name and "co2" not in param_name:
                reading.co = value
            elif "so2" in param_name:
                reading.so2 = value
            else:
                # Unknown parameter, store as PM2.5 for now
                reading.pm25 = value
            
            return reading
            
        except Exception:
            return None
    
    # =========================================
    # Context Manager Support
    # =========================================
    
    def close(self):
        """Close the HTTP client."""
        self._client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()


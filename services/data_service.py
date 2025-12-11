"""
Data Service.
Handles fetching, storing, and retrieving air quality data.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from clients.openaq_client import OpenAQClient, OpenAQError
from clients.raindrop_client import RaindropClient
from models.air_reading import AirReading
from models.location import Location
from config.settings import settings


class DataService:
    """
    Service for managing air quality data.
    
    Responsibilities:
    - Fetch data from OpenAQ API
    - Store data in SmartBuckets for RAG retrieval
    - Store structured data in SmartSQL for queries
    - Cache management for performance
    
    Usage:
        service = DataService(openaq_client, raindrop_client)
        readings = service.get_air_quality("Tokyo")
        service.store_readings(readings)
    """
    
    BUCKET_NAME = "air-readings"
    TABLE_NAME = "readings"
    
    def __init__(self, openaq: OpenAQClient, raindrop: RaindropClient):
        """
        Initialize the data service.
        
        Args:
            openaq: OpenAQ API client
            raindrop: Raindrop client for storage
        """
        self.openaq = openaq
        self.raindrop = raindrop
        self._cache: Dict[str, Dict[str, Any]] = {}  # Simple in-memory cache
    
    # =========================================
    # Data Fetching Methods
    # =========================================
    
    def get_air_quality(self, city: str, limit: int = 10) -> List[AirReading]:
        """
        Get current air quality readings for a city.
        
        Checks cache first, then fetches from OpenAQ if needed.
        
        Args:
            city: City name to search
            limit: Maximum number of readings
            
        Returns:
            List of AirReading objects
        """
        # Check cache first
        cache_key = f"city:{city.lower()}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
        
        # Fetch from OpenAQ
        try:
            readings = self.openaq.get_air_quality(city, limit=limit)
            
            # Store in cache
            self._set_cache(cache_key, readings)
            
            # Store in Raindrop for persistence
            if readings:
                self.store_readings(readings)
            
            return readings
            
        except OpenAQError as e:
            print(f"[DataService] Error fetching data for {city}: {e}")
            return []
    
    def get_air_quality_near(
        self,
        latitude: float,
        longitude: float,
        radius_meters: int = None,
        limit: int = 10,
    ) -> List[AirReading]:
        """
        Get air quality readings near coordinates.
        
        Args:
            latitude: Geographic latitude
            longitude: Geographic longitude
            radius_meters: Search radius in meters
            limit: Maximum number of readings
            
        Returns:
            List of AirReading objects
        """
        cache_key = f"coords:{latitude:.4f},{longitude:.4f}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
        
        try:
            readings = self.openaq.get_air_quality_near(
                latitude, longitude, radius_meters, limit
            )
            
            self._set_cache(cache_key, readings)
            
            if readings:
                self.store_readings(readings)
            
            return readings
            
        except OpenAQError as e:
            print(f"[DataService] Error fetching data near {latitude},{longitude}: {e}")
            return []
    
    def get_locations(self, city: str, limit: int = 20) -> List[Location]:
        """
        Get monitoring locations in a city.
        
        Args:
            city: City name
            limit: Maximum results
            
        Returns:
            List of Location objects
        """
        try:
            return self.openaq.get_locations_by_city(city, limit=limit)
        except OpenAQError as e:
            print(f"[DataService] Error fetching locations for {city}: {e}")
            return []
    
    # =========================================
    # Data Storage Methods
    # =========================================
    
    def store_readings(self, readings: List[AirReading]) -> int:
        """
        Store readings in Raindrop for later retrieval.
        
        Stores in both SmartBuckets (for RAG) and SmartSQL (for queries).
        
        Args:
            readings: List of readings to store
            
        Returns:
            Number of readings stored
        """
        stored_count = 0
        
        for reading in readings:
            # Store in SmartBuckets for semantic search / RAG
            self.raindrop.buckets.store(
                bucket_name=self.BUCKET_NAME,
                data=reading.to_dict(),
                metadata={
                    "city": reading.city.lower(),
                    "country": reading.country.lower(),
                    "location_id": reading.location_id,
                    "health_category": reading.get_health_category(),
                },
            )
            
            # Store in SmartSQL for structured queries
            self.raindrop.sql.insert(self.TABLE_NAME, {
                **reading.to_dict(),
                "stored_at": datetime.utcnow().isoformat(),
            })
            
            stored_count += 1
        
        if settings.debug:
            print(f"[DataService] Stored {stored_count} readings")
        
        return stored_count
    
    # =========================================
    # Data Retrieval Methods
    # =========================================
    
    def get_historical_readings(
        self,
        city: str,
        days: int = 30,
        limit: int = 100,
    ) -> List[Dict]:
        """
        Get historical readings from SmartSQL.
        
        Args:
            city: City name
            days: Number of days to look back
            limit: Maximum results
            
        Returns:
            List of reading dictionaries
        """
        return self.raindrop.sql.select(
            table=self.TABLE_NAME,
            where={"city": city},
            order_by="-timestamp",
            limit=limit,
        )
    
    def search_readings(
        self,
        query: str,
        limit: int = 10,
    ) -> List[Dict]:
        """
        Search readings using semantic search.
        
        Args:
            query: Search query
            limit: Maximum results
            
        Returns:
            List of matching documents
        """
        return self.raindrop.buckets.search(
            bucket_name=self.BUCKET_NAME,
            query=query,
            limit=limit,
        )
    
    def get_readings_by_health_category(
        self,
        category: str,
        limit: int = 20,
    ) -> List[Dict]:
        """
        Get readings filtered by health category.
        
        Args:
            category: Health category (e.g., "Good", "Unhealthy")
            limit: Maximum results
            
        Returns:
            List of matching readings
        """
        return self.raindrop.buckets.search(
            bucket_name=self.BUCKET_NAME,
            query=category,
            limit=limit,
            metadata_filter={"health_category": category},
        )
    
    # =========================================
    # Statistics Methods
    # =========================================
    
    def get_city_stats(self, city: str) -> Dict[str, Any]:
        """
        Get statistics for a city.
        
        Args:
            city: City name
            
        Returns:
            Dictionary with stats (avg PM2.5, worst AQI, etc.)
        """
        readings = self.get_air_quality(city, limit=20)
        
        if not readings:
            return {"city": city, "error": "No data available"}
        
        pm25_values = [r.pm25 for r in readings if r.pm25 is not None]
        aqi_values = [r.aqi for r in readings if r.aqi is not None]
        
        return {
            "city": city,
            "num_readings": len(readings),
            "avg_pm25": sum(pm25_values) / len(pm25_values) if pm25_values else None,
            "max_pm25": max(pm25_values) if pm25_values else None,
            "min_pm25": min(pm25_values) if pm25_values else None,
            "avg_aqi": sum(aqi_values) / len(aqi_values) if aqi_values else None,
            "max_aqi": max(aqi_values) if aqi_values else None,
            "worst_category": max(
                (r.get_health_category() for r in readings),
                key=lambda x: ["Good", "Moderate", "Unhealthy for Sensitive Groups", 
                              "Unhealthy", "Very Unhealthy", "Hazardous"].index(x)
                if x in ["Good", "Moderate", "Unhealthy for Sensitive Groups", 
                        "Unhealthy", "Very Unhealthy", "Hazardous"] else 0,
                default="Unknown"
            ),
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    def compare_cities(self, city1: str, city2: str) -> Dict[str, Any]:
        """
        Compare air quality between two cities.
        
        Args:
            city1: First city
            city2: Second city
            
        Returns:
            Comparison dictionary
        """
        stats1 = self.get_city_stats(city1)
        stats2 = self.get_city_stats(city2)
        
        # Determine which city is cleaner
        cleaner = None
        if stats1.get("avg_aqi") and stats2.get("avg_aqi"):
            cleaner = city1 if stats1["avg_aqi"] < stats2["avg_aqi"] else city2
        
        return {
            "city1": stats1,
            "city2": stats2,
            "cleaner_city": cleaner,
            "aqi_difference": abs(
                (stats1.get("avg_aqi") or 0) - (stats2.get("avg_aqi") or 0)
            ),
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    # =========================================
    # Cache Methods
    # =========================================
    
    def _get_from_cache(self, key: str) -> Optional[List[AirReading]]:
        """Get data from cache if not expired."""
        if key in self._cache:
            entry = self._cache[key]
            if datetime.utcnow() - entry["timestamp"] < timedelta(seconds=settings.cache_ttl_seconds):
                return entry["data"]
            else:
                del self._cache[key]
        return None
    
    def _set_cache(self, key: str, data: List[AirReading]):
        """Store data in cache."""
        self._cache[key] = {
            "data": data,
            "timestamp": datetime.utcnow(),
        }
    
    def clear_cache(self):
        """Clear all cached data."""
        self._cache.clear()


"""
City Index Service.
Provides fast city-to-sensor lookup for OpenAQ data.
"""

import json
import os
from typing import List, Dict, Any, Optional
from pathlib import Path

from clients.openaq_client import OpenAQClient
from models.air_reading import AirReading
from config.settings import settings


class CityIndexService:
    """
    Service for looking up air quality sensors by city name.
    
    Uses a pre-built index of city names to OpenAQ sensor IDs.
    Supports fuzzy matching for cities not directly in the index.
    
    Usage:
        service = CityIndexService(openaq_client)
        service.load_index()
        
        readings = service.get_readings_for_city("Delhi")
        for reading in readings:
            print(f"{reading.city}: PM2.5 = {reading.pm25}")
    """
    
    INDEX_PATH = Path(__file__).parent.parent / "data" / "city_index.json"
    
    def __init__(self, openaq: OpenAQClient):
        """
        Initialize the city index service.
        
        Args:
            openaq: OpenAQ client for fetching measurements
        """
        self.openaq = openaq
        self._index: Dict[str, List[Dict]] = {}
        self._loaded = False
    
    def load_index(self) -> bool:
        """
        Load the city index from disk.
        
        Returns:
            True if loaded successfully
        """
        try:
            if self.INDEX_PATH.exists():
                with open(self.INDEX_PATH, 'r') as f:
                    self._index = json.load(f)
                self._loaded = True
                print(f"[CityIndex] Loaded {len(self._index)} city keywords")
                return True
            else:
                print(f"[CityIndex] Index file not found: {self.INDEX_PATH}")
                return False
        except Exception as e:
            print(f"[CityIndex] Error loading index: {e}")
            return False
    
    def search_city(self, query: str) -> List[Dict]:
        """
        Search for sensors matching a city name.
        
        Args:
            query: City name to search for
            
        Returns:
            List of sensor info dicts with sensor_id, location_name, country
        """
        if not self._loaded:
            self.load_index()
        
        query_lower = query.lower().strip()
        
        # 1. Exact match
        if query_lower in self._index:
            return self._index[query_lower]
        
        # 2. Partial match (query is substring of keyword)
        partial_matches = []
        for keyword, sensors in self._index.items():
            if query_lower in keyword:
                partial_matches.extend(sensors)
        
        if partial_matches:
            # Deduplicate by sensor_id
            seen = set()
            unique = []
            for s in partial_matches:
                if s['sensor_id'] not in seen:
                    seen.add(s['sensor_id'])
                    unique.append(s)
            return unique
        
        # 3. Keyword is substring of query
        for keyword, sensors in self._index.items():
            if keyword in query_lower and len(keyword) > 3:
                partial_matches.extend(sensors)
        
        if partial_matches:
            seen = set()
            unique = []
            for s in partial_matches:
                if s['sensor_id'] not in seen:
                    seen.add(s['sensor_id'])
                    unique.append(s)
            return unique
        
        return []
    
    def get_readings_for_city(
        self, 
        city: str, 
        limit: int = 5
    ) -> List[AirReading]:
        """
        Get current air quality readings for a city.
        
        Args:
            city: City name
            limit: Maximum number of readings to return
            
        Returns:
            List of AirReading objects with current data
        """
        sensors = self.search_city(city)
        
        if not sensors:
            print(f"[CityIndex] No sensors found for '{city}'")
            return []
        
        readings = []
        
        for sensor_info in sensors[:limit * 2]:  # Fetch more in case some have no data
            try:
                # Get latest measurement from this sensor
                measurements = self.openaq.get_sensor_measurements(
                    sensor_info['sensor_id'],
                    limit=1
                )
                
                if measurements:
                    meas = measurements[0]
                    value = meas.get('value')
                    
                    if value is not None:
                        reading = AirReading(
                            location_id=sensor_info.get('location_id', 0),
                            location_name=sensor_info.get('location_name', 'Unknown'),
                            city=city.title(),
                            country=sensor_info.get('country', 'Unknown'),
                            latitude=0.0,  # Not in index
                            longitude=0.0,
                            pm25=float(value),
                        )
                        readings.append(reading)
                        
                        if len(readings) >= limit:
                            break
                            
            except Exception as e:
                if settings.debug:
                    print(f"[CityIndex] Error fetching sensor {sensor_info['sensor_id']}: {e}")
                continue
        
        return readings
    
    def get_best_reading_for_city(self, city: str) -> Optional[AirReading]:
        """
        Get the single best (most recent) reading for a city.
        
        Args:
            city: City name
            
        Returns:
            AirReading or None if not found
        """
        readings = self.get_readings_for_city(city, limit=1)
        return readings[0] if readings else None
    
    def is_city_available(self, city: str) -> bool:
        """
        Check if we have data for a city.
        
        Args:
            city: City name
            
        Returns:
            True if we have sensors for this city
        """
        return len(self.search_city(city)) > 0
    
    def get_available_cities(self) -> List[str]:
        """
        Get list of all available city keywords.
        
        Returns:
            List of city/location keywords
        """
        if not self._loaded:
            self.load_index()
        return list(self._index.keys())
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the index.
        
        Returns:
            Dict with stats
        """
        if not self._loaded:
            self.load_index()
        
        total_sensors = sum(len(sensors) for sensors in self._index.values())
        
        return {
            "keywords": len(self._index),
            "total_sensors": total_sensors,
            "loaded": self._loaded,
        }


# Common city aliases for better matching
CITY_ALIASES = {
    "nyc": "new york",
    "ny": "new york",
    "la": "los angeles",
    "sf": "san francisco",
    "dc": "washington",
    "philly": "philadelphia",
    "vegas": "las vegas",
    "uk": "united kingdom",
    "usa": "united states",
    "us": "united states",
}


def normalize_city_name(city: str) -> str:
    """
    Normalize a city name using aliases.
    
    Args:
        city: Raw city name
        
    Returns:
        Normalized city name
    """
    city_lower = city.lower().strip()
    return CITY_ALIASES.get(city_lower, city_lower)


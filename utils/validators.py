"""
Validation utilities for AirSight.
Functions to validate user input.
"""

from typing import Tuple, Optional
import re


def validate_coordinates(
    latitude: float,
    longitude: float,
) -> Tuple[bool, Optional[str]]:
    """
    Validate geographic coordinates.
    
    Args:
        latitude: Geographic latitude
        longitude: Geographic longitude
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(latitude, (int, float)):
        return False, "Latitude must be a number"
    
    if not isinstance(longitude, (int, float)):
        return False, "Longitude must be a number"
    
    if latitude < -90 or latitude > 90:
        return False, "Latitude must be between -90 and 90"
    
    if longitude < -180 or longitude > 180:
        return False, "Longitude must be between -180 and 180"
    
    return True, None


def validate_city_name(city: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a city name.
    
    Args:
        city: City name to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not city:
        return False, "City name cannot be empty"
    
    if not isinstance(city, str):
        return False, "City name must be a string"
    
    city = city.strip()
    
    if len(city) < 2:
        return False, "City name must be at least 2 characters"
    
    if len(city) > 100:
        return False, "City name must be less than 100 characters"
    
    # Check for invalid characters
    if re.search(r'[<>{}|\[\]\\^`]', city):
        return False, "City name contains invalid characters"
    
    return True, None


def validate_threshold(
    threshold: float,
    alert_type: str,
) -> Tuple[bool, Optional[str]]:
    """
    Validate an alert threshold value.
    
    Args:
        threshold: Threshold value
        alert_type: Type of alert (pm25, aqi, etc.)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(threshold, (int, float)):
        return False, "Threshold must be a number"
    
    if threshold < 0:
        return False, "Threshold cannot be negative"
    
    # Type-specific validation
    if alert_type == "pm25_threshold":
        if threshold > 1000:
            return False, "PM2.5 threshold seems too high (max: 1000)"
    elif alert_type == "aqi_threshold":
        if threshold > 500:
            return False, "AQI threshold seems too high (max: 500)"
    elif alert_type == "ozone_threshold":
        if threshold > 1:
            return False, "Ozone threshold seems too high (max: 1 ppm)"
    
    return True, None


def validate_user_id(user_id: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a user ID.
    
    Args:
        user_id: User identifier
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not user_id:
        return False, "User ID cannot be empty"
    
    if not isinstance(user_id, str):
        return False, "User ID must be a string"
    
    if len(user_id) > 100:
        return False, "User ID must be less than 100 characters"
    
    # Check for valid characters (alphanumeric, underscore, hyphen)
    if not re.match(r'^[\w\-]+$', user_id):
        return False, "User ID can only contain letters, numbers, underscores, and hyphens"
    
    return True, None


def validate_question(question: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a user question.
    
    Args:
        question: User's question
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not question:
        return False, "Question cannot be empty"
    
    if not isinstance(question, str):
        return False, "Question must be a string"
    
    question = question.strip()
    
    if len(question) < 3:
        return False, "Question is too short"
    
    if len(question) > 1000:
        return False, "Question is too long (max: 1000 characters)"
    
    return True, None


def sanitize_input(text: str) -> str:
    """
    Sanitize user input by removing potentially harmful content.
    
    Args:
        text: Input text
        
    Returns:
        Sanitized text
    """
    if not text:
        return ""
    
    # Remove control characters
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    
    # Trim whitespace
    text = text.strip()
    
    # Limit length
    if len(text) > 10000:
        text = text[:10000]
    
    return text


def normalize_city_name(city: str) -> str:
    """
    Normalize a city name for consistent querying.
    
    Args:
        city: City name
        
    Returns:
        Normalized city name
    """
    if not city:
        return ""
    
    # Strip and title case
    city = city.strip().title()
    
    # Common normalizations
    normalizations = {
        "Nyc": "New York",
        "La": "Los Angeles",
        "Sf": "San Francisco",
        "Dc": "Washington",
        "Philly": "Philadelphia",
        "New Delhi": "Delhi",  # OpenAQ uses "Delhi"
    }
    
    return normalizations.get(city, city)


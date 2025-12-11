"""
Formatting utilities for AirSight.
Functions to format data for display.
"""

from typing import Optional, List
from models.air_reading import AirReading


def format_aqi(aqi: Optional[int]) -> str:
    """
    Format AQI value with color indicator.
    
    Args:
        aqi: Air Quality Index value
        
    Returns:
        Formatted string with emoji indicator
    """
    if aqi is None:
        return "⚪ N/A"
    
    if aqi <= 50:
        return f"🟢 {aqi} (Good)"
    elif aqi <= 100:
        return f"🟡 {aqi} (Moderate)"
    elif aqi <= 150:
        return f"🟠 {aqi} (Unhealthy for Sensitive)"
    elif aqi <= 200:
        return f"🔴 {aqi} (Unhealthy)"
    elif aqi <= 300:
        return f"🟣 {aqi} (Very Unhealthy)"
    else:
        return f"🟤 {aqi} (Hazardous)"


def format_pm25(pm25: Optional[float]) -> str:
    """
    Format PM2.5 value with unit.
    
    Args:
        pm25: PM2.5 value in μg/m³
        
    Returns:
        Formatted string with unit
    """
    if pm25 is None:
        return "N/A"
    return f"{pm25:.1f} μg/m³"


def format_reading(reading: AirReading, detailed: bool = False) -> str:
    """
    Format an air quality reading for display.
    
    Args:
        reading: AirReading object
        detailed: Whether to include all details
        
    Returns:
        Formatted string
    """
    color = reading.get_health_color()
    aqi = reading.aqi or reading.calculate_aqi()
    
    if detailed:
        lines = [
            f"{color} **{reading.location_name}**",
            f"📍 {reading.city}, {reading.country}",
            f"",
            f"**Measurements:**",
            f"- PM2.5: {format_pm25(reading.pm25)}",
            f"- AQI: {format_aqi(aqi)}",
            f"- Category: {reading.get_health_category()}",
        ]
        
        if reading.pm10:
            lines.append(f"- PM10: {reading.pm10:.1f} μg/m³")
        if reading.ozone:
            lines.append(f"- Ozone: {reading.ozone:.3f} ppm")
        if reading.no2:
            lines.append(f"- NO2: {reading.no2:.3f} ppm")
        
        if reading.timestamp:
            lines.append(f"")
            lines.append(f"🕐 {reading.timestamp.strftime('%Y-%m-%d %H:%M UTC')}")
        
        return "\n".join(lines)
    else:
        return (
            f"{color} {reading.city}: "
            f"PM2.5={format_pm25(reading.pm25)}, "
            f"AQI={aqi or 'N/A'} ({reading.get_health_category()})"
        )


def format_readings_table(readings: List[AirReading]) -> str:
    """
    Format multiple readings as a table.
    
    Args:
        readings: List of AirReading objects
        
    Returns:
        Formatted table string
    """
    if not readings:
        return "No readings available."
    
    lines = [
        "| Location | City | PM2.5 | AQI | Category |",
        "|----------|------|-------|-----|----------|",
    ]
    
    for r in readings:
        aqi = r.aqi or r.calculate_aqi() or "N/A"
        pm25 = f"{r.pm25:.1f}" if r.pm25 else "N/A"
        color = r.get_health_color()
        
        lines.append(
            f"| {r.location_name[:20]} | {r.city[:15]} | {pm25} | {aqi} | {color} {r.get_health_category()} |"
        )
    
    return "\n".join(lines)


def format_health_advice(reading: AirReading) -> str:
    """
    Format health advice based on air quality reading.
    
    Args:
        reading: AirReading object
        
    Returns:
        Health advice string
    """
    category = reading.get_health_category()
    advice = reading.get_health_advice()
    color = reading.get_health_color()
    
    return f"""
{color} **Air Quality: {category}**

{advice}

**Recommendations:**
{_get_recommendations(category)}
"""


def _get_recommendations(category: str) -> str:
    """Get specific recommendations based on category."""
    recommendations = {
        "Good": """
✅ Great day for outdoor activities
✅ No restrictions needed
✅ Enjoy the fresh air!
""",
        "Moderate": """
⚠️ Sensitive individuals should consider reducing prolonged outdoor exertion
✅ Most people can enjoy outdoor activities
✅ Keep windows open for ventilation
""",
        "Unhealthy for Sensitive Groups": """
⚠️ People with respiratory or heart conditions should limit outdoor activities
⚠️ Children and elderly should reduce prolonged outdoor exertion
✅ General population can be active outdoors
""",
        "Unhealthy": """
🚫 Avoid prolonged outdoor exertion
⚠️ Everyone may experience health effects
⚠️ Keep outdoor activities brief
✅ Use air purifiers indoors if available
""",
        "Very Unhealthy": """
🚫 Avoid all outdoor physical activities
🚫 Keep windows and doors closed
⚠️ Use air purifiers
⚠️ Wear N95 masks if going outside
""",
        "Hazardous": """
🚨 HEALTH EMERGENCY
🚫 Stay indoors
🚫 Keep all windows sealed
⚠️ Run air purifiers on high
⚠️ Seek medical attention if experiencing symptoms
""",
    }
    return recommendations.get(category, "No specific recommendations available.")


def format_comparison(city1: str, city2: str, stats1: dict, stats2: dict) -> str:
    """
    Format a comparison between two cities.
    
    Args:
        city1: First city name
        city2: Second city name
        stats1: Stats for first city
        stats2: Stats for second city
        
    Returns:
        Formatted comparison string
    """
    lines = [
        f"## Air Quality Comparison: {city1} vs {city2}",
        "",
        "| Metric | " + city1 + " | " + city2 + " |",
        "|--------|" + "-" * len(city1) + "--|" + "-" * len(city2) + "--|",
    ]
    
    # Average AQI
    aqi1 = stats1.get("avg_aqi")
    aqi2 = stats2.get("avg_aqi")
    aqi1_str = f"{aqi1:.0f}" if aqi1 else "N/A"
    aqi2_str = f"{aqi2:.0f}" if aqi2 else "N/A"
    lines.append(f"| Avg AQI | {aqi1_str} | {aqi2_str} |")
    
    # Average PM2.5
    pm1 = stats1.get("avg_pm25")
    pm2 = stats2.get("avg_pm25")
    pm1_str = f"{pm1:.1f}" if pm1 else "N/A"
    pm2_str = f"{pm2:.1f}" if pm2 else "N/A"
    lines.append(f"| Avg PM2.5 | {pm1_str} | {pm2_str} |")
    
    # Worst category
    cat1 = stats1.get("worst_category", "N/A")
    cat2 = stats2.get("worst_category", "N/A")
    lines.append(f"| Worst Category | {cat1} | {cat2} |")
    
    # Determine winner
    lines.append("")
    if aqi1 and aqi2:
        if aqi1 < aqi2:
            lines.append(f"🏆 **{city1}** has better air quality (lower AQI)")
        elif aqi2 < aqi1:
            lines.append(f"🏆 **{city2}** has better air quality (lower AQI)")
        else:
            lines.append("🤝 Both cities have similar air quality")
    
    return "\n".join(lines)


def format_latency(latency_ms: int) -> str:
    """
    Format latency with performance indicator.
    
    Args:
        latency_ms: Latency in milliseconds
        
    Returns:
        Formatted string with indicator
    """
    if latency_ms < 200:
        return f"⚡ {latency_ms}ms (Ultra Fast)"
    elif latency_ms < 500:
        return f"🚀 {latency_ms}ms (Fast)"
    elif latency_ms < 1000:
        return f"✓ {latency_ms}ms (Normal)"
    elif latency_ms < 2000:
        return f"⏳ {latency_ms}ms (Slow)"
    else:
        return f"🐢 {latency_ms}ms (Very Slow)"


"""
Query Service.
Handles natural language queries about air quality data.
Integrates OpenAQ real data with Cerebras AI for intelligent responses.
"""

from typing import Optional, List, Dict, Any
import time
import re

from clients.raindrop_client import RaindropClient
from clients.openaq_client import OpenAQClient
from services.city_index_service import CityIndexService, normalize_city_name
from models.query_result import QueryResult
from models.air_reading import AirReading
from config.settings import settings


class QueryService:
    """
    Service for handling natural language queries about air quality.
    
    This service:
    1. Extracts city names from user questions
    2. Fetches real-time data from OpenAQ via CityIndexService
    3. Builds rich context from the data
    4. Sends to Cerebras for intelligent interpretation
    5. Returns comprehensive, data-backed answers
    
    Usage:
        service = QueryService(raindrop_client, openaq_client)
        result = service.ask("Is the air safe in Tokyo?")
        print(result.answer)
    """
    
    SYSTEM_PROMPT = """You are AirSight, an expert AI assistant for air quality information.

You have access to REAL-TIME air quality data from monitoring stations worldwide.

IMPORTANT RULES:
1. ALWAYS use the provided data in your response - cite specific numbers
2. Be direct and actionable - users want to know if it's safe
3. Include health recommendations based on AQI levels
4. If data shows dangerous levels, clearly warn the user

AQI CATEGORIES (use these exact terms):
- 0-50: Good (🟢) - Air quality is satisfactory
- 51-100: Moderate (🟡) - Acceptable, sensitive people may be affected  
- 101-150: Unhealthy for Sensitive Groups (🟠) - Sensitive groups should limit outdoor activities
- 151-200: Unhealthy (🔴) - Everyone may experience health effects
- 201-300: Very Unhealthy (🟣) - Health alert, avoid outdoor activities
- 301+: Hazardous (🟤) - Health emergency, stay indoors

FORMAT YOUR RESPONSE:
1. Start with the AQI category emoji and status
2. State the actual PM2.5/AQI numbers
3. Explain what this means for the user
4. Give specific recommendations

Keep responses concise but complete (under 200 words)."""

    # Common city name variations
    CITY_ALIASES = {
        "nyc": "new york",
        "ny": "new york", 
        "la": "los angeles",
        "sf": "san francisco",
        "dc": "washington",
        "philly": "philadelphia",
        "vegas": "las vegas",
    }
    
    def __init__(
        self, 
        raindrop: RaindropClient, 
        openaq: OpenAQClient,
        city_index: CityIndexService = None
    ):
        """
        Initialize the query service.
        
        Args:
            raindrop: Raindrop client for AI inference
            openaq: OpenAQ client for data
            city_index: Optional pre-initialized city index
        """
        self.raindrop = raindrop
        self.openaq = openaq
        
        # Initialize city index
        if city_index:
            self.city_index = city_index
        else:
            self.city_index = CityIndexService(openaq)
            self.city_index.load_index()
    
    def ask(self, question: str, user_id: str = "default") -> QueryResult:
        """
        Answer a natural language question about air quality.
        
        This is the main entry point. It:
        1. Extracts the city from the question
        2. Fetches real data from OpenAQ
        3. Builds context for Cerebras
        4. Returns an informed answer
        
        Args:
            question: User's question
            user_id: User identifier for context
            
        Returns:
            QueryResult with answer and metadata
        """
        start_time = time.time()
        
        if not question.strip():
            return QueryResult.error("Please provide a question.", 0)
        
        try:
            # 1. Extract city from question
            city = self._extract_city(question)
            
            if not city:
                # No city found - give general response
                return self._handle_no_city(question, start_time)
            
            # 2. Fetch real data from OpenAQ
            readings = self.city_index.get_readings_for_city(city, limit=3)
            
            if not readings:
                # City recognized but no data
                return self._handle_no_data(city, question, start_time)
            
            # 3. Build context from real data
            context = self._build_data_context(city, readings)
            
            # 4. Query Cerebras with real data
            prompt = f"""USER QUESTION: {question}

REAL-TIME AIR QUALITY DATA:
{context}

Based on this REAL data, provide a helpful and accurate response to the user's question."""

            result = self.raindrop.inference.query(
                prompt=prompt,
                system_prompt=self.SYSTEM_PROMPT,
                max_tokens=400,
                temperature=0.7,
            )
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            # 5. Build response
            return QueryResult(
                answer=result["response"],
                confidence=0.95,  # High confidence with real data
                latency_ms=latency_ms,
                sources=[{
                    "type": "openaq",
                    "city": city,
                    "readings": len(readings),
                    "stations": [r.location_name for r in readings]
                }],
                readings=readings,
                metadata={
                    "city": city,
                    "data_points": len(readings),
                    "inference_latency_ms": result.get("latency_ms"),
                },
            )
            
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            return QueryResult.error(str(e), latency_ms)
    
    def compare(self, city1: str, city2: str, user_id: str = "default") -> QueryResult:
        """
        Compare air quality between two cities using real data.
        
        Args:
            city1: First city
            city2: Second city
            user_id: User identifier
            
        Returns:
            QueryResult with comparison
        """
        start_time = time.time()
        
        try:
            # Normalize city names
            city1 = normalize_city_name(city1)
            city2 = normalize_city_name(city2)
            
            # Get readings for both cities
            readings1 = self.city_index.get_readings_for_city(city1, limit=3)
            readings2 = self.city_index.get_readings_for_city(city2, limit=3)
            
            # Build comparison context
            context1 = self._build_data_context(city1, readings1) if readings1 else f"No data available for {city1}"
            context2 = self._build_data_context(city2, readings2) if readings2 else f"No data available for {city2}"
            
            prompt = f"""Compare the air quality between {city1.title()} and {city2.title()}.

{city1.upper()} DATA:
{context1}

{city2.upper()} DATA:
{context2}

Provide a clear comparison:
1. Which city has better air quality right now?
2. What are the specific differences in PM2.5/AQI?
3. Health recommendations for each city"""

            result = self.raindrop.inference.query(
                prompt=prompt,
                system_prompt=self.SYSTEM_PROMPT,
                max_tokens=500,
            )
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            all_readings = readings1 + readings2
            
            return QueryResult(
                answer=result["response"],
                confidence=0.9 if readings1 and readings2 else 0.7,
                latency_ms=latency_ms,
                sources=[{
                    "type": "comparison",
                    "cities": [city1, city2],
                    "data_available": [bool(readings1), bool(readings2)]
                }],
                readings=all_readings,
                metadata={
                    "city1": city1,
                    "city2": city2,
                    "city1_readings": len(readings1),
                    "city2_readings": len(readings2),
                },
            )
            
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            return QueryResult.error(str(e), latency_ms)
    
    def get_health_advice(self, city: str, user_id: str = "default") -> QueryResult:
        """
        Get detailed health advice based on current air quality.
        
        Args:
            city: City name
            user_id: User identifier
            
        Returns:
            QueryResult with health advice
        """
        start_time = time.time()
        
        city = normalize_city_name(city)
        readings = self.city_index.get_readings_for_city(city, limit=3)
        
        if not readings:
            latency_ms = int((time.time() - start_time) * 1000)
            return QueryResult.no_data(city, latency_ms)
        
        # Get worst reading for conservative advice
        worst_reading = max(readings, key=lambda r: r.aqi or r.calculate_aqi() or 0)
        
        context = self._build_data_context(city, readings)
        
        prompt = f"""Provide detailed health advice for {city.title()} based on current air quality.

CURRENT CONDITIONS:
{context}

Provide specific advice for:
1. 👶 Children and elderly
2. 🏃 Athletes and outdoor workers  
3. 😷 People with asthma/respiratory conditions
4. 👤 General population
5. 🏠 Indoor vs outdoor recommendations
6. 😷 Mask recommendations (if needed)

Be specific about what activities are safe or should be avoided."""

        result = self.raindrop.inference.query(
            prompt=prompt,
            system_prompt=self.SYSTEM_PROMPT,
            max_tokens=600,
        )
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        return QueryResult(
            answer=result["response"],
            confidence=0.95,
            latency_ms=latency_ms,
            sources=[{"type": "health_advice", "city": city}],
            readings=readings,
        )
    
    # =========================================
    # Helper Methods
    # =========================================
    
    def _extract_city(self, question: str) -> Optional[str]:
        """
        Extract city name from a question.
        
        Uses multiple strategies:
        1. Check for known city aliases
        2. Pattern matching for common phrases
        3. Check against city index
        
        Args:
            question: User's question
            
        Returns:
            City name or None
        """
        question_lower = question.lower()
        
        # 1. Check aliases
        for alias, city in self.CITY_ALIASES.items():
            # Use word boundary to avoid partial matches
            if re.search(rf'\b{alias}\b', question_lower):
                return city
        
        # 2. Common city names (expanded list)
        common_cities = [
            # Asia
            "delhi", "mumbai", "bangalore", "chennai", "kolkata", "hyderabad",
            "beijing", "shanghai", "guangzhou", "shenzhen", "hong kong",
            "tokyo", "osaka", "seoul", "singapore", "bangkok", "jakarta",
            "manila", "ho chi minh", "hanoi", "kuala lumpur",
            # Europe
            "london", "paris", "berlin", "madrid", "rome", "amsterdam",
            "brussels", "vienna", "prague", "warsaw", "moscow", "barcelona",
            # Americas
            "new york", "los angeles", "chicago", "houston", "phoenix",
            "san francisco", "seattle", "boston", "miami", "denver",
            "toronto", "vancouver", "montreal", "mexico city", "sao paulo",
            # Middle East & Africa
            "dubai", "cairo", "tel aviv", "johannesburg", "lagos", "nairobi",
            # Oceania
            "sydney", "melbourne", "auckland", "brisbane",
            # Countries (for broad queries)
            "india", "china", "united states", "united kingdom", "japan",
            "germany", "france", "canada", "australia", "brazil",
        ]
        
        for city in common_cities:
            if city in question_lower:
                return city
        
        # 3. Pattern matching: "in <City>", "for <City>"
        patterns = [
            r"(?:in|for|at|of)\s+([A-Z][a-zA-Z\s]+?)(?:\s+(?:right now|today|currently|now))?[?\.\,]?$",
            r"(?:in|for|at|of)\s+([A-Z][a-zA-Z\s]+?)(?:\s+air)",
            r"^([A-Z][a-zA-Z\s]+?)\s+air\s+quality",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, question)
            if match:
                potential_city = match.group(1).strip().lower()
                # Verify it's in our index
                if self.city_index.is_city_available(potential_city):
                    return potential_city
        
        return None
    
    def _build_data_context(self, city: str, readings: List[AirReading]) -> str:
        """
        Build a rich context string from air quality readings.
        
        Args:
            city: City name
            readings: List of readings
            
        Returns:
            Formatted context string
        """
        if not readings:
            return f"No data available for {city}"
        
        lines = [f"City: {city.title()}"]
        lines.append(f"Data Points: {len(readings)} monitoring station(s)")
        lines.append("")
        
        for i, reading in enumerate(readings, 1):
            aqi = reading.aqi or reading.calculate_aqi()
            category = reading.get_health_category()
            color = reading.get_health_color()
            
            lines.append(f"Station {i}: {reading.location_name}")
            lines.append(f"  - PM2.5: {reading.pm25:.1f} μg/m³")
            lines.append(f"  - AQI: {aqi}")
            lines.append(f"  - Category: {color} {category}")
            lines.append(f"  - Country: {reading.country}")
            lines.append("")
        
        # Add summary
        pm25_values = [r.pm25 for r in readings if r.pm25]
        aqi_values = [r.aqi or r.calculate_aqi() for r in readings]
        
        if pm25_values:
            avg_pm25 = sum(pm25_values) / len(pm25_values)
            max_pm25 = max(pm25_values)
            lines.append(f"Summary:")
            lines.append(f"  - Average PM2.5: {avg_pm25:.1f} μg/m³")
            lines.append(f"  - Highest PM2.5: {max_pm25:.1f} μg/m³")
            
            if aqi_values:
                avg_aqi = sum(aqi_values) / len(aqi_values)
                max_aqi = max(aqi_values)
                lines.append(f"  - Average AQI: {avg_aqi:.0f}")
                lines.append(f"  - Highest AQI: {max_aqi:.0f}")
        
        return "\n".join(lines)
    
    def _handle_no_city(self, question: str, start_time: float) -> QueryResult:
        """Handle questions where no city could be extracted."""
        prompt = f"""The user asked: "{question}"

I couldn't identify a specific city in this question. Please:
1. If this is a general air quality question, provide helpful information
2. If they're asking about a specific location, ask them to clarify which city
3. Suggest some example cities they could ask about

Keep the response helpful and friendly."""

        result = self.raindrop.inference.query(
            prompt=prompt,
            system_prompt=self.SYSTEM_PROMPT,
            max_tokens=300,
        )
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        return QueryResult(
            answer=result["response"],
            confidence=0.6,
            latency_ms=latency_ms,
            sources=[{"type": "general"}],
            metadata={"city_extracted": False},
        )
    
    def _handle_no_data(self, city: str, question: str, start_time: float) -> QueryResult:
        """Handle cases where city is recognized but no data is available."""
        prompt = f"""The user asked about {city}, but I don't have current monitoring data for that location.

User question: "{question}"

Please:
1. Apologize for not having data for {city}
2. Suggest nearby cities or countries that might have data
3. Recommend checking local air quality services for {city}

Available regions with good data: India (Delhi, etc.), China (Beijing, Shanghai), UK (London), USA (New York, LA), Australia (Sydney)"""

        result = self.raindrop.inference.query(
            prompt=prompt,
            system_prompt=self.SYSTEM_PROMPT,
            max_tokens=250,
        )
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        return QueryResult(
            answer=result["response"],
            confidence=0.5,
            latency_ms=latency_ms,
            sources=[{"type": "no_data", "city": city}],
            metadata={"city": city, "data_available": False},
        )

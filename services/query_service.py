"""
Query Service.
Handles natural language queries about air quality data.
"""

from typing import Optional, List, Dict, Any
import time
import re

from clients.raindrop_client import RaindropClient
from services.data_service import DataService
from models.query_result import QueryResult
from models.air_reading import AirReading
from config.settings import settings


class QueryService:
    """
    Service for handling natural language queries about air quality.
    
    Responsibilities:
    - Process user questions in natural language
    - Retrieve relevant context from SmartBuckets
    - Generate answers via Cerebras (SmartInference)
    - Maintain conversation context via SmartMemory
    
    Usage:
        service = QueryService(raindrop_client, data_service)
        result = service.ask("Is the air safe in Tokyo?")
        print(result.answer)
    """
    
    SYSTEM_PROMPT = """You are AirSight, an AI assistant that provides instant, accurate air quality information.

You have access to real-time air quality data from sensors worldwide via OpenAQ.

When answering questions:
1. Be direct and concise - users want quick answers
2. Always include specific measurements when available (PM2.5, AQI)
3. Provide health recommendations based on AQI levels
4. Use the health categories: Good, Moderate, Unhealthy for Sensitive Groups, Unhealthy, Very Unhealthy, Hazardous
5. If air quality is concerning, clearly warn the user

AQI Reference:
- 0-50: Good (Green) - Air quality is satisfactory
- 51-100: Moderate (Yellow) - Acceptable, sensitive people may be affected
- 101-150: Unhealthy for Sensitive Groups (Orange) - Sensitive groups should reduce outdoor activities
- 151-200: Unhealthy (Red) - Everyone may begin to experience health effects
- 201-300: Very Unhealthy (Purple) - Health alert, avoid outdoor activities
- 301+: Hazardous (Maroon) - Health emergency, stay indoors

Always respond in a helpful, informative tone. Keep responses under 150 words unless more detail is needed."""

    # Common city name variations for extraction
    CITY_ALIASES = {
        "la": "Los Angeles",
        "nyc": "New York",
        "sf": "San Francisco",
        "dc": "Washington",
        "philly": "Philadelphia",
    }
    
    def __init__(self, raindrop: RaindropClient, data_service: DataService):
        """
        Initialize the query service.
        
        Args:
            raindrop: Raindrop client for inference and memory
            data_service: Data service for fetching air quality data
        """
        self.raindrop = raindrop
        self.data_service = data_service
    
    def ask(self, question: str, user_id: str = "default") -> QueryResult:
        """
        Answer a natural language question about air quality.
        
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
            # 1. Get user context from SmartMemory
            user_context = self.raindrop.memory.get_context(user_id)
            
            # 2. Extract city from question
            city = self._extract_city(question)
            
            # 3. Fetch fresh data if city found
            readings = []
            if city:
                readings = self.data_service.get_air_quality(city, limit=5)
            
            # 4. Search SmartBuckets for additional context
            relevant_docs = self.raindrop.buckets.search(
                bucket_name="air-readings",
                query=question,
                limit=5,
            )
            
            # 5. Build context for the LLM
            context = self._build_context(readings, relevant_docs, user_context)
            
            # 6. Generate answer via Cerebras
            prompt = self._build_prompt(question, context)
            
            result = self.raindrop.inference.query(
                prompt=prompt,
                system_prompt=self.SYSTEM_PROMPT,
                max_tokens=300,
                temperature=0.7,
            )
            
            # 7. Store query in memory for context
            self._store_query_context(user_id, question, city)
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            return QueryResult(
                answer=result["response"],
                confidence=0.9 if readings else 0.7,
                latency_ms=latency_ms,
                sources=[{"type": "openaq", "readings": len(readings)}],
                readings=readings,
                metadata={
                    "city": city,
                    "model": result.get("model"),
                    "inference_latency_ms": result.get("latency_ms"),
                },
            )
            
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            return QueryResult.error(str(e), latency_ms)
    
    def compare(self, city1: str, city2: str, user_id: str = "default") -> QueryResult:
        """
        Compare air quality between two cities.
        
        Args:
            city1: First city
            city2: Second city
            user_id: User identifier
            
        Returns:
            QueryResult with comparison
        """
        start_time = time.time()
        
        try:
            # Get comparison data
            comparison = self.data_service.compare_cities(city1, city2)
            
            # Build prompt for comparison
            prompt = f"""Compare the air quality between {city1} and {city2}.

Data for {city1}:
- Average AQI: {comparison['city1'].get('avg_aqi', 'N/A')}
- Average PM2.5: {comparison['city1'].get('avg_pm25', 'N/A')} μg/m³
- Worst Category: {comparison['city1'].get('worst_category', 'N/A')}
- Number of readings: {comparison['city1'].get('num_readings', 0)}

Data for {city2}:
- Average AQI: {comparison['city2'].get('avg_aqi', 'N/A')}
- Average PM2.5: {comparison['city2'].get('avg_pm25', 'N/A')} μg/m³
- Worst Category: {comparison['city2'].get('worst_category', 'N/A')}
- Number of readings: {comparison['city2'].get('num_readings', 0)}

Provide a clear comparison highlighting which city has better air quality and any health recommendations."""

            result = self.raindrop.inference.query(
                prompt=prompt,
                system_prompt=self.SYSTEM_PROMPT,
                max_tokens=400,
            )
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Collect readings from both cities
            all_readings = []
            readings1 = self.data_service.get_air_quality(city1, limit=3)
            readings2 = self.data_service.get_air_quality(city2, limit=3)
            all_readings.extend(readings1)
            all_readings.extend(readings2)
            
            return QueryResult(
                answer=result["response"],
                confidence=0.9,
                latency_ms=latency_ms,
                sources=[{"cities": [city1, city2], "comparison": comparison}],
                readings=all_readings,
                metadata={"comparison": comparison},
            )
            
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            return QueryResult.error(str(e), latency_ms)
    
    def explain_reading(self, reading: AirReading, user_id: str = "default") -> QueryResult:
        """
        Explain an air quality reading in detail.
        
        Args:
            reading: Air quality reading to explain
            user_id: User identifier
            
        Returns:
            QueryResult with explanation
        """
        start_time = time.time()
        
        prompt = f"""Explain this air quality reading and provide health recommendations:

Location: {reading.location_name}, {reading.city}, {reading.country}
PM2.5: {reading.pm25} μg/m³
AQI: {reading.aqi or reading.calculate_aqi()}
Health Category: {reading.get_health_category()}
Time: {reading.timestamp}

Explain:
1. What these numbers mean
2. Health implications
3. Recommendations for outdoor activities
4. Who should be most careful"""

        result = self.raindrop.inference.query(
            prompt=prompt,
            system_prompt=self.SYSTEM_PROMPT,
            max_tokens=350,
        )
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        return QueryResult(
            answer=result["response"],
            confidence=0.95,
            latency_ms=latency_ms,
            sources=[{"type": "explanation"}],
            readings=[reading],
        )
    
    def get_health_advice(self, city: str, user_id: str = "default") -> QueryResult:
        """
        Get health advice for current air quality in a city.
        
        Args:
            city: City name
            user_id: User identifier
            
        Returns:
            QueryResult with health advice
        """
        start_time = time.time()
        
        readings = self.data_service.get_air_quality(city, limit=5)
        
        if not readings:
            latency_ms = int((time.time() - start_time) * 1000)
            return QueryResult.no_data(city, latency_ms)
        
        # Use the worst reading for advice
        worst_reading = max(
            readings,
            key=lambda r: r.aqi or r.calculate_aqi() or 0
        )
        
        prompt = f"""Based on the current air quality in {city}, provide detailed health advice.

Current conditions:
- PM2.5: {worst_reading.pm25} μg/m³
- AQI: {worst_reading.aqi or worst_reading.calculate_aqi()}
- Category: {worst_reading.get_health_category()}

Provide specific advice for:
1. General population
2. Children and elderly
3. People with respiratory conditions
4. Athletes and outdoor workers
5. Recommended activities and precautions"""

        result = self.raindrop.inference.query(
            prompt=prompt,
            system_prompt=self.SYSTEM_PROMPT,
            max_tokens=400,
        )
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        return QueryResult(
            answer=result["response"],
            confidence=0.9,
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
        
        Args:
            question: User's question
            
        Returns:
            City name or None
        """
        question_lower = question.lower()
        
        # Check aliases first
        for alias, full_name in self.CITY_ALIASES.items():
            if alias in question_lower.split():
                return full_name
        
        # Common city names to look for
        common_cities = [
            "tokyo", "delhi", "new delhi", "mumbai", "beijing", "shanghai",
            "london", "paris", "berlin", "rome", "madrid",
            "new york", "los angeles", "chicago", "houston", "phoenix",
            "san francisco", "seattle", "boston", "miami", "denver",
            "toronto", "vancouver", "montreal",
            "sydney", "melbourne", "auckland",
            "singapore", "hong kong", "seoul", "osaka", "bangkok",
            "dubai", "cairo", "lagos", "johannesburg",
            "sao paulo", "rio de janeiro", "mexico city", "buenos aires",
        ]
        
        for city in common_cities:
            if city in question_lower:
                return city.title()
        
        # Try to extract using patterns like "in <City>" or "for <City>"
        patterns = [
            r"in\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
            r"for\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
            r"of\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
            r"at\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, question)
            if match:
                return match.group(1)
        
        return None
    
    def _build_context(
        self,
        readings: List[AirReading],
        docs: List[Dict],
        user_context: Dict,
    ) -> str:
        """Build context string for the LLM."""
        parts = []
        
        if readings:
            parts.append("Current Air Quality Readings:")
            for r in readings[:5]:
                parts.append(
                    f"- {r.location_name}, {r.city}: "
                    f"PM2.5={r.pm25:.1f} μg/m³, "
                    f"AQI={r.aqi or r.calculate_aqi()}, "
                    f"Category={r.get_health_category()}"
                )
        
        if docs:
            parts.append("\nRelated Historical Data:")
            for doc in docs[:3]:
                data = doc.get("data", {})
                parts.append(f"- {data.get('city', 'Unknown')}: PM2.5={data.get('pm25', 'N/A')}")
        
        if user_context:
            if "last_city" in user_context:
                parts.append(f"\nUser previously asked about: {user_context['last_city']}")
        
        return "\n".join(parts) if parts else "No specific data available."
    
    def _build_prompt(self, question: str, context: str) -> str:
        """Build the full prompt for the LLM."""
        return f"""User Question: {question}

Available Data:
{context}

Please provide a helpful, accurate response based on the available data. If the data is limited, acknowledge this and provide general guidance."""
    
    def _store_query_context(self, user_id: str, question: str, city: Optional[str]):
        """Store query context in SmartMemory for future reference."""
        if city:
            self.raindrop.memory.store("last_city", city, user_id=user_id)
        
        # Store recent queries (keep last 5)
        recent = self.raindrop.memory.retrieve("recent_queries", user_id=user_id) or []
        recent.insert(0, {"question": question, "city": city, "timestamp": time.time()})
        recent = recent[:5]
        self.raindrop.memory.store("recent_queries", recent, user_id=user_id)


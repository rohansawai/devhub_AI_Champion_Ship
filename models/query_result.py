"""
Query result data model.
Represents the result of a natural language query.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .air_reading import AirReading
    from .alert import Alert


@dataclass
class QueryResult:
    """
    Represents the result of a natural language query.
    
    Attributes:
        answer: The AI-generated answer to the query
        confidence: Confidence score (0.0 to 1.0)
        sources: List of sources used to generate the answer
        latency_ms: Time taken to generate the response in milliseconds
        readings: Air quality readings used in the response
        alerts_triggered: Any alerts that were triggered
        metadata: Additional metadata about the query
    """
    
    answer: str
    confidence: float
    latency_ms: int
    sources: List[Dict[str, Any]] = field(default_factory=list)
    readings: Optional[List["AirReading"]] = None
    alerts_triggered: Optional[List["Alert"]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate and set defaults."""
        # Ensure confidence is between 0 and 1
        self.confidence = max(0.0, min(1.0, self.confidence))
        
        # Ensure latency is non-negative
        self.latency_ms = max(0, self.latency_ms)
    
    def is_successful(self) -> bool:
        """Check if the query was successful."""
        return bool(self.answer) and self.confidence > 0.5
    
    def get_latency_category(self) -> str:
        """
        Get a category for the latency.
        
        Returns:
            String describing the latency performance
        """
        if self.latency_ms < 200:
            return "⚡ Ultra Fast"
        elif self.latency_ms < 500:
            return "🚀 Fast"
        elif self.latency_ms < 1000:
            return "✓ Normal"
        elif self.latency_ms < 2000:
            return "⏳ Slow"
        else:
            return "🐢 Very Slow"
    
    def to_display(self) -> str:
        """
        Format the result for display in the UI.
        
        Returns:
            Formatted string for display
        """
        lines = [self.answer]
        
        # Add readings summary if available
        if self.readings:
            lines.append("\n---")
            lines.append(f"📊 Based on {len(self.readings)} measurement(s)")
        
        # Add alerts if any were triggered
        if self.alerts_triggered:
            lines.append("\n---")
            lines.append(f"🔔 {len(self.alerts_triggered)} alert(s) triggered")
        
        # Add latency info
        lines.append(f"\n⚡ Response time: {self.latency_ms}ms ({self.get_latency_category()})")
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/serialization."""
        return {
            "answer": self.answer,
            "confidence": self.confidence,
            "latency_ms": self.latency_ms,
            "sources": self.sources,
            "readings_count": len(self.readings) if self.readings else 0,
            "alerts_triggered_count": len(self.alerts_triggered) if self.alerts_triggered else 0,
            "metadata": self.metadata,
        }
    
    @classmethod
    def error(cls, message: str, latency_ms: int = 0) -> "QueryResult":
        """
        Create an error result.
        
        Args:
            message: Error message
            latency_ms: Time taken before error
            
        Returns:
            QueryResult with error state
        """
        return cls(
            answer=f"❌ Error: {message}",
            confidence=0.0,
            latency_ms=latency_ms,
            sources=[],
            metadata={"error": True, "error_message": message},
        )
    
    @classmethod
    def no_data(cls, query: str, latency_ms: int = 0) -> "QueryResult":
        """
        Create a result for when no data is available.
        
        Args:
            query: The original query
            latency_ms: Time taken
            
        Returns:
            QueryResult indicating no data
        """
        return cls(
            answer="I couldn't find any air quality data for your query. Please try a different location or check if the city name is correct.",
            confidence=0.3,
            latency_ms=latency_ms,
            sources=[],
            metadata={"no_data": True, "original_query": query},
        )
    
    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"QueryResult(confidence={self.confidence:.2f}, latency={self.latency_ms}ms, answer_length={len(self.answer)})"


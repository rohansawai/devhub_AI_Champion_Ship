"""
Application configuration - single source of truth for all settings.
Loads from environment variables with sensible defaults.
"""

from dataclasses import dataclass, field
from typing import Optional
import os
from pathlib import Path


@dataclass
class Settings:
    """Application configuration loaded from environment variables."""
    
    # ===================
    # Required API Keys
    # ===================
    openaq_api_key: str = ""
    raindrop_api_key: str = ""
    cerebras_api_key: str = ""
    
    # ===================
    # Optional API Keys (for future extensions)
    # ===================
    workos_client_id: Optional[str] = None
    workos_api_key: Optional[str] = None
    stripe_api_key: Optional[str] = None
    vultr_api_key: Optional[str] = None
    
    # ===================
    # App Settings
    # ===================
    app_name: str = "AirSight"
    app_version: str = "0.1.0"
    debug: bool = False
    
    # ===================
    # Data Settings
    # ===================
    cache_ttl_seconds: int = 300  # 5 minutes
    default_radius_meters: int = 25000  # 25km
    max_results: int = 100
    
    # ===================
    # API Settings
    # ===================
    openaq_base_url: str = "https://api.openaq.org/v3"
    cerebras_base_url: str = "https://api.cerebras.ai/v1"
    
    # ===================
    # Raindrop Settings
    # ===================
    raindrop_bucket_name: str = "air-readings"
    raindrop_table_name: str = "readings"
    
    @classmethod
    def from_env(cls) -> "Settings":
        """Load settings from environment variables."""
        return cls(
            # Required keys
            openaq_api_key=os.getenv("OPENAQ_API_KEY", ""),
            raindrop_api_key=os.getenv("RAINDROP_API_KEY", ""),
            cerebras_api_key=os.getenv("CEREBRAS_API_KEY", ""),
            
            # Optional keys
            workos_client_id=os.getenv("WORKOS_CLIENT_ID"),
            workos_api_key=os.getenv("WORKOS_API_KEY"),
            stripe_api_key=os.getenv("STRIPE_API_KEY"),
            vultr_api_key=os.getenv("VULTR_API_KEY"),
            
            # App settings
            debug=os.getenv("DEBUG", "false").lower() == "true",
            
            # Data settings
            cache_ttl_seconds=int(os.getenv("CACHE_TTL_SECONDS", "300")),
            default_radius_meters=int(os.getenv("DEFAULT_RADIUS_METERS", "25000")),
            max_results=int(os.getenv("MAX_RESULTS", "100")),
        )
    
    def validate(self) -> list[str]:
        """
        Validate required settings are present.
        Returns list of missing/invalid settings.
        """
        errors = []
        
        if not self.openaq_api_key:
            errors.append("OPENAQ_API_KEY is required")
        
        # Raindrop and Cerebras are needed for full functionality
        # but we can run in limited mode without them
        if not self.cerebras_api_key:
            errors.append("CEREBRAS_API_KEY is required for AI features")
        
        return errors
    
    def is_valid(self) -> bool:
        """Check if all required settings are valid."""
        return len(self.validate()) == 0
    
    def __repr__(self) -> str:
        """Safe repr that doesn't expose API keys."""
        return (
            f"Settings("
            f"app_name={self.app_name!r}, "
            f"debug={self.debug}, "
            f"openaq_key_set={bool(self.openaq_api_key)}, "
            f"cerebras_key_set={bool(self.cerebras_api_key)}, "
            f"raindrop_key_set={bool(self.raindrop_api_key)}"
            f")"
        )


# Global settings instance - loaded once at import time
settings = Settings.from_env()


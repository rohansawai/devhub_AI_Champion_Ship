"""
AirSight - Hugging Face Spaces Entry Point
"""
import os

# For HF Spaces, set env vars from secrets
# Users will add CEREBRAS_API_KEY and OPENAQ_API_KEY as secrets in Space settings

from ui.gradio_app import create_app

demo = create_app()
demo.launch()

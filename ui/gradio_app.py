"""
Gradio UI for AirSight.
Provides a beautiful web interface for air quality intelligence.
"""

import gradio as gr
from typing import Tuple

from app import AirSightApp
from models.alert import AlertType


# =========================================
# Global App Instance
# =========================================

app: AirSightApp = None


def get_app() -> AirSightApp:
    """Get or create the app instance."""
    global app
    if app is None:
        app = AirSightApp()
        app.initialize()
    return app


# =========================================
# Handler Functions
# =========================================

def handle_ask(question: str) -> str:
    """Handle a question from the user."""
    if not question.strip():
        return "❓ Please enter a question about air quality."
    
    try:
        return get_app().ask(question)
    except Exception as e:
        return f"❌ Error: {str(e)}"


def handle_compare(city1: str, city2: str) -> str:
    """Handle city comparison."""
    if not city1.strip() or not city2.strip():
        return "❓ Please enter both city names to compare."
    
    try:
        return get_app().compare(city1, city2)
    except Exception as e:
        return f"❌ Error: {str(e)}"


def handle_health_advice(city: str) -> str:
    """Handle health advice request."""
    if not city.strip():
        return "❓ Please enter a city name."
    
    try:
        return get_app().get_health_advice(city)
    except Exception as e:
        return f"❌ Error: {str(e)}"


def handle_set_alert(location: str, threshold: float, alert_type: str) -> str:
    """Handle alert creation."""
    if not location.strip():
        return "❓ Please enter a location."
    
    try:
        # Map display name to internal type
        type_map = {
            "PM2.5": "pm25",
            "PM10": "pm10",
            "AQI": "aqi",
            "Ozone": "ozone",
        }
        internal_type = type_map.get(alert_type, "pm25")
        
        return get_app().set_alert(
            user_id="demo_user",
            location=location,
            threshold=threshold,
            alert_type=internal_type,
        )
    except Exception as e:
        return f"❌ Error: {str(e)}"


def handle_get_alerts() -> str:
    """Handle getting alerts list."""
    try:
        return get_app().get_alerts_formatted("demo_user")
    except Exception as e:
        return f"❌ Error: {str(e)}"


def handle_check_alerts(city: str) -> str:
    """Handle checking alerts for a city."""
    if not city.strip():
        return "❓ Please enter a city name."
    
    try:
        return get_app().check_alerts("demo_user", city)
    except Exception as e:
        return f"❌ Error: {str(e)}"


def handle_get_air_quality(city: str) -> str:
    """Handle getting air quality data."""
    if not city.strip():
        return "❓ Please enter a city name."
    
    try:
        return get_app().get_air_quality_formatted(city, detailed=True)
    except Exception as e:
        return f"❌ Error: {str(e)}"


# =========================================
# Gradio Interface
# =========================================

def create_app() -> gr.Blocks:
    """Create the Gradio interface."""
    
    # Custom CSS for styling
    custom_css = """
    .gradio-container {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }
    
    .main-header {
        text-align: center;
        padding: 20px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        margin-bottom: 20px;
    }
    
    .main-header h1 {
        color: white !important;
        margin: 0;
        font-size: 2.5em;
    }
    
    .main-header p {
        color: rgba(255,255,255,0.9) !important;
        margin: 10px 0 0 0;
    }
    
    .feature-card {
        background: linear-gradient(145deg, #f0f0f0 0%, #ffffff 100%);
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    footer {
        text-align: center;
        padding: 20px;
        color: #666;
    }
    """
    
    with gr.Blocks(
        title="AirSight - Real-Time Air Quality Intelligence",
        css=custom_css,
        theme=gr.themes.Soft(
            primary_hue="purple",
            secondary_hue="blue",
        )
    ) as demo:
        
        # Header
        gr.HTML("""
        <div class="main-header">
            <h1>🌍 AirSight</h1>
            <p>Real-Time Air Quality Intelligence • Powered by Cerebras</p>
        </div>
        """)
        
        # Main tabs
        with gr.Tabs():
            
            # =========================================
            # Tab 1: Ask Questions
            # =========================================
            with gr.Tab("💬 Ask", id="ask"):
                gr.Markdown("""
                ### Ask anything about air quality
                Get instant answers about air quality conditions anywhere in the world.
                """)
                
                with gr.Row():
                    with gr.Column(scale=3):
                        question_input = gr.Textbox(
                            label="Your Question",
                            placeholder="Is the air safe in Tokyo right now?",
                            lines=2,
                        )
                    with gr.Column(scale=1):
                        ask_btn = gr.Button("🔍 Ask", variant="primary", size="lg")
                
                answer_output = gr.Textbox(
                    label="Answer",
                    lines=10,
                    show_copy_button=True,
                )
                
                gr.Examples(
                    examples=[
                        "Is the air safe in Tokyo?",
                        "What's the PM2.5 level in Delhi?",
                        "Should I go jogging in Los Angeles today?",
                        "How's the air quality in Beijing?",
                        "Is it safe to exercise outside in Mumbai?",
                    ],
                    inputs=question_input,
                    label="Example Questions",
                )
                
                ask_btn.click(
                    fn=handle_ask,
                    inputs=question_input,
                    outputs=answer_output,
                )
                
                question_input.submit(
                    fn=handle_ask,
                    inputs=question_input,
                    outputs=answer_output,
                )
            
            # =========================================
            # Tab 2: Compare Cities
            # =========================================
            with gr.Tab("🔄 Compare", id="compare"):
                gr.Markdown("""
                ### Compare air quality between cities
                See which city has better air quality with instant comparisons.
                """)
                
                with gr.Row():
                    city1_input = gr.Textbox(
                        label="City 1",
                        placeholder="Tokyo",
                    )
                    city2_input = gr.Textbox(
                        label="City 2",
                        placeholder="Beijing",
                    )
                
                compare_btn = gr.Button("🔄 Compare", variant="primary")
                
                compare_output = gr.Textbox(
                    label="Comparison Result",
                    lines=12,
                    show_copy_button=True,
                )
                
                with gr.Row():
                    gr.Examples(
                        examples=[
                            ["Tokyo", "Beijing"],
                            ["London", "Paris"],
                            ["New York", "Los Angeles"],
                            ["Delhi", "Mumbai"],
                            ["Sydney", "Singapore"],
                        ],
                        inputs=[city1_input, city2_input],
                        label="Popular Comparisons",
                    )
                
                compare_btn.click(
                    fn=handle_compare,
                    inputs=[city1_input, city2_input],
                    outputs=compare_output,
                )
            
            # =========================================
            # Tab 3: Health Advice
            # =========================================
            with gr.Tab("💊 Health", id="health"):
                gr.Markdown("""
                ### Get health advice based on air quality
                Personalized recommendations for your outdoor activities.
                """)
                
                with gr.Row():
                    health_city_input = gr.Textbox(
                        label="City",
                        placeholder="Enter city name",
                        scale=3,
                    )
                    health_btn = gr.Button("💊 Get Advice", variant="primary", scale=1)
                
                health_output = gr.Textbox(
                    label="Health Advice",
                    lines=15,
                    show_copy_button=True,
                )
                
                health_btn.click(
                    fn=handle_health_advice,
                    inputs=health_city_input,
                    outputs=health_output,
                )
            
            # =========================================
            # Tab 4: Alerts
            # =========================================
            with gr.Tab("🔔 Alerts", id="alerts"):
                gr.Markdown("""
                ### Set up air quality alerts
                Get notified when air quality exceeds your thresholds.
                """)
                
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("#### Create New Alert")
                        alert_location = gr.Textbox(
                            label="Location",
                            placeholder="Delhi",
                        )
                        alert_type = gr.Dropdown(
                            label="Alert Type",
                            choices=["PM2.5", "PM10", "AQI", "Ozone"],
                            value="PM2.5",
                        )
                        alert_threshold = gr.Slider(
                            label="Threshold",
                            minimum=10,
                            maximum=500,
                            value=100,
                            step=5,
                        )
                        create_alert_btn = gr.Button("➕ Create Alert", variant="primary")
                        alert_status = gr.Textbox(label="Status", lines=2)
                    
                    with gr.Column():
                        gr.Markdown("#### Your Alerts")
                        refresh_alerts_btn = gr.Button("🔄 Refresh")
                        alerts_list = gr.Textbox(
                            label="Active Alerts",
                            lines=8,
                        )
                        
                        gr.Markdown("#### Check Alerts")
                        check_city = gr.Textbox(
                            label="City to Check",
                            placeholder="Delhi",
                        )
                        check_btn = gr.Button("✓ Check Now")
                        check_result = gr.Textbox(label="Result", lines=4)
                
                create_alert_btn.click(
                    fn=handle_set_alert,
                    inputs=[alert_location, alert_threshold, alert_type],
                    outputs=alert_status,
                )
                
                refresh_alerts_btn.click(
                    fn=handle_get_alerts,
                    outputs=alerts_list,
                )
                
                check_btn.click(
                    fn=handle_check_alerts,
                    inputs=check_city,
                    outputs=check_result,
                )
            
            # =========================================
            # Tab 5: Data
            # =========================================
            with gr.Tab("📊 Data", id="data"):
                gr.Markdown("""
                ### View raw air quality data
                See detailed measurements from monitoring stations.
                """)
                
                with gr.Row():
                    data_city_input = gr.Textbox(
                        label="City",
                        placeholder="Enter city name",
                        scale=3,
                    )
                    data_btn = gr.Button("📊 Get Data", variant="primary", scale=1)
                
                data_output = gr.Textbox(
                    label="Air Quality Data",
                    lines=20,
                    show_copy_button=True,
                )
                
                data_btn.click(
                    fn=handle_get_air_quality,
                    inputs=data_city_input,
                    outputs=data_output,
                )
        
        # Footer
        gr.HTML("""
        <footer>
            <p>
                <strong>AirSight</strong> • Built with 
                <a href="https://openaq.org" target="_blank">OpenAQ</a> data • 
                Powered by <a href="https://cerebras.ai" target="_blank">Cerebras</a> inference •
                Deployed on <a href="https://raindrop.dev" target="_blank">Raindrop</a>
            </p>
            <p style="font-size: 0.8em; color: #999;">
                Built for AI Championship Hackathon 2024
            </p>
        </footer>
        """)
    
    return demo


# =========================================
# Entry Point
# =========================================

if __name__ == "__main__":
    demo = create_app()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
    )


"""
Gradio UI for AirSight with debounced city autocomplete.
"""

import gradio as gr
import json
from pathlib import Path
from typing import List

from app import AirSightApp


# Load city index once at startup
def load_city_index() -> dict:
    try:
        index_path = Path(__file__).parent.parent / "data" / "city_index.json"
        with open(index_path, 'r') as f:
            return json.load(f)
    except:
        return {}

CITY_INDEX = load_city_index()
print(f"[UI] Loaded {len(CITY_INDEX)} cities for search")


def search_cities(query: str) -> List[str]:
    """Search cities - called on every keystroke (debounced by Gradio)."""
    if not query or len(query) < 2:
        return []
    
    query_lower = query.lower()
    matches = []
    
    for city, sensors in CITY_INDEX.items():
        if query_lower in city.lower():
            matches.append((city.title(), len(sensors)))
    
    matches.sort(key=lambda x: x[1], reverse=True)
    return [f"{m[0]} ({m[1]} sensors)" for m in matches[:8]]


def update_suggestions(query: str):
    """Update dropdown with matches."""
    matches = search_cities(query)
    if matches:
        return gr.update(choices=matches, visible=True, value=None)
    return gr.update(choices=[], visible=False)


def select_city(selection: str, current: str) -> str:
    """Extract city name from selection."""
    if selection:
        return selection.split(" (")[0]
    return current


# Global app
app = None

def get_app():
    global app
    if app is None:
        app = AirSightApp()
        app.initialize()
    return app


def handle_ask(q):
    if not q.strip(): return "❓ Please enter a question."
    try: return get_app().ask(q)
    except Exception as e: return f"❌ {e}"

def handle_compare(c1, c2):
    if not c1.strip() or not c2.strip(): return "❓ Enter both cities."
    try: return get_app().compare(c1, c2)
    except Exception as e: return f"❌ {e}"

def handle_health(c):
    if not c.strip(): return "❓ Enter a city."
    try: return get_app().get_health_advice(c)
    except Exception as e: return f"❌ {e}"

def handle_data(c):
    if not c.strip(): return "❓ Enter a city."
    try: return get_app().get_air_quality_formatted(c, detailed=True)
    except Exception as e: return f"❌ {e}"


def create_app():
    with gr.Blocks(title="AirSight") as demo:
        
        gr.HTML("""
        <div style="text-align:center;padding:20px;background:linear-gradient(135deg,#667eea,#764ba2);border-radius:10px;margin-bottom:20px;">
            <h1 style="color:white;margin:0;font-size:2.5em;">🌍 AirSight</h1>
            <p style="color:rgba(255,255,255,0.9);margin:10px 0 0 0;">Real-Time Air Quality Intelligence • Powered by Cerebras</p>
        </div>
        """)
        
        with gr.Tabs():
            
            # Ask Tab
            with gr.Tab("💬 Ask"):
                gr.Markdown("### Ask anything about air quality")
                question = gr.Textbox(label="Question", placeholder="Is the air safe in Delhi?", lines=2)
                ask_btn = gr.Button("🔍 Ask", variant="primary")
                answer = gr.Textbox(label="Answer", lines=10)
                
                gr.Examples(
                    ["What is the air quality in Delhi?", 
                     "Should I go jogging in Beijing?",
                     "Is it safe outside in London?"],
                    inputs=question
                )
                
                ask_btn.click(handle_ask, question, answer)
                question.submit(handle_ask, question, answer)
            
            # Compare Tab
            with gr.Tab("🔄 Compare"):
                gr.Markdown("### Compare cities (type 2+ chars for suggestions)")
                
                with gr.Row():
                    with gr.Column():
                        c1_input = gr.Textbox(label="City 1", placeholder="Type city...")
                        c1_dropdown = gr.Dropdown(choices=[], visible=False, interactive=True)
                    with gr.Column():
                        c2_input = gr.Textbox(label="City 2", placeholder="Type city...")
                        c2_dropdown = gr.Dropdown(choices=[], visible=False, interactive=True)
                
                cmp_btn = gr.Button("🔄 Compare", variant="primary")
                cmp_result = gr.Textbox(label="Result", lines=12)
                
                # Debounced autocomplete
                c1_input.change(update_suggestions, c1_input, c1_dropdown)
                c1_dropdown.change(select_city, [c1_dropdown, c1_input], c1_input)
                c2_input.change(update_suggestions, c2_input, c2_dropdown)
                c2_dropdown.change(select_city, [c2_dropdown, c2_input], c2_input)
                
                gr.Examples([["Delhi", "London"], ["Beijing", "New York"]], inputs=[c1_input, c2_input])
                cmp_btn.click(handle_compare, [c1_input, c2_input], cmp_result)
            
            # Health Tab
            with gr.Tab("💊 Health"):
                gr.Markdown("### Get health advice")
                
                h_input = gr.Textbox(label="City", placeholder="Type city...")
                h_dropdown = gr.Dropdown(choices=[], visible=False, interactive=True)
                h_btn = gr.Button("💊 Get Advice", variant="primary")
                h_result = gr.Textbox(label="Health Advice", lines=15)
                
                h_input.change(update_suggestions, h_input, h_dropdown)
                h_dropdown.change(select_city, [h_dropdown, h_input], h_input)
                
                gr.Examples(["Delhi", "Beijing", "London"], inputs=h_input)
                h_btn.click(handle_health, h_input, h_result)
            
            # Data Tab
            with gr.Tab("📊 Data"):
                gr.Markdown("### View raw air quality data")
                
                d_input = gr.Textbox(label="City", placeholder="Type city...")
                d_dropdown = gr.Dropdown(choices=[], visible=False, interactive=True)
                d_btn = gr.Button("📊 Get Data", variant="primary")
                d_result = gr.Textbox(label="Data", lines=20)
                
                d_input.change(update_suggestions, d_input, d_dropdown)
                d_dropdown.change(select_city, [d_dropdown, d_input], d_input)
                
                gr.Examples(["Delhi", "London", "India"], inputs=d_input)
                d_btn.click(handle_data, d_input, d_result)
        
        gr.HTML(f"""
        <footer style="text-align:center;padding:20px;color:#666;">
            <strong>AirSight</strong> • OpenAQ + Cerebras • {len(CITY_INDEX)} cities searchable
        </footer>
        """)
    
    return demo


if __name__ == "__main__":
    demo = create_app()
    demo.launch(server_name="0.0.0.0", server_port=7860)

#!/usr/bin/env python3
"""
AirSight - Run Script
Quick way to launch the application.
"""

import sys
import os

# Add the current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="AirSight - Real-Time Air Quality Intelligence"
    )
    parser.add_argument(
        "--mode",
        choices=["ui", "cli", "test"],
        default="ui",
        help="Run mode: ui (Gradio), cli (command line), test (run tests)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=7860,
        help="Port for the web UI (default: 7860)",
    )
    parser.add_argument(
        "--share",
        action="store_true",
        help="Create a public share link (Gradio)",
    )
    parser.add_argument(
        "--question",
        type=str,
        help="Question to ask (cli mode)",
    )
    
    args = parser.parse_args()
    
    if args.mode == "ui":
        run_ui(args.port, args.share)
    elif args.mode == "cli":
        run_cli(args.question)
    elif args.mode == "test":
        run_tests()


def run_ui(port: int, share: bool):
    """Run the Gradio web interface."""
    print("=" * 50)
    print("🌍 AirSight - Starting Web Interface")
    print("=" * 50)
    
    try:
        from ui.gradio_app import create_app
        
        demo = create_app()
        demo.launch(
            server_name="0.0.0.0",
            server_port=port,
            share=share,
            show_error=True,
        )
    except ImportError as e:
        print(f"❌ Error: {e}")
        print("\nMake sure you have installed the requirements:")
        print("  pip install -r requirements.txt")
        sys.exit(1)


def run_cli(question: str = None):
    """Run in CLI mode."""
    from app import AirSightApp
    
    print("=" * 50)
    print("🌍 AirSight - Command Line Interface")
    print("=" * 50)
    print()
    
    app = AirSightApp()
    app.initialize()
    
    if question:
        # Single question mode
        print(f"Q: {question}")
        print("-" * 50)
        result = app.ask(question)
        print(result)
    else:
        # Interactive mode
        print("Type your questions about air quality.")
        print("Commands: 'compare <city1> <city2>', 'health <city>', 'quit'")
        print("-" * 50)
        
        while True:
            try:
                user_input = input("\n🌍 You: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ["quit", "exit", "q"]:
                    print("Goodbye! 👋")
                    break
                
                if user_input.lower().startswith("compare "):
                    parts = user_input[8:].split()
                    if len(parts) >= 2:
                        result = app.compare(parts[0], parts[1])
                    else:
                        result = "Usage: compare <city1> <city2>"
                elif user_input.lower().startswith("health "):
                    city = user_input[7:].strip()
                    result = app.get_health_advice(city)
                else:
                    result = app.ask(user_input)
                
                print()
                print(result)
                
            except KeyboardInterrupt:
                print("\nGoodbye! 👋")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
    
    app.close()


def run_tests():
    """Run tests."""
    print("=" * 50)
    print("🧪 AirSight - Running Tests")
    print("=" * 50)
    print()
    
    from app import AirSightApp
    from models.air_reading import AirReading
    from models.alert import Alert, AlertType
    
    # Test 1: Models
    print("Test 1: Models")
    reading = AirReading(
        location_id=1,
        location_name="Test",
        city="Tokyo",
        country="Japan",
        latitude=35.6895,
        longitude=139.6917,
        pm25=45.5
    )
    assert reading.aqi is not None
    assert reading.get_health_category() != "Unknown"
    print("  ✅ AirReading model working")
    
    alert = Alert(
        id="test",
        user_id="test",
        location_name="Tokyo",
        alert_type=AlertType.PM25_THRESHOLD,
        threshold=100
    )
    assert alert.should_trigger(reading) == False  # 45.5 < 100
    reading.pm25 = 150
    assert alert.should_trigger(reading) == True  # 150 > 100
    print("  ✅ Alert model working")
    
    # Test 2: App initialization
    print("\nTest 2: App initialization")
    app = AirSightApp()
    assert app.initialize() == True
    print("  ✅ App initializes correctly")
    
    # Test 3: Query
    print("\nTest 3: Query (mock mode)")
    result = app.ask("Test question")
    assert "Error" not in result or "Mock" in result
    print("  ✅ Query returns response")
    
    # Test 4: Alerts
    print("\nTest 4: Alerts")
    app.set_alert("test_user", "Tokyo", 50)
    alerts = app.get_alerts("test_user")
    assert len(alerts) > 0
    print("  ✅ Alert creation working")
    
    app.close()
    
    print()
    print("=" * 50)
    print("✅ All tests passed!")
    print("=" * 50)


if __name__ == "__main__":
    main()


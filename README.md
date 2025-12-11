# 🌍 AirSight - Real-Time Air Quality Intelligence

**Ask anything about air quality worldwide — get instant answers powered by Cerebras.**

Built for the [AI Championship Hackathon](https://devpost.com) by LiquidMetal AI.

![AirSight Demo](https://img.shields.io/badge/Status-In%20Development-yellow)
![Python](https://img.shields.io/badge/Python-3.9+-blue)
![License](https://img.shields.io/badge/License-MIT-green)

## 🎯 What is AirSight?

AirSight is an AI-powered air quality intelligence platform that provides:

- **Instant Q&A**: Ask natural language questions about air quality
- **City Comparisons**: Compare air quality between any two cities
- **Health Advice**: Get personalized health recommendations
- **Smart Alerts**: Set thresholds and get notified

All powered by **Cerebras inference** for ultra-low latency responses (<500ms).

## 🚀 Quick Start

### 1. Clone and Setup

```bash
cd airsight
pip install -r requirements.txt
```

### 2. Configure API Keys

Copy the environment template and add your keys:

```bash
cp env.example .env
```

Edit `.env` with your API keys:
```
OPENAQ_API_KEY=your_openaq_key_here
CEREBRAS_API_KEY=your_cerebras_key_here
RAINDROP_API_KEY=your_raindrop_key_here
```

### 3. Run the Application

**Web Interface (Gradio):**
```bash
python run.py --mode ui
```

**Command Line:**
```bash
python run.py --mode cli
```

**Run Tests:**
```bash
python run.py --mode test
```

## 📖 Usage Examples

### Ask Questions
```python
from app import AirSightApp

app = AirSightApp()
app.initialize()

# Ask about air quality
print(app.ask("Is the air safe in Tokyo?"))

# Get health advice
print(app.get_health_advice("Delhi"))

# Compare cities
print(app.compare("London", "Paris"))

app.close()
```

### Set Alerts
```python
# Create an alert
app.set_alert("user1", "Delhi", threshold=100, alert_type="pm25")

# Check alerts
print(app.check_alerts("user1", "Delhi"))
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       AirSight                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [Gradio UI] ─────────────────────────────────────────────┐│
│        │                                                   ││
│        ▼                                                   ││
│  [AirSightApp] ← Main Orchestrator                        ││
│        │                                                   ││
│  ┌─────┴─────────────────────────────────────────────┐    ││
│  │               SERVICES                             │    ││
│  │  DataService │ QueryService │ AlertService        │    ││
│  └───────────────────────────────────────────────────┘    ││
│        │                                                   ││
│  ┌─────┴─────────────────────────────────────────────┐    ││
│  │               CLIENTS                              │    ││
│  │  OpenAQClient │ RaindropClient                    │    ││
│  │               │  ├─ SmartBuckets                  │    ││
│  │               │  ├─ SmartSQL                      │    ││
│  │               │  ├─ SmartMemory                   │    ││
│  │               │  └─ SmartInference (Cerebras)     │    ││
│  └───────────────────────────────────────────────────┘    ││
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 📁 Project Structure

```
airsight/
├── config/
│   └── settings.py          # Configuration management
├── clients/
│   ├── openaq_client.py     # OpenAQ API wrapper
│   └── raindrop_client.py   # Raindrop Smart Components
├── services/
│   ├── data_service.py      # Data fetching & storage
│   ├── query_service.py     # Natural language queries
│   └── alert_service.py     # Alert management
├── models/
│   ├── air_reading.py       # Air quality data model
│   ├── location.py          # Location model
│   ├── alert.py             # Alert model
│   └── query_result.py      # Query result model
├── ui/
│   └── gradio_app.py        # Gradio web interface
├── utils/
│   ├── formatters.py        # Display formatting
│   └── validators.py        # Input validation
├── app.py                   # Main application
├── run.py                   # Run script
└── requirements.txt         # Dependencies
```

## 🔧 Technologies Used

| Technology | Purpose |
|------------|---------|
| **OpenAQ** | Real-time air quality data from 100+ countries |
| **Cerebras** | Ultra-low latency AI inference |
| **Raindrop** | Smart Components (Buckets, SQL, Memory, Inference) |
| **Gradio** | Web interface |
| **Python** | Backend |

## 📊 Features

### ✅ Implemented
- [x] Natural language Q&A about air quality
- [x] City comparisons
- [x] Health advice generation
- [x] Alert management
- [x] Data caching
- [x] Gradio web interface

### 🚧 Coming Soon
- [ ] Real-time data streaming
- [ ] Historical trend charts
- [ ] Push notifications
- [ ] Multi-language support
- [ ] Mobile app

## 🌟 Key Differentiators

1. **Ultra-Low Latency**: Powered by Cerebras for <500ms responses
2. **Natural Language**: Ask questions in plain English
3. **Real Data**: Live data from OpenAQ's global sensor network
4. **Smart Memory**: Remembers your preferences and context
5. **Modular Design**: Easy to extend with new features

## 📝 API Keys

| Service | Where to Get |
|---------|--------------|
| OpenAQ | [openaq.org](https://openaq.org) |
| Cerebras | [cerebras.ai](https://cerebras.ai) |
| Raindrop | [raindrop.dev](https://raindrop.dev) |

## 🤝 Contributing

This project was built for the AI Championship Hackathon. Feel free to fork and extend!

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

**Built with ❤️ for the AI Championship Hackathon 2024**

*Powered by Cerebras • Data from OpenAQ • Deployed on Raindrop*


<p align="center">
  <h1 align="center">🔧 FixIt AI</h1>
  <p align="center">
    <strong>AI-powered visual troubleshooting — snap a photo, get a fix.</strong>
  </p>
  <p align="center">
    <a href="#-features">Features</a> •
    <a href="#%EF%B8%8F-architecture">Architecture</a> •
    <a href="#-getting-started">Getting Started</a> •
    <a href="#-deployment">Deployment</a> •
    <a href="#-api-reference">API</a> •
    <a href="#-tech-stack">Tech Stack</a>
  </p>
  <p align="center">
    <img src="https://img.shields.io/badge/Next.js-16-black?logo=next.js" alt="Next.js" />
    <img src="https://img.shields.io/badge/FastAPI-0.3-009688?logo=fastapi" alt="FastAPI" />
    <img src="https://img.shields.io/badge/Gemini-3-4285F4?logo=google&logoColor=white" alt="Gemini" />
    <img src="https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript&logoColor=white" alt="TypeScript" />
    <img src="https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white" alt="Python" />
    <img src="https://img.shields.io/badge/Status-Beta-orange" alt="Status" />
  </p>
</p>

---

## 📖 Overview

**FixIt AI** is a full-stack application that uses computer vision and large language models to diagnose and troubleshoot hardware issues from photos. Upload an image of a broken device, describe your problem, and receive step-by-step repair guidance enriched with AR component overlays, safety assessments, and verified web sources — all in under 2 minutes.

> _"See the Problem. Fix it Fast."_

---

## ✨ Features

### 🎯 Core Capabilities

| Feature | Description |
|---|---|
| **Instant Device Detection** | AI identifies your device type, brand, model, and visible components with 95% accuracy |
| **AR Component Mapping** | Interactive overlays with bounding boxes pinpoint exact component locations on your image |
| **Smart Safety Checks** | Detects electrical hazards, overheating, exposed wiring — critical scenarios block DIY and recommend professionals |
| **Interactive Repair Workflows** | Step-by-step instructions with time estimates, difficulty levels, cause-effect analysis, and progress tracking |
| **Voice Input & Audio Playback** | Speak your question hands-free; listen to instructions while working on your device |
| **Web Grounding** | Gemini's native Google Search retrieves official docs, community solutions, and model-specific guidance in real-time |
| **Follow-Up Conversations** | Ask clarifying questions mid-repair — the AI retains context about your device and progress |
| **Multi-Device Support** | Routers, printers, laptops, circuit boards, microwaves, and more |

### 🛡️ Intelligent Decision Gates

FixIt doesn't blindly generate answers. A **gate-based routing pipeline** evaluates every request through multiple decision layers:

- **Image Validation** — Rejects screenshots, documents, people, non-device images
- **Device Confidence** — Routes low-confidence detections to clarification flows
- **Safety Override** — Critical hazards (fire, smoke, electrical shock) bypass all gates
- **Query Parsing** — Classifies intent as troubleshoot, explain, diagnose, locate, or identify
- **Device-Query Mismatch** — Catches incompatible queries (e.g., "replace GPU" for a printer)

---

## 🏗️ Architecture

```
fixit/
├── backend/                    # Python FastAPI server
│   ├── main.py                 # API endpoints & gate-based routing pipeline
│   ├── agents/                 # Specialized AI agents
│   │   ├── image_validator.py  # Gate 1: Image pre-validation
│   │   ├── device_detector.py  # Gate 2: Device identification
│   │   ├── spatial_mapper.py   # Gate 4: Component localization & AR coordinates
│   │   ├── query_parser.py     # Intent classification & query analysis
│   │   └── step_generator.py   # Gate 6: Answer-type-aware content generation
│   └── utils/
│       ├── gemini_client.py    # Gemini API wrapper with caching, rate limiting, circuit breaker
│       ├── image_processor.py  # Image preprocessing for Gemini
│       ├── response_builder.py # Structured response assembly
│       ├── schema_validator.py # Response schema validation
│       └── audio_generator.py  # TTS-ready audio script generation
│
├── frontend/                   # Next.js 16 + React 19 application
│   └── src/
│       ├── app/
│       │   ├── page.tsx        # Landing page
│       │   └── dashboard/      # Main application
│       │       ├── page.tsx    # Input hub (upload, camera, voice)
│       │       └── results/    # Results page
│       ├── components/
│       │   ├── landing/        # Hero, Features, HowItWorks, CTA sections
│       │   ├── input-hub/      # FileUpload, CameraCapture, VoiceInput
│       │   ├── results/        # AR canvas, repair steps, diagnosis, sources
│       │   ├── layout/         # Navbar, responsive sidebar
│       │   └── ui/             # Shared UI primitives (Button, etc.)
│       ├── lib/                # Utilities
│       └── types/              # TypeScript type definitions
│
├── requirements.txt            # Python dependencies
└── .env.example                # Environment variable template
```

### 🔄 Request Pipeline

Every troubleshooting request flows through an **8-gate pipeline**:

```
📸 Image Upload
     │
     ▼
┌─ GATE 0 ─┐  Image Processing
│  Resize   │  (max 1024px, format conversion)
└─────┬─────┘
      ▼
┌ GATES 1-3 ┐  Combined Analysis (single Gemini call)
│ Validate   │  → Image validity, device detection,
│ Detect     │    query parsing, safety assessment,
│ Parse      │    intent classification
└─────┬──────┘
      ▼
┌─ GATE 4 ──┐  Component Localization (conditional)
│ Spatial    │  → Multi-target bounding boxes,
│ Mapper     │    auto-discovery mode
└─────┬──────┘
      ▼
┌─ GATE 5 ──┐  Web Grounding (conditional)
│ Google     │  → Native Gemini Search for
│ Search     │    model-specific guidance
└─────┬──────┘
      ▼
┌─ GATE 6 ──┐  Response Generation
│ Step Gen   │  → Answer-type-aware content
│            │    (troubleshoot/explain/diagnose/mixed)
└─────┬──────┘
      ▼
┌─ GATE 7 ──┐  Response Assembly
│ Build +    │  → Schema validation, audio script,
│ Validate   │    visualization data
└────────────┘
```

---

## 🚀 Getting Started

### Prerequisites

- **Python** 3.10+
- **Node.js** 18+
- **Gemini API Key** — [Get one from Google AI Studio](https://aistudio.google.com/apikey)

### 1. Clone the repository

```bash
git clone https://github.com/SumitPatel-HQ/Fixit.git
cd fixit
```

### 2. Set up environment variables

```bash
# Root-level .env (for the backend)
cp .env.example .env
```

Edit `.env` and add your credentials:

```env
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL_NAME=gemini-2.0-flash-exp
```

```bash
# Frontend environment
cp frontend/.env.example frontend/.env.local
```

The default `frontend/.env.local` points to `http://localhost:8000` — no changes needed for local dev.

### 3. Start the Backend (FastAPI)

```bash
# Create and activate a virtual environment
python -m venv .venv

# Windows
.\.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn backend.main:app --reload --port 8000
```

The API will be live at **http://localhost:8000** — verify with `GET /health`.

### 4. Start the Frontend (Next.js)

```bash
cd frontend
npm install
npm run dev
```

The app will be available at **http://localhost:3000**.

---

## 📡 API Reference

### `POST /api/troubleshoot`

The main endpoint. Accepts an image + query and returns a full diagnostic response.

**Request** (`multipart/form-data`):

| Field | Type | Required | Description |
|---|---|---|---|
| `image_base64` | `string` | ✅ | Base64-encoded image |
| `query` | `string` | ✅ | User's question (e.g., "My printer is jamming") |
| `device_hint` | `string` | ❌ | Optional device type hint |
| `image_width` | `int` | ❌ | Original image width (for AR mapping) |
| `image_height` | `int` | ❌ | Original image height (for AR mapping) |

**Response** (JSON):

```json
{
  "answer_type": "troubleshoot_steps",
  "status": "success",
  "device_info": {
    "device_type": "HP LaserJet Pro M404",
    "brand": "HP",
    "confidence": 0.92,
    "components": ["paper tray", "toner cartridge", "fuser"]
  },
  "troubleshooting_steps": [...],
  "visualizations": [
    {
      "target": "paper tray",
      "status": "found",
      "bounding_box": { "x_min": 120, "y_min": 340, "x_max": 450, "y_max": 520 }
    }
  ],
  "diagnosis": {
    "issue": "Paper jam in rear access panel",
    "severity": "moderate",
    "possible_causes": [...]
  },
  "audio_instructions": "Step one: Turn off the printer and unplug it..."
}
```

### Other Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/health` | `GET` | Health check & version info |
| `/api/validate-image` | `POST` | Standalone image validation |
| `/api/identify-device` | `POST` | Standalone device identification |
| `/api/quota-status` | `GET` | Check Gemini API quota status |

---

## 🤖 AI Agent System

FixIt uses a **multi-agent architecture** where each agent is a specialized module:

| Agent | Responsibility |
|---|---|
| **Image Validator** | Pre-filters non-device images (screenshots, documents, people) |
| **Device Detector** | Identifies device type, brand, model with honest uncertainty reporting |
| **Query Parser** | Classifies user intent and extracts target components |
| **Spatial Mapper** | Locates components with pixel-accurate bounding boxes for AR overlays |
| **Step Generator** | Produces answer-type-aware content (troubleshoot / explain / diagnose / mixed) |

### Answer Types

The system classifies every request into an `answer_type` that shapes the response:

| Type | When | Output |
|---|---|---|
| `troubleshoot_steps` | "How do I fix..." | Step-by-step repair instructions |
| `explain_only` | "How does this work?" | Educational explanation with component breakdown |
| `diagnose_only` | "What's wrong with..." | Diagnosis without repair steps |
| `locate_only` | "Where is the..." | AR bounding box localization |
| `identify_only` | "What is this?" | Device identification |
| `mixed` | Complex multi-intent queries | Combined response |
| `safety_warning_only` | Hazardous situations | Professional help recommendation |
| `ask_clarifying_questions` | Ambiguous queries | Follow-up questions |
| `ask_for_better_input` | Poor image quality | Retry guidance |

---

## 🛠️ Tech Stack

### Backend

| Technology | Purpose |
|---|---|
| [FastAPI](https://fastapi.tiangolo.com/) | Async Python API framework |
| [Google Gemini](https://ai.google.dev/) | Vision + Language model (Gemini 2.0 Flash) |
| [Pillow](https://pillow.readthedocs.io/) | Image processing & resizing |
| [NumPy](https://numpy.org/) | Numerical computations |
| [httpx](https://www.python-httpx.org/) | Async HTTP client for web grounding |

### Frontend

| Technology | Purpose |
|---|---|
| [Next.js 16](https://nextjs.org/) | React framework with App Router |
| [React 19](https://react.dev/) | UI library |
| [TypeScript 5](https://www.typescriptlang.org/) | Type safety |
| [Tailwind CSS 4](https://tailwindcss.com/) | Utility-first styling |
| [Framer Motion](https://www.framer.com/motion/) | Animations & micro-interactions |
| [Lucide React](https://lucide.dev/) | Icon library |
| [Radix UI](https://www.radix-ui.com/) | Accessible UI primitives |

---

## 🧪 Testing the Pipeline

FixIt's gate-based routing responds differently based on inputs:

| Input | Expected Behavior |
|---|---|
| ✅ Clear device photo + repair query | Full troubleshoot flow with AR overlays |
| 🖼️ Game screenshot / meme | Rejected at Gate 1 (invalid image) |
| 📸 Blurry device photo | Asks for better input (Gate 1b) |
| ⚡ Query mentions "smoke" or "fire" | Safety override — recommends professional help |
| ❓ Gibberish query ("ddddd") | Invalid query modal |
| 🔀 Mismatched query ("replace GPU" for a printer) | Device-query mismatch detection |
| 🤔 Multiple devices in frame | Asks which device to focus on |

---

## 🔒 Quota Protection

FixIt includes built-in Gemini API quota management:

- **Rate Limiting** — Respects per-minute request caps
- **Response Caching** — Deduplicates identical prompts with TTL-based cache
- **Circuit Breaker** — Automatically pauses API calls after repeated quota errors
- **RPD Tracking** — Monitors requests-per-day against model limits
- **Graceful Degradation** — Returns structured error responses instead of crashing

---

## 📁 Environment Variables

### Backend (`.env`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `GEMINI_API_KEY` | ✅ | — | Your Gemini API key |
| `GEMINI_MODEL_NAME` | ✅ | — | Gemini model to use (e.g., `gemini-2.0-flash-exp`) |
| `ENABLE_WEB_GROUNDING` | ❌ | `true` | Toggle web grounding with Google Search |

### Frontend (`frontend/.env.local`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `NEXT_PUBLIC_API_URL` | ✅ | `http://localhost:8000` | Backend API URL |
| `NEXT_PUBLIC_ENV` | ❌ | `development` | Environment mode |

---

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

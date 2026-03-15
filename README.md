# AI Meeting Intelligence Agent

> Capture → Transcribe → Analyze → PDF Report  
> Powered by NVIDIA NIM APIs (free tier available at build.nvidia.com)

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Streamlit UI (app.py)                  │
│   Live recording tab │ Upload tab │ Report/download tab  │
└──────────────────────────┬──────────────────────────────┘
                           │ HTTP / WebSocket
┌──────────────────────────▼──────────────────────────────┐
│                  FastAPI Backend (main.py)                │
│  POST /sessions/*  │  POST /transcribe/*  │  GET /report │
└──────┬──────────────────────┬────────────────────────────┘
       │                      │
┌──────▼──────┐    ┌──────────▼──────────┐
│AudioCapture │    │   NVIDIA NIM APIs    │
│sounddevice  │    │  Parakeet ASR (STT)  │
│VB-Cable/BH  │    │  Llama 3.1 70B (LLM)│
└─────────────┘    │  NV-EmbedQA (embed) │
                   └──────────┬──────────┘
                              │
                   ┌──────────▼──────────┐
                   │  MeetingAnalyzer    │
                   │  4 parallel prompts │
                   │  summary/speakers/  │
                   │  timeline/insights  │
                   └──────────┬──────────┘
                              │
                   ┌──────────▼──────────┐
                   │  ReportGenerator    │
                   │  ReportLab PDF      │
                   │  Professional layout│
                   └─────────────────────┘
```

---

## Quick start (5 minutes)

### 1. Get NVIDIA API key (free)
1. Go to https://build.nvidia.com
2. Sign in with your NVIDIA account (free)
3. Click any model → "Get API Key"
4. Copy the key starting with `nvapi-`

### 2. Clone and install
```bash
git clone <your-repo>
cd meeting_agent

python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Configure environment
```bash
cp .env.example .env
# Edit .env and paste your NVIDIA_API_KEY
```

### 4. Run the backend
```bash
cd backend
uvicorn main:app --reload --port 8000
```

### 5. Run the frontend (new terminal)
```bash
cd frontend
streamlit run app.py
```

Open http://localhost:8501

---

## Audio capture setup (per platform)

### Windows
1. Download VB-Cable from https://vb-audio.com/Cable/ (free)
2. Install it (requires restart)
3. In Sound Settings → Playback: set "CABLE Input" as default device
4. Your meeting audio will now be capturable
5. In the app sidebar, set Device Index to the CABLE Output index

### macOS
1. Install BlackHole 2ch: https://existential.audio/blackhole/
2. Open Audio MIDI Setup (cmd+space → Audio MIDI Setup)
3. Click + → Create Multi-Output Device
4. Check both BlackHole 2ch and your speakers/headphones
5. Set this Multi-Output Device as your system output
6. Set device_index in the app to the BlackHole input

### Linux (PulseAudio)
```bash
# Create a virtual sink
pactl load-module module-null-sink sink_name=meeting_capture sink_properties=device.description=MeetingCapture

# Create loopback from your speakers to the virtual sink
pactl load-module module-loopback source=<your_speaker_monitor> sink=meeting_capture

# List sources to find the meeting_capture.monitor source index
pactl list sources short
```

---

## Usage guide

### Mode 1: Live recording (Google Meet / Zoom / Teams)
1. Set up audio loopback (see above)
2. Open the Streamlit app → **Live Recording** tab
3. Enter meeting title and participants
4. Click **▶ Start Recording** before your meeting begins
5. Join your Google Meet / Zoom call normally
6. Click **⏹ Stop & Analyze** when done
7. Wait ~30–60 seconds for NVIDIA AI analysis
8. Go to **Report** tab → Download PDF

### Mode 2: Upload recording
1. Open **Upload Audio** tab
2. Upload your WAV/MP3/M4A recording
3. Enter title and participants
4. Click **🚀 Transcribe & Analyze**
5. Download from **Report** tab

### Mode 3: API-only (no UI)
```bash
# 1. Create session
curl -X POST http://localhost:8000/sessions/create \
  -H "Content-Type: application/json" \
  -d '{"meeting_title": "Sprint Planning", "participants": ["Alice", "Bob"]}'

# 2. Upload audio file
curl -X POST "http://localhost:8000/transcribe/chunk?session_id=<ID>" \
  -F "audio_file=@meeting.wav"

# 3. Stop and trigger analysis
curl -X POST http://localhost:8000/sessions/<ID>/stop

# 4. Poll until completed
curl http://localhost:8000/sessions/<ID>/status

# 5. Download PDF
curl http://localhost:8000/report/<ID> -o report.pdf
```

---

## PDF Report contents

Each report contains:

| Section | Content |
|---|---|
| Header | Meeting title, date, duration, type |
| Executive Summary | AI-generated 2–3 sentence overview |
| Overview | Duration, participants, sentiment, effectiveness |
| Key Discussion Points | All major points discussed |
| Decisions Made | What was decided + rationale |
| Action Items | Task, owner, deadline, priority (color coded) |
| Speaker Analysis | Talk time %, role, contributions per person |
| Insights | Strategic recommendations, blockers |
| Open Questions | Unresolved items |
| Timeline | Chronological meeting flow |
| Full Transcript | Complete text with speaker labels |

---

## NVIDIA NIM models used

| Purpose | Model | Free tier |
|---|---|---|
| Speech-to-text | nvidia/parakeet-ctc-1.1b | ✅ |
| Meeting analysis | meta/llama-3.1-70b-instruct | ✅ (limited) |
| Fast analysis | meta/llama-3.1-8b-instruct | ✅ |
| Embeddings / RAG | nvidia/nv-embedqa-e5-v5 | ✅ |

All models accessible at: https://build.nvidia.com/models

---

## Deployment (production)

### Option A: Railway (easiest, free tier)
```bash
npm install -g @railway/cli
railway login
railway init
railway up
```
Set `NVIDIA_API_KEY` in Railway's environment variables.

### Option B: Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY backend/ .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```
```bash
docker build -t meeting-agent .
docker run -p 8000:8000 -e NVIDIA_API_KEY=nvapi-xxx meeting-agent
```

### Option C: Google Cloud Run
```bash
gcloud run deploy meeting-agent \
  --source . \
  --region us-central1 \
  --set-env-vars NVIDIA_API_KEY=nvapi-xxx \
  --allow-unauthenticated
```

---

## Project structure

```
meeting_agent/
├── backend/
│   ├── main.py              # FastAPI app, all endpoints
│   ├── nvidia_client.py     # NVIDIA NIM API wrapper (ASR + LLM)
│   ├── meeting_analyzer.py  # 4-pass LLM analysis + prompts
│   ├── report_generator.py  # ReportLab PDF builder
│   ├── audio_capture.py     # Cross-platform audio recording
│   └── session_manager.py   # Session persistence
├── frontend/
│   └── app.py              # Streamlit dashboard
├── reports/                 # Generated PDFs (auto-created)
├── sessions/                # Session JSON files (auto-created)
├── requirements.txt
├── .env.example
└── README.md
```

---

## Troubleshooting

**"NVIDIA API key invalid"**
→ Get a fresh key from build.nvidia.com → your model → "Get API Key"

**"No audio captured"**  
→ Check your loopback device setup. Run `python audio_capture.py` to list devices.

**"Transcription returns empty"**  
→ Ensure audio is 16kHz mono WAV. The capture module handles conversion automatically.

**"Analysis failed"**  
→ Check NVIDIA API rate limits. Switch to `meta/llama-3.1-8b-instruct` (faster, less quota).

**PDF report is empty**  
→ The transcript may be too short. Make sure recording ran for at least 30 seconds.

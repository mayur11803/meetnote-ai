"""
MeetNote AI — Fixed Backend
Fast flow: transcribe → check if empty → analyze → PDF
"""

import os
import uuid
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from nvidia_client import NVIDIAClient
from meeting_analyzer import MeetingAnalyzer
from report_generator import ReportGenerator
from session_manager import SessionManager

try:
    from deepgram_client import DeepgramClient
    DEEPGRAM_AVAILABLE = True
except ImportError:
    DEEPGRAM_AVAILABLE = False

app = FastAPI(title="MeetNote AI", version="3.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(exist_ok=True)

sessions: dict[str, dict] = {}
active_deepgram: dict = {}
nvidia_client = NVIDIAClient()
session_manager = SessionManager()

class SessionCreate(BaseModel):
    meeting_title: str
    participants: list[str] = []
    language: str = "en"
    mode: str = "professional"

class StartRecording(BaseModel):
    session_id: str
    device_index: Optional[int] = None
    language: str = "en"

class StopRecording(BaseModel):
    session_id: str

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "deepgram": bool(os.getenv("DEEPGRAM_API_KEY")),
        "nvidia": bool(os.getenv("NVIDIA_API_KEY")),
    }

@app.get("/devices")
async def list_devices():
    if DEEPGRAM_AVAILABLE:
        devices = DeepgramClient.list_audio_devices()
        vbcable = DeepgramClient.find_vbcable_device()
    else:
        devices = []
        vbcable = None
    return {"devices": devices, "vbcable_index": vbcable, "vbcable_detected": vbcable is not None}

@app.post("/sessions/create")
async def create_session(body: SessionCreate):
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "id": session_id, "title": body.meeting_title,
        "participants": body.participants, "language": body.language,
        "mode": body.mode, "status": "created",
        "transcript_chunks": [], "full_transcript": "",
        "live_transcript": "", "analysis": None,
        "started_at": datetime.utcnow().isoformat(),
        "ended_at": None, "duration_seconds": 0,
    }
    return {"session_id": session_id, "status": "created"}

@app.post("/sessions/{session_id}/start")
async def start_session(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    sessions[session_id]["status"] = "recording"
    sessions[session_id]["started_at"] = datetime.utcnow().isoformat()
    return {"status": "recording"}

@app.post("/sessions/{session_id}/stop")
async def stop_session(session_id: str, background_tasks: BackgroundTasks):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    session = sessions[session_id]
    if session_id in active_deepgram:
        dg = active_deepgram[session_id]
        transcript = dg.get_transcript()
        if transcript:
            session["full_transcript"] = transcript
        del active_deepgram[session_id]
    session["status"] = "processing"
    session["ended_at"] = datetime.utcnow().isoformat()
    try:
        started = datetime.fromisoformat(session["started_at"])
        ended = datetime.fromisoformat(session["ended_at"])
        session["duration_seconds"] = (ended - started).total_seconds()
    except Exception:
        pass
    if not session["full_transcript"]:
        session["full_transcript"] = "\n".join(
            f"{c.get('speaker','Speaker')}: {c['text']}"
            for c in session["transcript_chunks"] if c.get("text")
        )
    background_tasks.add_task(run_analysis_and_report, session_id)
    return {"status": "processing"}

@app.get("/sessions/{session_id}/status")
async def get_status(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    s = sessions[session_id]
    return {
        "session_id": session_id, "status": s["status"],
        "duration_seconds": s.get("duration_seconds", 0),
        "transcript_length": len(s.get("full_transcript", "")),
        "chunk_count": len(s.get("transcript_chunks", [])),
        "word_count": len(s.get("full_transcript", "").split()),
        "error": s.get("error", ""),
    }

@app.get("/sessions/{session_id}/transcript")
async def get_transcript(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    s = sessions[session_id]
    return {
        "transcript": s.get("full_transcript", "") or s.get("live_transcript", ""),
        "chunks": s.get("transcript_chunks", []),
        "live": s.get("live_transcript", ""),
    }

@app.get("/sessions/{session_id}/analysis")
async def get_analysis(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"analysis": sessions[session_id].get("analysis")}

@app.post("/recording/start")
async def start_deepgram_recording(body: StartRecording, background_tasks: BackgroundTasks):
    if body.session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    if not DEEPGRAM_AVAILABLE:
        raise HTTPException(status_code=400, detail="Deepgram not available")
    if not os.getenv("DEEPGRAM_API_KEY"):
        raise HTTPException(status_code=400, detail="DEEPGRAM_API_KEY not set")
    session = sessions[body.session_id]
    session["status"] = "recording"
    device_index = body.device_index
    if device_index is None:
        device_index = DeepgramClient.find_vbcable_device()
    dg = DeepgramClient()
    active_deepgram[body.session_id] = dg
    def on_transcript(speaker: str, text: str, is_final: bool):
        if is_final:
            session["transcript_chunks"].append({
                "index": len(session["transcript_chunks"]),
                "speaker": speaker, "text": text,
                "timestamp": datetime.utcnow().isoformat(), "is_final": True,
            })
            session["live_transcript"] += f"{speaker}: {text}\n"
        else:
            existing = "\n".join(f"{c['speaker']}: {c['text']}" for c in session["transcript_chunks"])
            session["live_transcript"] = existing + f"\n{speaker}: {text}..."
    background_tasks.add_task(dg.start_streaming, on_transcript=on_transcript,
                               language=body.language, device_index=device_index)
    return {
        "status": "recording", "device_index": device_index,
        "vbcable_detected": device_index is not None,
        "message": "Recording started" + (
            " with VB-Cable — all speakers captured" if device_index is not None
            else " with microphone only"),
    }

@app.post("/recording/stop")
async def stop_deepgram_recording(body: StopRecording, background_tasks: BackgroundTasks):
    if body.session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    session = sessions[body.session_id]
    if body.session_id in active_deepgram:
        dg = active_deepgram[body.session_id]
        transcript = dg.get_transcript()
        if transcript:
            session["full_transcript"] = transcript
        try:
            await dg.stop()
        except Exception:
            pass
        del active_deepgram[body.session_id]
    session["status"] = "processing"
    session["ended_at"] = datetime.utcnow().isoformat()
    try:
        started = datetime.fromisoformat(session["started_at"])
        ended = datetime.fromisoformat(session["ended_at"])
        session["duration_seconds"] = (ended - started).total_seconds()
    except Exception:
        pass
    if not session["full_transcript"]:
        session["full_transcript"] = session.get("live_transcript", "")
    background_tasks.add_task(run_analysis_and_report, session_id=body.session_id)
    return {"status": "processing", "has_content": bool(session["full_transcript"].strip())}

@app.post("/transcribe/chunk")
async def transcribe_chunk(session_id: str, audio_file: UploadFile = File(...)):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    audio_bytes = await audio_file.read()
    if len(audio_bytes) < 1000:
        chunk = {"index": 0, "text": "", "speaker": "Speaker 1", "timestamp": datetime.utcnow().isoformat()}
        sessions[session_id]["transcript_chunks"].append(chunk)
        return {"status": "ok", "chunk": chunk, "warning": "Audio too small"}
    try:
        result = await nvidia_client.transcribe_audio(audio_bytes, audio_file.filename or "audio.wav")
        chunk = {
            "index": len(sessions[session_id]["transcript_chunks"]),
            "text": result["text"], "speaker": result.get("speaker", "Speaker 1"),
            "timestamp": datetime.utcnow().isoformat(), "confidence": result.get("confidence", 1.0),
        }
        sessions[session_id]["transcript_chunks"].append(chunk)
        return {"status": "ok", "chunk": chunk}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

@app.get("/report/{session_id}")
async def get_report(session_id: str):
    report_path = REPORTS_DIR / f"{session_id}.pdf"
    if not report_path.exists():
        if session_id not in sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        status = sessions[session_id]["status"]
        if status in ("recording", "processing", "analyzing"):
            raise HTTPException(status_code=202, detail=f"Not ready. Status: {status}")
        raise HTTPException(status_code=404, detail="Report not generated yet")
    title = sessions.get(session_id, {}).get("title", "meeting")
    safe = "".join(c if c.isalnum() or c in " -_" else "_" for c in title)
    return FileResponse(str(report_path), media_type="application/pdf", filename=f"{safe}_report.pdf")

@app.post("/report/{session_id}/generate")
async def generate_report(session_id: str, background_tasks: BackgroundTasks):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    background_tasks.add_task(run_analysis_and_report, session_id)
    return {"status": "generating"}

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    last_len = 0
    try:
        while True:
            if session_id in sessions:
                s = sessions[session_id]
                live = s.get("live_transcript", "")
                if len(live) > last_len:
                    await websocket.send_json({"type": "transcript", "text": live, "new_text": live[last_len:]})
                    last_len = len(live)
                await websocket.send_json({"type": "status", "status": s["status"]})
                if s["status"] in ("completed", "failed"):
                    break
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass

async def run_analysis_and_report(session_id: str):
    """
    Fixed flow:
    1. Empty transcript → blank report instantly (no AI call, no waiting)
    2. Has transcript → NVIDIA AI analysis → full PDF report
    3. AI fails → basic report with just transcript (never hangs)
    """
    session = sessions[session_id]
    transcript = session.get("full_transcript", "").strip()
    generator = ReportGenerator()
    report_path = REPORTS_DIR / f"{session_id}.pdf"

    # ── EMPTY: generate blank report immediately — no AI call ─────────────────
    if not transcript:
        session["status"] = "completed"
        session["analysis"] = {
            "executive_summary": "No audio was captured in this session.",
            "meeting_type": "Unknown", "main_topics": [],
            "key_discussion_points": [], "decisions": [],
            "action_items": [], "open_questions": [],
            "risks_concerns": [], "speakers": [],
            "key_insights": [], "recommendations": [],
            "blockers_identified": [], "next_steps_summary": "",
            "word_count": 0, "analyzed_at": datetime.utcnow().isoformat(),
            "empty": True,
        }
        try:
            generator.generate(session=session, analysis=session["analysis"], output_path=str(report_path))
        except Exception:
            pass
        return

    # ── HAS CONTENT: run NVIDIA AI analysis ───────────────────────────────────
    try:
        session["status"] = "analyzing"
        analyzer = MeetingAnalyzer(nvidia_client)
        analysis = await analyzer.analyze(transcript=transcript, session=session)
        session["analysis"] = analysis
        generator.generate(session=session, analysis=analysis, output_path=str(report_path))
        session["status"] = "completed"

    except Exception as e:
        # AI failed — still give user a report with the transcript
        session["status"] = "completed"
        session["analysis"] = {
            "executive_summary": "AI analysis unavailable. Your full transcript is below.",
            "meeting_type": "Meeting", "main_topics": [],
            "key_discussion_points": [], "decisions": [],
            "action_items": [], "open_questions": [],
            "risks_concerns": [], "speakers": [],
            "key_insights": [], "recommendations": [],
            "blockers_identified": [],
            "next_steps_summary": "Review transcript manually.",
            "word_count": len(transcript.split()),
            "analyzed_at": datetime.utcnow().isoformat(),
        }
        try:
            generator.generate(session=session, analysis=session["analysis"], output_path=str(report_path))
        except Exception:
            pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
"""
MeetNote AI — Final Backend
Real-time transcription via Deepgram
Works with Google Meet, Zoom, Discord, Teams via VB-Cable
"""

import os
import uuid
import json
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
from deepgram_client import DeepgramClient

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="MeetNote AI", version="3.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(exist_ok=True)

sessions: dict[str, dict] = {}
active_deepgram: dict[str, DeepgramClient] = {}
nvidia_client = NVIDIAClient()
session_manager = SessionManager()

# ── Models ────────────────────────────────────────────────────────────────────
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

# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "deepgram": bool(os.getenv("DEEPGRAM_API_KEY")),
        "nvidia": bool(os.getenv("NVIDIA_API_KEY")),
    }

# ── Audio devices ─────────────────────────────────────────────────────────────
@app.get("/devices")
async def list_devices():
    """List all available audio input devices"""
    devices = DeepgramClient.list_audio_devices()
    vbcable = DeepgramClient.find_vbcable_device()
    return {
        "devices": devices,
        "vbcable_index": vbcable,
        "vbcable_detected": vbcable is not None,
    }

# ── Session endpoints ─────────────────────────────────────────────────────────
@app.post("/sessions/create")
async def create_session(body: SessionCreate):
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "id": session_id,
        "title": body.meeting_title,
        "participants": body.participants,
        "language": body.language,
        "mode": body.mode,
        "status": "created",
        "transcript_chunks": [],
        "full_transcript": "",
        "live_transcript": "",
        "analysis": None,
        "started_at": datetime.utcnow().isoformat(),
        "ended_at": None,
        "duration_seconds": 0,
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

    # Stop Deepgram if running
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

    # Merge chunks if no deepgram transcript
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
        "session_id": session_id,
        "status": s["status"],
        "duration_seconds": s.get("duration_seconds", 0),
        "transcript_length": len(s.get("full_transcript", "")),
        "chunk_count": len(s.get("transcript_chunks", [])),
        "word_count": len(s.get("full_transcript", "").split()),
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


# ── Deepgram real-time recording ──────────────────────────────────────────────
@app.post("/recording/start")
async def start_deepgram_recording(body: StartRecording, background_tasks: BackgroundTasks):
    """Start real-time transcription via Deepgram"""
    if body.session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    if not os.getenv("DEEPGRAM_API_KEY"):
        raise HTTPException(status_code=400, detail="DEEPGRAM_API_KEY not configured")

    session = sessions[body.session_id]
    session["status"] = "recording"

    # Auto-detect VB-Cable if no device specified
    device_index = body.device_index
    if device_index is None:
        device_index = DeepgramClient.find_vbcable_device()

    dg = DeepgramClient()
    active_deepgram[body.session_id] = dg

    def on_transcript(speaker: str, text: str, is_final: bool):
        if is_final:
            chunk = {
                "index": len(session["transcript_chunks"]),
                "speaker": speaker,
                "text": text,
                "timestamp": datetime.utcnow().isoformat(),
                "is_final": True,
            }
            session["transcript_chunks"].append(chunk)
            session["live_transcript"] += f"{speaker}: {text}\n"
        else:
            session["live_transcript"] = (
                "\n".join(f"{c['speaker']}: {c['text']}"
                          for c in session["transcript_chunks"])
                + f"\n{speaker}: {text}..."
            )

    background_tasks.add_task(
        dg.start_streaming,
        on_transcript=on_transcript,
        language=body.language,
        device_index=device_index,
    )

    return {
        "status": "recording",
        "device_index": device_index,
        "vbcable_detected": device_index is not None,
        "message": "Recording started" + (" with VB-Cable (all speakers)" if device_index is not None else " with microphone only"),
    }


@app.post("/recording/stop")
async def stop_deepgram_recording(body: StopRecording, background_tasks: BackgroundTasks):
    """Stop Deepgram recording and trigger analysis"""
    if body.session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[body.session_id]

    if body.session_id in active_deepgram:
        dg = active_deepgram[body.session_id]
        transcript = dg.get_transcript()
        if transcript:
            session["full_transcript"] = transcript
        await dg.stop()
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
    return {"status": "processing", "transcript_length": len(session["full_transcript"])}


# ── Audio file transcription ──────────────────────────────────────────────────
@app.post("/transcribe/chunk")
async def transcribe_chunk(session_id: str, audio_file: UploadFile = File(...)):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    audio_bytes = await audio_file.read()
    try:
        result = await nvidia_client.transcribe_audio(audio_bytes, audio_file.filename or "audio.wav")
        chunk = {
            "index": len(sessions[session_id]["transcript_chunks"]),
            "text": result["text"],
            "speaker": result.get("speaker", "Speaker 1"),
            "timestamp": datetime.utcnow().isoformat(),
            "confidence": result.get("confidence", 1.0),
        }
        sessions[session_id]["transcript_chunks"].append(chunk)
        return {"status": "ok", "chunk": chunk}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


# ── Report ────────────────────────────────────────────────────────────────────
@app.get("/report/{session_id}")
async def get_report(session_id: str):
    report_path = REPORTS_DIR / f"{session_id}.pdf"
    if not report_path.exists():
        if session_id not in sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        status = sessions[session_id]["status"]
        if status in ("recording", "processing", "analyzing"):
            raise HTTPException(status_code=202, detail=f"Not ready. Status: {status}")
        raise HTTPException(status_code=404, detail="Report not generated")
    title = sessions.get(session_id, {}).get("title", "meeting")
    safe = "".join(c if c.isalnum() or c in " -_" else "_" for c in title)
    return FileResponse(str(report_path), media_type="application/pdf",
                        filename=f"{safe}_report.pdf")


@app.post("/report/{session_id}/generate")
async def generate_report(session_id: str, background_tasks: BackgroundTasks):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    background_tasks.add_task(run_analysis_and_report, session_id)
    return {"status": "generating"}


# ── WebSocket for live transcript ─────────────────────────────────────────────
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
                    await websocket.send_json({
                        "type": "transcript",
                        "text": live,
                        "new_text": live[last_len:],
                    })
                    last_len = len(live)
                await websocket.send_json({"type": "status", "status": s["status"]})
                if s["status"] in ("completed", "failed"):
                    break
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass


# ── Background task ───────────────────────────────────────────────────────────
async def run_analysis_and_report(session_id: str):
    session = sessions[session_id]
    transcript = session.get("full_transcript", "")

    if not transcript.strip():
        session["status"] = "failed"
        session["error"] = "Empty transcript — no audio was captured"
        return

    try:
        session["status"] = "analyzing"
        analyzer = MeetingAnalyzer(nvidia_client)
        analysis = await analyzer.analyze(transcript=transcript, session=session)
        session["analysis"] = analysis

        generator = ReportGenerator()
        report_path = REPORTS_DIR / f"{session_id}.pdf"
        generator.generate(session=session, analysis=analysis, output_path=str(report_path))
        session["status"] = "completed"
    except Exception as e:
        session["status"] = "failed"
        session["error"] = str(e)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
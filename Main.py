"""
AI Meeting Intelligence Agent - FastAPI Backend
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

from audio_capture import AudioCapture
from nvidia_client import NVIDIAClient
from meeting_analyzer import MeetingAnalyzer
from report_generator import ReportGenerator
from session_manager import SessionManager

# ── App setup ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="AI Meeting Intelligence Agent",
    description="Capture, transcribe, analyze meetings and generate PDF reports",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Global state ─────────────────────────────────────────────────────────────
REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(exist_ok=True)

sessions: dict[str, dict] = {}
nvidia_client = NVIDIAClient()
session_manager = SessionManager()

# ── Request / Response models ─────────────────────────────────────────────────
class SessionCreate(BaseModel):
    meeting_title: str
    participants: list[str] = []
    language: str = "en-US"

class TranscribeRequest(BaseModel):
    session_id: str
    audio_base64: Optional[str] = None

class AnalyzeRequest(BaseModel):
    session_id: str
    transcript: Optional[str] = None

class SessionStatus(BaseModel):
    session_id: str
    status: str
    duration_seconds: float
    transcript_length: int
    chunk_count: int

# ── Session endpoints ─────────────────────────────────────────────────────────
@app.post("/sessions/create")
async def create_session(body: SessionCreate):
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "id": session_id,
        "title": body.meeting_title,
        "participants": body.participants,
        "language": body.language,
        "status": "created",
        "transcript_chunks": [],
        "full_transcript": "",
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
    return {"status": "recording", "session_id": session_id}


@app.post("/sessions/{session_id}/stop")
async def stop_session(session_id: str, background_tasks: BackgroundTasks):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    session["status"] = "processing"
    session["ended_at"] = datetime.utcnow().isoformat()
    
    started = datetime.fromisoformat(session["started_at"])
    ended = datetime.fromisoformat(session["ended_at"])
    session["duration_seconds"] = (ended - started).total_seconds()
    
    # Merge all transcript chunks
    session["full_transcript"] = "\n".join(
        c["text"] for c in session["transcript_chunks"] if c.get("text")
    )
    
    background_tasks.add_task(run_analysis_and_report, session_id)
    return {"status": "processing", "session_id": session_id}


@app.get("/sessions/{session_id}/status", response_model=SessionStatus)
async def get_status(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    s = sessions[session_id]
    return SessionStatus(
        session_id=session_id,
        status=s["status"],
        duration_seconds=s.get("duration_seconds", 0),
        transcript_length=len(s.get("full_transcript", "")),
        chunk_count=len(s.get("transcript_chunks", [])),
    )


@app.get("/sessions/{session_id}/transcript")
async def get_transcript(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "transcript": sessions[session_id].get("full_transcript", ""),
        "chunks": sessions[session_id].get("transcript_chunks", []),
    }


@app.get("/sessions/{session_id}/analysis")
async def get_analysis(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"analysis": sessions[session_id].get("analysis")}


# ── Audio transcription endpoint ──────────────────────────────────────────────
@app.post("/transcribe/chunk")
async def transcribe_chunk(
    session_id: str,
    audio_file: UploadFile = File(...),
):
    """Transcribe an audio chunk and append to session transcript."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    audio_bytes = await audio_file.read()
    
    try:
        result = await nvidia_client.transcribe_audio(audio_bytes, audio_file.filename or "chunk.wav")
        
        chunk = {
            "index": len(sessions[session_id]["transcript_chunks"]),
            "text": result["text"],
            "timestamp": datetime.utcnow().isoformat(),
            "confidence": result.get("confidence", 1.0),
            "speaker": result.get("speaker", "Unknown"),
        }
        sessions[session_id]["transcript_chunks"].append(chunk)
        
        return {"status": "ok", "chunk": chunk}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


@app.post("/transcribe/file")
async def transcribe_file(audio_file: UploadFile = File(...)):
    """Transcribe a complete audio file (no session required)."""
    audio_bytes = await audio_file.read()
    result = await nvidia_client.transcribe_audio(audio_bytes, audio_file.filename or "audio.wav")
    return result


# ── Analysis endpoint ─────────────────────────────────────────────────────────
@app.post("/analyze")
async def analyze_meeting(body: AnalyzeRequest, background_tasks: BackgroundTasks):
    if body.session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    transcript = body.transcript or sessions[body.session_id].get("full_transcript", "")
    if not transcript.strip():
        raise HTTPException(status_code=400, detail="No transcript to analyze")
    
    sessions[body.session_id]["status"] = "analyzing"
    background_tasks.add_task(run_analysis, body.session_id, transcript)
    return {"status": "analysis_started", "session_id": body.session_id}


# ── Report endpoint ───────────────────────────────────────────────────────────
@app.get("/report/{session_id}")
async def get_report(session_id: str):
    """Download the PDF report for a session."""
    report_path = REPORTS_DIR / f"{session_id}.pdf"
    
    if not report_path.exists():
        if session_id not in sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        status = sessions[session_id]["status"]
        if status in ("recording", "processing", "analyzing"):
            raise HTTPException(status_code=202, detail=f"Report not ready yet. Status: {status}")
        raise HTTPException(status_code=404, detail="Report not generated")
    
    title = sessions.get(session_id, {}).get("title", "meeting")
    safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in title)
    return FileResponse(
        path=str(report_path),
        media_type="application/pdf",
        filename=f"{safe_title}_report.pdf",
    )


@app.post("/report/{session_id}/generate")
async def generate_report(session_id: str, background_tasks: BackgroundTasks):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    background_tasks.add_task(run_analysis_and_report, session_id)
    return {"status": "generating", "session_id": session_id}


# ── WebSocket for live transcript streaming ───────────────────────────────────
@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    last_index = 0
    try:
        while True:
            if session_id in sessions:
                chunks = sessions[session_id]["transcript_chunks"]
                if len(chunks) > last_index:
                    new_chunks = chunks[last_index:]
                    await websocket.send_json({"type": "transcript", "chunks": new_chunks})
                    last_index = len(chunks)
                
                status = sessions[session_id]["status"]
                await websocket.send_json({"type": "status", "status": status})
                
                if status in ("completed", "failed"):
                    break
            
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass


# ── Background tasks ──────────────────────────────────────────────────────────
async def run_analysis(session_id: str, transcript: str):
    try:
        analyzer = MeetingAnalyzer(nvidia_client)
        analysis = await analyzer.analyze(
            transcript=transcript,
            session=sessions[session_id],
        )
        sessions[session_id]["analysis"] = analysis
        sessions[session_id]["status"] = "analyzed"
    except Exception as e:
        sessions[session_id]["status"] = "failed"
        sessions[session_id]["error"] = str(e)


async def run_analysis_and_report(session_id: str):
    session = sessions[session_id]
    transcript = session.get("full_transcript", "")
    
    if not transcript.strip():
        session["status"] = "failed"
        session["error"] = "Empty transcript"
        return
    
    try:
        # Analyze
        analyzer = MeetingAnalyzer(nvidia_client)
        analysis = await analyzer.analyze(transcript=transcript, session=session)
        session["analysis"] = analysis
        session["status"] = "analyzed"
        
        # Generate PDF
        generator = ReportGenerator()
        report_path = REPORTS_DIR / f"{session_id}.pdf"
        generator.generate(session=session, analysis=analysis, output_path=str(report_path))
        session["status"] = "completed"
        session["report_path"] = str(report_path)
    
    except Exception as e:
        session["status"] = "failed"
        session["error"] = str(e)
        raise


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

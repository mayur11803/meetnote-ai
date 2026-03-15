"""
AI Meeting Intelligence Agent — Streamlit UI
Run: streamlit run app.py
"""

import io
import time
import asyncio
import requests
import threading
import streamlit as st
from pathlib import Path

API_URL = "http://localhost:8000"

st.set_page_config(
    page_title="AI Meeting Intelligence Agent",
    page_icon="🎙",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .stApp { background: #F8FAFC; }
    .main-header {
        background: linear-gradient(135deg, #0A1628 0%, #1A3A6E 100%);
        color: white; padding: 2rem 2rem 1.5rem; border-radius: 12px;
        margin-bottom: 1.5rem;
    }
    .main-header h1 { color: white; margin: 0; font-size: 2rem; }
    .main-header p  { color: #A5C4F5; margin: 0.25rem 0 0; font-size: 0.95rem; }
    .nvidia-badge {
        background: #76B900; color: white; padding: 2px 10px;
        border-radius: 20px; font-size: 0.75rem; font-weight: bold;
        display: inline-block; margin-top: 0.5rem;
    }
    .status-recording { color: #EF4444; font-weight: bold; }
    .status-processing { color: #F59E0B; font-weight: bold; }
    .status-completed  { color: #10B981; font-weight: bold; }
    .metric-card {
        background: white; border: 1px solid #E5E7EB;
        border-radius: 10px; padding: 1rem; text-align: center;
    }
    .transcript-box {
        background: white; border: 1px solid #E5E7EB;
        border-radius: 8px; padding: 1rem; height: 300px;
        overflow-y: auto; font-family: monospace; font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>🎙 AI Meeting Intelligence Agent</h1>
    <p>Capture · Transcribe · Analyze · Report</p>
    <span class="nvidia-badge">⚡ Powered by NVIDIA NIM</span>
</div>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Session Setup")

    meeting_title = st.text_input("Meeting title", placeholder="e.g. Q4 Planning Sprint")
    participants   = st.text_area("Participants (one per line)",
                                  placeholder="Alice\nBob\nCarol")
    language       = st.selectbox("Language", ["en-US", "hi-IN", "es-ES", "fr-FR"])

    st.divider()
    st.header("🔌 Audio Device")
    st.info("Install VB-Cable (Windows) or BlackHole (Mac) to capture meeting audio.")
    audio_device = st.number_input("Device index (0 = default)", min_value=0, value=0)

    st.divider()
    st.header("🤖 AI Model")
    model = st.selectbox("NVIDIA NIM model", [
        "meta/llama-3.1-70b-instruct",
        "meta/llama-3.1-8b-instruct",
        "mistralai/mixtral-8x7b-instruct-v0.1",
        "microsoft/phi-3-medium-128k-instruct",
    ])

    st.divider()
    st.header("📂 Past Sessions")
    try:
        past = requests.get(f"{API_URL}/health", timeout=2)
        if past.ok:
            st.success("Backend connected ✓")
        else:
            st.error("Backend not responding")
    except Exception:
        st.error("Backend offline — run main.py first")

# ── Session state init ────────────────────────────────────────────────────────
if "session_id"    not in st.session_state: st.session_state.session_id    = None
if "recording"     not in st.session_state: st.session_state.recording     = False
if "transcript"    not in st.session_state: st.session_state.transcript    = ""
if "status"        not in st.session_state: st.session_state.status        = "idle"
if "analysis_done" not in st.session_state: st.session_state.analysis_done = False

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_record, tab_upload, tab_report = st.tabs(["🎙 Live Recording", "📁 Upload Audio", "📄 Report"])

# ══ Tab 1: Live Recording ═════════════════════════════════════════════════════
with tab_record:
    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        start_btn = st.button(
            "▶ Start Recording",
            type="primary",
            disabled=st.session_state.recording,
            use_container_width=True,
        )
    with col2:
        stop_btn = st.button(
            "⏹ Stop & Analyze",
            type="secondary",
            disabled=not st.session_state.recording,
            use_container_width=True,
        )
    with col3:
        if st.session_state.session_id:
            st.markdown(f"**Session:** `{st.session_state.session_id[:8]}…`")
            status_class = {
                "recording": "status-recording",
                "processing": "status-processing",
                "completed": "status-completed",
            }.get(st.session_state.status, "")
            st.markdown(
                f'Status: <span class="{status_class}">{st.session_state.status.upper()}</span>',
                unsafe_allow_html=True,
            )

    # Start recording
    if start_btn and meeting_title:
        plist = [p.strip() for p in participants.split("\n") if p.strip()]
        try:
            resp = requests.post(f"{API_URL}/sessions/create", json={
                "meeting_title": meeting_title,
                "participants": plist,
                "language": language,
            })
            session_id = resp.json()["session_id"]
            st.session_state.session_id    = session_id
            st.session_state.recording     = True
            st.session_state.status        = "recording"
            st.session_state.transcript    = ""
            st.session_state.analysis_done = False

            requests.post(f"{API_URL}/sessions/{session_id}/start")
            st.success(f"Recording started! Session: {session_id[:8]}…")
        except Exception as e:
            st.error(f"Failed to start: {e}")
    elif start_btn:
        st.warning("Please enter a meeting title first.")

    # Stop recording
    if stop_btn and st.session_state.session_id:
        try:
            requests.post(f"{API_URL}/sessions/{st.session_state.session_id}/stop")
            st.session_state.recording = False
            st.session_state.status    = "processing"
            st.success("Recording stopped. Analyzing with NVIDIA NIM…")
        except Exception as e:
            st.error(f"Stop failed: {e}")

    # Live transcript display
    st.subheader("📝 Live Transcript")
    transcript_area = st.empty()

    if st.session_state.session_id and st.session_state.recording:
        if st.button("🔄 Refresh transcript"):
            try:
                r = requests.get(f"{API_URL}/sessions/{st.session_state.session_id}/transcript")
                data = r.json()
                st.session_state.transcript = data.get("transcript", "")
            except Exception:
                pass

    transcript_area.markdown(
        f'<div class="transcript-box">{st.session_state.transcript or "<em>Transcript will appear here as the meeting progresses…</em>"}</div>',
        unsafe_allow_html=True,
    )

    # Status polling
    if st.session_state.session_id and st.session_state.status in ("processing", "analyzing"):
        with st.spinner("NVIDIA AI is analyzing your meeting…"):
            for _ in range(30):  # poll up to 30 times
                try:
                    r = requests.get(f"{API_URL}/sessions/{st.session_state.session_id}/status")
                    current_status = r.json().get("status", "")
                    st.session_state.status = current_status
                    if current_status == "completed":
                        st.session_state.analysis_done = True
                        st.success("✅ Analysis complete! Go to the Report tab.")
                        break
                    elif current_status == "failed":
                        st.error("Analysis failed. Check backend logs.")
                        break
                except Exception:
                    pass
                time.sleep(3)

# ══ Tab 2: Upload Audio File ═══════════════════════════════════════════════════
with tab_upload:
    st.subheader("Upload a meeting recording")
    uploaded = st.file_uploader(
        "Upload WAV, MP3, or M4A file",
        type=["wav", "mp3", "m4a", "ogg", "flac"],
    )
    upload_title = st.text_input("Meeting title for this recording",
                                  placeholder="Weekly standup — Jan 15")
    upload_participants = st.text_area("Participants (optional, one per line)")

    if st.button("🚀 Transcribe & Analyze", type="primary") and uploaded:
        if not upload_title:
            st.warning("Please enter a meeting title.")
        else:
            plist = [p.strip() for p in upload_participants.split("\n") if p.strip()]
            with st.spinner("Step 1/3: Creating session…"):
                try:
                    r = requests.post(f"{API_URL}/sessions/create", json={
                        "meeting_title": upload_title,
                        "participants": plist,
                        "language": language,
                    })
                    session_id = r.json()["session_id"]
                    st.session_state.session_id = session_id
                    requests.post(f"{API_URL}/sessions/{session_id}/start")
                except Exception as e:
                    st.error(f"Session creation failed: {e}")
                    st.stop()

            with st.spinner("Step 2/3: Transcribing with NVIDIA Parakeet ASR…"):
                try:
                    files = {"audio_file": (uploaded.name, uploaded.getvalue(), "audio/wav")}
                    r = requests.post(
                        f"{API_URL}/transcribe/chunk",
                        params={"session_id": session_id},
                        files=files,
                    )
                    transcript_text = r.json().get("chunk", {}).get("text", "")
                    st.session_state.transcript = transcript_text

                    # Also stop the session with the transcript
                    requests.post(f"{API_URL}/sessions/{session_id}/stop")
                except Exception as e:
                    st.error(f"Transcription failed: {e}")
                    st.stop()

            st.text_area("Transcript preview", transcript_text[:1000] + "…" if len(transcript_text) > 1000 else transcript_text, height=200)

            with st.spinner("Step 3/3: Generating PDF report…"):
                for _ in range(20):
                    try:
                        r = requests.get(f"{API_URL}/sessions/{session_id}/status")
                        if r.json().get("status") == "completed":
                            st.session_state.analysis_done = True
                            st.success("✅ Done! Go to the **Report** tab to download.")
                            break
                    except Exception:
                        pass
                    time.sleep(3)

# ══ Tab 3: Report ═════════════════════════════════════════════════════════════
with tab_report:
    if not st.session_state.session_id:
        st.info("Start a recording or upload a file to generate a report.")
    elif not st.session_state.analysis_done:
        st.info("Analysis in progress…")
        if st.button("Check status"):
            try:
                r = requests.get(f"{API_URL}/sessions/{st.session_state.session_id}/status")
                status = r.json().get("status")
                if status == "completed":
                    st.session_state.analysis_done = True
                    st.rerun()
                else:
                    st.write(f"Current status: **{status}**")
            except Exception as e:
                st.error(str(e))
    else:
        sid = st.session_state.session_id

        # Show analysis summary
        try:
            r = requests.get(f"{API_URL}/sessions/{sid}/analysis")
            analysis = r.json().get("analysis", {})

            if analysis:
                st.subheader("📊 Analysis Preview")

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Action Items",    len(analysis.get("action_items", [])))
                c2.metric("Decisions",       len(analysis.get("decisions", [])))
                c3.metric("Key Points",      len(analysis.get("key_discussion_points", [])))
                c4.metric("Speakers",        len(analysis.get("speakers", [])))

                with st.expander("Executive Summary"):
                    st.write(analysis.get("executive_summary", "—"))

                with st.expander("Action Items"):
                    for item in analysis.get("action_items", []):
                        st.markdown(f"- **{item.get('task')}** — Owner: `{item.get('owner', 'TBD')}` | Priority: `{item.get('priority', 'medium')}`")

                with st.expander("Decisions Made"):
                    for d in analysis.get("decisions", []):
                        st.markdown(f"- {d.get('decision')}")

                with st.expander("Recommendations"):
                    for r_item in analysis.get("recommendations", []):
                        st.markdown(f"- {r_item}")

        except Exception as e:
            st.warning(f"Could not load analysis preview: {e}")

        # Download PDF
        st.divider()
        st.subheader("📄 Download PDF Report")

        col_dl, col_regen = st.columns(2)
        with col_dl:
            try:
                pdf_resp = requests.get(f"{API_URL}/report/{sid}")
                if pdf_resp.status_code == 200:
                    st.download_button(
                        label="⬇️ Download PDF Report",
                        data=pdf_resp.content,
                        file_name=f"meeting_report_{sid[:8]}.pdf",
                        mime="application/pdf",
                        type="primary",
                        use_container_width=True,
                    )
                else:
                    st.warning(f"Report not ready: {pdf_resp.status_code}")
            except Exception as e:
                st.error(f"Could not fetch report: {e}")

        with col_regen:
            if st.button("🔄 Regenerate Report", use_container_width=True):
                requests.post(f"{API_URL}/report/{sid}/generate")
                st.info("Regenerating… refresh in a moment.")

"""
MeetNote AI v2 — Beautiful Dashboard
Super clean, user-friendly, works for Students & Professionals
"""

import os
import time
import requests
import streamlit as st
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────
API_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(
    page_title="MeetNote AI",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Full CSS ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');

*, html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    box-sizing: border-box;
}

.stApp { background: #080B14; color: #E2E8F0; }
.block-container { padding: 2rem 2.5rem !important; max-width: 1200px; }

/* ── Top navbar ── */
.navbar {
    display: flex; align-items: center; justify-content: space-between;
    padding: 0 0 1.5rem; border-bottom: 1px solid #1A2035; margin-bottom: 2rem;
}
.logo { display: flex; align-items: center; gap: 10px; }
.logo-icon {
    width: 36px; height: 36px; background: linear-gradient(135deg, #6366F1, #8B5CF6);
    border-radius: 10px; display: flex; align-items: center; justify-content: center;
    font-size: 18px;
}
.logo-text { font-size: 20px; font-weight: 800; color: #F1F5F9; letter-spacing: -.5px; }
.logo-text span { color: #6366F1; }
.nvidia-pill {
    background: rgba(118,183,0,0.12); border: 1px solid rgba(118,183,0,0.3);
    color: #76B900; padding: 4px 12px; border-radius: 20px;
    font-size: 11px; font-weight: 600; letter-spacing: .04em;
}

/* ── Mode toggle ── */
.mode-wrap {
    display: flex; background: #0F1420; border: 1px solid #1A2035;
    border-radius: 12px; padding: 4px; gap: 4px; width: fit-content; margin: 0 auto 2rem;
}
.mode-btn {
    padding: 8px 24px; border-radius: 9px; font-size: 13px; font-weight: 600;
    cursor: pointer; border: none; transition: all .2s;
}
.mode-btn.off { background: transparent; color: #4B5563; }
.mode-btn.on  { background: #6366F1; color: #fff; }

/* ── Status bar ── */
.status-bar {
    display: flex; align-items: center; justify-content: center; gap: 8px;
    padding: 10px 20px; border-radius: 12px; margin-bottom: 2rem;
    font-size: 13px; font-weight: 600;
}
.status-idle     { background: rgba(75,85,99,.15);   border: 1px solid #1F2937; color: #6B7280; }
.status-rec      { background: rgba(239,68,68,.1);   border: 1px solid rgba(239,68,68,.3); color: #FCA5A5; }
.status-proc     { background: rgba(245,158,11,.1);  border: 1px solid rgba(245,158,11,.3); color: #FCD34D; }
.status-done     { background: rgba(16,185,129,.1);  border: 1px solid rgba(16,185,129,.3); color: #6EE7B7; }
.pulse { width: 8px; height: 8px; border-radius: 50%; background: #EF4444;
         animation: pulse 1s infinite; flex-shrink: 0; }
@keyframes pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:.5;transform:scale(.8)} }

/* ── Big action cards ── */
.action-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 2rem; }
.action-card {
    background: #0F1420; border: 1px solid #1A2035; border-radius: 16px;
    padding: 1.5rem; text-align: center; transition: all .2s;
}
.action-card:hover { border-color: #6366F1; transform: translateY(-2px); }
.action-card.active { border-color: #6366F1; background: rgba(99,102,241,.06); }
.action-card.success { border-color: #10B981; background: rgba(16,185,129,.06); }
.ac-icon { font-size: 2.2rem; margin-bottom: .75rem; display: block; }
.ac-title { font-size: 15px; font-weight: 700; color: #F1F5F9; margin-bottom: 4px; }
.ac-desc  { font-size: 12px; color: #4B5563; line-height: 1.5; }

/* ── Info cards row ── */
.info-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 2rem; }
.info-card {
    background: #0F1420; border: 1px solid #1A2035; border-radius: 12px;
    padding: 1rem; text-align: center;
}
.info-num   { font-size: 1.8rem; font-weight: 800; color: #6366F1; line-height: 1; }
.info-label { font-size: 11px; color: #4B5563; margin-top: 4px; text-transform: uppercase; letter-spacing: .06em; }

/* ── Transcript box ── */
.tx-wrap {
    background: #0A0D18; border: 1px solid #1A2035; border-radius: 14px;
    padding: 1.2rem; margin-bottom: 1.5rem;
}
.tx-header {
    display: flex; align-items: center; justify-content: space-between;
    margin-bottom: 10px; padding-bottom: 10px; border-bottom: 1px solid #1A2035;
}
.tx-title { font-size: 12px; font-weight: 600; color: #6366F1;
            text-transform: uppercase; letter-spacing: .06em; }
.tx-body {
    min-height: 140px; max-height: 220px; overflow-y: auto;
    font-size: 13px; color: #9CA3AF; line-height: 1.75;
}
.tx-empty { color: #2D3748; font-style: italic; font-size: 13px; }
.speaker-chip {
    display: inline-block; background: rgba(99,102,241,.15);
    color: #818CF8; padding: 1px 8px; border-radius: 6px;
    font-size: 11px; font-weight: 600; margin-right: 6px;
}

/* ── Insights section ── */
.insight-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 1.5rem; }
.insight-card {
    background: #0A0D18; border: 1px solid #1A2035; border-radius: 12px; padding: 1rem;
}
.ic-label { font-size: 10px; font-weight: 600; color: #6366F1;
            text-transform: uppercase; letter-spacing: .06em; margin-bottom: 8px; }
.ic-item  { font-size: 12px; color: #9CA3AF; line-height: 1.6; padding: 4px 0;
            border-bottom: 1px solid #0F1420; }
.ic-item:last-child { border-bottom: none; }
.ic-item strong { color: #E2E8F0; }

/* ── Download button ── */
.dl-wrap {
    background: linear-gradient(135deg, rgba(99,102,241,.15), rgba(139,92,246,.1));
    border: 1px solid rgba(99,102,241,.3); border-radius: 16px;
    padding: 1.5rem; text-align: center; margin-bottom: 1.5rem;
}
.dl-title { font-size: 16px; font-weight: 700; color: #F1F5F9; margin-bottom: 4px; }
.dl-sub   { font-size: 12px; color: #6B7280; margin-bottom: 1rem; }

/* ── Setup guide ── */
.setup-card {
    background: #0F1420; border: 1px solid #1A2035; border-radius: 14px;
    padding: 1.2rem; margin-bottom: 1rem;
}
.setup-title { font-size: 13px; font-weight: 700; color: #E2E8F0; margin-bottom: 8px; }
.setup-step  { font-size: 12px; color: #6B7280; line-height: 1.85; }
.setup-step strong { color: #9CA3AF; }

/* ── Streamlit overrides ── */
.stButton > button {
    border-radius: 10px !important; font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-weight: 600 !important; transition: all .2s !important;
    border: none !important;
}
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background: #0F1420 !important; border: 1px solid #1A2035 !important;
    color: #E2E8F0 !important; border-radius: 10px !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}
.stSelectbox > div > div {
    background: #0F1420 !important; border: 1px solid #1A2035 !important;
    color: #E2E8F0 !important; border-radius: 10px !important;
}
.stFileUploader > div {
    background: #0F1420 !important; border: 1px dashed #1A2035 !important;
    border-radius: 12px !important;
}
[data-testid="stSidebar"] { display: none !important; }
.stTabs [data-baseweb="tab-list"] {
    background: #0F1420 !important; border-radius: 12px !important;
    padding: 4px !important; gap: 4px !important; border: 1px solid #1A2035 !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 9px !important; color: #4B5563 !important;
    font-weight: 600 !important; font-size: 13px !important;
}
.stTabs [aria-selected="true"] {
    background: #6366F1 !important; color: #fff !important;
}
div[data-testid="stStatusWidget"] { display: none; }
#MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
for k, v in {
    "session_id": None, "recording": False, "transcript": "",
    "status": "idle", "analysis": None, "report_ready": False,
    "mode": "professional", "title": "", "participants": "",
    "chunk_count": 0, "duration": 0, "start_time": None,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Helper ────────────────────────────────────────────────────────────────────
def backend_ok():
    try:
        return requests.get(f"{API_URL}/health", timeout=2).ok
    except:
        return False

def fmt_duration(sec):
    m, s = divmod(int(sec), 60)
    return f"{m}m {s}s"

# ── NAVBAR ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="navbar">
    <div class="logo">
        <div class="logo-icon">🎙️</div>
        <div class="logo-text">Meet<span>Note</span> AI</div>
    </div>
    <div class="nvidia-pill">⚡ NVIDIA NIM</div>
</div>
""", unsafe_allow_html=True)

# ── MODE TOGGLE ───────────────────────────────────────────────────────────────
col_l, col_m, col_r = st.columns([1, 2, 1])
with col_m:
    m1, m2 = st.columns(2)
    with m1:
        if st.button("🎓  Student", use_container_width=True,
                     type="primary" if st.session_state.mode == "student" else "secondary"):
            st.session_state.mode = "student"
    with m2:
        if st.button("💼  Professional", use_container_width=True,
                     type="primary" if st.session_state.mode == "professional" else "secondary"):
            st.session_state.mode = "professional"

st.markdown("<div style='margin-bottom:1.5rem'></div>", unsafe_allow_html=True)

# ── STATUS BAR ────────────────────────────────────────────────────────────────
status = st.session_state.status
if status == "recording":
    dur = int(time.time() - st.session_state.start_time) if st.session_state.start_time else 0
    st.markdown(f'<div class="status-bar status-rec"><div class="pulse"></div> Recording in progress — {fmt_duration(dur)}</div>', unsafe_allow_html=True)
elif status == "processing":
    st.markdown('<div class="status-bar status-proc">⚙️ &nbsp; NVIDIA AI is analyzing your meeting...</div>', unsafe_allow_html=True)
elif status == "completed":
    st.markdown('<div class="status-bar status-done">✅ &nbsp; Analysis complete — your report is ready!</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="status-bar status-idle">🎙️ &nbsp; Ready — enter your meeting details below and click Start</div>', unsafe_allow_html=True)

# ── MAIN TABS ─────────────────────────────────────────────────────────────────
tab_live, tab_upload, tab_report = st.tabs([
    "🔴  Live Meeting",
    "📁  Upload Recording",
    "📄  Report & Insights",
])

# ════════════════════════════════════════════════════════
# TAB 1 — LIVE MEETING
# ════════════════════════════════════════════════════════
with tab_live:

    # ── Meeting details (always visible, pre-filled defaults) ──
    st.markdown("<div style='margin-bottom:1rem'></div>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns([2, 2, 1])
    with c1:
        title = st.text_input("Meeting / Lecture title",
                              value=st.session_state.title or f"Meeting — {datetime.now().strftime('%b %d, %Y')}",
                              placeholder="e.g. Sprint Planning / Physics Lecture")
        st.session_state.title = title
    with c2:
        participants = st.text_input("Participants (comma separated)",
                                     value=st.session_state.participants or "",
                                     placeholder="Alice, Bob, Prof. Sharma")
        st.session_state.participants = participants
    with c3:
        language = st.selectbox("Language", [
            "English", "Hindi + English", "Hindi", "Auto-detect"
        ])

    st.markdown("<div style='margin-bottom:1.2rem'></div>", unsafe_allow_html=True)

    # ── 3 Big action cards ──
    col1, col2, col3 = st.columns(3)

    with col1:
        active_cls = "active" if status == "recording" else ""
        st.markdown(f"""
        <div class="action-card {active_cls}">
            <span class="ac-icon">{"🔴" if status == "recording" else "▶️"}</span>
            <div class="ac-title">{"Recording..." if status == "recording" else "Start Meeting"}</div>
            <div class="ac-desc">Click to start capturing all audio from your meeting</div>
        </div>""", unsafe_allow_html=True)
        start_disabled = st.session_state.recording or not title
        if st.button("▶  Start Recording", use_container_width=True,
                     disabled=start_disabled, type="primary"):
            plist = [p.strip() for p in participants.split(",") if p.strip()]
            try:
                r = requests.post(f"{API_URL}/sessions/create", json={
                    "meeting_title": title,
                    "participants": plist,
                    "language": language,
                }, timeout=5)
                sid = r.json()["session_id"]
                st.session_state.session_id = sid
                st.session_state.recording = True
                st.session_state.status = "recording"
                st.session_state.transcript = ""
                st.session_state.report_ready = False
                st.session_state.start_time = time.time()
                requests.post(f"{API_URL}/sessions/{sid}/start")
                st.rerun()
            except Exception as e:
                st.error(f"Could not connect to backend: {e}\n\nMake sure uvicorn is running on your PC.")

    with col2:
        active_cls = "active" if not st.session_state.recording else ""
        st.markdown(f"""
        <div class="action-card {active_cls}">
            <span class="ac-icon">⏹️</span>
            <div class="ac-title">Stop & Analyze</div>
            <div class="ac-desc">Stop recording and let NVIDIA AI analyze everything</div>
        </div>""", unsafe_allow_html=True)
        if st.button("⏹  Stop & Analyze", use_container_width=True,
                     disabled=not st.session_state.recording):
            try:
                requests.post(f"{API_URL}/sessions/{st.session_state.session_id}/stop")
                st.session_state.recording = False
                st.session_state.status = "processing"
                if st.session_state.start_time:
                    st.session_state.duration = int(time.time() - st.session_state.start_time)
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

    with col3:
        done_cls = "success" if st.session_state.report_ready else ""
        st.markdown(f"""
        <div class="action-card {done_cls}">
            <span class="ac-icon">📄</span>
            <div class="ac-title">Download PDF</div>
            <div class="ac-desc">Get your complete meeting report as a PDF</div>
        </div>""", unsafe_allow_html=True)
        if st.session_state.report_ready and st.session_state.session_id:
            try:
                pdf = requests.get(f"{API_URL}/report/{st.session_state.session_id}")
                if pdf.status_code == 200:
                    st.download_button(
                        "⬇  Download PDF Report",
                        data=pdf.content,
                        file_name=f"MeetNote_{title[:20].replace(' ','_')}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                        type="primary",
                    )
            except:
                st.button("PDF not ready yet", disabled=True, use_container_width=True)
        else:
            st.button("⬇  PDF not ready yet", disabled=True, use_container_width=True)

    st.markdown("<div style='margin-bottom:1.2rem'></div>", unsafe_allow_html=True)

    # ── Stats row ──
    if st.session_state.session_id:
        s1, s2, s3, s4 = st.columns(4)
        chunks = len(st.session_state.transcript.split("\n")) if st.session_state.transcript else 0
        wc = len(st.session_state.transcript.split()) if st.session_state.transcript else 0
        dur_str = fmt_duration(st.session_state.duration) if st.session_state.duration else "—"
        analysis = st.session_state.analysis or {}

        s1.markdown(f'<div class="info-card"><div class="info-num">{dur_str}</div><div class="info-label">Duration</div></div>', unsafe_allow_html=True)
        s2.markdown(f'<div class="info-card"><div class="info-num">{wc}</div><div class="info-label">Words</div></div>', unsafe_allow_html=True)
        s3.markdown(f'<div class="info-card"><div class="info-num">{len(analysis.get("action_items",[]))}</div><div class="info-label">Action Items</div></div>', unsafe_allow_html=True)
        s4.markdown(f'<div class="info-card"><div class="info-num">{len(analysis.get("decisions",[]))}</div><div class="info-label">Decisions</div></div>', unsafe_allow_html=True)

        st.markdown("<div style='margin-bottom:.5rem'></div>", unsafe_allow_html=True)

    # ── Live transcript ──
    if st.session_state.recording:
        rcol1, rcol2 = st.columns([4, 1])
        with rcol2:
            if st.button("🔄 Refresh", use_container_width=True):
                try:
                    r = requests.get(f"{API_URL}/sessions/{st.session_state.session_id}/transcript")
                    st.session_state.transcript = r.json().get("transcript", "")
                except:
                    pass

    tx = st.session_state.transcript
    tx_content = tx if tx else '<span class="tx-empty">Transcript will appear here as people speak...</span>'
    st.markdown(f"""
    <div class="tx-wrap">
        <div class="tx-header">
            <div class="tx-title">📝 Live Transcript</div>
            {"<div class='pulse'></div>" if status == "recording" else ""}
        </div>
        <div class="tx-body">{tx_content}</div>
    </div>""", unsafe_allow_html=True)

    # ── Auto-poll when processing ──
    if st.session_state.status == "processing" and st.session_state.session_id:
        with st.spinner("NVIDIA AI is analyzing your meeting... please wait"):
            for _ in range(40):
                try:
                    r = requests.get(f"{API_URL}/sessions/{st.session_state.session_id}/status")
                    s = r.json().get("status", "")
                    if s == "completed":
                        r2 = requests.get(f"{API_URL}/sessions/{st.session_state.session_id}/analysis")
                        st.session_state.analysis = r2.json().get("analysis", {})
                        st.session_state.status = "completed"
                        st.session_state.report_ready = True
                        st.success("✅ Done! Click **Download PDF Report** above.")
                        st.rerun()
                        break
                    elif s == "failed":
                        st.error("Analysis failed. Check backend logs.")
                        break
                except:
                    pass
                time.sleep(3)

    # ── Backend status ──
    if not backend_ok():
        st.markdown("""
        <div style="background:rgba(239,68,68,.08);border:1px solid rgba(239,68,68,.2);
                    border-radius:10px;padding:12px 16px;font-size:12px;color:#FCA5A5;margin-top:1rem">
            <strong>⚠ Backend offline</strong> — Live recording needs the FastAPI backend running on your PC.<br>
            Open VS Code terminal and run: <code style="background:rgba(0,0,0,.3);padding:1px 6px;border-radius:4px">uvicorn Main:app --reload --port 8000</code><br><br>
            <strong>For online use</strong> — use the Upload Recording tab instead (works without backend).
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="background:rgba(16,185,129,.06);border:1px solid rgba(16,185,129,.2);
                    border-radius:10px;padding:10px 16px;font-size:12px;color:#6EE7B7;margin-top:1rem">
            ✅ Backend connected and ready
        </div>""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════
# TAB 2 — UPLOAD RECORDING
# ════════════════════════════════════════════════════════
with tab_upload:
    st.markdown("<div style='margin-bottom:1.2rem'></div>", unsafe_allow_html=True)

    uc1, uc2 = st.columns([3, 2])
    with uc1:
        u_title = st.text_input("Meeting title",
                                value=f"Recording — {datetime.now().strftime('%b %d, %Y')}",
                                key="u_title")
        u_participants = st.text_input("Participants (comma separated)",
                                       placeholder="Alice, Bob, Prof. Sharma", key="u_part")
        u_language = st.selectbox("Language",
                                  ["English", "Hindi + English", "Hindi", "Auto-detect"],
                                  key="u_lang")
        uploaded = st.file_uploader("Upload audio file",
                                    type=["wav", "mp3", "m4a", "ogg", "flac"],
                                    label_visibility="visible")
        analyze_btn = st.button("🚀  Transcribe & Analyze",
                                type="primary", use_container_width=True,
                                disabled=not uploaded or not u_title)

    with uc2:
        st.markdown("""
        <div class="setup-card">
            <div class="setup-title">📱 How to record your meeting</div>
            <div class="setup-step">
                <strong>Option A — Record on phone</strong><br>
                Use your phone's voice recorder during the meeting → send the file to your PC → upload here<br><br>
                <strong>Option B — Windows Voice Recorder</strong><br>
                Search "Voice Recorder" in Start menu → record → save → upload<br><br>
                <strong>Option C — Record Google Meet</strong><br>
                Use Meet's built-in recording → download → upload here<br><br>
                <strong>Supported formats:</strong> WAV, MP3, M4A, OGG, FLAC
            </div>
        </div>
        """, unsafe_allow_html=True)

        mode_label = "🎓 Student Mode" if st.session_state.mode == "student" else "💼 Professional Mode"
        mode_features = """
        <strong>Student mode gives you:</strong><br>
        Key concepts · Definitions · Quiz questions · Important dates · Study tips
        """ if st.session_state.mode == "student" else """
        <strong>Professional mode gives you:</strong><br>
        Requirements · Action items with owner · Decisions · Blockers · Clarification questions
        """
        st.markdown(f"""
        <div class="setup-card">
            <div class="setup-title">{mode_label}</div>
            <div class="setup-step">{mode_features}</div>
        </div>""", unsafe_allow_html=True)

    if analyze_btn and uploaded:
        plist = [p.strip() for p in u_participants.split(",") if p.strip()]
        with st.status("Analyzing your recording with NVIDIA AI...", expanded=True) as status_widget:
            try:
                st.write("⚙️ Creating session...")
                r = requests.post(f"{API_URL}/sessions/create", json={
                    "meeting_title": u_title,
                    "participants": plist,
                    "language": u_language,
                    "mode": st.session_state.mode,
                }, timeout=10)
                sid = r.json()["session_id"]
                st.session_state.session_id = sid
                requests.post(f"{API_URL}/sessions/{sid}/start")

                st.write("🎙️ Transcribing audio with NVIDIA Parakeet ASR...")
                files = {"audio_file": (uploaded.name, uploaded.getvalue(), "audio/wav")}
                r = requests.post(f"{API_URL}/transcribe/chunk",
                                  params={"session_id": sid}, files=files, timeout=120)
                tx = r.json().get("chunk", {}).get("text", "")
                st.session_state.transcript = tx
                requests.post(f"{API_URL}/sessions/{sid}/stop")

                st.write("🤖 NVIDIA Llama 3.1 analyzing content...")
                for _ in range(40):
                    r = requests.get(f"{API_URL}/sessions/{sid}/status")
                    s = r.json().get("status", "")
                    if s == "completed":
                        r2 = requests.get(f"{API_URL}/sessions/{sid}/analysis")
                        st.session_state.analysis = r2.json().get("analysis", {})
                        st.session_state.status = "completed"
                        st.session_state.report_ready = True
                        break
                    elif s == "failed":
                        st.write("❌ Analysis failed")
                        break
                    time.sleep(3)

                status_widget.update(label="✅ Analysis complete!", state="complete")

            except Exception as e:
                st.error(f"Error: {e}\n\nMake sure backend is running: uvicorn Main:app --reload --port 8000")

    if st.session_state.transcript and st.session_state.status == "completed":
        st.markdown(f"""
        <div class="tx-wrap" style="margin-top:1.5rem">
            <div class="tx-header"><div class="tx-title">📝 Transcript</div></div>
            <div class="tx-body">{st.session_state.transcript[:600]}{"..." if len(st.session_state.transcript) > 600 else ""}</div>
        </div>""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════
# TAB 3 — REPORT & INSIGHTS
# ════════════════════════════════════════════════════════
with tab_report:
    st.markdown("<div style='margin-bottom:1.2rem'></div>", unsafe_allow_html=True)

    if not st.session_state.report_ready or not st.session_state.analysis:
        st.markdown("""
        <div style="text-align:center;padding:4rem 1rem">
            <div style="font-size:4rem;margin-bottom:1rem">📄</div>
            <div style="font-size:16px;font-weight:600;color:#374151;margin-bottom:8px">No report yet</div>
            <div style="font-size:13px;color:#4B5563">Record a live meeting or upload an audio file first</div>
        </div>""", unsafe_allow_html=True)
    else:
        analysis = st.session_state.analysis

        # ── Stats ──
        s1, s2, s3, s4 = st.columns(4)
        s1.markdown(f'<div class="info-card"><div class="info-num">{len(analysis.get("action_items",[]))}</div><div class="info-label">Action Items</div></div>', unsafe_allow_html=True)
        s2.markdown(f'<div class="info-card"><div class="info-num">{len(analysis.get("key_discussion_points",[]))}</div><div class="info-label">Key Points</div></div>', unsafe_allow_html=True)
        s3.markdown(f'<div class="info-card"><div class="info-num">{len(analysis.get("decisions",[]))}</div><div class="info-label">Decisions</div></div>', unsafe_allow_html=True)
        s4.markdown(f'<div class="info-card"><div class="info-num">{analysis.get("word_count",0)}</div><div class="info-label">Words</div></div>', unsafe_allow_html=True)

        st.markdown("<div style='margin-bottom:1.2rem'></div>", unsafe_allow_html=True)

        # ── Summary ──
        if analysis.get("executive_summary"):
            st.markdown(f"""
            <div style="background:#0A0D18;border:1px solid #1A2035;border-left:3px solid #6366F1;
                        border-radius:0 12px 12px 0;padding:14px 16px;margin-bottom:1.2rem;
                        font-size:14px;color:#CBD5E1;line-height:1.7">
                {analysis["executive_summary"]}
            </div>""", unsafe_allow_html=True)

        # ── Insights grid ──
        mode = st.session_state.mode

        col_a, col_b = st.columns(2)

        with col_a:
            # Action items
            actions = analysis.get("action_items", [])
            if actions:
                items_html = ""
                for item in actions[:5]:
                    t = item.get("task","") if isinstance(item,dict) else str(item)
                    o = item.get("owner","TBD") if isinstance(item,dict) else "TBD"
                    p = item.get("priority","medium") if isinstance(item,dict) else "medium"
                    pc = {"high":"#FCA5A5","medium":"#FCD34D","low":"#6EE7B7"}.get(p,"#9CA3AF")
                    items_html += f'<div class="ic-item"><strong>{t}</strong><br><span style="font-size:11px;color:#4B5563">👤 {o} · <span style="color:{pc}">{p.upper()}</span></span></div>'
                st.markdown(f'<div class="insight-card"><div class="ic-label">✅ Action Items</div>{items_html}</div>', unsafe_allow_html=True)

            # Key points / concepts
            if mode == "student":
                concepts = analysis.get("key_concepts", analysis.get("main_topics", []))
                if concepts:
                    items_html = "".join(f'<div class="ic-item">• {c}</div>' for c in concepts[:6])
                    st.markdown(f'<div class="insight-card" style="margin-top:12px"><div class="ic-label">💡 Key Concepts</div>{items_html}</div>', unsafe_allow_html=True)
            else:
                reqs = analysis.get("requirements", [])
                if reqs:
                    items_html = "".join(f'<div class="ic-item">• {r}</div>' for r in reqs[:5])
                    st.markdown(f'<div class="insight-card" style="margin-top:12px"><div class="ic-label">📋 Requirements</div>{items_html}</div>', unsafe_allow_html=True)

        with col_b:
            # Decisions
            decisions = analysis.get("decisions", [])
            if decisions:
                items_html = ""
                for d in decisions[:4]:
                    dec = d.get("decision","") if isinstance(d,dict) else str(d)
                    items_html += f'<div class="ic-item">✓ {dec}</div>'
                st.markdown(f'<div class="insight-card"><div class="ic-label">🎯 Decisions Made</div>{items_html}</div>', unsafe_allow_html=True)

            # Mode specific
            if mode == "student":
                quiz = analysis.get("quiz_questions", [])
                if quiz:
                    items_html = "".join(f'<div class="ic-item">❓ {q}</div>' for q in quiz[:4])
                    st.markdown(f'<div class="insight-card" style="margin-top:12px"><div class="ic-label">📚 Quiz Questions</div>{items_html}</div>', unsafe_allow_html=True)
            else:
                blockers = analysis.get("blockers_identified", [])
                if blockers:
                    items_html = "".join(f'<div class="ic-item" style="color:#FCA5A5">⚠ {b}</div>' for b in blockers[:4])
                    st.markdown(f'<div class="insight-card" style="margin-top:12px"><div class="ic-label">🚧 Blockers</div>{items_html}</div>', unsafe_allow_html=True)

        st.markdown("<div style='margin-bottom:1.2rem'></div>", unsafe_allow_html=True)

        # ── Download PDF ──
        st.markdown(f"""
        <div class="dl-wrap">
            <div class="dl-title">📄 Your report is ready</div>
            <div class="dl-sub">Complete PDF with all insights, action items, transcript and AI analysis</div>
        </div>""", unsafe_allow_html=True)

        dl_col, _, regen_col = st.columns([2, 1, 1])
        with dl_col:
            if st.session_state.session_id:
                try:
                    pdf = requests.get(f"{API_URL}/report/{st.session_state.session_id}")
                    if pdf.status_code == 200:
                        st.download_button(
                            "⬇️  Download Full PDF Report",
                            data=pdf.content,
                            file_name=f"MeetNote_{st.session_state.title[:20].replace(' ','_')}.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                            type="primary",
                        )
                except Exception as e:
                    st.error(f"Could not fetch PDF: {e}")
        with regen_col:
            if st.button("🔄 Regenerate", use_container_width=True):
                requests.post(f"{API_URL}/report/{st.session_state.session_id}/generate")
                st.info("Regenerating...")
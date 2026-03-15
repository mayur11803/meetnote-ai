"""
MeetNote AI — Final Version
Real-time transcription via Deepgram + VB-Cable
Works with Google Meet, Zoom, Discord, Teams
"""

import os
import time
import requests
import streamlit as st
from datetime import datetime

API_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(
    page_title="MeetNote AI",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
*,[class*="css"]{font-family:'Plus Jakarta Sans',sans-serif!important;box-sizing:border-box}
.stApp{background:#080B14;color:#E2E8F0}
.block-container{padding:2rem 2.5rem!important;max-width:1100px}

.navbar{display:flex;align-items:center;justify-content:space-between;padding:0 0 1.5rem;border-bottom:1px solid #1A2035;margin-bottom:1.5rem}
.logo{font-size:22px;font-weight:800;color:#F1F5F9;letter-spacing:-.5px}
.logo span{color:#6366F1}
.pills{display:flex;gap:8px}
.pill{padding:4px 12px;border-radius:20px;font-size:11px;font-weight:600}
.p-green{background:rgba(118,183,0,.12);border:1px solid rgba(118,183,0,.3);color:#76B900}
.p-indigo{background:rgba(99,102,241,.12);border:1px solid rgba(99,102,241,.3);color:#818CF8}
.p-blue{background:rgba(59,130,246,.12);border:1px solid rgba(59,130,246,.3);color:#93C5FD}

.status-bar{display:flex;align-items:center;justify-content:center;gap:8px;padding:10px 20px;border-radius:12px;margin-bottom:1.5rem;font-size:13px;font-weight:600}
.s-idle{background:rgba(75,85,99,.12);border:1px solid #1F2937;color:#6B7280}
.s-rec{background:rgba(239,68,68,.1);border:1px solid rgba(239,68,68,.3);color:#FCA5A5}
.s-proc{background:rgba(245,158,11,.1);border:1px solid rgba(245,158,11,.3);color:#FCD34D}
.s-done{background:rgba(16,185,129,.1);border:1px solid rgba(16,185,129,.3);color:#6EE7B7}
.pulse{width:8px;height:8px;border-radius:50%;background:#EF4444;animation:pulse 1s infinite;flex-shrink:0;display:inline-block}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}

.step-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-bottom:1.5rem}
.step-card{background:#0F1420;border:1px solid #1A2035;border-radius:14px;padding:1.2rem;text-align:center;transition:all .2s}
.step-card.active{border-color:#6366F1;background:rgba(99,102,241,.06)}
.step-card.done{border-color:#10B981;background:rgba(16,185,129,.06)}
.sc-step{font-size:10px;font-weight:600;color:#4B5563;text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px}
.sc-icon{font-size:2rem;margin-bottom:8px;display:block}
.sc-title{font-size:14px;font-weight:700;color:#F1F5F9;margin-bottom:4px}
.sc-desc{font-size:11px;color:#4B5563;line-height:1.5}

.stat-row{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:1.2rem}
.stat-card{background:#0F1420;border:1px solid #1A2035;border-radius:10px;padding:.8rem;text-align:center}
.stat-num{font-size:1.5rem;font-weight:800;color:#6366F1;line-height:1}
.stat-lbl{font-size:10px;color:#4B5563;margin-top:3px;text-transform:uppercase;letter-spacing:.05em}

.tx-box{background:#0A0D18;border:1px solid #1A2035;border-radius:12px;padding:1rem;margin-bottom:1.2rem}
.tx-label{font-size:11px;font-weight:600;color:#6366F1;text-transform:uppercase;letter-spacing:.06em;margin-bottom:8px;padding-bottom:8px;border-bottom:1px solid #1A2035;display:flex;align-items:center;justify-content:space-between}
.tx-content{font-size:13px;color:#9CA3AF;line-height:1.8;max-height:240px;overflow-y:auto;white-space:pre-wrap}
.tx-empty{color:#2D3748;font-style:italic}
.spk{color:#818CF8;font-weight:600}

.insight-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:1.2rem}
.ic{background:#0A0D18;border:1px solid #1A2035;border-radius:10px;padding:.9rem}
.ic-title{font-size:10px;font-weight:600;color:#6366F1;text-transform:uppercase;letter-spacing:.06em;margin-bottom:8px}
.ic-item{font-size:12px;color:#9CA3AF;line-height:1.6;padding:5px 0;border-bottom:1px solid #0F1420}
.ic-item:last-child{border:none}

.dl-box{background:linear-gradient(135deg,rgba(99,102,241,.12),rgba(139,92,246,.08));border:1px solid rgba(99,102,241,.25);border-radius:14px;padding:1.2rem;text-align:center;margin-bottom:1rem}
.dl-title{font-size:15px;font-weight:700;color:#F1F5F9;margin-bottom:4px}
.dl-sub{font-size:12px;color:#6B7280;margin-bottom:.8rem}

.info-box{background:rgba(99,102,241,.06);border:1px solid rgba(99,102,241,.15);border-radius:10px;padding:10px 14px;font-size:12px;color:#818CF8;line-height:1.7}
.warn-box{background:rgba(239,68,68,.06);border:1px solid rgba(239,68,68,.15);border-radius:10px;padding:10px 14px;font-size:12px;color:#FCA5A5;line-height:1.7}
.ok-box{background:rgba(16,185,129,.06);border:1px solid rgba(16,185,129,.15);border-radius:10px;padding:10px 14px;font-size:12px;color:#6EE7B7;line-height:1.7}
.setup-box{background:#0F1420;border:1px solid #1A2035;border-radius:12px;padding:1rem}
.setup-title{font-size:13px;font-weight:700;color:#E2E8F0;margin-bottom:8px}
.setup-step{font-size:12px;color:#6B7280;line-height:1.9}
.setup-step strong{color:#9CA3AF}
.setup-step code{background:rgba(99,102,241,.1);color:#818CF8;padding:1px 5px;border-radius:4px;font-size:11px}

.stButton>button{border-radius:10px!important;font-family:'Plus Jakarta Sans',sans-serif!important;font-weight:600!important;border:none!important}
.stTextInput>div>div>input,.stTextArea>div>div>textarea{background:#0F1420!important;border:1px solid #1A2035!important;color:#E2E8F0!important;border-radius:10px!important}
.stSelectbox>div>div{background:#0F1420!important;border:1px solid #1A2035!important;color:#E2E8F0!important;border-radius:10px!important}
.stFileUploader>div{background:#0F1420!important;border:1px dashed #1A2035!important;border-radius:12px!important}
[data-testid="stSidebar"]{display:none!important}
.stTabs [data-baseweb="tab-list"]{background:#0F1420!important;border-radius:12px!important;padding:4px!important;gap:4px!important;border:1px solid #1A2035!important}
.stTabs [data-baseweb="tab"]{border-radius:9px!important;color:#4B5563!important;font-weight:600!important;font-size:13px!important}
.stTabs [aria-selected="true"]{background:#6366F1!important;color:#fff!important}
#MainMenu,footer,header{visibility:hidden}
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
defaults = {
    "session_id": None, "recording": False, "transcript": "",
    "live_transcript": "", "status": "idle", "analysis": None,
    "report_ready": False, "mode": "professional",
    "start_time": None, "duration": 0, "title": "",
    "vbcable_detected": False, "device_index": None,
    "word_count": 0,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

def fmt_dur(sec):
    m, s = divmod(int(sec), 60)
    return f"{m}m {s}s"

def backend_ok():
    try:
        return requests.get(f"{API_URL}/health", timeout=2).ok
    except:
        return False

def get_live_transcript():
    try:
        r = requests.get(f"{API_URL}/sessions/{st.session_state.session_id}/transcript", timeout=3)
        data = r.json()
        return data.get("live", "") or data.get("transcript", "")
    except:
        return st.session_state.live_transcript

# ── NAVBAR ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="navbar">
    <div class="logo">🎙️ Meet<span>Note</span> AI</div>
    <div class="pills">
        <div class="pill p-blue">🎧 Deepgram Live</div>
        <div class="pill p-green">⚡ NVIDIA NIM</div>
        <div class="pill p-indigo">🤖 AI Analysis</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── MODE TOGGLE ───────────────────────────────────────────────────────────────
_, mc, _ = st.columns([1, 2, 1])
with mc:
    m1, m2 = st.columns(2)
    with m1:
        if st.button("🎓  Student", use_container_width=True,
                     type="primary" if st.session_state.mode == "student" else "secondary"):
            st.session_state.mode = "student"
            st.rerun()
    with m2:
        if st.button("💼  Professional", use_container_width=True,
                     type="primary" if st.session_state.mode == "professional" else "secondary"):
            st.session_state.mode = "professional"
            st.rerun()

st.markdown("<div style='margin-bottom:1rem'></div>", unsafe_allow_html=True)

# ── STATUS BAR ────────────────────────────────────────────────────────────────
status = st.session_state.status
status_cfg = {
    "idle":      ("s-idle", "🎙️  Ready — enter details and click Start Recording"),
    "recording": ("s-rec",  "🔴  Recording — all speakers being captured in real time"),
    "processing":("s-proc", "⚙️  Processing transcript with NVIDIA AI..."),
    "analyzing": ("s-proc", "🧠  Analyzing meeting content..."),
    "completed": ("s-done", "✅  Report ready — go to Report tab to download!"),
    "failed":    ("s-idle", "❌  Something went wrong — try again"),
}
sc, st_txt = status_cfg.get(status, ("s-idle", "Ready"))
pulse = '<div class="pulse"></div>' if status == "recording" else ""
st.markdown(f'<div class="status-bar {sc}">{pulse}{st_txt}</div>', unsafe_allow_html=True)

# ── TABS ──────────────────────────────────────────────────────────────────────
tab_live, tab_upload, tab_report = st.tabs([
    "🔴  Live Meeting",
    "📁  Upload Recording",
    "📄  Report & Insights",
])

# ══════════════════════════════════════════════════════
# TAB 1 — LIVE MEETING
# ══════════════════════════════════════════════════════
with tab_live:
    st.markdown("<div style='margin-bottom:1rem'></div>", unsafe_allow_html=True)

    # Step cards
    s1_cls = "active" if status == "idle" else "done"
    s2_cls = "active" if status == "recording" else ("done" if status in ("processing","analyzing","completed") else "")
    s3_cls = "active" if status in ("processing","analyzing") else ("done" if status == "completed" else "")

    st.markdown(f"""
    <div class="step-grid">
        <div class="step-card {s1_cls}">
            <div class="sc-step">Step 1</div>
            <span class="sc-icon">📋</span>
            <div class="sc-title">Enter Details</div>
            <div class="sc-desc">Title, participants, language</div>
        </div>
        <div class="step-card {s2_cls}">
            <div class="sc-step">Step 2</div>
            <span class="sc-icon">{"🔴" if status=="recording" else "🎙️"}</span>
            <div class="sc-title">{"Recording..." if status=="recording" else "Record Meeting"}</div>
            <div class="sc-desc">All speakers captured via Deepgram</div>
        </div>
        <div class="step-card {s3_cls}">
            <div class="sc-step">Step 3</div>
            <span class="sc-icon">{"✅" if status=="completed" else "📄"}</span>
            <div class="sc-title">{"PDF Ready!" if status=="completed" else "Get PDF Report"}</div>
            <div class="sc-desc">AI-generated complete report</div>
        </div>
    </div>""", unsafe_allow_html=True)

    # ── Input form (only when idle) ──
    if status in ("idle", "failed"):
        c1, c2 = st.columns(2)
        with c1:
            title = st.text_input("Meeting title",
                value=f"Meeting — {datetime.now().strftime('%b %d, %Y')}",
                placeholder="e.g. Sprint Planning / Physics Lecture")
            st.session_state.title = title
        with c2:
            participants = st.text_input("Participants",
                placeholder="Alice, Bob, Prof. Sharma")
            language = st.selectbox("Language", [
                "English", "Hindi + English", "Hindi", "Auto-detect"])

        # Check VB-Cable
        try:
            r = requests.get(f"{API_URL}/devices", timeout=3)
            dev_data = r.json()
            vb_detected = dev_data.get("vbcable_detected", False)
            vb_index = dev_data.get("vbcable_index")
            st.session_state.vbcable_detected = vb_detected
            st.session_state.device_index = vb_index
        except:
            vb_detected = False
            vb_index = None

        if vb_detected:
            st.markdown(f"""
            <div class="ok-box" style="margin-bottom:1rem">
                ✅ <strong>VB-Cable detected!</strong> All speakers from Google Meet / Zoom / Discord will be captured automatically.
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="info-box" style="margin-bottom:1rem">
                🎧 <strong>VB-Cable not detected</strong> — Only your microphone will be recorded.<br>
                To capture all meeting speakers: Download free VB-Cable from <strong>vb-audio.com/Cable</strong> → install → restart PC.<br>
                <em>Without VB-Cable, the app still works — just records your mic only.</em>
            </div>""", unsafe_allow_html=True)

        lang_map = {"English":"en","Hindi + English":"hi","Hindi":"hi","Auto-detect":"en"}
        lang_code = lang_map.get(language, "en")

        if st.button("▶  Start Recording", type="primary",
                     use_container_width=True, disabled=not title):
            plist = [p.strip() for p in participants.split(",") if p.strip()]
            try:
                # Create session
                r = requests.post(f"{API_URL}/sessions/create", json={
                    "meeting_title": title,
                    "participants": plist,
                    "language": lang_code,
                    "mode": st.session_state.mode,
                }, timeout=10)
                sid = r.json()["session_id"]
                st.session_state.session_id = sid
                requests.post(f"{API_URL}/sessions/{sid}/start")

                # Start Deepgram recording
                r2 = requests.post(f"{API_URL}/recording/start", json={
                    "session_id": sid,
                    "device_index": vb_index,
                    "language": lang_code,
                }, timeout=10)
                result = r2.json()

                st.session_state.recording = True
                st.session_state.status = "recording"
                st.session_state.start_time = time.time()
                st.session_state.live_transcript = ""
                st.session_state.report_ready = False
                st.session_state.analysis = None

                msg = result.get("message", "Recording started")
                st.success(f"✅ {msg}")
                time.sleep(1)
                st.rerun()

            except Exception as e:
                st.error(f"Error: {e}\n\nMake sure backend is deployed on Railway with DEEPGRAM_API_KEY set.")

    # ── Recording active ──
    elif status == "recording":
        dur = int(time.time() - st.session_state.start_time) if st.session_state.start_time else 0

        # Live stats
        live_tx = get_live_transcript()
        st.session_state.live_transcript = live_tx
        wc = len(live_tx.split())

        s1, s2, s3, s4 = st.columns(4)
        s1.markdown(f'<div class="stat-card"><div class="stat-num">{fmt_dur(dur)}</div><div class="stat-lbl">Duration</div></div>', unsafe_allow_html=True)
        s2.markdown(f'<div class="stat-card"><div class="stat-num">{wc}</div><div class="stat-lbl">Words</div></div>', unsafe_allow_html=True)
        s3.markdown(f'<div class="stat-card"><div class="stat-num">{"VB" if st.session_state.vbcable_detected else "Mic"}</div><div class="stat-lbl">Source</div></div>', unsafe_allow_html=True)
        s4.markdown(f'<div class="stat-card"><div class="stat-num">🔴</div><div class="stat-lbl">Recording</div></div>', unsafe_allow_html=True)

        # Live transcript
        tx_display = live_tx if live_tx else '<span class="tx-empty">Listening... speak now</span>'
        formatted_tx = ""
        for line in live_tx.split("\n")[-20:]:  # show last 20 lines
            if ": " in line:
                spk, txt = line.split(": ", 1)
                formatted_tx += f'<span class="spk">{spk}:</span> {txt}\n'
            else:
                formatted_tx += line + "\n"

        st.markdown(f"""
        <div class="tx-box">
            <div class="tx-label">
                <span>📝 Live Transcript</span>
                <div class="pulse"></div>
            </div>
            <div class="tx-content">{formatted_tx or '<span class="tx-empty">Listening... speak now</span>'}</div>
        </div>""", unsafe_allow_html=True)

        col_stop, col_refresh = st.columns(2)
        with col_stop:
            if st.button("⏹  Stop & Generate Report", type="primary", use_container_width=True):
                try:
                    requests.post(f"{API_URL}/recording/stop", json={
                        "session_id": st.session_state.session_id,
                    }, timeout=15)
                    st.session_state.recording = False
                    st.session_state.status = "processing"
                    st.session_state.duration = int(time.time() - st.session_state.start_time)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
        with col_refresh:
            if st.button("🔄  Refresh Transcript", use_container_width=True):
                st.rerun()

    # ── Processing ──
    elif status in ("processing", "analyzing"):
        st.markdown("""
        <div class="info-box" style="text-align:center;padding:2rem">
            <div style="font-size:2.5rem;margin-bottom:.5rem">🧠</div>
            <div style="font-size:14px;font-weight:700;color:#818CF8;margin-bottom:6px">NVIDIA AI is analyzing your meeting</div>
            <div style="font-size:12px;color:#4B5563">Extracting key points · Action items · Decisions · Generating PDF<br>Takes about 30–60 seconds...</div>
        </div>""", unsafe_allow_html=True)

        with st.spinner(""):
            for _ in range(40):
                try:
                    r = requests.get(f"{API_URL}/sessions/{st.session_state.session_id}/status")
                    s = r.json().get("status", "")
                    st.session_state.status = s
                    if s == "completed":
                        r2 = requests.get(f"{API_URL}/sessions/{st.session_state.session_id}/analysis")
                        st.session_state.analysis = r2.json().get("analysis", {})
                        r3 = requests.get(f"{API_URL}/sessions/{st.session_state.session_id}/transcript")
                        st.session_state.transcript = r3.json().get("transcript", "")
                        st.session_state.report_ready = True
                        st.rerun()
                        break
                    elif s == "failed":
                        st.error("Analysis failed. Check if transcript was captured.")
                        break
                except:
                    pass
                time.sleep(3)

    # ── Completed ──
    elif status == "completed":
        analysis = st.session_state.analysis or {}
        dur_str = fmt_dur(st.session_state.duration) if st.session_state.duration else "—"

        s1, s2, s3, s4 = st.columns(4)
        s1.markdown(f'<div class="stat-card"><div class="stat-num">{dur_str}</div><div class="stat-lbl">Duration</div></div>', unsafe_allow_html=True)
        s2.markdown(f'<div class="stat-card"><div class="stat-num">{len(analysis.get("action_items",[]))}</div><div class="stat-lbl">Action Items</div></div>', unsafe_allow_html=True)
        s3.markdown(f'<div class="stat-card"><div class="stat-num">{len(analysis.get("decisions",[]))}</div><div class="stat-lbl">Decisions</div></div>', unsafe_allow_html=True)
        s4.markdown(f'<div class="stat-card"><div class="stat-num">{analysis.get("word_count",0)}</div><div class="stat-lbl">Words</div></div>', unsafe_allow_html=True)

        # Download + new meeting
        st.markdown("""
        <div class="dl-box" style="margin-top:1rem">
            <div class="dl-title">📄 Your PDF report is ready!</div>
            <div class="dl-sub">Complete meeting report with transcript, action items, decisions and AI insights</div>
        </div>""", unsafe_allow_html=True)

        dc, nc = st.columns(2)
        with dc:
            try:
                pdf = requests.get(f"{API_URL}/report/{st.session_state.session_id}")
                if pdf.status_code == 200:
                    st.download_button("⬇️  Download PDF Report",
                        data=pdf.content,
                        file_name=f"MeetNote_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                        mime="application/pdf",
                        use_container_width=True, type="primary")
            except Exception as e:
                st.error(f"PDF error: {e}")
        with nc:
            if st.button("🆕  New Meeting", use_container_width=True):
                for k in defaults:
                    st.session_state[k] = defaults[k]
                st.rerun()

    # ── Backend check ──
    st.markdown("<div style='margin-top:.8rem'></div>", unsafe_allow_html=True)
    if not backend_ok():
        st.markdown("""
        <div class="warn-box">
            ⚠ <strong>Backend offline</strong><br>
            Make sure Railway is deployed with these environment variables:<br>
            <code>NVIDIA_API_KEY</code> · <code>DEEPGRAM_API_KEY</code>
        </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
# TAB 2 — UPLOAD
# ══════════════════════════════════════════════════════
with tab_upload:
    st.markdown("<div style='margin-bottom:1rem'></div>", unsafe_allow_html=True)
    uc1, uc2 = st.columns([3, 2])
    with uc1:
        u_title = st.text_input("Meeting title",
            value=f"Recording — {datetime.now().strftime('%b %d, %Y')}", key="ut")
        u_part = st.text_input("Participants", placeholder="Alice, Bob", key="up")
        u_lang = st.selectbox("Language",
            ["English","Hindi + English","Hindi","Auto-detect"], key="ul")
        uploaded = st.file_uploader("Upload audio file",
            type=["wav","mp3","m4a","ogg","flac"])
        if st.button("🚀  Transcribe & Analyze", type="primary",
                     use_container_width=True, disabled=not uploaded or not u_title):
            plist = [p.strip() for p in u_part.split(",") if p.strip()]
            lang_map = {"English":"en","Hindi + English":"hi","Hindi":"hi","Auto-detect":"en"}
            with st.status("Analyzing with NVIDIA AI...", expanded=True) as sw:
                try:
                    st.write("Creating session...")
                    r = requests.post(f"{API_URL}/sessions/create", json={
                        "meeting_title": u_title, "participants": plist,
                        "language": lang_map.get(u_lang,"en"),
                        "mode": st.session_state.mode,
                    }, timeout=10)
                    sid = r.json()["session_id"]
                    st.session_state.session_id = sid
                    requests.post(f"{API_URL}/sessions/{sid}/start")

                    st.write("Transcribing with NVIDIA Parakeet ASR...")
                    files = {"audio_file": (uploaded.name, uploaded.getvalue(), "audio/wav")}
                    r = requests.post(f"{API_URL}/transcribe/chunk",
                        params={"session_id": sid}, files=files, timeout=120)
                    tx = r.json().get("chunk", {}).get("text", "")
                    st.session_state.transcript = tx
                    requests.post(f"{API_URL}/sessions/{sid}/stop")

                    st.write("NVIDIA Llama 3.1 analyzing content...")
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
                    sw.update(label="✅ Done!", state="complete")
                    st.success("Go to Report & Insights tab to download your PDF!")
                except Exception as e:
                    st.error(f"Error: {e}")

    with uc2:
        st.markdown("""
        <div class="setup-box">
            <div class="setup-title">📱 How to get your meeting audio</div>
            <div class="setup-step">
                <strong>Google Meet</strong><br>
                Use Meet's built-in recording → download → upload<br><br>
                <strong>Zoom</strong><br>
                Record meeting → save locally → upload MP4 or M4A<br><br>
                <strong>Phone recorder</strong><br>
                Record on phone → send to PC → upload<br><br>
                <strong>Windows Voice Recorder</strong><br>
                Search in Start menu → record → upload<br><br>
                <strong>Supported:</strong> WAV · MP3 · M4A · OGG · FLAC
            </div>
        </div>""", unsafe_allow_html=True)

        st.markdown("<div style='margin-top:10px'></div>", unsafe_allow_html=True)

        mode_features = """
        <strong>Student:</strong> Key concepts · Definitions · Quiz questions · Important dates<br><br>
        <strong>Professional:</strong> Requirements · Action items · Decisions · Blockers
        """
        st.markdown(f"""
        <div class="setup-box">
            <div class="setup-title">{"🎓 Student" if st.session_state.mode=="student" else "💼 Professional"} Mode Active</div>
            <div class="setup-step">{mode_features}</div>
        </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
# TAB 3 — REPORT
# ══════════════════════════════════════════════════════
with tab_report:
    st.markdown("<div style='margin-bottom:1rem'></div>", unsafe_allow_html=True)

    if not st.session_state.analysis:
        st.markdown("""
        <div style="text-align:center;padding:3rem">
            <div style="font-size:3.5rem;margin-bottom:.8rem">📄</div>
            <div style="font-size:15px;font-weight:600;color:#374151">No report yet</div>
            <div style="font-size:13px;color:#4B5563;margin-top:6px">Record a live meeting or upload an audio file first</div>
        </div>""", unsafe_allow_html=True)
    else:
        analysis = st.session_state.analysis
        mode = st.session_state.mode

        # Stats
        s1, s2, s3, s4 = st.columns(4)
        s1.markdown(f'<div class="stat-card"><div class="stat-num">{len(analysis.get("action_items",[]))}</div><div class="stat-lbl">Action Items</div></div>', unsafe_allow_html=True)
        s2.markdown(f'<div class="stat-card"><div class="stat-num">{len(analysis.get("key_discussion_points",[]))}</div><div class="stat-lbl">Key Points</div></div>', unsafe_allow_html=True)
        s3.markdown(f'<div class="stat-card"><div class="stat-num">{len(analysis.get("decisions",[]))}</div><div class="stat-lbl">Decisions</div></div>', unsafe_allow_html=True)
        s4.markdown(f'<div class="stat-card"><div class="stat-num">{analysis.get("word_count",0)}</div><div class="stat-lbl">Words</div></div>', unsafe_allow_html=True)

        st.markdown("<div style='margin-bottom:1rem'></div>", unsafe_allow_html=True)

        # Summary
        if analysis.get("executive_summary"):
            st.markdown(f"""
            <div style="background:#0A0D18;border-left:3px solid #6366F1;border-radius:0 10px 10px 0;
                        padding:12px 16px;margin-bottom:1rem;font-size:13px;color:#CBD5E1;line-height:1.7">
                {analysis["executive_summary"]}
            </div>""", unsafe_allow_html=True)

        # Insights
        ca, cb = st.columns(2)
        with ca:
            actions = analysis.get("action_items", [])
            if actions:
                items = ""
                for item in actions[:5]:
                    t = item.get("task","") if isinstance(item,dict) else str(item)
                    o = item.get("owner","TBD") if isinstance(item,dict) else "TBD"
                    p = item.get("priority","medium") if isinstance(item,dict) else "medium"
                    pc = {"high":"#FCA5A5","medium":"#FCD34D","low":"#6EE7B7"}.get(p,"#9CA3AF")
                    items += f'<div class="ic-item"><strong style="color:#E2E8F0">{t}</strong><br><span style="font-size:11px;color:#4B5563">👤 {o} · <span style="color:{pc}">{p.upper()}</span></span></div>'
                st.markdown(f'<div class="ic"><div class="ic-title">✅ Action Items</div>{items}</div>', unsafe_allow_html=True)

            if mode == "student":
                concepts = analysis.get("key_concepts", analysis.get("main_topics", []))
                if concepts:
                    items = "".join(f'<div class="ic-item">• {c}</div>' for c in concepts[:6])
                    st.markdown(f'<div class="ic" style="margin-top:10px"><div class="ic-title">💡 Key Concepts</div>{items}</div>', unsafe_allow_html=True)
            else:
                reqs = analysis.get("requirements", [])
                if reqs:
                    items = "".join(f'<div class="ic-item">• {r}</div>' for r in reqs[:5])
                    st.markdown(f'<div class="ic" style="margin-top:10px"><div class="ic-title">📋 Requirements</div>{items}</div>', unsafe_allow_html=True)

        with cb:
            decisions = analysis.get("decisions", [])
            if decisions:
                items = "".join(f'<div class="ic-item">✓ {d.get("decision","") if isinstance(d,dict) else str(d)}</div>' for d in decisions[:4])
                st.markdown(f'<div class="ic"><div class="ic-title">🎯 Decisions</div>{items}</div>', unsafe_allow_html=True)

            if mode == "student":
                quiz = analysis.get("quiz_questions", [])
                if quiz:
                    items = "".join(f'<div class="ic-item">❓ {q}</div>' for q in quiz[:4])
                    st.markdown(f'<div class="ic" style="margin-top:10px"><div class="ic-title">📚 Quiz Questions</div>{items}</div>', unsafe_allow_html=True)
            else:
                blockers = analysis.get("blockers_identified", [])
                if blockers:
                    items = "".join(f'<div class="ic-item" style="color:#FCA5A5">⚠ {b}</div>' for b in blockers[:4])
                    st.markdown(f'<div class="ic" style="margin-top:10px"><div class="ic-title">🚧 Blockers</div>{items}</div>', unsafe_allow_html=True)

        st.markdown("<div style='margin-bottom:1rem'></div>", unsafe_allow_html=True)

        # Download
        st.markdown("""
        <div class="dl-box">
            <div class="dl-title">📄 Download Full PDF Report</div>
            <div class="dl-sub">Complete report — transcript, action items, decisions, speaker analysis, AI insights</div>
        </div>""", unsafe_allow_html=True)

        dc, rc = st.columns([2, 1])
        with dc:
            if st.session_state.session_id:
                try:
                    pdf = requests.get(f"{API_URL}/report/{st.session_state.session_id}")
                    if pdf.status_code == 200:
                        st.download_button("⬇️  Download PDF Report",
                            data=pdf.content,
                            file_name=f"MeetNote_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                            mime="application/pdf",
                            use_container_width=True, type="primary")
                except Exception as e:
                    st.error(f"PDF error: {e}")
        with rc:
            if st.button("🔄 Regenerate", use_container_width=True):
                if st.session_state.session_id:
                    requests.post(f"{API_URL}/report/{st.session_state.session_id}/generate")
                    st.info("Regenerating...")
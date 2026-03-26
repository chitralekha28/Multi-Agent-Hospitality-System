

import os
import time
import threading
import requests
import streamlit as st
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv

from tasks import HospitalityTasks

load_dotenv()

st.set_page_config(
    page_title="Hospitality AI Planner | GroqCloud",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
/* ---- Fonts ---- */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* ---- Background ---- */
[data-testid="stAppViewContainer"] {
    background: #0e1117;
}
[data-testid="stSidebar"] {
    background: #161b27;
    border-right: 1px solid #2a2f3e;
}

::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #0e1117; }
::-webkit-scrollbar-thumb { background: #3a4060; border-radius: 3px; }


.hero-title {
    font-size: 2.8rem;
    font-weight: 800;
    text-align: center;
    background: linear-gradient(135deg, #f97316 0%, #ec4899 50%, #8b5cf6 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    line-height: 1.2;
    margin-bottom: 0.3rem;
}
.hero-subtitle {
    text-align: center;
    color: #6b7280;
    font-size: 1rem;
    margin-bottom: 1.5rem;
}


.sidebar-section {
    color: #f97316;
    font-weight: 700;
    font-size: 0.8rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-top: 1rem;
    margin-bottom: 0.4rem;
}

.budget-low    { background:#1a3a1a; color:#4ade80; border:1px solid #16a34a; }
.budget-mod    { background:#1a2a3f; color:#60a5fa; border:1px solid #2563eb; }
.budget-high   { background:#3a1a2a; color:#f472b6; border:1px solid #db2777; }
.budget-pill {
    display: inline-block;
    padding: 0.2rem 0.8rem;
    border-radius: 999px;
    font-size: 0.8rem;
    font-weight: 600;
    margin-top: 0.4rem;
}


.agent-panel {
    display: flex;
    gap: 1rem;
    margin: 1rem 0;
}
.agent-card {
    flex: 1;
    background: #161b27;
    border: 1px solid #2a2f3e;
    border-radius: 12px;
    padding: 1rem 1.2rem;
    transition: all 0.3s ease;
}
.agent-card.active  { border-color: #f97316; box-shadow: 0 0 12px rgba(249,115,22,0.2); }
.agent-card.done    { border-color: #22c55e; box-shadow: 0 0 8px rgba(34,197,94,0.15); }
.agent-card.waiting { border-color: #2a2f3e; opacity: 0.6; }
.agent-name { font-weight: 700; color: #f9fafb; font-size: 0.95rem; }
.agent-role { font-size: 0.75rem; color: #9ca3af; margin-top: 2px; }
.agent-status { font-size: 0.82rem; margin-top: 0.5rem; }
.status-waiting  { color: #6b7280; }
.status-active   { color: #f97316; }
.status-done     { color: #22c55e; }

.stProgress > div > div { background: linear-gradient(90deg, #f97316, #ec4899) !important; }


.itinerary-box {
    background: #161b27;
    border: 1px solid #2a2f3e;
    border-radius: 16px;
    padding: 2rem 2.5rem;
    line-height: 1.8;
}
.itinerary-box h1, .itinerary-box h2 { color: #f97316 !important; }
.itinerary-box h3 { color: #ec4899 !important; }

/* ---- Download button ---- */
.stDownloadButton > button {
    background: linear-gradient(135deg, #f97316, #ec4899) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
    padding: 0.6rem 1.5rem !important;
    transition: opacity 0.2s !important;
}
.stDownloadButton > button:hover { opacity: 0.88; }

/* ---- Placeholder ---- */
.placeholder {
    text-align: center;
    padding: 5rem 2rem;
    color: #374151;
}
.placeholder-icon { font-size: 5rem; margin-bottom: 1rem; }
.placeholder-text { font-size: 1.1rem; }

/* ---- API warning ---- */
.api-warn {
    background: #2d1a00;
    border: 1px solid #f97316;
    border-radius: 10px;
    padding: 1rem 1.2rem;
    color: #fed7aa;
    font-size: 0.9rem;
}
</style>
""", unsafe_allow_html=True)
def check_api_key() -> bool:
    key = os.getenv("GROQ_API_KEY", "").strip()
    return bool(key) and key != "your_groq_api_key_here"


def fetch_destination_image(destination: str):
    """Try to fetch a travel photo from Unsplash."""
    try:
        query = destination.split(",")[0].strip().replace(" ", "+")
        url = f"https://source.unsplash.com/1200x500/?{query},travel,landmark"
        resp = requests.get(url, timeout=10)
        ct = resp.headers.get("Content-Type", "")
        if resp.status_code == 200 and "image" in ct:
            return Image.open(BytesIO(resp.content))
    except Exception:
        pass
    return None


def agent_card(name: str, role: str, status: str, state: str) -> str:
    """Render an HTML agent status card."""
    state_class = {"waiting": "waiting", "active": "active", "done": "done"}.get(state, "waiting")
    status_class = {"waiting": "status-waiting", "active": "status-active", "done": "status-done"}.get(state, "status-waiting")
    return f"""
    <div class="agent-card {state_class}">
        <div class="agent-name">{name}</div>
        <div class="agent-role">{role}</div>
        <div class="agent-status {status_class}">{status}</div>
    </div>
    """



if "result"    not in st.session_state: st.session_state.result    = None
if "running"   not in st.session_state: st.session_state.running   = False
if "error"     not in st.session_state: st.session_state.error     = None
if "last_dest" not in st.session_state: st.session_state.last_dest = ""



with st.sidebar:
    st.markdown("### ✈️ Trip Configuration")
    st.divider()

  
    if check_api_key():
        st.success("✅ GroqCloud API key detected")
    else:
        st.markdown("""
        <div class="api-warn">
            ⚠️ <b>GROQ_API_KEY not set</b><br>
            Create a <code>.env</code> file with your key from
            <a href="https://console.groq.com" target="_blank">console.groq.com</a>
        </div>
        """, unsafe_allow_html=True)
      

    st.divider()

    st.markdown('<div class="sidebar-section">📍 Destination</div>', unsafe_allow_html=True)
    destination_input = st.text_input(
        "Where are you going?",
        value="Paris, France",
        placeholder="e.g. Kyoto, Japan",
        label_visibility="collapsed",
    )

  
    st.markdown('<div class="sidebar-section">🗓️ Duration</div>', unsafe_allow_html=True)
    duration_input = st.slider("Trip length (days)", min_value=1, max_value=21, value=5)

  
    st.markdown('<div class="sidebar-section">💰 Budget Level</div>', unsafe_allow_html=True)
    budget_options = {
        "Low": "🪙  Low",
        "Moderate": "💳  Moderate",
        "High": "💎  High",
    }
    budget_choice = st.radio(
        "Budget",
        list(budget_options.keys()),
        index=1,
        format_func=lambda x: budget_options[x],
        label_visibility="collapsed",
    )
    budget = budget_choice

    pill_class = {"Low": "budget-low", "Moderate": "budget-mod", "High": "budget-high"}[budget]
    st.markdown(f'<div class="budget-pill {pill_class}">{budget} Budget</div>', unsafe_allow_html=True)

    st.divider()
    generate_btn = st.button(
        "🚀  Generate My Itinerary",
        type="primary",
        use_container_width=True,
        disabled=st.session_state.running or not check_api_key(),
    )

    st.markdown("""
    <div style="color:#4b5563; font-size:0.75rem; margin-top:1rem; text-align:center;">
        Powered by <b>Llama 3.3 70B</b><br>via <b>GroqCloud</b> ⚡
    </div>
    """, unsafe_allow_html=True)


if os.path.exists("logo.png"):
    st.image("logo.png", width=100)

st.markdown('<div class="hero-title">🌍 Multi-Agent Hospitality Planner</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="hero-subtitle">Powered by AI Researcher & Writer Agents via GroqCloud — crafting your perfect trip</div>',
    unsafe_allow_html=True,
)




if generate_btn and destination_input.strip():
    st.session_state.result    = None
    st.session_state.error     = None
    st.session_state.running   = True
    st.session_state.last_dest = destination_input

   
    with st.spinner("Fetching destination photo..."):
        img_obj = fetch_destination_image(destination_input)
    if img_obj:
        st.image(img_obj, caption=f"📸 {destination_input}", use_container_width=True)

    st.divider()
    st.markdown("### 🤖 Agent Activity")

    col_r, col_w = st.columns(2)

    with col_r:
        researcher_slot = st.empty()
    with col_w:
        writer_slot = st.empty()

    progress_bar  = st.progress(0, text="Initialising agents…")
    status_slot   = st.empty()

    def render_cards(r_state, r_status, w_state, w_status):
        researcher_slot.markdown(
            agent_card("🔍 Senior Travel Researcher",
                       "Searches the web for destination intel",
                       r_status, r_state),
            unsafe_allow_html=True,
        )
        writer_slot.markdown(
            agent_card("✍️  Travel Itinerary Writer",
                       "Crafts your polished markdown itinerary",
                       w_status, w_state),
            unsafe_allow_html=True,
        )

    render_cards("waiting", "⏳ Waiting to start…", "waiting", "⏳ Waiting for research…")

  
    try:
        tasks_orchestrator = HospitalityTasks()

        progress_bar.progress(10, text="🔍 Researcher gathering data…")
        render_cards("active", "🟠 Searching the web…", "waiting", "⏳ Waiting for research…")
        status_slot.info(f"**Phase 1 / 2** — Researcher is analysing **{destination_input}**…")
      
        research_output = tasks_orchestrator.factory.run_researcher(destination_input, str(duration_input), budget)
        
        progress_bar.progress(60, text="✍️ Writer crafting your itinerary…")
        render_cards("done", "✅ Research complete!", "active", "🟠 Writing itinerary…")
        status_slot.info("**Phase 2 / 2** — Writer is building a beautiful day-by-day itinerary…")
        
        final_output = tasks_orchestrator.factory.run_writer(research_output, destination_input, str(duration_input), budget)
        
        st.session_state.result = final_output
        progress_bar.progress(100, text="✅ Done!")
        render_cards("done", "✅ Research complete!", "done", "✅ Itinerary written!")
        status_slot.success("**✅ Your itinerary is ready!**")

    except Exception as exc:
        st.session_state.error = str(exc)
        progress_bar.empty()
        status_slot.empty()

    st.session_state.running = False



if st.session_state.result:
    res_text = st.session_state.result
    dest_name = st.session_state.last_dest

    st.divider()
    st.markdown(f"### 🗺️ Your Itinerary for {dest_name}")

    st.markdown('<div class="itinerary-box">', unsafe_allow_html=True)
    st.markdown(res_text)
    st.markdown("</div>", unsafe_allow_html=True)

    st.divider()

    safe_fname = dest_name.lower().replace(", ", "_").replace(" ", "_").replace("'", "")
    fname = f"{safe_fname}_itinerary.md"

    st.download_button(
        label="📥 Download Itinerary (Markdown)",
        data=res_text,
        file_name=fname,
        mime="text/markdown",
        use_container_width=True,
    )

elif st.session_state.error:
    st.error(f"❌ An error occurred:\n\n{st.session_state.error}")

else:
    # Placeholder
    st.markdown("""
    <div class="placeholder">
        <div class="placeholder-icon">✈️</div>
        <div class="placeholder-text">
            Configure your trip in the sidebar and click<br>
            <b>Generate My Itinerary</b> to let the AI agents get to work!
        </div>
    </div>
    """, unsafe_allow_html=True)

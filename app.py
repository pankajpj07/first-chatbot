"""Hopscotch Support - v2: raw OpenAI SDK + glue code, modern UI, dark/light mode."""
import html
import json
import os
import time
from pathlib import Path
from string import Template

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

st.set_page_config(
    page_title="Hopscotch Support",
    page_icon="🛍️",
    layout="centered",
    initial_sidebar_state="expanded",
)
ss = st.session_state

# =============================================================================
# 0. THEME (dark / light) - all colors live in CSS variables
# =============================================================================
THEMES = {
    "dark": dict(
        scheme="dark", bg="#0b0b14", text="#eceaf7", muted="#9b98b5",
        card="rgba(255,255,255,0.05)", border="rgba(255,255,255,0.10)",
        user_bubble="linear-gradient(135deg, rgba(139,92,246,0.30), rgba(255,106,176,0.22))",
        user_border="rgba(167,139,250,0.35)", input_bg="rgba(20,19,36,0.88)",
        side_bg="rgba(14,13,26,0.92)", pop_bg="#17162a", shadow="rgba(0,0,0,0.35)",
        a1="rgba(139,92,246,0.28)", a2="rgba(255,106,176,0.20)", a3="rgba(56,189,248,0.16)",
        hover_bg="rgba(139,92,246,0.14)", hover_text="#ffffff", avatar_user="#2a2745",
        pre_bg="rgba(0,0,0,0.35)", scroll="rgba(255,255,255,0.15)",
    ),
    "light": dict(
        scheme="light", bg="#f4f3ff", text="#1c1b2e", muted="#6b6885",
        card="rgba(255,255,255,0.75)", border="rgba(60,40,120,0.10)",
        user_bubble="linear-gradient(135deg, rgba(139,92,246,0.16), rgba(255,106,176,0.14))",
        user_border="rgba(139,92,246,0.30)", input_bg="rgba(255,255,255,0.94)",
        side_bg="rgba(255,255,255,0.88)", pop_bg="#ffffff", shadow="rgba(80,60,160,0.14)",
        a1="rgba(139,92,246,0.20)", a2="rgba(255,106,176,0.16)", a3="rgba(56,189,248,0.14)",
        hover_bg="rgba(139,92,246,0.10)", hover_text="#4c1d95", avatar_user="#e3defa",
        pre_bg="rgba(60,40,120,0.06)", scroll="rgba(60,40,120,0.20)",
    ),
}

CSS = Template("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

:root {
  color-scheme: ${scheme};
  --bg: ${bg}; --text: ${text}; --muted: ${muted};
  --card: ${card}; --border: ${border}; --shadow: ${shadow};
  --pink: #ff6ab0; --violet: #8b5cf6; --blue: #38bdf8;
  --grad: linear-gradient(135deg, #ff6ab0 0%, #8b5cf6 55%, #38bdf8 100%);
}
html, body, [class*="css"], .stApp, .stMarkdown, button, textarea, input {
  font-family: 'Plus Jakarta Sans', sans-serif !important;
}
.stApp {
  background:
    radial-gradient(900px 500px at 8% -10%, ${a1}, transparent 60%),
    radial-gradient(800px 500px at 100% 0%, ${a2}, transparent 60%),
    radial-gradient(700px 500px at 50% 110%, ${a3}, transparent 60%),
    var(--bg);
  color: var(--text);
}
.stApp p, .stApp li, .stApp span, .stApp label, .stApp h1, .stApp h2, .stApp h3,
[data-testid="stWidgetLabel"] p, [data-testid="stExpander"] summary * { color: var(--text); }
/* Hide only the junk. Do NOT hide stToolbar or stHeader: the sidebar reopen button lives there. */
#MainMenu, footer, [data-testid="stDecoration"], [data-testid="stAppDeployButton"],
[data-testid="stMainMenu"], .stDeployButton { display: none !important; }
header[data-testid="stHeader"] { background: transparent !important; visibility: visible !important; z-index: 999990; }

/* Sidebar open/close buttons: always visible, themed, on top */
[data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"],
[data-testid="stExpandSidebarButton"], [data-testid="stSidebarCollapseButton"] {
  visibility: visible !important; opacity: 1 !important; z-index: 999999;
}
[data-testid="stSidebarCollapsedControl"] button, [data-testid="collapsedControl"] button,
[data-testid="stExpandSidebarButton"], [data-testid="stSidebarCollapseButton"] button {
  background: var(--card) !important; border: 1px solid var(--border) !important;
  border-radius: 12px !important; color: var(--text) !important; backdrop-filter: blur(14px);
  box-shadow: 0 6px 18px var(--shadow);
}
[data-testid="stSidebarCollapsedControl"] svg, [data-testid="collapsedControl"] svg,
[data-testid="stExpandSidebarButton"] svg, [data-testid="stSidebarCollapseButton"] svg {
  color: var(--text) !important; fill: currentColor !important;
}
[data-testid="stSidebarCollapsedControl"] button:hover, [data-testid="collapsedControl"] button:hover,
[data-testid="stExpandSidebarButton"]:hover, [data-testid="stSidebarCollapseButton"] button:hover {
  border-color: var(--violet) !important; background: ${hover_bg} !important;
}
.block-container { padding-top: 1.4rem; padding-bottom: 7rem; max-width: 840px; }

/* Hero */
.hero {
  display: flex; align-items: center; gap: 16px; padding: 20px 22px; margin-bottom: 14px;
  background: var(--card); border: 1px solid var(--border); border-radius: 24px;
  backdrop-filter: blur(18px); box-shadow: 0 12px 40px var(--shadow);
}
.hero-logo {
  width: 58px; height: 58px; border-radius: 19px; display: grid; place-items: center; font-size: 29px;
  background: var(--grad); box-shadow: 0 8px 24px rgba(139,92,246,0.45);
}
.hero-title {
  font-size: 1.6rem; font-weight: 800; letter-spacing: -0.02em; line-height: 1.1;
  background: var(--grad); -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
}
.hero-sub { color: var(--muted) !important; font-size: 0.88rem; margin-top: 4px; }
.status {
  margin-left: auto; display: flex; align-items: center; gap: 8px; padding: 6px 12px; border-radius: 999px;
  font-size: 0.78rem; font-weight: 600; background: rgba(16,185,129,0.12);
  color: #10b981 !important; border: 1px solid rgba(16,185,129,0.35);
}
.status * { color: #10b981 !important; }
.dot { width: 8px; height: 8px; border-radius: 50%; background: #10b981; animation: pulse 1.8s infinite; }
@keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(16,185,129,.7); } 70% { box-shadow: 0 0 0 9px rgba(16,185,129,0); } 100% { box-shadow: 0 0 0 0 rgba(16,185,129,0); } }

/* Stat chips */
.stats { display: flex; gap: 10px; margin-bottom: 16px; flex-wrap: wrap; }
.stat {
  flex: 1; min-width: 120px; padding: 10px 14px; border-radius: 16px;
  background: var(--card); border: 1px solid var(--border);
}
.stat b { display: block; font-size: 1.15rem; font-weight: 800; }
.stat span { font-size: 0.72rem; text-transform: uppercase; letter-spacing: .08em; color: var(--muted) !important; font-weight: 600; }

/* Welcome */
.welcome { text-align: center; padding: 26px 10px 6px; }
.welcome h2 { font-size: 1.75rem; font-weight: 800; letter-spacing: -0.02em; margin: 0 0 6px; }
.welcome p { color: var(--muted) !important; margin: 0 auto; max-width: 520px; }

/* Bubbles */
[data-testid="stChatMessage"] {
  background: var(--card); border: 1px solid var(--border); border-radius: 22px;
  padding: 14px 18px; margin-bottom: 12px; backdrop-filter: blur(14px);
  box-shadow: 0 6px 22px var(--shadow); animation: rise .35s ease both;
}
@keyframes rise { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
  background: ${user_bubble}; border-color: ${user_border};
}
[data-testid="stChatMessageAvatarAssistant"] { background: var(--grad) !important; }
[data-testid="stChatMessageAvatarUser"] { background: ${avatar_user} !important; }
[data-testid="stChatMessage"] p { line-height: 1.65; margin-bottom: 0.4rem; }
[data-testid="stChatMessage"] code { background: ${pre_bg}; border-radius: 6px; padding: 1px 6px; }

.badge {
  display: inline-flex; align-items: center; gap: 8px; margin-top: 8px; padding: 6px 12px; border-radius: 999px;
  font-size: 0.78rem; font-weight: 600; background: rgba(245,158,11,0.14);
  color: #d97706 !important; border: 1px solid rgba(245,158,11,0.40);
}
.meta { margin-top: 8px; font-size: 0.74rem; color: var(--muted) !important; }

/* Typing */
.typing { display: inline-flex; gap: 6px; padding: 6px 2px; }
.typing span { width: 8px; height: 8px; border-radius: 50%; background: var(--violet); animation: bounce 1.2s infinite ease-in-out; }
.typing span:nth-child(2) { animation-delay: .15s; background: var(--pink); }
.typing span:nth-child(3) { animation-delay: .30s; background: var(--blue); }
@keyframes bounce { 0%, 80%, 100% { transform: scale(.6); opacity: .5; } 40% { transform: scale(1.1); opacity: 1; } }

/* Buttons */
.stButton > button, .stDownloadButton > button {
  width: 100%; text-align: left; white-space: normal; height: auto; padding: 12px 16px; border-radius: 16px;
  background: var(--card); color: var(--text); border: 1px solid var(--border);
  transition: all .2s ease; font-weight: 500; line-height: 1.4;
}
.stButton > button p, .stDownloadButton > button p { color: inherit !important; }
.stButton > button:hover, .stDownloadButton > button:hover {
  transform: translateY(-2px); border-color: rgba(139,92,246,0.7); background: ${hover_bg};
  box-shadow: 0 10px 28px rgba(139,92,246,0.25); color: ${hover_text};
}
.stButton > button:focus:not(:active) { border-color: var(--violet); color: ${hover_text}; }

/* Inputs */
[data-testid="stBottom"] > div { background: transparent !important; }
[data-testid="stChatInput"] {
  background: ${input_bg} !important; border: 1px solid var(--border) !important; border-radius: 22px !important;
  backdrop-filter: blur(18px); box-shadow: 0 10px 40px var(--shadow);
}
[data-testid="stChatInput"]:focus-within { border-color: var(--violet) !important; box-shadow: 0 0 0 3px rgba(139,92,246,0.25), 0 10px 40px var(--shadow); }
[data-testid="stChatInput"] textarea { color: var(--text) !important; background: transparent !important; }
[data-testid="stChatInput"] button { background: var(--grad) !important; border-radius: 12px !important; color: #fff !important; }
[data-baseweb="select"] > div, [data-baseweb="input"], [data-baseweb="base-input"], .stNumberInput input {
  background: var(--card) !important; color: var(--text) !important; border-color: var(--border) !important; border-radius: 12px !important;
}
[data-baseweb="select"] * { color: var(--text) !important; }
[data-baseweb="popover"] ul, [data-baseweb="menu"] { background: ${pop_bg} !important; }
[data-baseweb="popover"] li * { color: var(--text) !important; }

/* Sidebar */
[data-testid="stSidebar"] { background: ${side_bg}; border-right: 1px solid var(--border); backdrop-filter: blur(20px); }
.side-title { font-size: 0.72rem; text-transform: uppercase; letter-spacing: .12em; color: var(--muted) !important; font-weight: 700; margin: 18px 0 8px; }
[data-testid="stExpander"] { background: var(--card); border: 1px solid var(--border) !important; border-radius: 16px; }
pre.raw {
  max-height: 260px; overflow: auto; font-size: 0.72rem; line-height: 1.45; padding: 10px;
  background: ${pre_bg}; border-radius: 10px; color: var(--text); white-space: pre-wrap; word-break: break-word;
}
::-webkit-scrollbar { width: 8px; }
::-webkit-scrollbar-thumb { background: ${scroll}; border-radius: 8px; }
</style>
""")


def apply_theme() -> None:
    mode = "dark" if ss.get("dark", True) else "light"
    st.markdown(CSS.substitute(**THEMES[mode]), unsafe_allow_html=True)


apply_theme()

# =============================================================================
# 1. API key + client + models
# =============================================================================
load_dotenv()
api_key = os.getenv("OPENROUTER_API_KEY")
if not api_key:
    st.error("OPENROUTER_API_KEY not found. Copy `.env.example` to `.env`, "
             "paste your key from https://openrouter.ai/keys, then restart the app.")
    st.stop()

# OpenRouter speaks the OpenAI wire format, so we reuse the OpenAI SDK.
client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")

# Edit this list freely, any OpenRouter model id works.
MODELS = [
    "openai/gpt-4o-mini",
    "openai/gpt-4o",
    "anthropic/claude-3.5-haiku",
    "google/gemini-2.0-flash-001",
    "meta-llama/llama-3.3-70b-instruct",
]

# =============================================================================
# 2. System prompt
# =============================================================================
POLICY = (Path(__file__).parent / "hopscotch_policy.md").read_text(encoding="utf-8")
SYSTEM_PROMPT = f"""You are Hopscotch's customer support assistant for a premium kids' fashion
retailer in Mumbai. Be warm and concise.

=== RETURN POLICY ===
{POLICY}
=== END POLICY ===

Rules:
- Answer ONLY from the policy above. Never invent rules.
- If you need the delivery date, the item's condition, or the order value, ask for it.
- For ANY Section 4 case (child safety, skin reaction/allergy, order above INR 5,000,
  unclear facts, or uncertainty between defect and misuse) do NOT decide. Tell the
  customer their case will be passed to a human agent.
- For defect claims, ask the customer for photo evidence.
"""

# =============================================================================
# 3. State (the messages list IS the memory, resent in full every turn)
# =============================================================================
ss.setdefault("messages", [{"role": "system", "content": SYSTEM_PROMPT}])
ss.setdefault("pending", None)   # prompt queued by a button click
ss.setdefault("regen", False)
ss.setdefault("meta", {})        # {message index: {secs, words, model}}, never sent to the API

EXAMPLES = [
    ("👗", "Return a dress", "I bought a dress 10 days ago, never worn, tags on. Can I return it?"),
    ("👟", "Peeling sneakers", "The sole of my son's sneakers peeled off after 3 weeks of school"),
    ("⚠️", "Safety issue", "A button came off and my toddler nearly put it in his mouth"),
    ("💸", "High value refund", "My order was ₹7,200, I want a refund"),
]
CONDITIONS = ["Not specified", "Unworn, tags on", "Worn once", "Washed", "Damaged or defective"]


def escalated(text: str) -> bool:
    return "human agent" in text.lower()


def reset_chat() -> None:
    ss.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    ss.meta = {}
    ss.pending = None
    for k in [k for k in ss.keys() if k.startswith("fb_")]:
        del ss[k]


def case_context() -> str:
    """Optional sidebar form, appended to the system prompt at call time."""
    if not ss.get("ctx_on"):
        return ""
    lines = []
    if ss.get("ctx_value", 0) > 0:
        lines.append(f"- Order value: INR {ss.ctx_value:,}")
    if ss.get("ctx_days", 0) > 0:
        lines.append(f"- Days since delivery: {ss.ctx_days}")
    if ss.get("ctx_cond", CONDITIONS[0]) != CONDITIONS[0]:
        lines.append(f"- Item condition: {ss.ctx_cond}")
    if not lines:
        return ""
    return ("\n\nCase details entered in the support console "
            "(customer-stated, unverified):\n" + "\n".join(lines))


def api_messages() -> list:
    """Exactly what gets sent to the model each turn."""
    history = [m for m in ss.messages if m["role"] != "system"]
    return [{"role": "system", "content": SYSTEM_PROMPT + case_context()}] + history


def transcript_md() -> str:
    out = ["# Hopscotch Support chat", ""]
    for m in ss.messages:
        if m["role"] == "user":
            out.append(f"**Customer:** {m['content']}\n")
        elif m["role"] == "assistant":
            out.append(f"**Hopscotch:** {m['content']}\n")
    return "\n".join(out)


def stream_reply(messages: list, model: str, temperature: float, slot):
    """Yield text chunks (SDK-specific parsing). Clears the typing dots on first token."""
    stream = client.chat.completions.create(
        model=model, messages=messages, temperature=temperature, stream=True
    )
    first = True
    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta.content
        if delta:
            if first:
                slot.empty()
                first = False
            yield delta


# =============================================================================
# 4. Handle input BEFORE drawing anything (chat_input still pins to the bottom)
# =============================================================================
typed = st.chat_input("Ask about returns, refunds, defects…")

if ss.regen:
    ss.regen = False
    if ss.messages[-1]["role"] == "assistant":
        idx = len(ss.messages) - 1
        ss.messages.pop()
        ss.meta.pop(idx, None)
        ss.pop(f"fb_{idx}", None)

user_text = typed or ss.pending
ss.pending = None
if user_text:
    ss.messages.append({"role": "user", "content": user_text})

# =============================================================================
# 5. Sidebar
# =============================================================================
with st.sidebar:
    if st.button("🧹  New conversation", key="reset"):
        reset_chat()
        st.rerun()

    st.markdown('<div class="side-title">Model</div>', unsafe_allow_html=True)
    st.selectbox("Model", MODELS, key="model", label_visibility="collapsed")
    st.slider("Creativity (temperature)", 0.0, 1.0, 0.3, 0.05, key="temp")

    st.markdown('<div class="side-title">Case details</div>', unsafe_allow_html=True)
    st.toggle("Attach case details to the prompt", key="ctx_on")
    if ss.get("ctx_on"):
        st.number_input("Order value (INR)", min_value=0, step=100, key="ctx_value")
        st.number_input("Days since delivery (0 = unknown)", min_value=0, step=1, key="ctx_days")
        st.selectbox("Item condition", CONDITIONS, key="ctx_cond")

    st.markdown('<div class="side-title">Quick prompts</div>', unsafe_allow_html=True)
    for i, (icon, label, prompt) in enumerate(EXAMPLES):
        if st.button(f"{icon}  {label}", key=f"side_{i}"):
            ss.pending = prompt
            st.rerun()

    st.markdown('<div class="side-title">Tools</div>', unsafe_allow_html=True)
    st.download_button(
        "⬇️  Export chat (.md)", data=transcript_md(), file_name="hopscotch-chat.md",
        mime="text/markdown", disabled=len(ss.messages) <= 1,
    )
    with st.expander("📄 Return policy"):
        st.markdown(POLICY)
    with st.expander("🔍 Raw messages sent to the model"):
        raw = html.escape(json.dumps(api_messages(), indent=2, ensure_ascii=False))
        st.markdown(f'<pre class="raw">{raw}</pre>', unsafe_allow_html=True)
        st.caption(f"{len(api_messages())} messages in the list")

# =============================================================================
# 6. Header: theme switch, hero, live stats
# =============================================================================
_, tcol = st.columns([3, 1])
with tcol:
    dark_now = ss.get("dark", True)
    st.toggle(f"{'🌙' if dark_now else '☀️'} {'Dark' if dark_now else 'Light'}", key="dark", value=True)

st.markdown("""
<div class="hero">
  <div class="hero-logo">🛍️</div>
  <div>
    <div class="hero-title">Hopscotch Support</div>
    <div class="hero-sub">Returns, refunds and defects for premium kids' fashion</div>
  </div>
  <div class="status"><span class="dot"></span>Online</div>
</div>
""", unsafe_allow_html=True)

n_user = sum(1 for m in ss.messages if m["role"] == "user")
if n_user:
    n_esc = sum(1 for m in ss.messages if m["role"] == "assistant" and escalated(m["content"]))
    lat = [v["secs"] for v in ss.meta.values()]
    avg = f"{sum(lat) / len(lat):.1f}s" if lat else "n/a"
    st.markdown(
        f'<div class="stats">'
        f'<div class="stat"><b>{n_user}</b><span>Questions</span></div>'
        f'<div class="stat"><b>{n_esc}</b><span>Handed to humans</span></div>'
        f'<div class="stat"><b>{avg}</b><span>Avg reply time</span></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

# =============================================================================
# 7. Empty state
# =============================================================================
if len(ss.messages) == 1:
    st.markdown("""
<div class="welcome">
  <h2>Hi there, how can we help? 👋</h2>
  <p>Ask about returns, refunds or product issues. Tap a suggestion or type your own question.</p>
</div>
""", unsafe_allow_html=True)
    st.write("")
    cols = st.columns(2)
    for i, (icon, label, prompt) in enumerate(EXAMPLES):
        with cols[i % 2]:
            if st.button(f"{icon}  **{label}**\n\n{prompt}", key=f"card_{i}"):
                ss.pending = prompt
                st.rerun()

# =============================================================================
# 8. Render history
# =============================================================================
last_idx = len(ss.messages) - 1
for i, m in enumerate(ss.messages):
    if m["role"] == "system":
        continue
    with st.chat_message(m["role"], avatar="🛍️" if m["role"] == "assistant" else "🙂"):
        st.markdown(m["content"])
        if m["role"] == "assistant":
            if escalated(m["content"]):
                st.markdown('<span class="badge">🧑‍💼 Passed to a human agent</span>', unsafe_allow_html=True)
            info = ss.meta.get(i)
            if info:
                st.markdown(
                    f'<div class="meta">⏱ {info["secs"]:.1f}s · {info["words"]} words · '
                    f'{html.escape(info["model"].split("/")[-1])}</div>',
                    unsafe_allow_html=True,
                )
    # Actions under the latest assistant reply
    if i == last_idx and m["role"] == "assistant":
        c1, c2, _ = st.columns([1.3, 1.2, 3])
        with c1:
            if st.button("🔄  Regenerate", key="regen_btn"):
                ss.regen = True
                st.rerun()
        with c2:
            if hasattr(st, "feedback"):
                st.feedback("thumbs", key=f"fb_{i}")

# =============================================================================
# 9. One "loop iteration": last message is the user's -> stream the reply
# =============================================================================
if ss.messages[-1]["role"] == "user":
    ok = False
    with st.chat_message("assistant", avatar="🛍️"):
        slot = st.empty()
        slot.markdown('<div class="typing"><span></span><span></span><span></span></div>',
                      unsafe_allow_html=True)
        model = ss.get("model", MODELS[0])
        started = time.time()
        try:
            reply = st.write_stream(
                stream_reply(api_messages(), model, ss.get("temp", 0.3), slot)
            )
            ss.messages.append({"role": "assistant", "content": reply})
            ss.meta[len(ss.messages) - 1] = {
                "secs": time.time() - started,
                "words": len(reply.split()),
                "model": model,
            }
            ok = True
        except Exception as e:
            slot.empty()
            st.error(f"Something went wrong calling the model: {e}")
            ss.messages.pop()  # drop the unanswered user turn
    if ok:
        st.rerun()  # redraw so the action row, stats and badge appear
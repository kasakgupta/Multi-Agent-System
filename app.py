"""
ResearchFlow AI — Streamlit UI for the existing multi-agent research pipeline.

This file only renders and orchestrates the UI. It does not modify, redesign,
or reimplement any backend logic. It calls the single existing entry point:

    pipeline.run_research_pipeline(topic: str) -> dict

which returns a dict with keys: search_results, scraped_content, report, feedback.
See the notes at the end of the chat response for the assumptions made where
pipeline.py's output types were ambiguous.
"""

import os
import io
import time
import contextlib
import threading
from datetime import datetime
from urllib.parse import urlparse
import re


# --- Backend import -----------------------------------------------------
# The real pipeline is the source of truth. If it can't be imported, we stop
# with a clear message instead of guessing at a fake interface.
import streamlit as st
import os

# Load API keys from Streamlit Cloud Secrets
if "GROQ_API_KEY" in st.secrets:
    os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]

if "TAVILY_API_KEY" in st.secrets:
    os.environ["TAVILY_API_KEY"] = st.secrets["TAVILY_API_KEY"]

try:
    from pipeline import run_research_pipeline
except Exception as e:  # noqa: BLE001
    st.set_page_config(page_title="ResearchFlow AI", layout="wide")
    st.error(
        "Could not import `run_research_pipeline` from pipeline.py. "
        "Make sure app.py sits next to pipeline.py, agents.py and tools.py, "
        "and that your virtual environment is active."
    )
    with st.expander("Technical details"):
        st.code(str(e))
    st.stop()


# =========================================================================
# CONFIG
# =========================================================================

st.set_page_config(
    page_title="ResearchFlow AI",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded",
)

PIPELINE_STAGES = [
    ("Search", "Search Agent is gathering information...", "step 1"),
    ("Read", "Reader Agent is scraping the URLs...", "step 2"),
    ("Write", "Writer Chain is generating the research report...", "step 3"),
    ("Critique", "Critic Chain is evaluating the research report...", "step 4"),
]

EXAMPLE_QUERIES = [
    "Impact of generative AI on software engineering jobs in 2026",
    "How are AI agents changing enterprise SaaS products?",
    "Latest developments in on-device AI models",
    "Trends in AI-driven venture capital funding",
]


# =========================================================================
# STYLES
# =========================================================================

def inject_css():
    st.markdown(
        """
        <style>
        :root {
            --bg: #0b0e14;
            --panel: #12161f;
            --panel-border: #232a38;
            --text: #e6e9ef;
            --text-dim: #8b93a7;
            --accent: #5eead4;
            --accent-dim: #2dd4bf33;
            --danger: #f87171;
        }

        html, body, [class*="css"] { font-family: 'Inter', -apple-system, sans-serif; }
        .stApp { background-color: var(--bg); color: var(--text); }

        #MainMenu, footer, header { visibility: hidden; }

        section[data-testid="stSidebar"] {
            background-color: var(--panel);
            border-right: 1px solid var(--panel-border);
        }

        .rf-brand {
            font-size: 1.15rem;
            font-weight: 700;
            letter-spacing: 0.02em;
            color: var(--text);
            margin-bottom: 0.1rem;
        }
        .rf-brand-sub {
            font-size: 0.8rem;
            color: var(--text-dim);
            margin-bottom: 1.2rem;
        }

        .rf-hero-title {
            font-size: 2.4rem;
            font-weight: 800;
            letter-spacing: -0.02em;
            margin-bottom: 0.1rem;
        }
        .rf-hero-sub {
            font-size: 1.05rem;
            color: var(--text-dim);
            margin-bottom: 0.3rem;
        }
        .rf-hero-tagline {
            font-size: 0.9rem;
            color: var(--accent);
            font-weight: 500;
            margin-bottom: 1.6rem;
            letter-spacing: 0.02em;
        }

        .rf-card {
            background-color: var(--panel);
            border: 1px solid var(--panel-border);
            border-radius: 10px;
            padding: 1.1rem 1.3rem;
            margin-bottom: 0.8rem;
        }

        .rf-source-card {
            background-color: var(--panel);
            border: 1px solid var(--panel-border);
            border-left: 3px solid var(--accent);
            border-radius: 8px;
            padding: 0.8rem 1rem;
            margin-bottom: 0.6rem;
            font-size: 0.9rem;
        }
        .rf-source-domain {
            color: var(--accent);
            font-weight: 600;
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.03em;
        }
        .rf-source-url a { color: var(--text-dim); text-decoration: none; word-break: break-all; }
        .rf-source-url a:hover { color: var(--accent); }

        .rf-status-row { display: flex; align-items: center; gap: 0.5rem; font-size: 0.85rem; margin-bottom: 0.35rem; }
        .rf-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
        .rf-dot-ok { background-color: var(--accent); }
        .rf-dot-bad { background-color: var(--danger); }

        .rf-stage-line { font-size: 0.92rem; margin-bottom: 0.45rem; }
        .rf-stage-done { color: var(--accent); }
        .rf-stage-active { color: var(--text); font-weight: 600; }
        .rf-stage-pending { color: var(--text-dim); }

        .rf-agent-node {
            background-color: var(--panel);
            border: 1px solid var(--panel-border);
            border-radius: 8px;
            padding: 0.6rem 1rem;
            margin-bottom: 0.2rem;
            font-weight: 600;
            font-size: 0.88rem;
            letter-spacing: 0.02em;
        }
        .rf-agent-arrow { color: var(--text-dim); margin: 0.1rem 0 0.1rem 1.3rem; font-size: 0.9rem; }

        div.stButton > button {
            background-color: var(--accent);
            color: #0b0e14;
            border: none;
            font-weight: 600;
            border-radius: 8px;
        }
        div.stButton > button:hover { background-color: #7ff3e0; color: #0b0e14; }

        .rf-chip button {
            background-color: var(--panel) !important;
            color: var(--text-dim) !important;
            border: 1px solid var(--panel-border) !important;
            font-weight: 400 !important;
            font-size: 0.82rem !important;
        }
        .rf-chip button:hover { border-color: var(--accent) !important; color: var(--text) !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )


# =========================================================================
# HELPERS
# =========================================================================

def extract_text(value) -> str:
    """Best-effort conversion of a chain/agent return value to plain text.

    pipeline.py doesn't pin down whether writer_chain / critic_chain return
    a plain string or a LangChain message object, so this handles both
    without assuming a schema that doesn't exist in the backend.
    """
    if value is None:
        return ""
    if hasattr(value, "content"):
        try:
            return str(value.content)
        except Exception:  # noqa: BLE001
            pass
    if isinstance(value, dict):
        for key in ("content", "text", "output", "result"):
            if key in value:
                return extract_text(value[key])
        return str(value)
    return str(value)


def extract_urls(text: str):
    if not text:
        return []
    urls = re.findall(r'https?://[^\s\)\]\}"\'<>]+', text)
    # de-duplicate, keep order
    seen = set()
    out = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def domain_of(url: str) -> str:
    try:
        return urlparse(url).netloc or url
    except Exception:  # noqa: BLE001
        return url


def stage_progress_from_log(log_text: str):
    """Reads the real print() output from pipeline.py to know which stage
    has started. Nothing here is invented — it's parsed from actual stdout.
    """
    log_lower = (log_text or "").lower()
    last_started = -1
    for i, (_, _, marker) in enumerate(PIPELINE_STAGES):
        if marker in log_lower:
            last_started = i
    return last_started


def render_stage_markup(log_text: str, done: bool = False) -> str:
    last_started = stage_progress_from_log(log_text)
    lines = []
    for i, (name, desc, _) in enumerate(PIPELINE_STAGES):
        if done or i < last_started:
            cls, mark = "rf-stage-done", "●"
        elif i == last_started:
            cls, mark = "rf-stage-active", "●"
        else:
            cls, mark = "rf-stage-pending", "○"
        lines.append(
            f'<div class="rf-stage-line {cls}">{mark} <b>{name}</b> — {desc}</div>'
        )
    return "\n".join(lines)


# =========================================================================
# SESSION STATE
# =========================================================================

def init_state():
    defaults = {
        "topic_input": "",
        "result": None,
        "log": "",
        "error": None,
        "last_topic": "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def reset_state():
    st.session_state["topic_input"] = ""
    st.session_state["result"] = None
    st.session_state["log"] = ""
    st.session_state["error"] = None
    st.session_state["last_topic"] = ""


# =========================================================================
# SIDEBAR
# =========================================================================

def render_sidebar():
    with st.sidebar:
        st.markdown('<div class="rf-brand">ResearchFlow AI</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="rf-brand-sub">Autonomous multi-agent research system</div>',
            unsafe_allow_html=True,
        )

        st.markdown("**Pipeline agents**")
        for name, _, _ in PIPELINE_STAGES:
            st.markdown(f'<div class="rf-agent-node">{name}</div>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("**Research settings**")
        st.caption(
            "The backend currently accepts a single research topic string. "
            "No additional parameters are exposed by pipeline.py."
        )

        st.markdown("---")
        if st.button("↺ New Research", use_container_width=True):
            reset_state()
            st.rerun()

        st.markdown("---")
        st.markdown("**System status**")
        groq_ok = bool(os.getenv("GROQ_API_KEY"))
        tavily_ok = bool(os.getenv("TAVILY_API_KEY"))
        for label, ok in [("GROQ_API_KEY", groq_ok), ("TAVILY_API_KEY", tavily_ok)]:
            dot_cls = "rf-dot-ok" if ok else "rf-dot-bad"
            status_text = "configured" if ok else "missing"
            st.markdown(
                f'<div class="rf-status-row"><span class="rf-dot {dot_cls}"></span>'
                f'{label} — {status_text}</div>',
                unsafe_allow_html=True,
            )


# =========================================================================
# HEADER / EMPTY STATE
# =========================================================================

def render_header():
    st.markdown('<div class="rf-hero-title">ResearchFlow AI</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="rf-hero-sub">Multi-Agent Research &amp; Intelligence</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="rf-hero-tagline">Search. Analyze. Synthesize. Critique.</div>',
        unsafe_allow_html=True,
    )


def render_query_box():
    st.text_area(
        "Research query",
        key="topic_input",
        placeholder="Research the impact of generative AI on software engineering jobs in 2026...",
        label_visibility="collapsed",
        height=90,
    )
    start = st.button("Start Research →", type="primary")
    return start


def set_topic(topic: str):
    st.session_state["topic_input"] = topic


def render_empty_state():
    st.markdown(
        '<div class="rf-card">Turn a question into a research report. '
        'ResearchFlow AI runs a search agent, a reader agent, a writer chain '
        'and a critic chain end to end and returns a full report.</div>',
        unsafe_allow_html=True,
    )
    st.caption("Try an example:")
    cols = st.columns(2)
    for i, q in enumerate(EXAMPLE_QUERIES):
        with cols[i % 2]:
            st.markdown('<div class="rf-chip">', unsafe_allow_html=True)
            st.button(
                q,
                key=f"example_{i}",
                use_container_width=True,
                on_click=set_topic,
                args=(q,),
            )
            st.markdown("</div>", unsafe_allow_html=True)


# =========================================================================
# PIPELINE EXECUTION
# =========================================================================

def run_pipeline_with_live_log(topic: str):
    log_buffer = io.StringIO()
    result_box = {}
    error_box = {}

    def target():
        try:
            with contextlib.redirect_stdout(log_buffer):
                result_box["state"] = run_research_pipeline(topic)
        except Exception as e:  # noqa: BLE001
            error_box["error"] = e

    thread = threading.Thread(target=target, daemon=True)
    thread.start()

    with st.status("Running ResearchFlow pipeline...", expanded=True) as status:
        stage_area = st.empty()
        while thread.is_alive():
            stage_area.markdown(
                render_stage_markup(log_buffer.getvalue()), unsafe_allow_html=True
            )
            time.sleep(0.4)
        thread.join()
        log_text = log_buffer.getvalue()

        if "error" in error_box:
            stage_area.markdown(render_stage_markup(log_text), unsafe_allow_html=True)
            status.update(label="Research failed", state="error", expanded=True)
        else:
            stage_area.markdown(render_stage_markup(log_text, done=True), unsafe_allow_html=True)
            status.update(label="Research complete", state="complete", expanded=False)

    with st.expander("Execution log", expanded=False):
        st.code(log_text or "No output captured.", language=None)

    if "error" in error_box:
        raise error_box["error"]

    return result_box["state"], log_text


# =========================================================================
# RESULTS
# =========================================================================

def render_sources(search_results_text: str):
    urls = extract_urls(search_results_text)
    if not urls:
        st.caption("No source URLs were found in the search agent's output.")
        return
    for url in urls:
        st.markdown(
            f'<div class="rf-source-card">'
            f'<div class="rf-source-domain">{domain_of(url)}</div>'
            f'<div class="rf-source-url"><a href="{url}" target="_blank">{url}</a></div>'
            f"</div>",
            unsafe_allow_html=True,
        )


def render_agent_trace(state: dict):
    search_text = extract_text(state.get("search_results"))
    scraped_text = extract_text(state.get("scraped_content"))
    report_text = extract_text(state.get("report"))
    feedback_text = extract_text(state.get("feedback"))

    trace = [
        ("Search Agent", search_text),
        ("Reader Agent", scraped_text),
        ("Writer Chain", report_text),
        ("Critic Chain", feedback_text),
    ]

    for i, (name, content) in enumerate(trace):
        st.markdown(f'<div class="rf-agent-node">{name}</div>', unsafe_allow_html=True)
        with st.expander(f"View {name} output", expanded=False):
            st.markdown(content if content.strip() else "_No output returned._")
        if i < len(trace) - 1:
            st.markdown('<div class="rf-agent-arrow">↓</div>', unsafe_allow_html=True)


def render_results(state: dict, topic: str):
    report_text = extract_text(state.get("report"))
    feedback_text = extract_text(state.get("feedback"))
    search_text = extract_text(state.get("search_results"))

    tabs = st.tabs(["Report", "Quality Review", "Sources", "Agent Trace"])

    with tabs[0]:
        st.markdown(
            f'<div class="rf-card">{report_text if report_text.strip() else "_No report returned._"}</div>',
            unsafe_allow_html=True,
        )
        if report_text.strip():
            st.download_button(
                "Download Report",
                data=report_text,
                file_name=f"researchflow_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain",
            )

    with tabs[1]:
        st.markdown(
            f'<div class="rf-card">{feedback_text if feedback_text.strip() else "_No critic feedback returned._"}</div>',
            unsafe_allow_html=True,
        )

    with tabs[2]:
        render_sources(search_text)

    with tabs[3]:
        render_agent_trace(state)


# =========================================================================
# MAIN
# =========================================================================

def main():
    inject_css()
    init_state()
    render_sidebar()
    render_header()

    start = render_query_box()
    topic = st.session_state["topic_input"].strip()

    if start:
        if not topic:
            st.warning("Enter a research topic before starting.")
        else:
            try:
                state, log = run_pipeline_with_live_log(topic)
                st.session_state["result"] = state
                st.session_state["log"] = log
                st.session_state["error"] = None
                st.session_state["last_topic"] = topic
            except Exception as e:  # noqa: BLE001
                st.session_state["result"] = None
                st.session_state["error"] = str(e)

    if st.session_state["error"]:
        st.error("Something went wrong while running the research pipeline.")
        with st.expander("Technical details"):
            st.code(st.session_state["error"])

    if st.session_state["result"]:
        st.markdown("---")
        st.caption(f"Results for: {st.session_state['last_topic']}")
        render_results(st.session_state["result"], st.session_state["last_topic"])
    elif not start and not st.session_state["error"]:
        st.markdown("---")
        render_empty_state()


if __name__ == "__main__":
    main()
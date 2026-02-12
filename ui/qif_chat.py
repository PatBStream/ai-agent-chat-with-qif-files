import os
from datetime import datetime

import requests
import streamlit as st
import streamlit.components.v1 as components

QIF_API_URL = os.environ.get("QIF_API_URL", "http://qif-agent:8000")

st.set_page_config(page_title="Chat with My QIF Agent", page_icon="💸", layout="centered")

if "history" not in st.session_state:
    st.session_state.history = []
if "is_processing" not in st.session_state:
    st.session_state.is_processing = False
if "pending_question" not in st.session_state:
    st.session_state.pending_question = None
if "results_container_height" not in st.session_state:
    st.session_state.results_container_height = 420
if "results_scroll_target" not in st.session_state:
    st.session_state.results_scroll_target = None

st.markdown(
    """
    <style>
      .qif-topbar-shell {
        position: sticky;
        top: 0;
        z-index: 1000;
        border: 1px solid rgba(49, 51, 63, 0.25);
        background: rgba(255, 255, 255, 0.95);
        color: #111111;
        backdrop-filter: blur(6px);
        border-radius: 0.5rem;
        padding: 0.45rem 0.75rem;
        margin-bottom: 0.75rem;
      }

      @media (prefers-color-scheme: dark) {
        .qif-topbar-shell {
          background: rgba(14, 17, 23, 0.95);
          color: #fafafa;
          border: 1px solid rgba(250, 250, 250, 0.2);
        }
      }

      .qif-topbar-time {
        font-size: 0.92rem;
        font-weight: 600;
      }

      .qif-status-pill {
        border: 1px solid currentColor;
        border-radius: 999px;
        padding: 0.12rem 0.45rem;
        white-space: nowrap;
        display: inline-block;
        font-size: 0.9rem;
      }

    </style>

    <a id="page-top"></a>
    """,
    unsafe_allow_html=True,
)

st.title("💸 Chat with My QIF Agent")
st.markdown(
    """
    Ask questions about your finances!
    The agent is trained on your QIF files and can answer queries about transactions.
    The table fields are:
    - **date**: The date of the transaction
    - **payee**: The entity you paid or received money from
    - **category**: The category of the transaction
    - **memo**: Additional notes about the transaction
    - **amount**: The amount of money involved in the transaction

    You can ask about specific transactions, totals, or trends in your finances.
    - For example, what the sum total for all of 2018 where the category like Dues?
    - List all transaction from 2018 where category like Util or like Electric
    """
)

user_input = st.chat_input(
    "Ask about your finances, table fields are date, payee, category, memo, amount."
)

if user_input:
    st.session_state.history.append({"role": "user", "content": user_input})
    st.session_state.pending_question = user_input
    st.session_state.is_processing = True
    st.rerun()

if st.session_state.pending_question:
    with st.spinner("Processing your request..."):
        try:
            resp = requests.post(
                f"{QIF_API_URL}/chat",
                json={"question": st.session_state.pending_question},
                timeout=60,
            )
            answer = resp.json().get("answer", "No answer.")
        except Exception as e:
            answer = f"❌ Error: {e}"

    st.session_state.history.append({"role": "assistant", "content": answer})
    st.session_state.pending_question = None
    st.session_state.is_processing = False
    st.rerun()

status_icon = "⏳" if st.session_state.is_processing else "✅"
status_text = "Processing" if st.session_state.is_processing else "Ready"

st.markdown('<div class="qif-topbar-shell">', unsafe_allow_html=True)
left_col, status_col, clear_col, up_col, down_col = st.columns([6, 2.4, 1, 1, 1])

with left_col:
    st.markdown(
        f'<div class="qif-topbar-time">{datetime.now().strftime("%A, %B %d, %Y at %I:%M:%S %p")}</div>',
        unsafe_allow_html=True,
    )
with status_col:
    st.markdown(f'<span class="qif-status-pill">{status_icon} {status_text}</span>', unsafe_allow_html=True)
with clear_col:
    if st.button("🧹", help="Clear results", use_container_width=True, type="secondary"):
        st.session_state.history = []
        st.session_state.pending_question = None
        st.session_state.is_processing = False
        st.rerun()
with up_col:
    if st.button("⤒", help="Scroll results to top", use_container_width=True, type="secondary"):
        st.session_state.results_scroll_target = "top"
with down_col:
    if st.button("⤓", help="Scroll results to bottom", use_container_width=True, type="secondary"):
        st.session_state.results_scroll_target = "bottom"

st.markdown('</div>', unsafe_allow_html=True)

results_container = st.container(
    height=st.session_state.results_container_height,
    border=True,
)

with results_container:
    if not st.session_state.history:
        st.caption("No results yet. Ask a question to see responses here.")

    for entry in st.session_state.history:
        with st.chat_message(entry["role"]):
            st.markdown(entry["content"])

if st.session_state.results_scroll_target:
    scroll_target = st.session_state.results_scroll_target
    components.html(
        f"""
        <script>
          const target = "{scroll_target}";
          const scrollResultsContainer = () => {{
            const candidates = Array.from(window.parent.document.querySelectorAll('div[data-testid=\"stVerticalBlock\"]'));
            const scrollable = candidates.filter((node) => {{
              const style = window.parent.getComputedStyle(node);
              return (style.overflowY === 'auto' || style.overflowY === 'scroll') && node.scrollHeight > node.clientHeight;
            }});
            if (!scrollable.length) return;
            const resultsNode = scrollable.sort((a, b) => (b.scrollHeight - b.clientHeight) - (a.scrollHeight - a.clientHeight))[0];
            resultsNode.scrollTo({{
              top: target === 'top' ? 0 : resultsNode.scrollHeight,
              behavior: 'auto',
            }});
          }};
          setTimeout(scrollResultsContainer, 50);
        </script>
        """,
        height=0,
    )
    st.session_state.results_scroll_target = None

import os
from datetime import datetime

import requests
import streamlit as st

QIF_API_URL = os.environ.get("QIF_API_URL", "http://qif-agent:8000")

st.set_page_config(page_title="Chat with My QIF Agent", page_icon="💸", layout="centered")

if "history" not in st.session_state:
    st.session_state.history = []
if "is_processing" not in st.session_state:
    st.session_state.is_processing = False
if "pending_question" not in st.session_state:
    st.session_state.pending_question = None

status_icon = "⏳" if st.session_state.is_processing else "✅"
status_text = "Processing" if st.session_state.is_processing else "Ready"

st.markdown(
    f"""
    <style>
      div.block-container {{
        padding-top: 6.2rem !important;
      }}

      .qif-floating-title-bar {{
        position: fixed;
        top: 0.75rem;
        left: 50%;
        transform: translateX(-50%);
        width: min(900px, calc(100vw - 1rem));
        z-index: 999999;
        border: 1px solid rgba(49, 51, 63, 0.25);
        background: rgba(255, 255, 255, 0.97);
        color: #111111;
        border-radius: 0.6rem;
        backdrop-filter: blur(7px);
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.14);
        padding: 0.55rem 0.8rem;
      }}

      @media (prefers-color-scheme: dark) {{
        .qif-floating-title-bar {{
          background: rgba(14, 17, 23, 0.97);
          color: #fafafa;
          border: 1px solid rgba(250, 250, 250, 0.2);
        }}
      }}

      .qif-title-content {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 0.75rem;
        font-size: 0.92rem;
      }}

      .qif-right-icons {{
        display: inline-flex;
        align-items: center;
        gap: 0.65rem;
        white-space: nowrap;
      }}

      .qif-status-pill {{
        border: 1px solid currentColor;
        border-radius: 999px;
        padding: 0.12rem 0.45rem;
      }}

      .qif-nav-arrow {{
        text-decoration: none;
        font-size: 1.1rem;
        line-height: 1;
      }}

      .qif-nav-arrow:hover {{
        opacity: 0.75;
      }}

      @media (max-width: 640px) {{
        .qif-title-content {{
          font-size: 0.78rem;
          gap: 0.4rem;
        }}
        .qif-right-icons {{
          gap: 0.35rem;
        }}
      }}
    </style>

    <a id="page-top"></a>
    <div class="qif-floating-title-bar">
      <div class="qif-title-content">
        <div><strong>{datetime.now().strftime('%A, %B %d, %Y at %I:%M:%S %p')}</strong></div>
        <div class="qif-right-icons">
          <span class="qif-status-pill">{status_icon} {status_text}</span>
          <a class="qif-nav-arrow" href="#page-top" title="Go to top">⬆️</a>
          <a class="qif-nav-arrow" href="#page-bottom" title="Go to bottom">⬇️</a>
        </div>
      </div>
    </div>
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

for entry in st.session_state.history:
    with st.chat_message(entry["role"]):
        st.markdown(entry["content"])

st.markdown('<a id="page-bottom"></a>', unsafe_allow_html=True)

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

status_icon = "⏳" if st.session_state.is_processing else "✅"
status_text = "Processing" if st.session_state.is_processing else "Ready"

st.markdown(
    f"""
    <style>
      .app-shell-top-padding {{
        padding-top: 5rem;
      }}

      .app-fixed-header {{
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        z-index: 9999;
        background: rgba(14, 17, 23, 0.95);
        border-bottom: 1px solid rgba(250, 250, 250, 0.15);
        backdrop-filter: blur(4px);
        padding: 0.55rem 1rem;
      }}

      .app-fixed-header-content {{
        max-width: 46rem;
        margin: 0 auto;
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 0.75rem;
        color: #fafafa;
        font-size: 0.9rem;
      }}

      .app-header-right {{
        display: flex;
        align-items: center;
        gap: 0.8rem;
      }}

      .app-nav-arrow {{
        color: #fafafa;
        text-decoration: none;
        font-size: 1.15rem;
        line-height: 1;
      }}

      .app-nav-arrow:hover {{
        opacity: 0.8;
      }}

      .app-status-pill {{
        border: 1px solid rgba(250, 250, 250, 0.35);
        border-radius: 999px;
        padding: 0.15rem 0.5rem;
        white-space: nowrap;
      }}
    </style>

    <a id="page-top"></a>
    <div class="app-fixed-header">
      <div class="app-fixed-header-content">
        <div><strong>{datetime.now().strftime('%A, %B %d, %Y at %I:%M:%S %p')}</strong></div>
        <div class="app-header-right">
          <span class="app-status-pill">{status_icon} {status_text}</span>
          <a class="app-nav-arrow" href="#page-top" title="Go to top">⬆️</a>
          <a class="app-nav-arrow" href="#page-bottom" title="Go to bottom">⬇️</a>
        </div>
      </div>
    </div>
    <div class="app-shell-top-padding"></div>
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

    st.session_state.is_processing = True
    with st.spinner("Processing your request..."):
        try:
            resp = requests.post(
                f"{QIF_API_URL}/chat", json={"question": user_input}, timeout=60
            )
            answer = resp.json().get("answer", "No answer.")
        except Exception as e:
            answer = f"❌ Error: {e}"

    st.session_state.history.append({"role": "assistant", "content": answer})
    st.session_state.is_processing = False
    st.rerun()

for entry in st.session_state.history:
    with st.chat_message(entry["role"]):
        st.markdown(entry["content"])

st.markdown('<a id="page-bottom"></a>', unsafe_allow_html=True)

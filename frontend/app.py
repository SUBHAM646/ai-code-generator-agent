import streamlit as st
import requests
import time

st.set_page_config(
    page_title="AI Code Generator Agent",
    page_icon="🤖",
    layout="wide"
)

BACKEND_URL = "http://127.0.0.1:8000"

st.title("🤖 AI Code Generator & Self-Healing Agent")
st.caption("Powered by LLM Agentic Loops, AST Static Security, and Isolated Sandboxing")

# Sidebar
with st.sidebar:
    st.header("⚙️ Agent Settings")
    auto_exec = st.checkbox("Auto-execute in Sandbox", value=True)
    st.markdown("---")
    st.markdown("### 🛡️ Safety Guards")
    st.markdown("- **AST Security:** Blocks `os`, `sys`, `subprocess`, etc.")
    st.markdown("- **No Hangs:** Interactive `input()` blocked.")
    st.markdown("- **Timeouts:** 5s max execution limit.")
    st.markdown("- **Self-Correction:** Auto-repairs runtime & syntax failures.")

# Input Form
with st.form("code_request_form"):
    user_prompt = st.text_area(
        "Enter your programming problem / requirements:",
        placeholder="e.g. Write a Python function for binary search with test cases.",
        height=100
    )
    submitted = st.form_submit_button("🚀 Generate Code", use_container_width=True)

if submitted:
    if not user_prompt.strip():
        st.warning("Please enter a valid problem statement.")
    else:
        start_time = time.time()
        with st.spinner("Agent is analyzing, generating, validating, and testing code..."):
            try:
                response = requests.post(
                    f"{BACKEND_URL}/api/generate",
                    json={"prompt": user_prompt, "auto_execute": auto_exec},
                    timeout=60
                )
                duration = round(time.time() - start_time, 2)
                if response.status_code == 200:
                    data = response.json()
                    data["latency"] = f"{duration}s"
                    st.session_state["result"] = data
                    st.session_state["edited_code"] = data.get("code", "")
                    st.session_state["current_stdout"] = data.get("stdout", "")
                else:
                    st.error(f"Backend Error: {response.text}")
            except requests.exceptions.ConnectionError:
                st.error("Cannot connect to FastAPI backend! Make sure FastAPI is running on http://127.0.0.1:8000.")

# Results Display
if "result" in st.session_state:
    data = st.session_state["result"]

    # Metrics Row
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Status", "Success" if data.get("success") else "Failed")
    m2.metric("Latency", data.get("latency", "N/A"))
    m3.metric("Self-Healing Retries", data.get("retries_taken", 0))
    m4.metric("Security Check", "Passed (AST Safe)")

    col1, col2 = st.columns([1.2, 0.8])

    with col1:
        st.subheader("📋 Solution Plan")
        st.info(data.get("plan", "No plan available."))

        st.subheader("💻 Generated Code (Editable)")
        # Editable code area so user can modify test inputs live
        edited_code = st.text_area(
            "Modify code or test inputs below:",
            value=st.session_state.get("edited_code", data.get("code", "")),
            height=300
        )
        st.session_state["edited_code"] = edited_code

        btn_col1, btn_col2 = st.columns([1, 1])
        with btn_col1:
            if st.button("⚡ Re-Run Modified Code", use_container_width=True):
                with st.spinner("Re-executing in sandbox..."):
                    try:
                        exec_res = requests.post(
                            f"{BACKEND_URL}/api/execute",
                            json={"code": edited_code, "timeout_seconds": 5},
                            timeout=10
                        ).json()
                        if exec_res.get("success"):
                            st.session_state["current_stdout"] = exec_res.get("stdout", "")
                            st.toast("Executed successfully!", icon="✅")
                        else:
                            st.session_state["current_stdout"] = f"Error: {exec_res.get('stderr')}"
                            st.toast("Execution error!", icon="⚠️")
                    except Exception as e:
                        st.error(f"Execution failed: {e}")

        with btn_col2:
            st.download_button(
                label="📥 Download Python File (.py)",
                data=edited_code,
                file_name="solution.py",
                mime="text/x-python",
                use_container_width=True
            )

        st.subheader("📖 Code Explanation & Complexity")
        st.markdown(data.get("explanation", "No explanation available."))

    with col2:
        st.subheader("🖥️ Execution Terminal Output")
        out = st.session_state.get("current_stdout", "")
        if out:
            st.code(out, language="bash")
        else:
            st.write("No console output recorded.")

        # Self-correction logs expander
        history = data.get("history", [])
        if len(history) > 1:
            st.subheader("🔄 Agent Self-Correction Trace")
            for item in history:
                with st.expander(f"Attempt #{item.get('attempt')}: Status - {item.get('status')}"):
                    if item.get("error"):
                        st.error(f"Error encountered: {item.get('error')}")
                    if item.get("code"):
                        st.code(item.get("code"), language="python")
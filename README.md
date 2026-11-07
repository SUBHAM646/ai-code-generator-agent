# 🤖 AI Code Generator & Self-Healing Agent

An end-to-end autonomous AI coding assistant built using **FastAPI**, **Streamlit**, and **LLMs (Groq / Gemini)**. Features static AST security validation and an isolated runtime sandbox with automated error recovery.

---

## 🏛️ System Architecture

```text
User Request
     │
     ▼
[Input Processor & System Prompt]
     │
     ▼
[LLM Code Generator] (Plan + Python Code + Explanation)
     │
     ▼
[AST Static Validator] ───(Restricted Modules / input() hang)───► [Self-Healing Feedback Loop]
     │ (Passed)                                                             ▲
     ▼                                                                      │ (Syntax/Runtime Error)
[Isolated Subprocess Sandbox] ───(5s Timeout / Execution Check)─────────────┘
     │ (Passed)
     ▼
[Final Verified Code + Execution Output]
import os
import re
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

def _extract_sections(raw_text: str) -> Dict[str, str]:
    """Extracts PLAN, CODE, and EXPLANATION sections from LLM response."""
    plan = ""
    code = ""
    explanation = ""

    plan_match = re.search(r"### PLAN\s*\n(.*?)(?=### CODE|\Z)", raw_text, re.DOTALL)
    if plan_match:
        plan = plan_match.group(1).strip()

    code_match = re.search(r"```python\s*\n(.*?)\n```", raw_text, re.DOTALL)
    if not code_match:
        code_match = re.search(r"```\s*\n(.*?)\n```", raw_text, re.DOTALL)

    if code_match:
        code = code_match.group(1).strip()
    else:
        code = raw_text.strip()

    exp_match = re.search(r"### EXPLANATION\s*\n(.*)", raw_text, re.DOTALL)
    if exp_match:
        explanation = exp_match.group(1).strip()
    else:
        explanation = "No explicit explanation provided."

    return {
        "plan": plan,
        "code": code,
        "explanation": explanation
    }

def call_llm(system_prompt: str, user_prompt: str) -> str:
    """Dynamically fetches active Groq models or falls back to Gemini."""
    if GROQ_API_KEY and not GROQ_API_KEY.startswith("your_"):
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY)
        
        try:
            # Groq account se currently active models ki real list lete hain
            models_list = client.models.list().data
            # Filter chat models (audio/whisper models exclude karte hain)
            active_model_ids = [m.id for m in models_list if "whisper" not in m.id.lower() and "guard" not in m.id.lower()]
            
            for model_id in active_model_ids:
                try:
                    response = client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        temperature=0.2
                    )
                    return response.choices[0].message.content
                except Exception as e:
                    continue
        except Exception as e:
            print(f"[Warning] Groq dynamic model fetch failed: {e}. Trying fallback...")

    # Fallback to Google Gemini
    if GEMINI_API_KEY and not GEMINI_API_KEY.startswith("your_"):
        try:
            from google import genai
            client = genai.Client(api_key=GEMINI_API_KEY)
            response = client.models.generate_content(
                model="gemini-1.5-flash",
                contents=f"{system_prompt}\n\nUser Request: {user_prompt}"
            )
            return response.text
        except Exception as e:
            raise RuntimeError(f"Gemini API Call failed: {e}")

    raise ValueError("Valid GROQ_API_KEY or GEMINI_API_KEY missing or model access denied.")

def generate_code_response(system_prompt: str, user_prompt: str) -> Dict[str, str]:
    raw_response = call_llm(system_prompt, user_prompt)
    return _extract_sections(raw_response)
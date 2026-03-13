"""
ai_router.py — THE GIANT AI Router
====================================
Handles all AI calls across the system.
Priority order:
  1. Groq  llama-3.3-70b-versatile   (primary — best quality)
  2. Groq  llama-3.1-8b-instant      (if Groq quota hit)
  3. Gemini 2.0 Flash                (if all Groq fails)

Usage:
    from ai_router import call_ai
    result = call_ai(prompt)
"""

import requests
import json
from config import (
    GROQ_API_KEY, GROQ_MODEL, GROQ_MODEL_FAST,
    GEMINI_API_KEY, GEMINI_MODEL
)

# ================================================================
#  GROQ
# ================================================================
def _call_groq(prompt, model):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type":  "application/json"
    }
    payload = {
        "model":       model,
        "messages":    [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens":  4000
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=60)

    if resp.status_code == 429:
        raise QuotaError(f"Groq quota exceeded on {model}")
    if resp.status_code == 401:
        raise AuthError("Groq API key invalid")

    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


# ================================================================
#  GEMINI
# ================================================================
def _call_gemini(prompt):
    if not GEMINI_API_KEY:
        raise AuthError("GEMINI_API_KEY not set in .env")

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature":    0.7,
            "maxOutputTokens": 4000
        }
    }
    resp = requests.post(url, json=payload, timeout=60)

    if resp.status_code == 429:
        raise QuotaError("Gemini quota exceeded")
    if resp.status_code == 400:
        raise AuthError("Gemini API key invalid or request malformed")

    resp.raise_for_status()
    data = resp.json()

    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as e:
        raise Exception(f"Gemini response parse error: {e} | Raw: {data}")


# ================================================================
#  CUSTOM EXCEPTIONS
# ================================================================
class QuotaError(Exception):
    pass

class AuthError(Exception):
    pass


# ================================================================
#  MAIN ROUTER — call this from anywhere in the project
# ================================================================
def call_ai(prompt, verbose=True):
    """
    Call AI with automatic fallback chain.
    Returns the text response as a string.
    Raises Exception only if ALL providers fail.
    """
    attempts = [
        ("Groq",   GROQ_MODEL,      lambda: _call_groq(prompt, GROQ_MODEL)),
        ("Groq",   GROQ_MODEL_FAST, lambda: _call_groq(prompt, GROQ_MODEL_FAST)),
        ("Gemini", GEMINI_MODEL,    lambda: _call_gemini(prompt)),
    ]

    last_error = None
    for provider, model, fn in attempts:
        try:
            result = fn()
            if verbose:
                short = model.split("-")[0] + "-" + model.split("-")[-1]
                print(f"  [AI] {provider} / {short}")
            return result

        except QuotaError as e:
            if verbose:
                print(f"  [AI] {provider} quota hit — switching to next model...")
            last_error = e
            continue

        except AuthError as e:
            if verbose:
                print(f"  [AI] {provider} auth error — skipping: {e}")
            last_error = e
            continue

        except Exception as e:
            if verbose:
                print(f"  [AI] {provider} error: {e} — trying next...")
            last_error = e
            continue

    raise Exception(
        f"All AI providers failed. Last error: {last_error}\n"
        f"Check your GROQ_API_KEY and GEMINI_API_KEY in .env"
    )


# ================================================================
#  TEST — run this file directly to verify your AI setup
# ================================================================
if __name__ == "__main__":
    print("\n" + "="*55)
    print("  THE GIANT — AI Router Test")
    print("="*55)

    print(f"\n  GROQ_API_KEY  : {'SET' if GROQ_API_KEY  else 'MISSING'}")
    print(f"  GEMINI_API_KEY: {'SET' if GEMINI_API_KEY else 'MISSING (optional)'}")

    print("\n  Testing AI call...")
    try:
        result = call_ai(
            "Reply with exactly these words: AI router working perfectly",
            verbose=True
        )
        print(f"\n  Response: {result.strip()}")
        print("\n  AI router is working correctly.")
    except Exception as e:
        print(f"\n  FAILED: {e}")

    print("\n" + "="*55 + "\n")

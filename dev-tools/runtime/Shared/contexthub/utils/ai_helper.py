
import os
import json
import threading
from pathlib import Path

def get_gemini_key():
    """Centralized key retrieval for internal app use."""
    # Try core settings first
    try:
        from core.settings import load_settings
        settings = load_settings()
        key = settings.get('GEMINI_API_KEY') or settings.get('GOOGLE_API_KEY')
        if key: return key
    except: pass
    
    # Try environment
    return os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')

def refine_text_ai(text, type="prompt", callback=None):
    """
    Asynchronously refines text using Gemini.
    type: "prompt", "lyrics", "simplify"
    callback: function(result_text) or function(None, error_msg)
    """
    key = get_gemini_key()
    if not key:
        if callback: callback(None, "Gemini API Key missing in settings.")
        return

    def _task():
        try:
            from google import genai
            from google.genai import types
            
            client = genai.Client(api_key=key)
            
            prompts = {
                "prompt": "Refine the following image/audio generation prompt to be more descriptive and professional. Focus on visual or auditory textures. Output ONLY the refined text.",
                
                "lyrics": """Refine the lyrics. IMPORTANT: ACE Step model requires Romanized English characters for non-English text.
1. If the lyrics are in Korean/Japanese/Chinese/etc., convert them to Romanized English (pronunciation).
2. Add the language tag at the start of the line, e.g., '[ko]annyeonghaseyo', '[ja]konnichiwa'.
3. Supported tags: [ko], [ja], [zh], [es], [fr], [en].
4. Keep the structure ([Verse], [Chorus]) if present.
5. Output ONLY the processed lyrics.""",

                "style": "Convert the following description into a comma-separated list of musical style tags (e.g., 'genre, instrument, mood, tempo'). Output ONLY the tags.",
                
                "simplify": "Simplify the following text. Output ONLY the simplified text."
            }
            
            system_instruction = "You are a professional AI prompt and lyrics engineer. Output only the final text."
            user_prompt = f"{prompts.get(type, prompts['prompt'])}\n\nText: {text}"
            
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.7
                )
            )
            
            result = response.text.strip()
            if callback: callback(result)
        except Exception as e:
            if callback: callback(None, str(e))

    threading.Thread(target=_task, daemon=True).start()

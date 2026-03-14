import os
import threading
import time
from pathlib import Path
try:
    import ollama
except Exception:
    ollama = None
try:
    from deep_translator import GoogleTranslator
except Exception:
    GoogleTranslator = None
try:
    from google import genai
except Exception:
    genai = None
from core.settings import load_settings
from core.logger import setup_logger

logger = setup_logger("ai_text_lab_service")

class AITextLabService:
    def __init__(self):
        self.settings = load_settings()
        self.gemini_api_key = self.settings.get("GEMINI_API_KEY", "")
        self.gemini_client = None
        self.translator = GoogleTranslator(source='auto', target='ko') if GoogleTranslator is not None else None
        
    def list_ollama_models(self):
        """Returns a list of model names from Ollama."""
        if ollama is None:
            return []
        try:
            models_response = ollama.list()
            return [m.get('name', '') for m in models_response.get('models', [])]
        except Exception as e:
            logger.error(f"Failed to list Ollama models: {e}")
            return []

    def warmup_model(self, model_name):
        """Pre-loads a model into memory."""
        if model_name.startswith("✦ ") or "Google" in model_name:
            return
        if ollama is None:
            return
        try:
            ollama.chat(
                model=model_name,
                messages=[{'role': 'user', 'content': 'hi'}],
                options={'num_predict': 1}
            )
        except Exception as e:
            logger.error(f"Failed to warmup model {model_name}: {e}")

    def translate(self, text, target_lang="ko"):
        """Performs machine translation."""
        if self.translator is None:
            raise RuntimeError("deep_translator package is not installed.")
        try:
            self.translator.target = target_lang
            return self.translator.translate(text)
        except Exception as e:
            logger.error(f"Translation error: {e}")
            raise e

    def stream_ollama(self, model, system_prompt, prompt, req_id, callback, cancel_event):
        """Streams response from Ollama."""
        if ollama is None:
            raise RuntimeError("Ollama Python package is not installed.")
        try:
            stream = ollama.chat(
                model=model,
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': prompt}
                ],
                stream=True
            )
            
            in_think_block = False
            for chunk in stream:
                if cancel_event.is_set():
                    break
                content = chunk.get('message', {}).get('content', '')
                
                # Simple <think> tag handling
                if '<think>' in content:
                    in_think_block = True
                    content = content.split('<think>')[0]
                if '</think>' in content:
                    in_think_block = False
                    content = content.split('</think>')[-1]
                
                if not in_think_block and content:
                    callback(content)
                    
        except Exception as e:
            logger.error(f"Ollama stream error: {e}")
            raise e

    def stream_gemini(self, model_name, system_prompt, prompt, callback, cancel_event):
        """Streams response from Gemini."""
        if genai is None:
            raise RuntimeError("google-genai package is not installed.")
        if not self.gemini_api_key:
            raise ValueError("Gemini API Key is missing")
            
        try:
            if not self.gemini_client:
                self.gemini_client = genai.Client(api_key=self.gemini_api_key)
            
            clean_model = model_name.replace("✦ ", "")
            response = self.gemini_client.models.generate_content_stream(
                model=clean_model,
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.7,
                )
            )
            
            for chunk in response:
                if cancel_event.is_set():
                    break
                if chunk.text:
                    callback(chunk.text)
        except Exception as e:
            logger.error(f"Gemini stream error: {e}")
            raise e

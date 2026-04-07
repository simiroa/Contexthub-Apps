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

# Note: The specific model 'qwen3.5:4b' is now the standard for this app.
PREFERRED_OLLAMA_MODELS = [
    "qwen3.5:4b",
    "qwen3:4b",
    "gemma4:e2b",
    "qwen3:8b",
]

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
            model_names = [m.get('name', '') for m in models_response.get('models', []) if m.get('name')]

            def sort_key(name: str):
                lowered = name.lower()
                try:
                    preferred_index = PREFERRED_OLLAMA_MODELS.index(lowered)
                except ValueError:
                    preferred_index = len(PREFERRED_OLLAMA_MODELS)
                qwen_bias = 0 if lowered.startswith("qwen3:") else 1
                return (preferred_index, qwen_bias, lowered)

            return sorted(model_names, key=sort_key)
        except Exception as e:
            logger.error(f"Failed to list Ollama models: {e}")
            return []

    def get_preferred_model(self, available_models):
        normalized = {str(model).lower(): str(model) for model in available_models if model}
        for preferred in PREFERRED_OLLAMA_MODELS:
            if preferred in normalized:
                return normalized[preferred]
        return available_models[0] if available_models else "✦ gemini-2.0-flash"

    def ensure_model(self, model_name: str) -> bool:
        """Check if model exists, if not pull it."""
        if ollama is None: return False
        try:
            logger.info(f"Ensuring model exists: {model_name}")
            models = ollama.list().get('models', [])
            if any(m.get('name') == model_name or m.get('model') == model_name for m in models):
                return True
            
            logger.info(f"Model {model_name} not found. Pulling (this may take time)...")
            ollama.pull(model_name)
            return True
        except Exception as e:
            logger.error(f"Error pulling model {model_name}: {e}")
            return False

    def warmup_model(self, model_name="qwen3.5:4b"):
        """Pre-loads a model into memory."""
        if model_name.startswith("✦ ") or "Google" in model_name:
            return
        if ollama is None:
            return
        
        # Ensure model before warming
        self.ensure_model(model_name)
        
        logger.info(f"Warming up model: {model_name}")
        try:
            # A simple chat call with num_predict: 1 triggers the load
            ollama.chat(
                model=model_name,
                messages=[{'role': 'user', 'content': 'hi'}],
                options={'num_predict': 1}
            )
            logger.info(f"Model {model_name} warmed up successfully.")
        except Exception as e:
            logger.error(f"Failed to warmup model {model_name}: {e}")

    def unload_model(self, model_name):
        """Explicitly unloads a model from VRAM by setting keep_alive to 0."""
        if model_name.startswith("✦ ") or "Google" in model_name:
            return
        if ollama is None:
            return
        logger.info(f"Unloading model: {model_name} to release VRAM")
        try:
            # Setting keep_alive to 0 in a generate call unloads the model
            ollama.generate(model=model_name, keep_alive=0)
            logger.info(f"Model {model_name} unloaded.")
        except Exception as e:
            logger.error(f"Failed to unload model {model_name}: {e}")

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

    def stream_ollama(self, model, system_prompt, prompt, callback, cancel_event):
        """Streams response from Ollama."""
        if ollama is None:
            raise RuntimeError("Ollama Python package is not installed.")
        
        # Ensure model exists before streaming
        self.ensure_model(model)
        
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
                if not content:
                    continue
                
                # Enhanced tag handling (covers cases where tags are in the middle of content)
                lowered = content.lower()
                if '<think>' in lowered:
                    in_think_block = True
                    parts = content.split('<think>')
                    # Keep text BEFORE <think>
                    if parts[0]: callback(parts[0])
                    continue
                
                if '</think>' in lowered:
                    in_think_block = False
                    parts = content.split('</think>')
                    # Keep text AFTER </think>
                    if len(parts) > 1 and parts[1]: 
                        callback(parts[1])
                    continue
                
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

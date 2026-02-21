"""
Gemini Text Refinement Script.
Provides professional text polishing using Google Gemini.
"""
import sys
import os
import argparse
import json
from pathlib import Path

# Add src to path to load settings if needed
current_dir = Path(__file__).resolve().parent
src_dir = current_dir.parent.parent.parent
if str(src_dir) not in sys.path:
    sys.path.append(str(src_dir))

def get_api_key():
    """Retrieve Gemini API Key from multiple sources."""
    # 1. Env
    key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
    if key: return key
    
    # 2. Settings
    try:
        from core.settings import load_settings
        settings = load_settings()
        key = settings.get('GEMINI_API_KEY') or settings.get('GOOGLE_API_KEY')
        if key: return key
    except: pass
    
    # 3. JSON file
    try:
        config_path = src_dir.parent / "config" / "api_keys.json"
        if config_path.exists():
            with open(config_path, 'r') as f:
                data = json.load(f)
                key = data.get('gemini_api_key') or data.get('google_api_key')
                if key: return key
    except: pass
    return None

def refine_text(text, model='gemini-2.0-flash', task_type='refine'):
    api_key = get_api_key()
    if not api_key:
        print("Error: GEMINI_API_KEY not found. Please set it in ContextUp settings.")
        return False

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        print("Error: google-genai library not installed. Please install it.")
        return False

    prompts = {
        'refine': "Refine and polish the following text to be more professional, fluent, and descriptive. Ideal for image generation prompts. Output ONLY the refined text.\n\nText:\n",
        'fix': "Fix grammar and spelling errors. Output ONLY the corrected text.\n\nText:\n",
        'simplify': "Simplify the text. Output ONLY the simplified text.\n\nText:\n"
    }
    
    system_prompt = "You are a professional editor. Output only the refined text without any explanation or conversational filler."
    user_prompt = prompts.get(task_type, prompts['refine']) + text
    
    try:
        print(f"Refining text with {model}...")
        client = genai.Client(api_key=api_key)
        
        # Determine model name (handle potential 'gemini-' prefix issues if any, usually clean)
        # Using 2.0-flash as default as requested/implied for speed
        
        response = client.models.generate_content(
            model=model,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.7
            )
        )
        
        result_text = response.text.strip()
        
        print("\n--- Result ---\n")
        print(result_text)
        print("\n--------------\n")
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Gemini Text Refine Tool')
    parser.add_argument('--text', help='Text to refine')
    parser.add_argument('--model', default='gemini-2.0-flash', help='Gemini model (default: gemini-2.0-flash)')
    parser.add_argument('--type', choices=['refine', 'fix', 'simplify'], default='refine', help='Refinement type')
    
    args = parser.parse_args()
    
    if not args.text:
        print("Error: No input text provided.")
        return 1
        
    success = refine_text(args.text, model=args.model, task_type=args.type)
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())

"""
Clipboard Error Analysis Tool.
Analyzes clipboard content (Image or Text) for errors using Ollama.
"""
import sys
import argparse
import pyperclip
from PIL import ImageGrab, Image
import ollama
import io
import tempfile
from pathlib import Path

def analyze_clipboard_error(model_vision='llava', model_text='llama3'):
    """Analyze clipboard for errors."""
    
    # 1. Check for Image
    try:
        img = ImageGrab.grabclipboard()
        if isinstance(img, Image.Image):
            print("Detected Image in clipboard.")
            # Save to temp
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                img.save(tmp.name)
                tmp_path = tmp.name
                
            print(f"Analyzing image with {model_vision}...")
            prompt = "Analyze this image. It likely contains an error message, stack trace, or bug. Extract the text and explain the error clearly. Suggest a fix if possible."
            
            res = ollama.chat(
                model=model_vision,
                messages=[{
                    'role': 'user',
                    'content': prompt,
                    'images': [tmp_path]
                }]
            )
            
            # Cleanup
            Path(tmp_path).unlink()
            return res['message']['content']
    except Exception as e:
        print(f"Image check failed: {e}")

    # 2. Check for Text
    try:
        text = pyperclip.paste()
        if text and len(text.strip()) > 0:
            print("Detected Text in clipboard.")
            print(f"Preview: {text[:100]}...")
            
            print(f"Analyzing text with {model_text}...")
            prompt = f"Analyze the following error message, code, or log. Explain what went wrong and suggest a fix.\n\nContent:\n{text}"
            
            res = ollama.chat(
                model=model_text,
                messages=[{'role': 'user', 'content': prompt}]
            )
            return res['message']['content']
    except Exception as e:
        print(f"Text check failed: {e}")
        
    return "No usable content found in clipboard (Image or Text)."

def main():
    parser = argparse.ArgumentParser(description='Clipboard Error Analysis')
    parser.add_argument('--model-vision', default='qwen3-vl:8b', help='Vision model')
    parser.add_argument('--model-text', default='qwen3-vl:8b', help='Text model')
    
    args = parser.parse_args()
    
    result = analyze_clipboard_error(args.model_vision, args.model_text)
    
    print("\n--- Analysis Result ---\n")
    print(result)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

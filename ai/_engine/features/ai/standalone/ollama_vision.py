"""
Ollama Vision & Prompt Generation Script.
Interfaces with local Ollama server.
"""
import sys
import argparse
import base64
import io
from pathlib import Path
import ollama
from PIL import Image
import pyperclip

def check_server():
    """Check if Ollama server is running."""
    try:
        ollama.list()
        return True
    except Exception:
        return False

def get_vision_models():
    """Get list of available vision models."""
    try:
        models = ollama.list()
        # Filter for known vision models or assume 'llava' family
        # This is a heuristic; Ollama doesn't explicitly tag vision models in list yet
        vision_keywords = ['llava', 'moondream', 'bakllava', 'minicpm-v', 'qwen']
        available = []
        for m in models.models:
            name = m.model
            if any(k in name for k in vision_keywords):
                available.append(name)
        return available
    except Exception as e:
        print(f"Error listing models: {e}")
        return []

def image_to_base64(image_path):
    """Convert image to base64 string."""
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode('utf-8')

def analyze_image(image_path, model='llava', prompt_type='describe'):
    """
    Analyze image using Ollama vision model.
    """
    if not check_server():
        print("Error: Ollama server is not running. Please start Ollama.")
        return False
    
    # Define prompts
    prompts = {
        'describe': "Describe this image in detail.",
        'prompt': "Create a detailed text-to-image prompt for Stable Diffusion based on this image. Include style, lighting, and composition details.",
        'analyze': "Analyze the content of this image. What objects, text, or scenes are present?",
        'ocr': "Extract all text visible in this image. Output only the text."
    }
    
    user_prompt = prompts.get(prompt_type, prompts['describe'])
    
    print(f"Analyzing image with {model}...")
    print(f"Task: {prompt_type}")
    
    try:
        res = ollama.chat(
            model=model,
            messages=[
                {
                    'role': 'user',
                    'content': user_prompt,
                    'images': [image_path]
                }
            ]
        )
        
        result_text = res['message']['content']
        print("\n--- Result ---\n")
        print(result_text)
        print("\n--------------\n")
        
        # Copy to clipboard
        pyperclip.copy(result_text)
        print("✓ Result copied to clipboard.")
        
        return True
        
    except ollama.ResponseError as e:
        print(f"Ollama Error: {e.error}")
        if 'pull' in str(e):
            print(f"Tip: Run 'ollama pull {model}' to install the model.")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Ollama Vision Tool')
    parser.add_argument('image_path', nargs='?', help='Input image path (optional if using clipboard)')
    parser.add_argument('--model', default='qwen3-vl:8b', help='Ollama model to use (default: qwen3-vl:8b)')
    parser.add_argument('--type', choices=['describe', 'prompt', 'analyze', 'ocr'], 
                       default='describe', help='Analysis type')
    parser.add_argument('--clipboard', action='store_true', help='Use image from clipboard')
    parser.add_argument('--list-models', action='store_true', help='List available vision models')
    
    args = parser.parse_args()
    
    if args.list_models:
        if check_server():
            models = get_vision_models()
            print("Available Vision Models:")
            for m in models:
                print(f" - {m}")
        else:
            print("Ollama server is not running.")
        return 0
    
    target_path = None
    
    if args.clipboard:
        from PIL import ImageGrab
        try:
            img = ImageGrab.grabclipboard()
            if isinstance(img, Image.Image):
                # Save to temp file
                import tempfile
                temp_dir = Path(tempfile.gettempdir())
                target_path = temp_dir / "ollama_clipboard_temp.png"
                img.save(target_path)
                print(f"Processing clipboard image: {target_path}")
            else:
                print("Error: No image found in clipboard.")
                return 1
        except Exception as e:
            print(f"Clipboard error: {e}")
            return 1
    elif args.image_path:
        target_path = Path(args.image_path)
        if not target_path.exists():
            print(f"Error: File not found: {target_path}")
            return 1
    else:
        print("Error: Please provide an image path or use --clipboard")
        return 1
        
    success = analyze_image(str(target_path), model=args.model, prompt_type=args.type)
    
    # Cleanup temp file if used
    if args.clipboard and target_path and target_path.exists():
        try:
            target_path.unlink()
        except:
            pass
            
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())

"""
Smart Rename Tool using Ollama.
Renames files or folders based on their content (Image or Text) or current name.
"""
import sys
import argparse
import os
from pathlib import Path
import ollama
from PIL import Image

def get_folder_context(folder_path):
    """Get a quick summary of folder contents."""
    try:
        items = os.listdir(folder_path)
        files = [f for f in items if os.path.isfile(os.path.join(folder_path, f))]
        dirs = [d for d in items if os.path.isdir(os.path.join(folder_path, d))]
        
        context = f"Folder name: {Path(folder_path).name}\n"
        context += f"Contains {len(files)} files and {len(dirs)} subfolders.\n"
        context += "Sample files: " + ", ".join(files[:5])
        return context
    except Exception:
        return f"Folder: {Path(folder_path).name}"

def get_suggestions(content, current_name, model, is_image=False, image_path=None):
    """Get 3 filename suggestions."""
    try:
        if is_image:
            prompt = "Analyze this image and suggest 3 concise filenames (max 5 words, underscores, no extension). Output ONLY the 3 names, one per line."
            messages = [{'role': 'user', 'content': prompt, 'images': [image_path]}]
            res = ollama.chat(model=model, messages=messages, stream=False)
            text = res['message']['content']
        else:
            prompt = f"Suggest 3 concise filenames (max 5 words, underscores, no extension) for this content. Current name: '{current_name}'.\n\nContent Context:\n{content[:500]}\n\nOutput ONLY the 3 names, one per line."
            res = ollama.chat(model=model, messages=[{'role': 'user', 'content': prompt}], stream=False)
            text = res['message']['content']
            
        # Parse lines
        suggestions = [line.strip().lstrip('- 123.').strip() for line in text.splitlines() if line.strip()]
        return suggestions[:3]
    except Exception as e:
        print(f"Error generating suggestions: {e}")
        return []

def smart_rename(target_path, model_vision='llava', model_text='llama3', dry_run=False):
    """
    Generate new name suggestions.
    """
    path = Path(target_path)
    if not path.exists():
        print(f"Error: {path} not found")
        return False
        
    suggestions = []
    
    # 1. Image File
    if path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp', '.bmp']:
        print(f"Analyzing image: {path.name}...")
        suggestions = get_suggestions(None, path.stem, model_vision, is_image=True, image_path=str(path))
        
    # 2. Text File
    elif path.suffix.lower() in ['.txt', '.md', '.py', '.json', '.log']:
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(1000)
            print(f"Analyzing text: {path.name}...")
            suggestions = get_suggestions(content, path.stem, model_text)
        except Exception as e:
            print(f"Error reading text: {e}")
            
    # 3. Folder
    elif path.is_dir():
        print(f"Analyzing folder: {path.name}...")
        context = get_folder_context(path)
        suggestions = get_suggestions(context, path.name, model_text)
        
    # 4. Unknown File
    else:
        print(f"Analyzing name: {path.name}...")
        suggestions = get_suggestions(f"File named {path.name}", path.stem, model_text)
        
    if not suggestions:
        print("Failed to generate suggestions.")
        return False
        
    print("\n--- Suggestions ---")
    for i, name in enumerate(suggestions, 1):
        # Clean up
        valid_chars = "-_.() abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        clean = "".join(c for c in name if c in valid_chars).replace(" ", "_")
        if not path.is_dir():
             clean += path.suffix
        print(f"{i}. {clean}")
    print("-------------------\n")
    
    return True

def main():
    parser = argparse.ArgumentParser(description='Smart Rename Tool')
    parser.add_argument('target_path', help='File or folder to rename')
    parser.add_argument('--model-vision', default='qwen3-vl:8b', help='Vision model')
    parser.add_argument('--model-text', default='qwen3-vl:8b', help='Text model')
    parser.add_argument('--dry-run', action='store_true', help='Show suggestion only')
    
    args = parser.parse_args()
    
    success = smart_rename(
        args.target_path,
        model_vision=args.model_vision,
        model_text=args.model_text,
        dry_run=args.dry_run
    )
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())

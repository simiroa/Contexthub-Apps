"""
Ollama Text Refinement Script.
Provides professional text polishing and grammar correction using local Ollama.
"""
import sys
import argparse
# Optional imports moved to functions to support minimum install environments
# import ollama
# import pyperclip
from pathlib import Path

def check_server():
    try:
        import ollama
        ollama.list()
        return True
    except Exception:
        return False

def refine_text(text, model='qwen3:8b', task_type='refine'):
    if not check_server():
        print("Error: Ollama server is not running. Please start Ollama.")
        return False
    
    prompts = {
        'refine': "Refine and polish the following text, making it more professional and fluent. Keep the language the same as input.\n\nText:\n",
        'fix': "Fix grammar and spelling errors in the following text. Output only the corrected text.\n\nText:\n",
        'simplify': "Simplify the following text while keeping the core meaning.\n\nText:\n",
        'translate_kr': "Translate the following text to professional Korean.\n\nText:\n"
    }
    
    system_prompt = "You are a professional editor. Output only the refined text without any comments or conversational filler."
    user_prompt = prompts.get(task_type, prompts['refine']) + text
    
    try:
        import ollama
        import pyperclip
        print(f"Refining text with {model}...")
        res = ollama.chat(
            model=model,
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt}
            ]
        )
        
        result_text = res['message']['content'].strip()
        print("\n--- Result ---\n")
        print(result_text)
        print("\n--------------\n")
        
        pyperclip.copy(result_text)
        print("✓ Result copied to clipboard.")
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Ollama Text Refine Tool')
    parser.add_argument('--text', help='Text to refine')
    parser.add_argument('--clipboard', action='store_true', help='Use text from clipboard')
    parser.add_argument('--model', default='qwen3:8b', help='Ollama model (default: qwen3:8b)')
    parser.add_argument('--type', choices=['refine', 'fix', 'simplify', 'translate_kr'], 
                       default='refine', help='Refinement type')
    
    args = parser.parse_args()
    
    input_text = ""
    if args.text:
        input_text = args.text
    elif args.clipboard:
        import pyperclip
        input_text = pyperclip.paste()
    else:
        print("Error: No input text provided.")
        return 1
    
    if not input_text.strip():
        print("Error: Input text is empty.")
        return 1
        
    success = refine_text(input_text, model=args.model, task_type=args.type)
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())

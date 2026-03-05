"""
Document Analysis Tool using Ollama and PyMuPDF.
"""
import sys
import argparse
import fitz  # pymupdf
import ollama
from pathlib import Path

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF file."""
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        return text
    except Exception as e:
        print(f"Error extracting text: {e}")
        return None

def summarize_text(text, model='llama3'):
    """Summarize text using Ollama."""
    try:
        prompt = f"Please summarize the following text:\n\n{text}"
        response = ollama.generate(model=model, prompt=prompt)
        return response['response']
    except Exception as e:
        return f"Error summarizing text: {e}"

def translate_text(text, target_lang, model='llama3'):
    """Translate text using Ollama."""
    try:
        prompt = f"Please translate the following text to {target_lang}:\n\n{text}"
        response = ollama.generate(model=model, prompt=prompt)
        return response['response']
    except Exception as e:
        return f"Error translating text: {e}"

def main():
    parser = argparse.ArgumentParser(description='Document Analysis Tool')
    parser.add_argument('file_path', nargs='?', help='Input file path (PDF)')
    parser.add_argument('--action', choices=['extract', 'summarize', 'translate'], help='Action to perform')
    parser.add_argument('--model', default='qwen3-vl:8b', help='Ollama model to use')
    parser.add_argument('--lang', help='Target language for translation')
    parser.add_argument('--list-models', action='store_true', help='List available models')
    
    args = parser.parse_args()
    
    if args.list_models:
        try:
            models = ollama.list()
            print("Available Models:")
            for m in models.models:
                print(f" - {m.model}")
            return 0
        except Exception as e:
            print(f"Error listing models: {e}")
            return 1

    if not args.file_path:
        print("Error: file_path is required unless --list-models is used")
        return 1
        
    file_path = Path(args.file_path)
    if not file_path.exists():
        print(f"Error: File not found: {file_path}")
        return 1
        
    # Extract text
    if file_path.suffix.lower() == '.pdf':
        text = extract_text_from_pdf(str(file_path))
    else:
        # Fallback for text files
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
        except:
            print("Error: Unsupported file type or encoding")
            return 1
            
    if not text:
        print("Error: No text extracted")
        return 1
        
    if args.action == 'extract':
        print(text)
    elif args.action == 'summarize':
        print("Summarizing...")
        result = summarize_text(text, model=args.model)
        print("\n--- Summary ---\n")
        print(result)
    elif args.action == 'translate':
        if not args.lang:
            print("Error: --lang is required for translation")
            return 1
        print(f"Translating to {args.lang}...")
        result = translate_text(text, args.lang, model=args.model)
        print(f"\n--- Translation ({args.lang}) ---\n")
        print(result)
        
    return 0

if __name__ == "__main__":
    sys.exit(main())

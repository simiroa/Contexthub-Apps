"""
Metadata Tagger using Ollama.
Generates keywords from image content and writes to EXIF (XPKeywords).
"""
import sys
import argparse
import ollama
import piexif
from PIL import Image

def generate_tags(image_path, model='llava'):
    """Generate tags using Ollama."""
    try:
        prompt = "Analyze this image and list 5-10 relevant keywords or tags describing the content, style, and mood. Separate them with semicolons. Example: beach; sunset; tropical; vacation; vibrant"
        res = ollama.chat(
            model=model,
            messages=[
                {
                    'role': 'user',
                    'content': prompt,
                    'images': [image_path]
                }
            ]
        )
        content = res['message']['content'].strip()
        # Clean up
        tags = [t.strip() for t in content.replace(',', ';').split(';') if t.strip()]
        return tags
    except Exception as e:
        print(f"Error generating tags: {e}")
        return []

def write_tags(image_path, tags):
    """Write tags to EXIF XPKeywords."""
    try:
        # Join tags with semicolons
        tag_str = ";".join(tags)
        print(f"Writing tags: {tag_str}")
        
        # Prepare EXIF data
        # XPKeywords is tag 0x9C9E (40094)
        # Must be encoded as UTF-16LE (UCS-2)
        xp_keywords = tag_str.encode('utf-16le')
        
        # Load existing EXIF
        try:
            exif_dict = piexif.load(image_path)
        except:
            exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
            
        # Update 0th IFD
        exif_dict["0th"][piexif.ImageIFD.XPKeywords] = xp_keywords
        
        # Dump and save
        exif_bytes = piexif.dump(exif_dict)
        piexif.insert(exif_bytes, image_path)
        
        return True
    except Exception as e:
        print(f"Error writing EXIF: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Metadata Tagger')
    parser.add_argument('image_path', help='Image file path')
    parser.add_argument('--model', default='qwen3-vl:8b', help='Vision model')
    parser.add_argument('--dry-run', action='store_true', help='Show tags only')
    
    args = parser.parse_args()
    
    print(f"Analyzing {args.image_path}...")
    tags = generate_tags(args.image_path, model=args.model)
    
    if not tags:
        print("No tags generated.")
        return 1
        
    print("Generated Tags:")
    for t in tags:
        print(f"- {t}")
        
    if args.dry_run:
        return 0
        
    success = write_tags(args.image_path, tags)
    if success:
        print("Tags written successfully.")
        return 0
    else:
        return 1

if __name__ == "__main__":
    sys.exit(main())

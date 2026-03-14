import requests
import base64
import json
import os
from PIL import Image
import io

class AIHandler:
    def __init__(self, model="llava", host="http://localhost:11434"):
        self.host = host
        self.model = model
        self.api_url = f"{host}/api/generate"

    def _prepare_image(self, image_path, max_size=(800, 800)):
        """Resizes image and converts to base64 for vision processing."""
        try:
            with Image.open(image_path) as img:
                # Resize if too large to save bandwidth/local memory
                img.thumbnail(max_size)
                # Convert to RGB if necessary (e.g. for RGBA)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                buffered = io.BytesIO()
                img.save(buffered, format="JPEG", quality=85)
                return base64.b64encode(buffered.getvalue()).decode('utf-8')
        except Exception as e:
            print(f"Image processing error: {e}")
            return None

    def analyze_images(self, image_paths, project_name=""):
        """Sends multiple images to Ollama vision model to extract structured data."""
        images_b64 = []
        for path in image_paths:
            b64 = self._prepare_image(path)
            if b64:
                images_b64.append(b64)

        if not images_b64:
            return {"error": "No valid images to analyze."}

        prompt = f"""
        Analyze these product images for a comparison project: "{project_name}".
        Extract technical specifications (criteria) and their associated values.
        
        Return ONLY a JSON object in this format:
        {{
            "criteria": [
                {{"name": "Spec Name", "value": "Value", "unit": "Unit if any"}},
                ...
            ]
        }}
        
        Focus on numerical data, prices, performance metrics, and dimensions.
        Do not include conversational text, only the JSON.
        """

        payload = {
            "model": self.model,
            "prompt": prompt,
            "images": images_b64,
            "stream": False,
            "format": "json"
        }

        try:
            response = requests.post(self.api_url, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()
            
            # Robust JSON parsing
            output_text = result.get("response", "").strip()
            # Often Ollama might wrap in ```json ... ```
            if "```" in output_text:
                output_text = output_text.split("```")[1]
                if output_text.startswith("json"):
                    output_text = output_text[4:]
            
            return json.loads(output_text.strip())
        except Exception as e:
            return {"error": f"Ollama connection error: {str(e)}"}

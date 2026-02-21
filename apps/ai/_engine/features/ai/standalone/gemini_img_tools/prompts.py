"""
Gemini Image Tools - Prompt Generation Module
Contains prompt templates and generation logic for each tab.
"""


def generate_style_prompt(image_type: str, style: str, strength: float) -> str:
    """Generate prompt for Style tab."""
    type_context = f"Input image is a {image_type}." if image_type != "Select Type" else ""
    str_desc = "subtle" if strength < 0.3 else "moderate" if strength < 0.7 else "strong"
    return f"{type_context} Transform this texture into {style} style. Style strength: {str_desc} ({strength:.1f}). Preserve the underlying pattern, geometry, and composition while applying the artistic style. The result should look like a high-quality texture."


def generate_pbr_prompt(image_type: str, ai_target: str) -> str:
    """Generate prompt for PBR Gen tab."""
    type_context = f"Input image is a {image_type}." if image_type != "Select Type" else ""
    
    if ai_target == "None (Local Only)":
        return "AI Generation is disabled in this mode. Use 'Generate PBR Maps (Local)' button above, or select a map type to generate via AI."
    
    tech_specs = {
        "Normal": "Generate a tangent space normal map (purple/blue base). High frequency details should be crisp and defined. The map should accurately represent the surface depth.",
        "Roughness": "Generate a grayscale roughness map. White represents rough areas, Black represents glossy/smooth areas. Ensure high contrast where necessary.",
        "Displacement": "Generate a grayscale height/displacement map. White represents high points, Black represents low points. Smooth transitions for gradients.",
        "Occlusion": "Generate an ambient occlusion map. Darken crevices, corners, and deep areas. The rest should be white."
    }
    
    tech_spec = ""
    for key, value in tech_specs.items():
        if key in ai_target:
            tech_spec = value
            break
    
    return f"{type_context} Generate a high-quality {ai_target} for this texture. {tech_spec} Ensure it is accurate and aligned with the original details."


def generate_tile_prompt(image_type: str, scale: float, description: str) -> str:
    """Generate prompt for Tileable tab."""
    type_context = f"Input image is a {image_type}." if image_type != "Select Type" else ""
    desc_text = f"Context: {description}." if description else ""
    
    return f"{type_context} {desc_text} Generate a seamless tileable texture based on this image. The texture should represent the surface material shown. Scale the details by a factor of {scale:.1f}x (where >1 means zoom in/larger details, <1 means zoom out/smaller details). The result MUST be seamlessly tileable on all sides (x and y axes). Eliminate any visible seams or borders. Maintain a consistent texture density. Output the texture only."


def generate_weather_prompt(image_type: str, mode: str, intensity: float) -> str:
    """Generate prompt for Weathering tab."""
    type_context = f"Input image is a {image_type}." if image_type != "Select Type" else ""
    return f"{type_context} Apply {mode} weathering effect. Intensity: {intensity:.1f} (0-1). Make it look worn and realistic."


def generate_analyze_prompt(image_type: str, style: str) -> str:
    """Generate prompt for Analysis tab."""
    type_context = f"Input image is a {image_type}." if image_type != "Select Type" else ""
    
    instructions = {
        "Midjourney Prompt": "Analyze this texture and write a highly detailed Midjourney v6 prompt to recreate it. Focus on lighting, material properties, and camera settings. Format: '/imagine prompt: ... --v 6.0'",
        "Flux Prompt": "Analyze this texture and write a natural language prompt optimized for Flux.1 models. Describe the texture flow, details, and atmosphere vividly.",
        "ComfyUI Prompt": "Analyze this texture and provide a comma-separated list of keywords (tags) suitable for Stable Diffusion/ComfyUI positive prompt. Use Danbooru-style tags where applicable. Include material tags, quality tags, and lighting tags.",
    }
    
    instruction = instructions.get(style, "Analyze this texture in detail. Describe its material, pattern, roughness, and suggest PBR settings.")
    return f"{type_context} {instruction} Output text only. Do not generate an image."


def generate_outpaint_prompt(image_type: str, direction: str, scale: float) -> str:
    """Generate prompt for Outpaint tab."""
    type_context = f"Input image is a {image_type}." if image_type != "Select Type" else ""
    return f"{type_context} Outpaint this image. The input image is a crop. Generate a larger, zoomed-out view of this texture/scene, extending the patterns seamlessly in {direction} direction(s) by {scale:.1f}x. Maintain the same resolution and detail level. Fill the new areas naturally matching the existing texture."


def generate_inpaint_prompt(image_type: str, target: str, replace: str) -> str:
    """Generate prompt for Inpaint tab."""
    type_context = f"Input image is a {image_type}." if image_type != "Select Type" else ""
    
    if not target:
        return "Please specify a target object to remove or replace."
    elif not replace:
        return f"{type_context} Remove the '{target}' from this image. Fill the area naturally to match the background."
    else:
        return f"{type_context} Replace the '{target}' with '{replace}' in this image. Blend it naturally with the lighting and perspective."

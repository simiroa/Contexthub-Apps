import os


# Paths
# Paths
# Anchor to this file: src/features/prompt_master/constants.py
# We want to go up to ContextUp root
HEADER_DIR = os.path.dirname(os.path.abspath(__file__)) # src/features/prompt_master
FEATURES_DIR = os.path.dirname(HEADER_DIR)              # src/features
SRC_DIR = os.path.dirname(FEATURES_DIR)                 # src
BASE_DIR = os.path.dirname(SRC_DIR)                     # ContextUp root

PRESETS_DIR = os.path.join(BASE_DIR, "config", "features", "prompt_master", "presets")
TAGS_FILE = os.path.join(BASE_DIR, "config", "features", "prompt_master", "tags", "global_tags.json")
TAG_CATEGORIES_FILE = os.path.join(BASE_DIR, "config", "features", "prompt_master", "tags", "tag_categories.json")

print(f"[PromptMaster] BASE_DIR: {BASE_DIR}")
print(f"[PromptMaster] PRESETS_DIR: {PRESETS_DIR}")

# Engine color themes (for tabs)
ENGINE_COLORS = {
    "Flux": ("#6B4986", "#5E347D"),      # Subdued Purple
    "Midj": ("#A73C2C", "#90291B"),      # Subdued Red
    "Veo3": ("#2478AB", "#196099"),      # Subdued Blue
    "nanobanana": ("#C37C12", "#B66E22"), # Subdued Orange
    "custom": ("#758586", "#5F6C6D")      # Neutral Gray
}

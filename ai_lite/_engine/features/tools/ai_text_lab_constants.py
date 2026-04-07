from contexthub.ui.qt.shell import qt_t

APP_ID = "ai_text_lab"
APP_TITLE = qt_t("ai_text_lab.title", "AI Text Lab Pro")

# Default Model Configuration
DEFAULT_MODEL = "qwen3.5:4b"

# Prompt Instructions
SYSTEM_PROMPT_BASE = "You are a professional editor."
NO_THINK_INSTRUCTION = " (IMPORTANT: Provide a direct response without any internal thinking, chain-of-thought, or <think> tags. Be concise.)"
DIRECT_OUTPUT_PROMPT = " Output only the refined text ohne labels or explanations."

# UI Styling
POPUP_STYLE = """
    QWidget#OpacityPopup {
        background: #181d24;
        border: 1px solid #2a3440;
        border-radius: 8px;
    }
"""

SLIDER_STYLE = """
    QSlider::groove:horizontal {
        height: 4px;
        background: rgba(255, 255, 255, 0.1);
        border-radius: 2px;
    }
    QSlider::handle:horizontal {
        width: 12px;
        height: 12px;
        margin: -4px 0;
        background: #3A82FF;
        border-radius: 6px;
    }
"""

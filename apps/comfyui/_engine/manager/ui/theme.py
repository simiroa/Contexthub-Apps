"""
Centralized UI theme constants for ContextUp Manager.
Extreme Minimal Design: 3 colors only (Gray, Red, Blue)
"""

class Theme:
    # --- Backgrounds ---
    BG_MAIN = ("#f0f2f5", "#020202")         # Deep Dark Background
    BG_SIDEBAR = ("#e3e6e8", "#080808")      # Subdued Sidebar (Slightly brighter than BG)
    BG_SIDEBAR_FOOTER = ("#e3e6e8", "#080808")
    BG_CARD = ("#ffffff", "#0c0c0c")         # Subdued Cards
    BG_DANGER_CARD = ("#fee2e2", "#1a0808")  # Subdued danger
    
    # --- Action Colors: MINIMAL PALETTE ---
    
    # PRIMARY: Only for Apply Changes button (Royal Blue)
    PRIMARY = ("#0123B4", "#0123B4")
    PRIMARY_HOVER = ("#012fdf", "#012fdf")
    
    # STANDARD: Darker Grey for secondary buttons
    STANDARD = ("#4a4a4a", "#1a1a1a")
    STANDARD_HOVER = ("#5a5a5a", "#222222")
    
    # DANGER: Subdued Red
    DANGER = ("#8c2e2e", "#4a1a1a")
    DANGER_HOVER = ("#a63a3a", "#5a2222")
    
    # --- Legacy aliases for compatibility ---
    SUCCESS = STANDARD
    SUCCESS_HOVER = STANDARD_HOVER
    WARNING = STANDARD
    WARNING_HOVER = STANDARD_HOVER
    NEUTRAL = STANDARD
    NEUTRAL_HOVER = STANDARD_HOVER
    GRAY_BTN = STANDARD
    GRAY_BTN_HOVER = STANDARD_HOVER
    
    # --- Text Colors ---
    TEXT_MAIN = ("gray10", "#e0e0e0")
    TEXT_DIM = ("gray40", "#666666")
    TEXT_DANGER = ("#e74c3c", "#e74c3c")      # Vibrant Red for Stop/Error
    TEXT_SUCCESS = ("#2ecc71", "#2ecc71")     # Vibrant Green for On/Success
    
    # --- Accent & Utilities ---
    ACCENT = PRIMARY
    BORDER = ("#d1d5db", "#1a1a1a")

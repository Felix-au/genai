"""
╔══════════════════════════════════════════════════════════════╗
║              CodeMate — Design System / Theme                ║
╚══════════════════════════════════════════════════════════════╝
Dark-mode-first color palette, fonts, and QSS stylesheets.
"""

# ── Color Palette ────────────────────────────────────────────
COLORS = {
    "bg_primary":       "#0D0F14",
    "bg_secondary":     "#141820",
    "bg_card":          "#1A1F2E",
    "bg_card_hover":    "#222840",
    "bg_input":         "#111520",
    "border":           "#2A3040",
    "border_accent":    "#3A4565",
    "text_primary":     "#E8ECF4",
    "text_secondary":   "#8892A8",
    "text_muted":       "#5A6478",
    "accent_cyan":      "#00D4FF",
    "accent_purple":    "#A855F7",
    "accent_green":     "#10B981",
    "accent_orange":    "#F59E0B",
    "accent_red":       "#EF4444",
    "accent_blue":      "#3B82F6",
    "gradient_start":   "#00D4FF",
    "gradient_end":     "#A855F7",
    "bubble_bg":        "#00D4FF",
    "bubble_glow":      "rgba(0, 212, 255, 0.4)",
    "gauge_track":      "#1E2436",
    "success":          "#10B981",
    "warning":          "#F59E0B",
    "error":            "#EF4444",
}

# ── Fonts ────────────────────────────────────────────────────
FONTS = {
    "family": "Segoe UI, Inter, -apple-system, sans-serif",
    "mono": "Cascadia Code, Consolas, 'Courier New', monospace",
    "size_xs": "11px",
    "size_sm": "12px",
    "size_md": "14px",
    "size_lg": "18px",
    "size_xl": "24px",
    "size_xxl": "32px",
    "weight_normal": "400",
    "weight_medium": "500",
    "weight_bold": "700",
}

# ── Dimensions ───────────────────────────────────────────────
DIMS = {
    "radius_sm": "6px",
    "radius_md": "10px",
    "radius_lg": "16px",
    "radius_xl": "20px",
    "spacing_xs": "4px",
    "spacing_sm": "8px",
    "spacing_md": "16px",
    "spacing_lg": "24px",
    "spacing_xl": "32px",
}

# ── Global QSS ──────────────────────────────────────────────
def get_global_stylesheet() -> str:
    return f"""
    * {{
        font-family: {FONTS['family']};
        font-size: {FONTS['size_md']};
        color: {COLORS['text_primary']};
    }}
    QMainWindow, QWidget {{
        background-color: {COLORS['bg_primary']};
    }}
    QLabel {{
        background: transparent;
    }}
    QLabel#title {{
        font-size: {FONTS['size_xl']};
        font-weight: {FONTS['weight_bold']};
        color: {COLORS['accent_cyan']};
    }}
    QLabel#subtitle {{
        font-size: {FONTS['size_sm']};
        color: {COLORS['text_secondary']};
    }}
    QPushButton {{
        background-color: {COLORS['bg_card']};
        border: 1px solid {COLORS['border']};
        border-radius: {DIMS['radius_md']};
        padding: 8px 18px;
        font-weight: {FONTS['weight_medium']};
        color: {COLORS['text_primary']};
    }}
    QPushButton:hover {{
        background-color: {COLORS['bg_card_hover']};
        border-color: {COLORS['accent_cyan']};
    }}
    QPushButton#primary {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 {COLORS['accent_cyan']}, stop:1 {COLORS['accent_purple']});
        color: #FFFFFF;
        border: none;
        font-weight: {FONTS['weight_bold']};
    }}
    QCheckBox {{
        spacing: 8px;
        color: {COLORS['text_primary']};
    }}
    QCheckBox::indicator {{
        width: 20px; height: 20px;
        border-radius: 4px;
        border: 2px solid {COLORS['border_accent']};
        background: {COLORS['bg_input']};
    }}
    QCheckBox::indicator:checked {{
        background: {COLORS['accent_cyan']};
        border-color: {COLORS['accent_cyan']};
    }}
    QScrollArea {{
        border: none;
        background: transparent;
    }}
    QScrollBar:vertical {{
        background: {COLORS['bg_secondary']};
        width: 8px;
        border-radius: 4px;
    }}
    QScrollBar::handle:vertical {{
        background: {COLORS['border_accent']};
        border-radius: 4px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {COLORS['accent_cyan']};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    QTextEdit, QPlainTextEdit {{
        background-color: {COLORS['bg_input']};
        border: 1px solid {COLORS['border']};
        border-radius: {DIMS['radius_md']};
        padding: 10px;
        font-family: {FONTS['mono']};
        font-size: {FONTS['size_sm']};
        color: {COLORS['text_primary']};
        selection-background-color: {COLORS['accent_cyan']};
    }}
    """

def card_style() -> str:
    return f"""
        background-color: {COLORS['bg_card']};
        border: 1px solid {COLORS['border']};
        border-radius: {DIMS['radius_lg']};
        padding: {DIMS['spacing_md']};
    """

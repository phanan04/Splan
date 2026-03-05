"""Color themes (LIGHT / DARK) and QSS generator."""

LIGHT = {
    'bg':             '#E8E8EC',
    'surface':        '#D4D4DA',
    'surface_hover':  '#C8C8D0',
    'surface_active': '#C0C0D0',
    'surface_done':   '#C8DCC8',
    'border':         '#B0B0BC',
    'border_light':   '#F0F0F4',
    'border_subtle':  '#D8D8E0',
    'accent':         '#5B5FC7',
    'accent_hover':   '#4B4FB7',
    'accent_light':   '#D8D8EC',
    'accent_text':    '#FFFFFF',
    'green':          '#22C55E',
    'green_bg':       '#C8DCC8',
    'red':            '#EF4444',
    'red_bg':         '#F0D0D0',
    'orange':         '#E08800',
    'orange_bg':      '#F0E0C0',
    'text':           '#1A1A24',
    'text_secondary': '#3A3A4C',
    'text_muted':     '#5A5A6E',
    'shadow':         (0, 0, 0, 30),
    'shadow_card':    (0, 0, 0, 20),
    'top_gradient_1': '#5B5FC7',
    'top_gradient_2': '#7C3AED',
    'heatmap_0':      '#D4D4DA',
    'heatmap_1':      '#9BE9A8',
    'heatmap_2':      '#40C463',
    'heatmap_3':      '#30A14E',
    'heatmap_4':      '#216E39',
    'gauge_bg':       '#CDCDD4',
    'gauge_tick':     '#9090A0',
    'panel_top':      '#DCDCE2',
    'panel_bot':      '#C4C4CC',
    'title_bg_1':     '#D8D8DE',
    'title_bg_2':     '#B8B8C4',
    'title_text':     '#1A1A24',
    'title_accent':   '#5B5FC7',
}

DARK = {
    'bg':             '#0C0C0C',     # Near-black background
    'surface':        '#1A1A1A',     # Panels
    'surface_hover':  '#252525',
    'surface_active': '#202020',
    'surface_done':   '#0F1C12',
    'border':         '#3A3A3A',     # Metallic border
    'border_light':   '#585858',     # Lighter metallic highlight
    'border_subtle':  '#222222',
    'accent':         '#CC0000',     # MSI Dragon Red
    'accent_hover':   '#E01A00',
    'accent_light':   '#1E0505',
    'accent_text':    '#FFFFFF',
    'green':          '#22E055',     # Neon green
    'green_bg':       '#0C1A10',
    'red':            '#FF2200',
    'red_bg':         '#220A0A',
    'orange':         '#FF7700',
    'orange_bg':      '#2A1500',
    'text':           '#F0F0F0',
    'text_secondary': '#AAAAAA',
    'text_muted':     '#606060',
    'shadow':         (0, 0, 0, 140),
    'shadow_card':    (0, 0, 0, 90),
    'top_gradient_1': '#880000',     # Deep red accent strip
    'top_gradient_2': '#440000',
    'heatmap_0':      '#161616',
    'heatmap_1':      '#3D0A0A',
    'heatmap_2':      '#6B1010',
    'heatmap_3':      '#A01818',
    'heatmap_4':      '#CC2020',
    'gauge_bg':       '#040404',     # Deep-black gauge interior
    'gauge_tick':     '#484848',     # Metallic tick marks
    'panel_top':      '#2A2A2A',     # Gunmetal top
    'panel_bot':      '#141414',     # Near-black bottom
    # extras for the title bar
    'title_bg_1':     '#1E1E1E',
    'title_bg_2':     '#0A0A0A',
    'title_text':     '#FFFFFF',
    'title_accent':   '#CC0000',
}


def _qss(C: dict) -> str:
    return f"""
        * {{ font-family: 'Segoe UI', 'Inter', sans-serif; }}
        QMainWindow {{ background: {C['bg']}; }}
        QScrollArea {{ background: transparent; border: none; }}
        QScrollBar:vertical {{
            background: {C['bg']}; width: 6px; margin: 0; border: none;
        }}
        QScrollBar::handle:vertical {{
            background: {C['border']}; border-radius: 3px; min-height: 30px;
        }}
        QScrollBar::handle:vertical:hover {{ background: {C['text_muted']}; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        QToolTip {{
            background: {C['surface']}; color: {C['text']};
            border: 1px solid {C['border_light']}; padding: 5px 10px;
            font-size: 11px;
        }}
        QCheckBox {{
            spacing: 4px; color: {C['text_secondary']};
            background: transparent;
        }}
        QCheckBox::indicator {{
            width: 13px; height: 13px;
            border: 1px solid {C['border_light']};
            border-radius: 3px;
            background: {C['bg']};
        }}
        QCheckBox::indicator:checked {{
            background: {C['accent']};
            border-color: {C['accent']};
        }}
    """



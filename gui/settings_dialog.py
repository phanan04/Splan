"""Settings dialog: _PillToggle widget and SettingsDialog."""
from PyQt5.QtWidgets import (QDialog, QWidget, QVBoxLayout, QHBoxLayout,
                              QLabel, QPushButton, QFrame, QComboBox,
                              QScrollArea, QStackedWidget, QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QPen, QFont, QCursor

from gui.themes import LIGHT
from i18n import t

class _PillToggle(QWidget):
    """Custom pill-shaped toggle switch drawn via QPainter."""
    toggled = pyqtSignal(bool)

    def __init__(self, checked=False, accent='#CC0000', bg_off=None, parent=None):
        super().__init__(parent)
        self._checked = checked
        self._accent  = accent
        self._bg_off  = bg_off or '#484848'
        self.setFixedSize(46, 26)
        self.setCursor(QCursor(Qt.PointingHandCursor))

    def isChecked(self):        return self._checked
    def setChecked(self, v):
        self._checked = bool(v); self.update()

    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            self._checked = not self._checked
            self.toggled.emit(self._checked)
            self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        r = h / 2
        pad = 3

        # Track
        track = QColor(self._accent if self._checked else self._bg_off)
        p.setPen(Qt.NoPen)
        p.setBrush(track)
        p.drawRoundedRect(0, 0, w, h, r, r)

        # Thumb glow when on
        if self._checked:
            glow = QColor(self._accent); glow.setAlpha(45)
            p.setBrush(glow)
            p.drawRoundedRect(-2, -2, w + 4, h + 4, r + 2, r + 2)
            p.setBrush(QColor(self._accent))
            p.drawRoundedRect(0, 0, w, h, r, r)

        # Thumb
        tx = w - h + pad if self._checked else pad
        p.setBrush(QColor('#FFFFFF'))
        p.setPen(QPen(QColor(0, 0, 0, 30), 0.8))
        p.drawEllipse(int(tx), pad, h - 2 * pad, h - 2 * pad)
        p.end()


class SettingsDialog(QDialog):
    """Settings dialog: sidebar nav + content area, responsive grid cards."""

    _NAV_W = 130   # sidebar width

    def __init__(self, settings: dict, parent=None, colors=None):
        super().__init__(parent)
        self.settings = dict(settings)
        self.C = colors or LIGHT
        C = self.C
        self._toggles: dict[str, _PillToggle] = {}   # key → widget

        self.setWindowTitle(t('settings_title'))
        self.setMinimumSize(460, 420)
        self.resize(580, 520)
        self.setSizeGripEnabled(True)
        self.setStyleSheet(f"""
            QDialog   {{ background: {C['bg']}; }}
            QLabel    {{ background: transparent; }}
            QComboBox {{
                padding: 5px 10px; border: 1px solid {C['border']};
                border-radius: 7px; font-size: 12px;
                background: {C['surface']}; color: {C['text']};
            }}
            QComboBox QAbstractItemView {{
                background: {C['surface']}; border: 1px solid {C['border']};
                color: {C['text']};
                selection-background-color: {C['surface_hover']};
            }}
            QScrollArea {{ background: transparent; border: none; }}
            QScrollBar:vertical {{
                background: {C['bg']}; width: 5px; margin: 0; border: none;
            }}
            QScrollBar::handle:vertical {{
                background: {C['border']}; border-radius: 2px; min-height: 20px;
            }}
        """)

        root = QVBoxLayout(self)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        # ═══ HEADER BAR ═══
        hdr = QFrame()
        hdr.setFixedHeight(52)
        hdr.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 {C.get('title_bg_1', C['surface'])},
                    stop:1 {C.get('title_bg_2', C['bg'])});
                border-bottom: 2px solid {C['accent']};
            }}
        """)
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(20, 0, 20, 0)
        lbl_hdr = QLabel(t('settings_title').upper())
        lbl_hdr.setFont(QFont('Segoe UI', 13, QFont.Bold))
        lbl_hdr.setStyleSheet(f"color: {C['text']}; letter-spacing: 2px;")
        hdr_lay.addWidget(lbl_hdr)
        hdr_lay.addStretch()
        root.addWidget(hdr)

        # ═══ BODY: sidebar + content ═══
        body = QWidget()
        body.setStyleSheet(f"background: {C['bg']};")
        body_lay = QHBoxLayout(body)
        body_lay.setSpacing(0)
        body_lay.setContentsMargins(0, 0, 0, 0)

        # ── Left sidebar ──
        self._sidebar = QFrame()
        self._sidebar.setFixedWidth(self._NAV_W)
        self._sidebar.setStyleSheet(f"""
            QFrame {{
                background: {C.get('panel_bot', C['surface'])};
                border-right: 1px solid {C['border']};
            }}
        """)
        side_lay = QVBoxLayout(self._sidebar)
        side_lay.setSpacing(2)
        side_lay.setContentsMargins(8, 14, 8, 14)

        # ── Right stack ──
        self._stack = QStackedWidget()
        self._stack.setStyleSheet(f"background: {C['surface']};")
        # Nav categories definition
        categories = [
            t('settings_appearance'),
            t('settings_behavior'),
            t('settings_smart'),
        ]
        self._nav_labels = list(categories)   # store for resizeEvent
        self._nav_btns: list[QPushButton] = []

        _nav_base = f"""
            QPushButton {{
                background: transparent;
                color: {C['text_secondary']};
                border: none; border-radius: 8px;
                text-align: left;
                padding: 9px 10px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background: {C['surface_hover']};
                color: {C['text']};
            }}
        """
        _nav_active = f"""
            QPushButton {{
                background: {C['accent']};
                color: #FFFFFF;
                border: none; border-radius: 8px;
                text-align: left;
                padding: 9px 10px;
                font-size: 12px;
                font-weight: 600;
            }}
        """

        def _switch_tab(idx):
            self._stack.setCurrentIndex(idx)
            for i, b in enumerate(self._nav_btns):
                b.setStyleSheet(_nav_active if i == idx else _nav_base)

        for idx, label in enumerate(categories):
            btn = QPushButton(label)
            btn.setFont(QFont('Segoe UI', 11))
            btn.setCursor(QCursor(Qt.PointingHandCursor))
            btn.setStyleSheet(_nav_base)
            btn.clicked.connect(lambda _, i=idx: _switch_tab(i))
            side_lay.addWidget(btn)
            self._nav_btns.append(btn)

        side_lay.addStretch()
        body_lay.addWidget(self._sidebar)
        body_lay.addWidget(self._stack, stretch=1)
        root.addWidget(body, stretch=1)

        # ═══ PAGES ═══
        # helper: build a scrollable page with a grid of cards
        def _make_page():
            page = QWidget()
            page.setStyleSheet(f"background: {C['surface']};")
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.NoFrame)
            scroll.setWidget(page)
            outer = QWidget()
            outer.setStyleSheet(f"background: {C['surface']};")
            ol = QVBoxLayout(outer)
            ol.setContentsMargins(0, 0, 0, 0)
            ol.addWidget(scroll)
            return outer, page

        # helper: build a setting card (toggle)
        def _card_toggle(parent_lay, label, sub, key):
            card = QFrame()
            card.setObjectName('settingCard')
            card.setStyleSheet(f"""
                QFrame#settingCard {{
                    background: {C['surface']};
                    border: 1px solid {C['border']};
                    border-radius: 8px;
                }}
                QFrame#settingCard:hover {{
                    border-color: {C['border_light']};
                    background: {C['surface_hover']};
                }}
                QFrame#settingCard QLabel {{
                    border: none;
                    background: transparent;
                    border-radius: 0;
                }}
            """)
            cl = QHBoxLayout(card)
            cl.setContentsMargins(14, 11, 14, 11)
            cl.setSpacing(12)

            # Text
            txt = QVBoxLayout(); txt.setSpacing(2)
            lbl_m = QLabel(label)
            lbl_m.setFont(QFont('Segoe UI', 11, QFont.DemiBold))
            lbl_m.setStyleSheet(f"color: {C['text']};")
            lbl_s = QLabel(sub)
            lbl_s.setFont(QFont('Segoe UI', 9))
            lbl_s.setStyleSheet(f"color: {C['text_muted']};")
            lbl_s.setWordWrap(True)
            txt.addWidget(lbl_m); txt.addWidget(lbl_s)
            cl.addLayout(txt, stretch=1)

            # Toggle
            sw = _PillToggle(
                checked=self.settings.get(key, False),
                accent=C['accent'],
                bg_off=C['border'],
            )
            sw.toggled.connect(lambda v, k=key: self.settings.update({k: v}))
            cl.addWidget(sw)
            self._toggles[key] = sw
            parent_lay.addWidget(card)
            return sw

        def _card_combo(parent_lay, label, sub, key, items):
            card = QFrame()
            card.setObjectName('settingCard')
            card.setStyleSheet(f"""
                QFrame#settingCard {{
                    background: {C['surface']};
                    border: 1px solid {C['border']};
                    border-radius: 8px;
                }}
                QFrame#settingCard:hover {{
                    border-color: {C['border_light']};
                    background: {C['surface_hover']};
                }}
                QFrame#settingCard QLabel {{
                    border: none;
                    background: transparent;
                    border-radius: 0;
                }}
            """)
            cl = QHBoxLayout(card)
            cl.setContentsMargins(14, 11, 14, 11)
            cl.setSpacing(12)

            txt = QVBoxLayout(); txt.setSpacing(2)
            lbl_m = QLabel(label)
            lbl_m.setFont(QFont('Segoe UI', 11, QFont.DemiBold))
            lbl_m.setStyleSheet(f"color: {C['text']};")
            lbl_s = QLabel(sub)
            lbl_s.setFont(QFont('Segoe UI', 9))
            lbl_s.setStyleSheet(f"color: {C['text_muted']};")
            txt.addWidget(lbl_m); txt.addWidget(lbl_s)
            cl.addLayout(txt, stretch=1)

            combo = QComboBox()
            combo.setFixedWidth(120)
            cur = self.settings.get(key, items[0][1])
            for disp, val in items:
                combo.addItem(disp, val)
                if val == cur:
                    combo.setCurrentIndex(combo.count() - 1)
            combo.currentIndexChanged.connect(
                lambda _, k=key, cb=combo: self.settings.update({k: cb.currentData()}))
            cl.addWidget(combo)
            parent_lay.addWidget(card)

        def _page_layout(page):
            lay = QVBoxLayout(page)
            lay.setSpacing(8)
            lay.setContentsMargins(16, 16, 16, 16)
            return lay

        # ── PAGE 0: Appearance ──
        p0_outer, p0 = _make_page()
        p0_lay = _page_layout(p0)
        _card_toggle(p0_lay, t('settings_dark_mode'),     t('settings_dark_mode_sub'),      'darkMode')
        _card_toggle(p0_lay, t('settings_always_on_top'), t('settings_always_on_top_sub'),  'alwaysOnTop')
        _card_combo( p0_lay, t('settings_lang'),          t('settings_lang_sub'),           'language',
                    [('Tiếng Việt', 'vi'), ('English', 'en')])
        hint = QLabel(t('settings_restart_hint'))
        hint.setFont(QFont('Segoe UI', 8))
        hint.setStyleSheet(f"color: {C['text_muted']}; padding: 4px 2px;")
        p0_lay.addWidget(hint)
        p0_lay.addStretch()
        self._stack.addWidget(p0_outer)

        # ── PAGE 1: Behavior ──
        p1_outer, p1 = _make_page()
        p1_lay = _page_layout(p1)
        _card_toggle(p1_lay, t('settings_autostart'),     t('settings_autostart_sub'),      'autoStart')
        _card_toggle(p1_lay, t('settings_sound'),         t('settings_sound_sub'),          'soundEnabled')
        _card_toggle(p1_lay, t('settings_minimize_tray'), t('settings_minimize_tray_sub'),  'minimizeToTray')
        p1_lay.addStretch()
        self._stack.addWidget(p1_outer)

        # ── PAGE 2: Smart Features ──
        p2_outer, p2 = _make_page()
        p2_lay = _page_layout(p2)
        _card_toggle(p2_lay, t('settings_auto_advance'),  t('settings_auto_advance_sub'),   'autoAdvance')
        _card_toggle(p2_lay, t('settings_smart_break'),   t('settings_smart_break_sub'),    'smartBreakSkip')
        p2_lay.addStretch()
        self._stack.addWidget(p2_outer)

        # Activate first tab
        _switch_tab(0)

        # ═══ FOOTER ═══
        foot = QFrame()
        foot.setFixedHeight(54)
        foot.setStyleSheet(f"""
            QFrame {{
                background: {C.get('panel_bot', C['bg'])};
                border-top: 1px solid {C['border']};
            }}
        """)
        foot_lay = QHBoxLayout(foot)
        foot_lay.setContentsMargins(16, 0, 16, 0)
        foot_lay.addStretch()

        btn_cancel = QPushButton(t('btn_cancel'))
        btn_cancel.setFixedSize(90, 34)
        btn_cancel.setCursor(QCursor(Qt.PointingHandCursor))
        btn_cancel.setFont(QFont('Segoe UI', 10))
        btn_cancel.setStyleSheet(f"""
            QPushButton {{
                background: {C['surface']}; color: {C['text_secondary']};
                border: 1px solid {C['border']}; border-radius: 8px;
            }}
            QPushButton:hover {{ color: {C['text']}; border-color: {C['border_light']}; background: {C['surface_hover']}; }}
            QPushButton:pressed {{ background: {C['bg']}; }}
        """)
        btn_cancel.clicked.connect(self.reject)
        foot_lay.addWidget(btn_cancel)
        foot_lay.addSpacing(8)

        btn_save = QPushButton(t('btn_save'))
        btn_save.setFixedSize(100, 34)
        btn_save.setCursor(QCursor(Qt.PointingHandCursor))
        btn_save.setFont(QFont('Segoe UI', 10, QFont.Bold))
        btn_save.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 {C['accent']}, stop:1 {C['accent_hover']});
                color: #FFFFFF; border: none; border-radius: 8px;
            }}
            QPushButton:hover {{ background: {C['accent_hover']}; }}
            QPushButton:pressed {{ background: {C['accent_hover']}; }}
        """)
        btn_save.clicked.connect(self.accept)
        foot_lay.addWidget(btn_save)
        root.addWidget(foot)

    def resizeEvent(self, ev):
        """Collapse sidebar to abbreviated labels when dialog is narrow."""
        super().resizeEvent(ev)
        narrow = self.width() < 480
        new_w = 40 if narrow else self._NAV_W
        if self._sidebar.width() != new_w:
            self._sidebar.setFixedWidth(new_w)
            short = [t('day_mon')[0], t('day_wed')[0], t('day_fri')[0]]  # M/T/W fallback
            abbrs = ['GD', 'CH', 'TM']   # Giao diện / Chức năng / Thông minh
            for i, btn in enumerate(self._nav_btns):
                if narrow:
                    btn.setText(abbrs[i])
                    btn.setFont(QFont('Segoe UI', 9, QFont.Bold))
                else:
                    btn.setText(self._nav_labels[i])
                    btn.setFont(QFont('Segoe UI', 11))

    def get_settings(self) -> dict:
        return self.settings



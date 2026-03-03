"""
Study Timer GUI v7.0 — Feature-Rich Edition
════════════════════════════════════════════
New in v7:
  1. Per-subject Pomodoro (work/break duration per subject)
  8. Drag & Drop reorder subject cards
  11. ICS calendar export/import (Google Calendar compatible)
  12. Multi-language (Vietnamese / English)
  13. Mini floating timer overlay
  14. GitHub-style activity heatmap in stats
  15. Auto-start timer when scheduled time arrives
"""

import sys, os, json, threading, platform, math, copy
from datetime import datetime, timedelta
from typing import List, Optional

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QScrollArea,
    QDialog, QLineEdit, QSpinBox, QTimeEdit, QFormLayout,
    QMessageBox, QMenu, QAction, QSystemTrayIcon,
    QComboBox, QProgressBar, QShortcut, QGridLayout,
    QGraphicsDropShadowEffect, QCheckBox, QSizePolicy,
    QFileDialog,
)
from PyQt5.QtCore import (
    Qt, QTimer, pyqtSignal, QObject, QTime, QSize, QRectF, QPointF,
    QMimeData, QPoint,
)
from PyQt5.QtGui import (
    QFont, QColor, QCursor, QIcon, QKeySequence,
    QPainter, QLinearGradient, QRadialGradient, QBrush, QPen, QPainterPath,
    QPixmap, QPalette, QDrag,
)

from timetable_manager import TimetableManager
from timer_engine import TimerEngine, TimerState
from icon_generator import create_app_icon, create_tray_icon
from study_stats import StudyStats
from i18n import t, set_language, get_language, get_day_short, get_day_full, LANGUAGES
from calendar_sync import export_ics, import_ics


# ═══════════════════════════════════════════════════════════
#  SETTINGS
# ═══════════════════════════════════════════════════════════
def _user_data_dir() -> str:
    """Return %APPDATA%\\StudyTimer (Windows) or ~/.studytimer (Linux/macOS).
    Created on first access."""
    if platform.system() == 'Windows':
        base = os.environ.get('APPDATA', os.path.expanduser('~'))
    else:
        base = os.path.expanduser('~')
        return os.path.join(base, '.studytimer')
    d = os.path.join(base, 'StudyTimer')
    os.makedirs(d, exist_ok=True)
    return d

_SETTINGS_FILE = os.path.join(_user_data_dir(), 'settings.json')


def _load_settings() -> dict:
    defaults = {
        'darkMode': True,
        'alwaysOnTop': False,
        'soundEnabled': True,
        'minimizeToTray': True,
        'language': 'vi',
        'autoStart': True,
    }
    if os.path.exists(_SETTINGS_FILE):
        try:
            with open(_SETTINGS_FILE, 'r') as f:
                saved = json.load(f)
            defaults.update(saved)
        except Exception:
            pass
    return defaults


def _save_settings(s: dict):
    with open(_SETTINGS_FILE, 'w') as f:
        json.dump(s, f, indent=2)


# ═══════════════════════════════════════════════════════════
#  COLOR THEMES
# ═══════════════════════════════════════════════════════════
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


# ═══════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════
def _shadow(widget, rgba=(0, 0, 0, 18), blur=16, dy=4):
    e = QGraphicsDropShadowEffect(widget)
    e.setBlurRadius(blur)
    e.setColor(QColor(*rgba))
    e.setOffset(0, dy)
    widget.setGraphicsEffect(e)


class SignalEmitter(QObject):
    tick = pyqtSignal(dict)
    state_changed = pyqtSignal(dict)
    notification = pyqtSignal(dict)


def _play_chime(kind='break'):
    def _beep():
        try:
            if platform.system() != 'Windows':
                return
            import winsound
            if kind == 'break':
                for f in [523, 659, 784]:
                    winsound.Beep(f, 180)
            elif kind == 'resume':
                for f in [784, 659, 523]:
                    winsound.Beep(f, 150)
            else:
                winsound.Beep(880, 250)
        except Exception:
            pass
    threading.Thread(target=_beep, daemon=True).start()


SUBJECT_COLORS = [
    '#5B5FC7', '#0EA5E9', '#8B5CF6', '#EC4899',
    '#F59E0B', '#10B981', '#EF4444', '#6366F1',
]


# ═══════════════════════════════════════════════════════════
#  CIRCULAR TIMER WIDGET
# ═══════════════════════════════════════════════════════════
class CircularTimer(QWidget):
    """MSI Afterburner-style gauge with tick marks and arc progress."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(80, 80)
        self.setMaximumSize(220, 220)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self._progress = 0.0
        self._time_text = "00:00"
        self._label = ""
        self._accent = '#5B5FC7'
        self._track = '#E5E7EB'
        self._text_color = '#1D1D1F'
        self._label_color = '#9CA3AF'
        self._gauge_bg = None      # optional dark fill
        self._tick_color = None    # tick mark color

    def sizeHint(self):
        return QSize(150, 150)

    def set_colors(self, accent, track, text_color, label_color):
        self._accent = accent
        self._track = track
        self._text_color = text_color
        self._label_color = label_color
        self.update()

    def set_gauge_style(self, gauge_bg, tick_color):
        """Set gauge background and tick mark colors for Afterburner style."""
        self._gauge_bg = gauge_bg
        self._tick_color = tick_color
        self.update()

    def set_progress(self, v: float):
        self._progress = max(0.0, min(1.0, v))
        self.update()

    def set_time(self, t: str):
        self._time_text = t
        self.update()

    def set_label(self, text: str):
        self._label = text
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        side = min(w, h)
        cx, cy = w / 2, h / 2
        margin = max(8, side * 0.07)
        radius = side / 2 - margin
        ring_w = max(7, side * 0.07)
        time_fs = max(13, int(side * 0.185))
        label_fs = max(7, int(side * 0.068))

        accent_c = QColor(self._accent)
        track_c  = QColor(self._track)

        # Detect light vs dark mode from gauge background luminance
        face_bg = QColor(self._gauge_bg) if self._gauge_bg else QColor('#0A0A0A')
        _r, _g, _b = face_bg.red(), face_bg.green(), face_bg.blue()
        _lum = (_r * 299 + _g * 587 + _b * 114) / 1000
        is_light = _lum > 128

        # ── 1. Outer drop-shadow ring ──
        face_r = radius + ring_w * 0.5 + max(2, side * 0.015)
        shadow_c = QColor(0, 0, 0, 22 if is_light else 60)
        shad_pen = QPen(shadow_c)
        shad_pen.setWidthF(max(2.5, side * 0.02))
        p.setPen(shad_pen)
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QRectF(cx - face_r - 1, cy - face_r - 1,
                             (face_r + 1) * 2, (face_r + 1) * 2))

        # ── 2. Gauge face with off-center radial gradient ──
        rad_grad = QRadialGradient(cx - side * 0.08, cy - side * 0.08,
                                   face_r * 1.3)
        if is_light:
            rad_grad.setColorAt(0.0, QColor('#FFFFFF'))
            rad_grad.setColorAt(0.45, face_bg.lighter(106))
            rad_grad.setColorAt(1.0, face_bg.darker(104))
        else:
            center_col = QColor(min(_r + 22, 255),
                                min(_g + 22, 255),
                                min(_b + 22, 255))
            rad_grad.setColorAt(0.0, center_col)
            rad_grad.setColorAt(0.55, face_bg)
            rad_grad.setColorAt(1.0, face_bg.darker(118))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(rad_grad))
        p.drawEllipse(QRectF(cx - face_r, cy - face_r,
                             face_r * 2, face_r * 2))

        # ── 3. Subtle inner border ring ──
        bdr_c = QColor(accent_c)
        bdr_c.setAlpha(35 if is_light else 55)
        bdr_pen = QPen(bdr_c)
        bdr_pen.setWidthF(max(0.8, side * 0.007))
        p.setPen(bdr_pen)
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QRectF(cx - face_r + 0.5, cy - face_r + 0.5,
                             face_r * 2 - 1, face_r * 2 - 1))

        # ── 4. Track arc ──
        arc_r = radius
        arc_rect = QRectF(cx - arc_r, cy - arc_r, arc_r * 2, arc_r * 2)
        trk_c = QColor(track_c)
        trk_c.setAlpha(48 if is_light else 55)
        trk_pen = QPen(trk_c)
        trk_pen.setWidthF(ring_w)
        trk_pen.setCapStyle(Qt.RoundCap)
        p.setPen(trk_pen)
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(arc_rect)

        # ── 5. Progress arc with glow + endpoint dot ──
        if self._progress > 0.001:
            span = -int(self._progress * 360 * 16)

            # Outer glow
            glow1 = QColor(accent_c); glow1.setAlpha(22)
            gp1 = QPen(glow1); gp1.setWidthF(ring_w + 11)
            gp1.setCapStyle(Qt.RoundCap); p.setPen(gp1)
            p.drawArc(arc_rect, 90 * 16, span)

            # Mid glow
            glow2 = QColor(accent_c); glow2.setAlpha(46)
            gp2 = QPen(glow2); gp2.setWidthF(ring_w + 4)
            gp2.setCapStyle(Qt.RoundCap); p.setPen(gp2)
            p.drawArc(arc_rect, 90 * 16, span)

            # Solid arc
            arc_pen = QPen(accent_c)
            arc_pen.setWidthF(ring_w)
            arc_pen.setCapStyle(Qt.RoundCap)
            p.setPen(arc_pen)
            p.drawArc(arc_rect, 90 * 16, span)

            # Bright endpoint dot
            tip_angle = math.radians(90.0 - self._progress * 360.0)
            tip_x = cx + arc_r * math.cos(tip_angle)
            tip_y = cy - arc_r * math.sin(tip_angle)
            dot_r = ring_w * 0.36
            tip_bright = accent_c.lighter(155)
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(tip_bright))
            p.drawEllipse(QRectF(tip_x - dot_r, tip_y - dot_r,
                                 dot_r * 2, dot_r * 2))

        # ── 6. Minimal tick marks (12 positions, 4 cardinal emphasized) ──
        tick_c = QColor(self._tick_color if self._tick_color else self._track)
        for i in range(12):
            angle_deg = i * 30.0 - 90.0
            angle_rad = math.radians(angle_deg)
            is_cardinal = (i % 3 == 0)
            tl = max(5, side * 0.042) if is_cardinal else max(2.5, side * 0.024)
            tw = max(1.5, side * 0.012) if is_cardinal else max(0.8, side * 0.006)
            r_out = face_r - max(2, side * 0.018)
            r_in  = r_out - tl
            x1 = cx + r_out * math.cos(angle_rad)
            y1 = cy + r_out * math.sin(angle_rad)
            x2 = cx + r_in  * math.cos(angle_rad)
            y2 = cy + r_in  * math.sin(angle_rad)
            tc = QColor(tick_c)
            tc.setAlpha(130 if is_cardinal else 60)
            tp = QPen(tc); tp.setWidthF(tw); tp.setCapStyle(Qt.RoundCap)
            p.setPen(tp)
            p.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        # ── 7. Time text ──
        p.setPen(QColor(self._text_color))
        time_font = QFont("Consolas", time_fs, QFont.Bold)
        p.setFont(time_font)
        th = int(side * 0.28)
        p.drawText(QRectF(0, cy - th * 0.62, w, th),
                   Qt.AlignCenter, self._time_text)

        # ── 8. Label ──
        if self._label:
            p.setPen(QColor(self._label_color))
            lbl_font = QFont("Segoe UI", label_fs, QFont.DemiBold)
            p.setFont(lbl_font)
            p.drawText(QRectF(0, cy + th * 0.42, w, int(side * 0.20)),
                       Qt.AlignCenter, self._label.upper())
        p.end()


# ═══════════════════════════════════════════════════════════
#  HEATMAP WIDGET (Github-style)
# ═══════════════════════════════════════════════════════════
class HeatmapWidget(QWidget):
    """Draws a GitHub-style contribution heatmap."""

    def __init__(self, data: dict, colors: dict, parent=None):
        super().__init__(parent)
        self._data = data  # {'YYYY-MM-DD': minutes, ...}
        self.C = colors
        self.setMinimumHeight(110)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def paintEvent(self, _):
        if not self._data:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        C = self.C

        dates = sorted(self._data.keys())
        values = list(self._data.values())
        max_val = max(values) if values and max(values) > 0 else 1

        cell = 11
        gap = 3
        total = cell + gap
        margin_left = 28
        margin_top = 18

        # Determine how many weeks fit
        w = self.width()
        max_weeks = max(1, (w - margin_left - 10) // total)
        total_days = len(dates)
        weeks_in_data = (total_days + 6) // 7
        weeks = min(weeks_in_data, max_weeks)
        start_idx = max(0, total_days - weeks * 7)

        # Month labels
        p.setPen(QColor(C['text_muted']))
        p.setFont(QFont("Segoe UI", 7))
        last_month = ""
        for i in range(start_idx, len(dates)):
            rel = i - start_idx
            col = rel // 7
            if col >= weeks:
                break
            d = datetime.strptime(dates[i], '%Y-%m-%d')
            mon = d.strftime('%b')
            if mon != last_month and d.day <= 7:
                x = margin_left + col * total
                p.drawText(x, margin_top - 5, mon)
                last_month = mon

        # Day labels
        day_labels = ['', 'M', '', 'W', '', 'F', '']
        for r in range(7):
            if day_labels[r]:
                y = margin_top + r * total + cell - 1
                p.drawText(2, y, day_labels[r])

        # Cells
        for i in range(start_idx, len(dates)):
            rel = i - start_idx
            col = rel // 7
            row = rel % 7
            if col >= weeks:
                break

            v = values[i]
            ratio = v / max_val if max_val > 0 else 0

            if ratio == 0:
                color = QColor(C['heatmap_0'])
            elif ratio < 0.25:
                color = QColor(C['heatmap_1'])
            elif ratio < 0.5:
                color = QColor(C['heatmap_2'])
            elif ratio < 0.75:
                color = QColor(C['heatmap_3'])
            else:
                color = QColor(C['heatmap_4'])

            x = margin_left + col * total
            y = margin_top + row * total
            p.setPen(Qt.NoPen)
            p.setBrush(color)
            p.drawRoundedRect(x, y, cell, cell, 2, 2)

        p.end()


# ═══════════════════════════════════════════════════════════
#  SUBJECT CARD (with drag & drop)
# ═══════════════════════════════════════════════════════════
class SubjectCard(QFrame):
    clicked = pyqtSignal(int)
    edit_requested = pyqtSignal(int)
    delete_requested = pyqtSignal(int)
    drop_reorder = pyqtSignal(int, int)  # from_index, to_index

    def __init__(self, index, subject, start, duration, notes,
                 colors, accent_color='#5B5FC7', pomodoro_info='',
                 parent=None):
        super().__init__(parent)
        self.index = index
        self.subject = subject
        self.start_time = start
        self.duration = duration
        self.notes = notes
        self.C = colors
        self.accent_color = accent_color
        self.pomodoro_info = pomodoro_info
        self.status = 'upcoming'
        self._progress = 0.0
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._ctx_menu)
        self.setAcceptDrops(True)
        self._drag_start = None
        self._build()

    def _build(self):
        C = self.C
        self.setMinimumHeight(64)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Left accent strip ──
        self.accent_strip = QFrame()
        self.accent_strip.setFixedWidth(4)
        self.accent_strip.setStyleSheet(
            f"background: {C['border']}; border: none;"
            f" border-top-left-radius: 6px;"
            f" border-bottom-left-radius: 6px;")
        root.addWidget(self.accent_strip)

        # ── Drag handle ──
        drag_handle = QLabel("⠿")
        drag_handle.setFixedWidth(20)
        drag_handle.setAlignment(Qt.AlignCenter)
        drag_handle.setStyleSheet(
            f"color: {C['text_muted']}; background: transparent;"
            f" border: none; font-size: 14px;")
        drag_handle.setCursor(QCursor(Qt.OpenHandCursor))
        root.addWidget(drag_handle)

        # ── Content ──
        content = QWidget()
        content.setStyleSheet("background: transparent; border: none;")
        cl = QHBoxLayout(content)
        cl.setContentsMargins(8, 12, 12, 12)
        cl.setSpacing(12)

        # Time column
        end_dt = (datetime.strptime(self.start_time, "%H:%M")
                  + timedelta(minutes=self.duration))
        time_w = QWidget()
        time_w.setFixedWidth(50)
        time_w.setStyleSheet("background: transparent; border: none;")
        tl = QVBoxLayout(time_w)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.setSpacing(1)
        t1 = QLabel(self.start_time)
        t1.setFont(QFont("Segoe UI", 11, QFont.DemiBold))
        t1.setStyleSheet(f"color: {C['text']}; border: none; background: transparent;")
        t2 = QLabel(end_dt.strftime('%H:%M'))
        t2.setFont(QFont("Segoe UI", 9))
        t2.setStyleSheet(f"color: {C['text_muted']}; border: none; background: transparent;")
        tl.addWidget(t1)
        tl.addWidget(t2)
        cl.addWidget(time_w)

        # Subject info
        info_w = QWidget()
        info_w.setStyleSheet("background: transparent; border: none;")
        il = QVBoxLayout(info_w)
        il.setContentsMargins(0, 0, 0, 0)
        il.setSpacing(2)
        self.name_label = QLabel(self.subject)
        self.name_label.setFont(QFont("Segoe UI", 12, QFont.DemiBold))
        self.name_label.setStyleSheet(
            f"color: {C['text']}; border: none; background: transparent;")
        il.addWidget(self.name_label)

        meta_parts = [f"{self.duration} {t('minutes_short')}"]
        if self.pomodoro_info:
            meta_parts.append(self.pomodoro_info)
        if self.notes:
            meta_parts.append(self.notes)
        meta = QLabel("  ·  ".join(meta_parts))
        meta.setFont(QFont("Segoe UI", 9))
        meta.setStyleSheet(
            f"color: {C['text_secondary']}; border: none; background: transparent;")
        il.addWidget(meta)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 1000)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(3)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background: {C['border_subtle']}; border: none; border-radius: 1px;
            }}
            QProgressBar::chunk {{
                background: {self.accent_color}; border-radius: 1px;
            }}
        """)
        il.addWidget(self.progress_bar)
        self.progress_bar.hide()

        cl.addWidget(info_w, stretch=1)

        # Status dot
        self.status_dot = QLabel()
        self.status_dot.setFixedSize(10, 10)
        self.status_dot.setStyleSheet(
            f"background: {C['border']}; border-radius: 5px; border: none;")
        cl.addWidget(self.status_dot, alignment=Qt.AlignVCenter)

        # Action buttons
        act_w = QWidget()
        act_w.setStyleSheet("background: transparent; border: none;")
        al = QVBoxLayout(act_w)
        al.setContentsMargins(0, 0, 0, 0)
        al.setSpacing(2)
        for text, tip_key, sig in [
            ("✎", 'ctx_edit', self.edit_requested),
            ("✕", 'ctx_delete', self.delete_requested),
        ]:
            b = QPushButton(text)
            b.setFixedSize(26, 26)
            b.setCursor(QCursor(Qt.PointingHandCursor))
            b.setToolTip(t(tip_key))
            b.setFont(QFont("Segoe UI", 11))
            b.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; border: none;
                    color: {C['text_muted']}; border-radius: 6px;
                }}
                QPushButton:hover {{
                    background: {C['surface_hover']}; color: {C['text']};
                }}
            """)
            idx = self.index
            b.clicked.connect(lambda _, s=sig, i=idx: s.emit(i))
            al.addWidget(b)
        cl.addWidget(act_w)
        root.addWidget(content, stretch=1)
        self._apply_style()

    # ── Drag & Drop ──
    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            self._drag_start = ev.pos()
        super().mousePressEvent(ev)

    def mouseMoveEvent(self, ev):
        if (self._drag_start and
                (ev.pos() - self._drag_start).manhattanLength() > 20):
            drag = QDrag(self)
            mime = QMimeData()
            mime.setText(str(self.index))
            drag.setMimeData(mime)
            # Create semi-transparent pixmap
            pixmap = self.grab()
            pixmap.setDevicePixelRatio(2.0)
            drag.setPixmap(pixmap.scaled(
                pixmap.width() // 2, pixmap.height() // 2,
                Qt.KeepAspectRatio, Qt.SmoothTransformation))
            drag.exec_(Qt.MoveAction)
            self._drag_start = None
            return
        super().mouseMoveEvent(ev)

    def mouseReleaseEvent(self, ev):
        if ev.button() == Qt.LeftButton and self._drag_start:
            if (ev.pos() - self._drag_start).manhattanLength() < 20:
                self.clicked.emit(self.index)
            self._drag_start = None
        super().mouseReleaseEvent(ev)

    def dragEnterEvent(self, ev):
        if ev.mimeData().hasText():
            ev.acceptProposedAction()

    def dropEvent(self, ev):
        try:
            from_idx = int(ev.mimeData().text())
            if from_idx != self.index:
                self.drop_reorder.emit(from_idx, self.index)
        except (ValueError, TypeError):
            pass

    # ── Status / Style ──
    def set_progress(self, ratio):
        self._progress = max(0.0, min(1.0, ratio))
        self.progress_bar.setValue(int(self._progress * 1000))
        if self._progress > 0 and self.status == 'active':
            self.progress_bar.show()

    def set_status(self, status):
        self.status = status
        if status == 'done':
            self.set_progress(1.0)
            self.progress_bar.hide()
        elif status == 'upcoming':
            self.set_progress(0.0)
            self.progress_bar.hide()
        elif status == 'active':
            self.progress_bar.show()
        self._apply_style()

    def _apply_style(self):
        C = self.C
        bl = C.get('border_light', C['border'])
        if self.status == 'done':
            bg, bg2, strip, dot = C['surface_done'], C['surface_done'], C['green'], C['green']
        elif self.status == 'active':
            bg = C['surface_active']
            bg2 = C['surface']
            strip, dot = self.accent_color, self.accent_color
        else:
            bg, bg2, strip, dot = C['surface'], C.get('panel_bot', C['surface']), C['border'], C['text_muted']

        self.setStyleSheet(f"""
            SubjectCard {{
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 {bg}, stop:1 {bg2});
                border: 1px solid {C['border']};
                border-top: 1px solid {bl};
                border-radius: 6px;
            }}
            SubjectCard:hover {{
                background: {C['surface_hover']};
                border-color: {bl};
            }}
        """)
        self.accent_strip.setStyleSheet(
            f"background: {strip}; border: none;"
            f" border-top-left-radius: 6px; border-bottom-left-radius: 6px;")
        self.status_dot.setStyleSheet(
            f"background: {dot}; border-radius: 5px; border: none;")
        blur = 16 if self.status == 'active' else 8
        dy = 3 if self.status == 'active' else 1
        _shadow(self, C['shadow_card'], blur, dy)

    def _ctx_menu(self, pos):
        C = self.C
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background: {C['surface']}; border: 1px solid {C['border']};
                border-radius: 8px; padding: 4px;
            }}
            QMenu::item {{
                padding: 8px 20px; border-radius: 4px; color: {C['text']};
            }}
            QMenu::item:selected {{ background: {C['surface_hover']}; }}
        """)
        e = menu.addAction(t('ctx_edit'))
        d = menu.addAction(t('ctx_delete'))
        action = menu.exec_(self.mapToGlobal(pos))
        if action == e:
            self.edit_requested.emit(self.index)
        elif action == d:
            self.delete_requested.emit(self.index)


# ═══════════════════════════════════════════════════════════
#  SUBJECT DIALOG (with per-subject pomodoro)
# ═══════════════════════════════════════════════════════════
class SubjectDialog(QDialog):
    def __init__(self, parent=None, title_key="dlg_add_title",
                 subject="", duration=60,
                 notes="", work_min=0, break_min=0, colors=None):
        super().__init__(parent)
        C = colors or LIGHT
        title = t(title_key)
        self.setWindowTitle(title)
        self.setMinimumWidth(320)
        self.setMaximumWidth(500)
        self.resize(420, self.sizeHint().height())
        self.setStyleSheet(f"""
            QDialog {{
                background: {C['surface']}; border: 1px solid {C['border']};
            }}
            QLabel {{
                color: {C['text_secondary']}; background: transparent; font-size: 12px;
            }}
            QLineEdit, QSpinBox, QTimeEdit {{
                padding: 8px 12px; border: 1px solid {C['border']};
                border-radius: 8px; font-size: 13px;
                background: {C['bg']}; color: {C['text']};
            }}
            QLineEdit:focus, QSpinBox:focus, QTimeEdit:focus {{
                border-color: {C['accent']};
            }}
            QCheckBox {{
                color: {C['text_secondary']}; background: transparent;
            }}
        """)

        lay = QVBoxLayout(self)
        lay.setSpacing(14)
        lay.setContentsMargins(24, 24, 24, 20)

        h = QLabel(title)
        h.setFont(QFont("Segoe UI", 16, QFont.DemiBold))
        h.setStyleSheet(f"color: {C['text']}; font-size: 16px;")
        lay.addWidget(h)

        form = QFormLayout()
        form.setSpacing(10)

        self.name_input = QLineEdit(subject)
        self.name_input.setPlaceholderText(t('dlg_subject_placeholder'))
        form.addRow(t('dlg_subject_name'), self.name_input)

        self.dur_input = QSpinBox()
        self.dur_input.setRange(5, 480)
        self.dur_input.setSuffix(f" {t('minutes_short')}")
        self.dur_input.setValue(duration)
        self.dur_input.setSingleStep(5)
        form.addRow(t('dlg_duration'), self.dur_input)

        self.notes_input = QLineEdit(notes)
        self.notes_input.setPlaceholderText(t('dlg_notes_placeholder'))
        form.addRow(t('dlg_notes'), self.notes_input)

        lay.addLayout(form)

        # ── Per-subject Pomodoro ──
        pomo_frame = QFrame()
        pomo_frame.setStyleSheet(f"""
            QFrame {{
                background: {C['bg']}; border: 1px solid {C['border']};
                border-radius: 8px;
            }}
        """)
        pl = QVBoxLayout(pomo_frame)
        pl.setContentsMargins(14, 10, 14, 10)
        pl.setSpacing(8)

        ph = QLabel("🍅 Pomodoro")
        ph.setFont(QFont("Segoe UI", 11, QFont.DemiBold))
        ph.setStyleSheet(f"color: {C['text']}; font-size: 11px;")
        pl.addWidget(ph)

        self.cb_default_pomo = QCheckBox(t('dlg_use_default'))
        self.cb_default_pomo.setChecked(work_min == 0 and break_min == 0)
        self.cb_default_pomo.stateChanged.connect(self._toggle_pomo)
        pl.addWidget(self.cb_default_pomo)

        pomo_row = QHBoxLayout()
        pomo_row.setSpacing(10)

        self.work_input = QSpinBox()
        self.work_input.setRange(5, 120)
        self.work_input.setSuffix(f" {t('minutes_short')}")
        self.work_input.setValue(work_min if work_min > 0 else 30)
        self.work_input.valueChanged.connect(self._sync_break_max)
        pomo_row.addWidget(QLabel(t('dlg_work_duration')))
        pomo_row.addWidget(self.work_input)

        self.break_input = QSpinBox()
        self.break_input.setRange(1, max(1, (work_min if work_min > 0 else 30) - 1))
        self.break_input.setSuffix(f" {t('minutes_short')}")
        self.break_input.setValue(min(break_min if break_min > 0 else 5,
                                     max(1, (work_min if work_min > 0 else 30) - 1)))
        pomo_row.addWidget(QLabel(t('dlg_break_duration')))
        pomo_row.addWidget(self.break_input)

        pl.addLayout(pomo_row)
        lay.addWidget(pomo_frame)
        self._toggle_pomo()

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel = QPushButton(t('btn_cancel'))
        cancel.setFixedHeight(36)
        cancel.setCursor(QCursor(Qt.PointingHandCursor))
        cancel.setStyleSheet(f"""
            QPushButton {{
                background: {C['bg']}; color: {C['text_secondary']};
                border: 1px solid {C['border']}; border-radius: 8px;
                padding: 0 20px; font-size: 13px;
            }}
            QPushButton:hover {{ background: {C['surface_hover']}; color: {C['text']}; }}
        """)
        cancel.clicked.connect(self.reject)
        btn_row.addWidget(cancel)

        save = QPushButton(t('btn_save'))
        save.setFixedHeight(36)
        save.setCursor(QCursor(Qt.PointingHandCursor))
        save.setStyleSheet(f"""
            QPushButton {{
                background: {C['accent']}; color: {C['accent_text']};
                border: none; border-radius: 8px;
                padding: 0 24px; font-size: 13px; font-weight: 600;
            }}
            QPushButton:hover {{ background: {C['accent_hover']}; }}
        """)
        save.clicked.connect(self._validate)
        btn_row.addWidget(save)
        lay.addLayout(btn_row)

    def _toggle_pomo(self):
        is_default = self.cb_default_pomo.isChecked()
        self.work_input.setEnabled(not is_default)
        self.break_input.setEnabled(not is_default)

    def _sync_break_max(self, work_val):
        """Keep break < work: cap break_input.max to work - 1."""
        new_max = max(1, work_val - 1)
        self.break_input.setMaximum(new_max)
        if self.break_input.value() > new_max:
            self.break_input.setValue(new_max)

    def _validate(self):
        if not self.name_input.text().strip():
            self.name_input.setStyleSheet(
                "border: 1.5px solid #EF4444; padding: 8px 12px;"
                " border-radius: 8px; font-size: 13px;")
            return
        self.accept()

    def get_data(self):
        is_default = self.cb_default_pomo.isChecked()
        return {
            'subject': self.name_input.text().strip(),
            'duration': self.dur_input.value(),
            'notes': self.notes_input.text().strip(),
            'workMinutes': 0 if is_default else self.work_input.value(),
            'breakMinutes': 0 if is_default else self.break_input.value(),
        }


# ═══════════════════════════════════════════════════════════
#  STATS DIALOG (with heatmap)
# ═══════════════════════════════════════════════════════════
class StatsDialog(QDialog):
    def __init__(self, stats: StudyStats, parent=None, colors=None):
        super().__init__(parent)
        C = colors or LIGHT
        self.setWindowTitle(t('stats_title'))
        self.setMinimumSize(400, 520)
        self.resize(500, 620)
        self.setStyleSheet(f"""
            QDialog {{ background: {C['surface']}; }}
            QLabel {{ color: {C['text']}; background: transparent; }}
        """)

        lay = QVBoxLayout(self)
        lay.setSpacing(12)
        lay.setContentsMargins(24, 24, 24, 20)

        h = QLabel(t('stats_title'))
        h.setFont(QFont("Segoe UI", 16, QFont.DemiBold))
        lay.addWidget(h)

        # Summary cards
        streak = stats.get_streak()
        today_m = stats.get_today_minutes()
        week_m = stats.get_week_minutes()
        total_m = stats.get_total_minutes()

        grid = QGridLayout()
        grid.setSpacing(10)
        cards_data = [
            (f"{streak}", t('stats_streak'), C['accent']),
            (f"{today_m:.0f}", t('stats_today'), C['green']),
            (f"{week_m:.0f}", t('stats_week'), '#0EA5E9'),
            (f"{total_m:.0f}", t('stats_total'), C['orange']),
        ]
        for i, (val, label, color) in enumerate(cards_data):
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background: {C['bg']}; border: 1px solid {C['border']};
                    border-radius: 10px;
                }}
            """)
            cl = QVBoxLayout(card)
            cl.setSpacing(2)
            cl.setContentsMargins(12, 10, 12, 10)
            v = QLabel(val)
            v.setFont(QFont("Segoe UI", 22, QFont.Bold))
            v.setAlignment(Qt.AlignCenter)
            v.setStyleSheet(f"color: {color};")
            cl.addWidget(v)
            lb = QLabel(label)
            lb.setFont(QFont("Segoe UI", 9))
            lb.setAlignment(Qt.AlignCenter)
            lb.setStyleSheet(f"color: {C['text_secondary']};")
            cl.addWidget(lb)
            grid.addWidget(card, i // 2, i % 2)
        lay.addLayout(grid)

        # ── Heatmap ──
        hm_label = QLabel(t('stats_heatmap'))
        hm_label.setFont(QFont("Segoe UI", 12, QFont.DemiBold))
        hm_label.setStyleSheet(f"color: {C['text']}; margin-top: 6px;")
        lay.addWidget(hm_label)

        heatmap_data = stats.get_heatmap_data(weeks=16)
        hm = HeatmapWidget(heatmap_data, C)
        lay.addWidget(hm)

        # Subject breakdown
        breakdown = stats.get_subject_breakdown(days=7)
        if breakdown:
            sh = QLabel(t('stats_7days'))
            sh.setFont(QFont("Segoe UI", 12, QFont.DemiBold))
            sh.setStyleSheet(f"color: {C['text']}; margin-top: 4px;")
            lay.addWidget(sh)

            max_v = max(breakdown.values()) or 1
            bar_colors = [C['accent'], C['green'], '#0EA5E9',
                          C['orange'], C['red'], C['text_secondary']]
            for idx, (subj, mins) in enumerate(list(breakdown.items())[:6]):
                row = QHBoxLayout()
                row.setSpacing(8)
                n = QLabel(subj)
                n.setFont(QFont("Segoe UI", 10))
                n.setFixedWidth(120)
                n.setStyleSheet(f"color: {C['text']};")
                row.addWidget(n)

                bar = QProgressBar()
                bar.setRange(0, int(max_v))
                bar.setValue(int(mins))
                bar.setTextVisible(False)
                bar.setFixedHeight(8)
                bc = bar_colors[idx % len(bar_colors)]
                bar.setStyleSheet(f"""
                    QProgressBar {{
                        background: {C['border_subtle']}; border: none; border-radius: 4px;
                    }}
                    QProgressBar::chunk {{ background: {bc}; border-radius: 4px; }}
                """)
                row.addWidget(bar, stretch=1)

                d = QLabel(f"{mins:.0f}p")
                d.setFont(QFont("Segoe UI", 9))
                d.setStyleSheet(f"color: {C['text_muted']};")
                d.setFixedWidth(36)
                d.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                row.addWidget(d)
                lay.addLayout(row)
        else:
            empty = QLabel(t('stats_no_data'))
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet(f"color: {C['text_muted']}; padding: 20px;")
            lay.addWidget(empty)

        lay.addStretch()

        foot = QLabel(t('stats_sessions', n=stats.get_total_sessions()))
        foot.setFont(QFont("Segoe UI", 9))
        foot.setAlignment(Qt.AlignCenter)
        foot.setStyleSheet(f"color: {C['text_muted']};")
        lay.addWidget(foot)

        close = QPushButton(t('btn_close'))
        close.setFixedHeight(36)
        close.setCursor(QCursor(Qt.PointingHandCursor))
        close.setStyleSheet(f"""
            QPushButton {{
                background: {C['accent']}; color: white;
                border: none; border-radius: 8px;
                padding: 0 24px; font-weight: 600;
            }}
            QPushButton:hover {{ background: {C['accent_hover']}; }}
        """)
        close.clicked.connect(self.accept)
        lay.addWidget(close, alignment=Qt.AlignCenter)


# ═══════════════════════════════════════════════════════════
#  DUPLICATE DAY DIALOG
# ═══════════════════════════════════════════════════════════
class DuplicateDayDialog(QDialog):
    def __init__(self, current_day, parent=None, colors=None):
        super().__init__(parent)
        C = colors or LIGHT
        self.setWindowTitle(t('dup_title'))
        self.setMinimumWidth(300)
        self.setMaximumWidth(440)
        self.resize(340, self.sizeHint().height())
        self.setStyleSheet(f"""
            QDialog {{ background: {C['surface']}; }}
            QLabel {{ color: {C['text']}; background: transparent; }}
            QComboBox {{
                padding: 8px 12px; border: 1px solid {C['border']};
                border-radius: 8px; font-size: 13px;
                background: {C['bg']}; color: {C['text']};
            }}
            QComboBox:focus {{ border-color: {C['accent']}; }}
            QComboBox QAbstractItemView {{
                background: {C['surface']}; border: 1px solid {C['border']};
                color: {C['text']}; selection-background-color: {C['surface_hover']};
            }}
        """)

        lay = QVBoxLayout(self)
        lay.setSpacing(14)
        lay.setContentsMargins(24, 24, 24, 20)

        h = QLabel(t('dup_header', day=get_day_full(current_day)))
        h.setFont(QFont("Segoe UI", 14, QFont.DemiBold))
        lay.addWidget(h)

        hint = QLabel(t('dup_hint'))
        hint.setFont(QFont("Segoe UI", 11))
        hint.setStyleSheet(f"color: {C['text_secondary']};")
        lay.addWidget(hint)

        self.combo = QComboBox()
        for d in TimetableManager.DAY_NAMES:
            if d != current_day:
                self.combo.addItem(get_day_full(d), d)
        lay.addWidget(self.combo)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel = QPushButton(t('btn_cancel'))
        cancel.setFixedHeight(34)
        cancel.setCursor(QCursor(Qt.PointingHandCursor))
        cancel.setStyleSheet(f"""
            QPushButton {{
                background: {C['bg']}; color: {C['text_secondary']};
                border: 1px solid {C['border']}; border-radius: 8px; padding: 0 18px;
            }}
            QPushButton:hover {{ background: {C['surface_hover']}; }}
        """)
        cancel.clicked.connect(self.reject)
        btn_row.addWidget(cancel)

        ok = QPushButton(t('btn_copy'))
        ok.setFixedHeight(34)
        ok.setCursor(QCursor(Qt.PointingHandCursor))
        ok.setStyleSheet(f"""
            QPushButton {{
                background: {C['accent']}; color: white;
                border: none; border-radius: 8px; padding: 0 20px; font-weight: 600;
            }}
            QPushButton:hover {{ background: {C['accent_hover']}; }}
        """)
        ok.clicked.connect(self.accept)
        btn_row.addWidget(ok)
        lay.addLayout(btn_row)

    def get_source_day(self):
        return self.combo.currentData()


# ═══════════════════════════════════════════════════════════
#  MINI FLOATING TIMER (Feature 13)
# ═══════════════════════════════════════════════════════════
class MiniTimerWindow(QWidget):
    """Small frameless always-on-top floating timer."""
    back_requested = pyqtSignal()

    def __init__(self, colors, parent=None):
        super().__init__(parent)
        self.C = colors
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setFixedSize(280, 110)
        self._drag_pos = None
        self._build()

    def _build(self):
        C = self.C
        self.setStyleSheet(f"""
            MiniTimerWindow {{
                background: {C['surface']};
                border: 1px solid {C['border']};
                border-radius: 14px;
            }}
        """)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 8)
        lay.setSpacing(4)

        # Subject + time row
        top = QHBoxLayout()
        self.lbl_subject = QLabel("—")
        self.lbl_subject.setFont(QFont("Segoe UI", 10, QFont.DemiBold))
        self.lbl_subject.setStyleSheet(
            f"color: {C['text']}; background: transparent;")
        self.lbl_subject.setWordWrap(True)
        top.addWidget(self.lbl_subject, stretch=1)

        self.lbl_time = QLabel("00:00")
        self.lbl_time.setFont(QFont("Consolas", 18, QFont.Bold))
        self.lbl_time.setStyleSheet(
            f"color: {C['accent']}; background: transparent;")
        top.addWidget(self.lbl_time)

        self.lbl_subj_time = QLabel("")
        self.lbl_subj_time.setFont(QFont("Consolas", 12, QFont.Bold))
        self.lbl_subj_time.setStyleSheet(
            f"color: {C['green']}; background: transparent;")
        top.addWidget(self.lbl_subj_time)
        lay.addLayout(top)

        # Status + back button
        bot = QHBoxLayout()
        self.lbl_status = QLabel("")
        self.lbl_status.setFont(QFont("Segoe UI", 8))
        self.lbl_status.setStyleSheet(
            f"color: {C['text_muted']}; background: transparent;")
        bot.addWidget(self.lbl_status, stretch=1)

        btn_back = QPushButton(t('mini_back'))
        btn_back.setFixedHeight(22)
        btn_back.setCursor(QCursor(Qt.PointingHandCursor))
        btn_back.setFont(QFont("Segoe UI", 8))
        btn_back.setStyleSheet(f"""
            QPushButton {{
                background: {C['bg']}; color: {C['text_secondary']};
                border: 1px solid {C['border']}; border-radius: 6px;
                padding: 0 8px;
            }}
            QPushButton:hover {{
                background: {C['surface_hover']}; color: {C['text']};
            }}
        """)
        btn_back.clicked.connect(self._on_back)
        bot.addWidget(btn_back)
        lay.addLayout(bot)

    def _on_back(self):
        self.hide()
        self.back_requested.emit()

    def update_display(self, time_str, subject, status, accent_color,
                       subj_remain_str=""):
        self.lbl_time.setText(time_str)
        self.lbl_subject.setText(subject)
        self.lbl_status.setText(status)
        self.lbl_time.setStyleSheet(
            f"color: {accent_color}; background: transparent;")
        self.lbl_subj_time.setText(subj_remain_str)

    def update_theme(self, C):
        self.C = C
        self.setStyleSheet(f"""
            MiniTimerWindow {{
                background: {C['surface']};
                border: 1px solid {C['border']};
                border-radius: 14px;
            }}
        """)
        self.lbl_subject.setStyleSheet(
            f"color: {C['text']}; background: transparent;")
        self.lbl_status.setStyleSheet(
            f"color: {C['text_muted']}; background: transparent;")

    # Draggable
    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            self._drag_pos = ev.globalPos() - self.pos()

    def mouseMoveEvent(self, ev):
        if self._drag_pos and ev.buttons() & Qt.LeftButton:
            self.move(ev.globalPos() - self._drag_pos)

    def mouseReleaseEvent(self, ev):
        self._drag_pos = None


# ═══════════════════════════════════════════════════════════
#  MAIN WINDOW
# ═══════════════════════════════════════════════════════════
class StudyTimerApp(QMainWindow):

    def __init__(self):
        super().__init__()

        self.settings = _load_settings()
        set_language(self.settings.get('language', 'vi'))
        self.C = DARK if self.settings['darkMode'] else LIGHT
        self.setStyleSheet(_qss(self.C))

        self._app_icon = create_app_icon()
        self.setWindowIcon(self._app_icon)
        QApplication.instance().setWindowIcon(self._app_icon)

        # Data
        self.timetable = TimetableManager(self._path('timetable.json'))
        self.stats = StudyStats(self._path('study_history.json'))
        work = self.timetable.get_work_duration()
        brk = self.timetable.get_break_duration()

        # Signal bridge
        self.sig = SignalEmitter()
        self.sig.tick.connect(self._on_tick)
        self.sig.state_changed.connect(self._on_state)
        self.sig.notification.connect(self._on_notif)

        # Timer engine
        self.engine = TimerEngine(
            work_duration_sec=work * 60,
            break_duration_sec=brk * 60,
            on_tick=lambda d: self.sig.tick.emit(d),
            on_state_changed=lambda d: self.sig.state_changed.emit(d),
            on_notification=lambda d: self.sig.notification.emit(d),
        )

        # State
        self.selected_day = datetime.now().strftime('%A')
        self.day_classes: List[dict] = []
        self.cards: List[SubjectCard] = []
        self.active_idx = -1
        self._session_work_secs = 0
        self._subject_elapsed_secs = 0  # Total elapsed for current subject
        self._subject_wall_start: Optional[datetime] = None  # Wall-clock start of current subject
        self._pomo_cycle = 0  # Current pomodoro cycle
        self._auto_started_indices: set = set()  # Track auto-started as (subject, startTime) tuples

        # Mini timer
        self._mini = MiniTimerWindow(self.C)
        self._mini.back_requested.connect(self._close_mini)

        # Auto-refresh + auto-start timer
        self._tick_timer = QTimer()
        self._tick_timer.timeout.connect(self._periodic_check)
        self._tick_timer.start(5_000)

        # Build
        self._build_ui()
        self._setup_shortcuts()
        self._setup_tray()
        self._switch_day(self.selected_day)

        if self.settings.get('alwaysOnTop'):
            self.cb_pin.setChecked(True)

    @staticmethod
    def _bundle_dir():
        """Directory where bundled read-only resources live (temp dir when frozen)."""
        if getattr(sys, 'frozen', False):
            return sys._MEIPASS
        return os.path.dirname(os.path.abspath(__file__))

    @classmethod
    def _path(cls, name):
        """Path for user data file in APPDATA. Auto-copies from bundled example on first run."""
        dest = os.path.join(_user_data_dir(), name)
        if not os.path.exists(dest):
            # Try to seed from bundled example
            example = os.path.join(cls._bundle_dir(), name.replace('.json', '.example.json'))
            if os.path.exists(example):
                import shutil
                shutil.copy2(example, dest)
        return dest

    # ══════════════════════════════════════════════════
    #  SHORTCUTS
    # ══════════════════════════════════════════════════
    def _setup_shortcuts(self):
        QShortcut(QKeySequence(Qt.Key_Space), self, self._toggle_start_pause)
        QShortcut(QKeySequence(Qt.Key_S), self, self._on_stop)
        QShortcut(QKeySequence(Qt.Key_N), self, self._on_skip)
        QShortcut(QKeySequence("Ctrl+N"), self, self._add_subject)
        QShortcut(QKeySequence(Qt.Key_D), self, self._toggle_dark)
        QShortcut(QKeySequence(Qt.Key_M), self, self._open_mini)
        for i, day in enumerate(TimetableManager.DAY_NAMES):
            QShortcut(QKeySequence(str(i + 1)), self,
                      lambda d=day: self._switch_day(d))

    def _toggle_start_pause(self):
        if self.engine.state in (TimerState.IDLE, TimerState.STOPPED):
            self._on_start()
        elif self.engine.state == TimerState.RUNNING:
            self._on_pause()
        elif self.engine.state == TimerState.PAUSED:
            self._on_start()

    # ══════════════════════════════════════════════════
    #  TRAY
    # ══════════════════════════════════════════════════
    def _setup_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self._tray = None
            return
        self._tray = QSystemTrayIcon(self._app_icon, self)
        self._tray.setToolTip("Study Timer")
        self._tray.activated.connect(self._tray_click)

        C = self.C
        menu = QMenu()
        menu.setStyleSheet(f"""
            QMenu {{
                background: {C['surface']}; border: 1px solid {C['border']};
                border-radius: 8px; padding: 4px;
            }}
            QMenu::item {{
                padding: 6px 18px; border-radius: 4px; color: {C['text']};
            }}
            QMenu::item:selected {{ background: {C['surface_hover']}; }}
        """)
        menu.addAction(t('tray_show')).triggered.connect(self._show_from_tray)
        menu.addSeparator()
        menu.addAction(t('tray_start')).triggered.connect(self._on_start)
        menu.addAction(t('tray_pause')).triggered.connect(self._on_pause)
        menu.addSeparator()
        menu.addAction(t('tray_quit')).triggered.connect(self._quit_app)
        self._tray.setContextMenu(menu)
        self._tray.show()

    def _tray_click(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self._show_from_tray()

    def _show_from_tray(self):
        self.showNormal()
        self.activateWindow()

    def _quit_app(self):
        self.engine.stop()
        self._tick_timer.stop()
        self._mini.hide()
        if self._tray:
            self._tray.hide()
        QApplication.instance().quit()

    # ══════════════════════════════════════════════════
    #  DARK MODE
    # ══════════════════════════════════════════════════
    def _toggle_dark(self):
        self.settings['darkMode'] = not self.settings['darkMode']
        _save_settings(self.settings)
        self.C = DARK if self.settings['darkMode'] else LIGHT
        self.setStyleSheet(_qss(self.C))
        self._rebuild_theme()

    def _rebuild_theme(self):
        C = self.C
        pt = C.get('panel_top', C['surface'])
        pb = C.get('panel_bot', C['surface'])
        bl = C.get('border_light', C['border'])
        self.centralWidget().setStyleSheet(f"background: {C['bg']};")

        g1, g2 = C['top_gradient_1'], C['top_gradient_2']
        self.accent_strip.setStyleSheet(
            f"background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 {g1}, stop:0.5 {C['accent']}, stop:1 {g2}); border: none;")

        # Title bar
        _is_dark = self.settings.get('darkMode', True)
        tb1 = C.get('title_bg_1', '#1E1E1E') if _is_dark else '#DCDCE2'
        tb2 = C.get('title_bg_2', '#0A0A0A') if _is_dark else '#C0C0C8'
        self.title_bar.setStyleSheet(f"""
            QFrame#titleBar {{
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 {tb1}, stop:1 {tb2});
                border-bottom: 1px solid {C['accent']};
            }}
        """)
        self.lbl_title_bar.setStyleSheet(
            f"color: {C.get('title_text', C['text'])};"
            f" background: transparent; border: none; letter-spacing: 3px;")

        self.top_frame.setStyleSheet(f"""
            QFrame#topBar {{
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 {pt}, stop:0.5 {C['surface']}, stop:1 {pb});
                border-top: 1px solid {bl};
                border-bottom: 2px solid {C['accent']};
            }}
        """)
        _shadow(self.top_frame, C['shadow'], 24, 6)

        self.timer_circle.set_colors(
            C['accent'], C['border'], C['text'], C['text_muted'])
        self.timer_circle.set_gauge_style(C.get('gauge_bg'), C.get('gauge_tick'))

        self.subject_circle.set_colors(
            C['green'], C['border'], C['text'], C['text_muted'])
        self.subject_circle.set_gauge_style(C.get('gauge_bg'), C.get('gauge_tick'))

        # Center panel
        self.lbl_subject.setStyleSheet(
            f"color: {C['text']}; background: transparent; letter-spacing: 0.5px;")
        self.lbl_status.setStyleSheet(
            f"color: {C['accent']}; background: transparent; letter-spacing: 1.5px;")

        # Center recessed panel
        self.center_panel.setStyleSheet(f"""
            QFrame#centerPanel {{
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 {C['bg']}, stop:1 {C['surface']});
                border: 1px solid {C['border']};
                border-top: 1px solid {bl};
                border-radius: 4px;
            }}
        """)
        _shadow(self.center_panel, C['shadow'], 10, 2)

        self._update_button_states()

        for b in self._util_btns:
            b.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                        stop:0 {C['surface_hover']}, stop:1 {C['surface']});
                    color: {C['text_secondary']};
                    border: 1px solid {C['border']};
                    border-bottom: 2px solid {C['border']};
                    border-radius: 8px; padding: 0;
                    font-size: 13px;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                        stop:0 {C['accent']}, stop:1 {C['accent_hover']});
                    color: #FFFFFF;
                    border-color: {C['accent_hover']};
                }}
                QPushButton:pressed {{
                    background: {C['accent_hover']};
                }}
            """)

        self.lbl_pomo.setStyleSheet(
            f"color: {C['text_muted']}; background: transparent; letter-spacing: 1px;")
        self.lbl_today_total.setStyleSheet(
            f"color: {C['accent']}; background: transparent; letter-spacing: 1px;")

        self.btn_dark.setText('\u2600' if self.settings['darkMode'] else '\U0001f319')
        self.btn_dark.setToolTip(t('btn_light') if self.settings['darkMode'] else t('btn_dark'))

        self._center_divider.setStyleSheet(
            f"background: {C['accent']}; border: none; margin: 0 8px;")

        _cb_style = f"""
            QCheckBox {{
                color: {C['text_secondary']};
                background: transparent;
                spacing: 5px;
                font-size: 12px;
            }}
            QCheckBox::indicator {{
                width: 14px; height: 14px;
                border: 1px solid {C['border']};
                border-radius: 3px;
                background: {C['bg']};
            }}
            QCheckBox::indicator:checked {{
                background: {C['accent']};
                border-color: {C['accent']};
                image: none;
            }}
            QCheckBox::indicator:hover {{
                border-color: {C['accent']};
            }}
        """
        self.cb_pin.setStyleSheet(_cb_style)
        self.cb_auto.setStyleSheet(_cb_style.replace(
            f"background: {C['accent']};\n                border-color: {C['accent']};",
            f"background: {C['orange']};\n                border-color: {C['orange']};"
        ))

        self.tabs_frame.setStyleSheet(f"""
            QFrame#tabStrip {{
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 {pt}, stop:1 {C['surface']});
                border-bottom: 1px solid {C['bg']};
                border-top: 1px solid {bl};
            }}
        """)
        self._style_day_tabs()

        self.btn_dup.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {C['text_muted']};
                border: none; padding: 0 8px;
            }}
            QPushButton:hover {{ color: {C['accent']}; }}
        """)
        self.lbl_day_title.setStyleSheet(
            f"color: {C['text']}; background: transparent;")

        self.body_frame.setStyleSheet(f"background: {C['bg']}; border: none;")
        self.scroll_area.setStyleSheet(f"background: {C['bg']};")
        self.scroll_area.viewport().setStyleSheet(f"background: {C['bg']};")
        self.cards_widget.setStyleSheet(f"background: {C['bg']};")

        self.lbl_summary.setStyleSheet(
            f"color: {C['text_muted']}; background: transparent;")
        self.btn_add.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 {C['surface_hover']}, stop:1 {C['surface']});
                color: {C['text_secondary']};
                border: 1.5px dashed {C['border']};
                border-radius: 6px; font-size: 12px;
            }}
            QPushButton:hover {{
                color: {C['accent']}; border-color: {C['accent']};
                background: {C['accent_light']};
            }}
        """)
        self.lbl_hints.setStyleSheet(
            f"color: {C['text_muted']}; background: transparent;")

        if self._tray and self._tray.contextMenu():
            self._tray.contextMenu().setStyleSheet(f"""
                QMenu {{
                    background: {C['surface']}; border: 1px solid {C['border']};
                    border-radius: 8px; padding: 4px;
                }}
                QMenu::item {{
                    padding: 6px 18px; border-radius: 4px; color: {C['text']};
                }}
                QMenu::item:selected {{ background: {C['surface_hover']}; }}
            """)

        self._mini.update_theme(C)
        self._load_cards()

    # ══════════════════════════════════════════════════
    #  SMART BUTTON STATES
    # ══════════════════════════════════════════════════
    def _update_button_states(self):
        """Update button text, colors, and visibility based on timer state."""
        C = self.C
        state = self.engine.state
        has_subject = self.active_idx >= 0
        br = 3   # tight radius – industrial look

        # ── Primary button (Start / Pause / Resume) ──
        if state == TimerState.RUNNING:
            self.btn_primary.setText(f"⏸  {t('btn_pause')}")
            color = C['orange']
            c_dark = '#AA5500'
        elif state == TimerState.PAUSED:
            self.btn_primary.setText(f"▶  {t('btn_resume')}")
            color = C['green']
            c_dark = '#117733'
        elif state == TimerState.BREAK:
            self.btn_primary.setText(f"⏸  {t('state_break')}")
            color = C['orange']
            c_dark = '#AA5500'
            self.btn_primary.setEnabled(False)
        else:
            self.btn_primary.setText(f"▶  {t('btn_start')}")
            color = C['green']
            c_dark = '#117733'
        if state != TimerState.BREAK:
            self.btn_primary.setEnabled(True)

        self.btn_primary.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 {color}, stop:1 {c_dark});
                color: white;
                border: 1px solid {c_dark};
                border-top: 1px solid {color};
                border-radius: {br}px;
                padding: 0 18px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {color};
                border-color: {color};
            }}
            QPushButton:pressed {{
                background: {c_dark};
                border-top: 2px solid {c_dark};
            }}
            QPushButton:disabled {{
                background: {C['border']}; color: {C['text_muted']};
                border-color: {C['border']};
            }}
        """)

        # ── Stop button ──
        is_active = state in (TimerState.RUNNING, TimerState.PAUSED, TimerState.BREAK)
        self.btn_stop.setVisible(is_active)
        self.btn_stop.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 {C['surface_hover']}, stop:1 {C['bg']});
                color: {C['red']};
                border: 1px solid {C['border']};
                border-bottom: 2px solid {C['border']};
                border-radius: {br}px; padding: 0 14px;
            }}
            QPushButton:hover {{
                background: {C['red_bg']}; border-color: {C['red']};
                color: {C['red']};
            }}
            QPushButton:pressed {{
                background: {C['red_bg']};
                border-bottom: 1px solid {C['border']};
                border-top: 2px solid {C['border']};
            }}
        """)

        # ── Finish button (mark done + advance) ──
        self.btn_finish.setVisible(has_subject and is_active)
        self.btn_finish.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 {C['surface_hover']}, stop:1 {C['bg']});
                color: {C['accent']};
                border: 1px solid {C['border']};
                border-bottom: 2px solid {C['border']};
                border-radius: {br}px; padding: 0 14px;
            }}
            QPushButton:hover {{
                background: {C['accent_light']}; border-color: {C['accent']};
                color: {C['accent']};
            }}
            QPushButton:pressed {{
                background: {C['accent_light']};
                border-bottom: 1px solid {C['border']};
                border-top: 2px solid {C['border']};
            }}
        """)

        # ── Pomodoro cycle label ──
        self.lbl_pomo.setStyleSheet(
            f"color: {C['text_muted']}; background: transparent; letter-spacing: 1px;")

        # ── Today total label ──
        self.lbl_today_total.setStyleSheet(
            f"color: {C['accent']}; background: transparent; letter-spacing: 1px;")
        self._update_today_total()

    def _update_today_total(self):
        """Show today's total study time."""
        today_m = self.stats.get_today_minutes()
        h, m = divmod(int(today_m), 60)
        self.lbl_today_total.setText(t('today_total', h=h, m=m))

    def _update_pomo_label(self):
        """Update pomodoro cycle indicator."""
        if self.active_idx < 0 or self.active_idx >= len(self.day_classes):
            self.lbl_pomo.setText("")
            return
        cls = self.day_classes[self.active_idx]
        work_m = self.timetable.get_subject_work_duration(cls)
        total_cycles = max(1, math.ceil(cls['duration'] / work_m)) if work_m > 0 else 1
        self.lbl_pomo.setText(t('pomo_cycle', cur=self._pomo_cycle, total=total_cycles))

    # ══════════════════════════════════════════════════
    #  LANGUAGE TOGGLE
    # ══════════════════════════════════════════════════
    def _toggle_language(self):
        lang = 'en' if get_language() == 'vi' else 'vi'
        set_language(lang)
        self.settings['language'] = lang
        _save_settings(self.settings)
        # Rebuild entire UI with new language
        self._full_rebuild()

    def _full_rebuild(self):
        """Rebuild UI completely for language change."""
        # Save state
        day = self.selected_day
        pinned = self.settings.get('alwaysOnTop', False)
        geo = self.geometry()

        # Rebuild
        self.C = DARK if self.settings['darkMode'] else LIGHT
        self.setStyleSheet(_qss(self.C))
        self._build_ui()
        self._setup_shortcuts()
        self._switch_day(day)

        if pinned:
            self.cb_pin.setChecked(True)

        self.setGeometry(geo)

    # ══════════════════════════════════════════════════
    #  BUILD UI
    # ══════════════════════════════════════════════════
    def _build_ui(self):
        C = self.C

        central = QWidget()
        central.setStyleSheet(f"background: {C['bg']};")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        # ── Accent strip (thin top bar gradient) ──
        self.accent_strip = QFrame()
        self.accent_strip.setFixedHeight(4)
        g1, g2 = C['top_gradient_1'], C['top_gradient_2']
        self.accent_strip.setStyleSheet(
            f"background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 {g1}, stop:0.5 {C['accent']}, stop:1 {g2}); border: none;")
        root.addWidget(self.accent_strip)

        # ── MSI-style title bar ("STUDY TIMER" centered like "RADEON") ──
        _is_dark = self.settings.get('darkMode', True)
        if _is_dark:
            tb1 = C.get('title_bg_1', '#1E1E1E')
            tb2 = C.get('title_bg_2', '#0A0A0A')
        else:
            tb1 = '#DCDCE2'
            tb2 = '#C0C0C8'
        self.title_bar = QFrame()
        self.title_bar.setObjectName("titleBar")
        self.title_bar.setFixedHeight(30)
        self.title_bar.setStyleSheet(f"""
            QFrame#titleBar {{
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 {tb1}, stop:1 {tb2});
                border-bottom: 1px solid {C['accent']};
            }}
        """)
        tb_lay = QHBoxLayout(self.title_bar)
        tb_lay.setContentsMargins(16, 0, 16, 0)
        tb_lay.setSpacing(8)

        lbl_brand_dot = QLabel("●")
        lbl_brand_dot.setFont(QFont("Segoe UI", 8))
        lbl_brand_dot.setStyleSheet(f"color: {C['accent']}; background: transparent; border: none;")
        tb_lay.addWidget(lbl_brand_dot)

        self.lbl_title_bar = QLabel("STUDY TIMER")
        self.lbl_title_bar.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.lbl_title_bar.setStyleSheet(
            f"color: {C.get('title_text', C['text'])};"
            f" background: transparent; border: none; letter-spacing: 3px;")
        self.lbl_title_bar.setAlignment(Qt.AlignCenter)
        tb_lay.addWidget(self.lbl_title_bar, stretch=1)

        lbl_brand_dot2 = QLabel("●")
        lbl_brand_dot2.setFont(QFont("Segoe UI", 8))
        lbl_brand_dot2.setStyleSheet(f"color: {C['accent']}; background: transparent; border: none;")
        tb_lay.addWidget(lbl_brand_dot2)
        root.addWidget(self.title_bar)

        # ── TOP BAR (metallic panel) ──
        self.top_frame = QFrame()
        self.top_frame.setObjectName("topBar")
        pt = C.get('panel_top', C['surface'])
        pb = C.get('panel_bot', C['surface'])
        bl = C.get('border_light', C['border'])
        self.top_frame.setStyleSheet(f"""
            QFrame#topBar {{
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 {pt}, stop:0.5 {C['surface']}, stop:1 {pb});
                border-top: 1px solid {bl};
                border-bottom: 2px solid {C['accent']};
            }}
        """)
        _shadow(self.top_frame, C['shadow'], 24, 6)

        top_layout = QHBoxLayout(self.top_frame)
        top_layout.setContentsMargins(16, 12, 16, 12)
        top_layout.setSpacing(8)

        # ── Left circle: Pomodoro timer ──
        self.timer_circle = CircularTimer()
        self.timer_circle.set_colors(
            C['accent'], C['border'], C['text'], C['text_muted'])
        self.timer_circle.set_gauge_style(C.get('gauge_bg'), C.get('gauge_tick'))
        top_layout.addWidget(self.timer_circle, alignment=Qt.AlignVCenter)

        # ── Center block: recessed panel like Afterburner center ──
        self.center_panel = QFrame()
        self.center_panel.setObjectName("centerPanel")
        self.center_panel.setStyleSheet(f"""
            QFrame#centerPanel {{
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 {C['bg']}, stop:1 {C['surface']});
                border: 1px solid {C['border']};
                border-top: 1px solid {bl};
                border-radius: 4px;
            }}
        """)
        _shadow(self.center_panel, C['shadow'], 10, 2)
        center_lay = QVBoxLayout(self.center_panel)
        center_lay.setContentsMargins(12, 8, 12, 8)
        center_lay.setSpacing(6)

        # Subject name
        self.lbl_subject = QLabel(t('choose_subject'))
        self.lbl_subject.setFont(QFont("Segoe UI", 13, QFont.Bold))
        self.lbl_subject.setStyleSheet(
            f"color: {C['text']}; background: transparent; letter-spacing: 0.5px;")
        self.lbl_subject.setWordWrap(True)
        self.lbl_subject.setAlignment(Qt.AlignCenter)
        center_lay.addWidget(self.lbl_subject)

        # Status text
        self.lbl_status = QLabel(t('not_started'))
        self.lbl_status.setFont(QFont("Segoe UI", 9, QFont.DemiBold))
        self.lbl_status.setStyleSheet(
            f"color: {C['accent']}; background: transparent; letter-spacing: 2px;")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        center_lay.addWidget(self.lbl_status)

        # ── Control row: action buttons ──
        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(8)
        ctrl_row.addStretch()

        # Primary action button (Start / Pause / Resume)
        self.btn_primary = QPushButton(f"▶  {t('btn_start')}")
        self.btn_primary.setFixedHeight(36)
        self.btn_primary.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_primary.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.btn_primary.clicked.connect(self._toggle_start_pause)
        ctrl_row.addWidget(self.btn_primary)

        # Stop button
        self.btn_stop = QPushButton(f"■  {t('btn_stop')}")
        self.btn_stop.setFixedHeight(36)
        self.btn_stop.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_stop.setFont(QFont("Arial", 9))
        self.btn_stop.clicked.connect(self._on_stop)
        ctrl_row.addWidget(self.btn_stop)

        # Finish (mark done + advance)
        self.btn_finish = QPushButton(f"✓  {t('btn_finish')}")
        self.btn_finish.setFixedHeight(36)
        self.btn_finish.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_finish.setFont(QFont("Arial", 9))
        self.btn_finish.clicked.connect(self._on_skip)
        ctrl_row.addWidget(self.btn_finish)

        ctrl_row.addStretch()
        center_lay.addLayout(ctrl_row)

        # ── Info row: pomodoro cycle + today total (centered below buttons) ──
        info_row = QHBoxLayout()
        info_row.setSpacing(12)
        info_row.addStretch()

        self.lbl_pomo = QLabel("")
        self.lbl_pomo.setFont(QFont("Consolas", 8))
        self.lbl_pomo.setStyleSheet(
            f"color: {C['text_muted']}; background: transparent; letter-spacing: 1px;")
        self.lbl_pomo.setAlignment(Qt.AlignCenter)
        info_row.addWidget(self.lbl_pomo)

        self.lbl_today_total = QLabel("")
        self.lbl_today_total.setFont(QFont("Consolas", 8))
        self.lbl_today_total.setStyleSheet(
            f"color: {C['accent']}; background: transparent; letter-spacing: 1px;")
        self.lbl_today_total.setAlignment(Qt.AlignCenter)
        info_row.addWidget(self.lbl_today_total)

        info_row.addStretch()
        center_lay.addLayout(info_row)

        # Keep a list for resize handler
        self._ctrl_btns = [self.btn_primary, self.btn_stop, self.btn_finish]

        # Apply initial button states
        self._update_button_states()

        # ── Thin divider ──
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setFixedHeight(1)
        divider.setStyleSheet(f"background: {C['border']}; border: none; margin: 0 8px;")
        center_lay.addWidget(divider)
        self._center_divider = divider

        # ── Utility row: compact icon buttons + checkboxes ──
        util_row = QHBoxLayout()
        util_row.setSpacing(5)
        util_row.addStretch()
        self._util_btns = []

        _dark_icon = '☀' if self.settings['darkMode'] else '🌙'
        _dark_tip = t('btn_light') if self.settings['darkMode'] else t('btn_dark')

        _icon_btn_style = f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 {C['surface_hover']}, stop:1 {C['surface']});
                color: {C['text_secondary']};
                border: 1px solid {C['border']};
                border-bottom: 2px solid {C.get('border', C['border'])};
                border-radius: 8px; padding: 0;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 {C['accent']}, stop:1 {C['accent_hover']});
                color: #FFFFFF;
                border-color: {C['accent_hover']};
            }}
            QPushButton:pressed {{
                background: {C['accent_hover']};
                border-top: 2px solid {C.get('border', C['border'])};
                border-bottom: 1px solid {C.get('border', C['border'])};
            }}
        """

        for icon, tip, slot in [
            ('▦', t('btn_stats'), self._show_stats),
            (_dark_icon, _dark_tip, self._toggle_dark),
            ('⧉', t('mini_open'), self._open_mini),
            ('⊕', t('btn_lang'), self._toggle_language),
        ]:
            b = QPushButton(icon)
            b.setToolTip(tip)
            b.setFixedSize(32, 28)
            b.setCursor(QCursor(Qt.PointingHandCursor))
            b.setFont(QFont("Segoe UI", 12))
            b.setStyleSheet(_icon_btn_style)
            b.clicked.connect(slot)
            util_row.addWidget(b)
            self._util_btns.append(b)

        self.btn_dark = self._util_btns[1]

        # Small separator
        sep = QLabel("│")
        sep.setStyleSheet(f"color: {C['border']}; background: transparent;")
        sep.setFont(QFont("Segoe UI", 9))
        util_row.addWidget(sep)
        self._util_sep = sep

        _cb_style = f"""
            QCheckBox {{
                color: {C['text_secondary']};
                background: transparent;
                spacing: 5px;
                font-size: 12px;
            }}
            QCheckBox::indicator {{
                width: 14px; height: 14px;
                border: 1px solid {C['border']};
                border-radius: 3px;
                background: {C['bg']};
            }}
            QCheckBox::indicator:checked {{
                background: {C['accent']};
                border-color: {C['accent']};
                image: none;
            }}
            QCheckBox::indicator:hover {{
                border-color: {C['accent']};
            }}
        """

        self.cb_pin = QCheckBox(t('btn_pin'))
        self.cb_pin.setFont(QFont("Segoe UI", 8))
        self.cb_pin.setStyleSheet(_cb_style)
        self.cb_pin.stateChanged.connect(self._toggle_pin)
        util_row.addWidget(self.cb_pin)

        self.cb_auto = QCheckBox(t('autostart_label'))
        self.cb_auto.setFont(QFont("Segoe UI", 8))
        self.cb_auto.setChecked(self.settings.get('autoStart', True))
        self.cb_auto.setStyleSheet(_cb_style.replace(
            f"background: {C['accent']};\n                border-color: {C['accent']};",
            f"background: {C['orange']};\n                border-color: {C['orange']};"
        ))
        self.cb_auto.stateChanged.connect(self._toggle_autostart)
        util_row.addWidget(self.cb_auto)

        util_row.addStretch()
        center_lay.addLayout(util_row)

        top_layout.addWidget(self.center_panel, stretch=1)

        # ── Right circle: Subject remaining timer ──
        self.subject_circle = CircularTimer()
        self.subject_circle.set_colors(
            C['green'], C['border'], C['text'], C['text_muted'])
        self.subject_circle.set_gauge_style(C.get('gauge_bg'), C.get('gauge_tick'))
        self.subject_circle.set_label(t('subject_remaining_short'))
        top_layout.addWidget(self.subject_circle, alignment=Qt.AlignVCenter)

        root.addWidget(self.top_frame)

        # ── DAY TABS (beveled strip) ──
        self.tabs_frame = QFrame()
        self.tabs_frame.setObjectName("tabStrip")
        self.tabs_frame.setStyleSheet(f"""
            QFrame#tabStrip {{
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 {C.get('panel_top', C['surface'])},
                    stop:1 {C['surface']});
                border-bottom: 1px solid {C['bg']};
                border-top: 1px solid {C.get('border_light', C['border'])};
            }}
        """)
        tabs_lay = QHBoxLayout(self.tabs_frame)
        tabs_lay.setContentsMargins(24, 6, 24, 6)
        tabs_lay.setSpacing(4)

        self.day_buttons = {}
        for day_en in TimetableManager.DAY_NAMES:
            short = get_day_short(day_en)
            btn = QPushButton(short)
            btn.setFixedHeight(30)
            btn.setMinimumWidth(42)
            btn.setCursor(QCursor(Qt.PointingHandCursor))
            btn.setFont(QFont("Segoe UI", 10, QFont.DemiBold))
            btn.clicked.connect(lambda _, d=day_en: self._switch_day(d))
            self.day_buttons[day_en] = btn
            tabs_lay.addWidget(btn)

        tabs_lay.addStretch()

        # ICS export/import buttons
        self._ics_btns = []
        for label_key, slot in [('cal_export', self._export_ics),
                                ('cal_import', self._import_ics)]:
            b = QPushButton(t(label_key))
            b.setFixedHeight(26)
            b.setCursor(QCursor(Qt.PointingHandCursor))
            b.setFont(QFont("Segoe UI", 8))
            b.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; color: {C['text_muted']};
                    border: none; padding: 0 6px;
                }}
                QPushButton:hover {{ color: {C['accent']}; }}
            """)
            b.clicked.connect(slot)
            tabs_lay.addWidget(b)
            self._ics_btns.append(b)

        self.btn_dup = QPushButton(t('copy_schedule'))
        self.btn_dup.setFixedHeight(28)
        self.btn_dup.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_dup.setFont(QFont("Segoe UI", 9))
        self.btn_dup.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {C['text_muted']};
                border: none; padding: 0 8px;
            }}
            QPushButton:hover {{ color: {C['accent']}; }}
        """)
        self.btn_dup.clicked.connect(self._duplicate_day)
        tabs_lay.addWidget(self.btn_dup)

        self.lbl_day_title = QLabel("")
        self.lbl_day_title.setFont(QFont("Segoe UI", 11, QFont.DemiBold))
        self.lbl_day_title.setStyleSheet(
            f"color: {C['text']}; background: transparent;")
        tabs_lay.addWidget(self.lbl_day_title)

        root.addWidget(self.tabs_frame)

        # ── BODY ──
        self.body_frame = QFrame()
        self.body_frame.setStyleSheet(f"background: {C['bg']}; border: none;")
        body_lay = QVBoxLayout(self.body_frame)
        body_lay.setContentsMargins(24, 12, 24, 8)
        body_lay.setSpacing(0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setStyleSheet(f"background: {C['bg']};")
        self.scroll_area.viewport().setStyleSheet(f"background: {C['bg']};")
        self.cards_widget = QWidget()
        self.cards_widget.setStyleSheet(f"background: {C['bg']};")
        self.cards_layout = QVBoxLayout(self.cards_widget)
        self.cards_layout.setSpacing(8)
        self.cards_layout.setContentsMargins(0, 0, 4, 0)
        self.cards_layout.addStretch()
        self.scroll_area.setWidget(self.cards_widget)
        body_lay.addWidget(self.scroll_area, stretch=1)

        self.btn_add = QPushButton(t('add_subject'))
        self.btn_add.setFixedHeight(40)
        self.btn_add.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_add.setFont(QFont("Segoe UI", 11))
        self.btn_add.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 {C['surface_hover']}, stop:1 {C['surface']});
                color: {C['text_secondary']};
                border: 1.5px dashed {C['border']};
                border-radius: 6px; font-size: 12px;
            }}
            QPushButton:hover {{
                color: {C['accent']}; border-color: {C['accent']};
                background: {C['accent_light']};
            }}
        """)
        self.btn_add.clicked.connect(self._add_subject)
        body_lay.addWidget(self.btn_add)

        self.lbl_summary = QLabel("")
        self.lbl_summary.setFont(QFont("Segoe UI", 9))
        self.lbl_summary.setStyleSheet(
            f"color: {C['text_muted']}; background: transparent;")
        self.lbl_summary.setAlignment(Qt.AlignCenter)
        body_lay.addWidget(self.lbl_summary)

        self.lbl_hints = QLabel(t('hints'))
        self.lbl_hints.setFont(QFont("Segoe UI", 8))
        self.lbl_hints.setAlignment(Qt.AlignCenter)
        self.lbl_hints.setStyleSheet(
            f"color: {C['text_muted']}; background: transparent; padding: 2px 0;")
        body_lay.addWidget(self.lbl_hints)

        root.addWidget(self.body_frame, stretch=1)

        self.setWindowTitle(t('app_title'))
        self.setMinimumSize(380, 520)
        self.resize(600, 780)
        self._last_layout_mode = None

    # ══════════════════════════════════════════════════
    #  RESPONSIVE RESIZE
    # ══════════════════════════════════════════════════
    def resizeEvent(self, event):
        super().resizeEvent(event)
        w = self.width()

        if w < 500:
            mode = 'compact'
        elif w < 750:
            mode = 'normal'
        else:
            mode = 'wide'

        timer_size = (max(90, min(110, int(w * 0.24))) if w < 500
                      else max(120, min(160, int(w * 0.22))) if w < 750
                      else max(160, min(220, int(w * 0.2))))
        self.timer_circle.setFixedSize(timer_size, timer_size)
        self.subject_circle.setFixedSize(timer_size, timer_size)
        # Hide subject circle in very narrow mode to save space
        self.subject_circle.setVisible(w >= 460)

        if w < 500:
            self.top_frame.layout().setContentsMargins(12, 8, 12, 8)
            self.top_frame.layout().setSpacing(8)
        elif w < 750:
            self.top_frame.layout().setContentsMargins(18, 12, 18, 12)
            self.top_frame.layout().setSpacing(12)
        else:
            self.top_frame.layout().setContentsMargins(28, 16, 28, 16)
            self.top_frame.layout().setSpacing(20)

        if w < 500:
            self.lbl_subject.setFont(QFont("Segoe UI", 11, QFont.DemiBold))
            self.lbl_status.setFont(QFont("Segoe UI", 9))
        elif w < 750:
            self.lbl_subject.setFont(QFont("Segoe UI", 13, QFont.DemiBold))
            self.lbl_status.setFont(QFont("Segoe UI", 10))
        else:
            self.lbl_subject.setFont(QFont("Segoe UI", 15, QFont.DemiBold))
            self.lbl_status.setFont(QFont("Segoe UI", 11))

        ctrl_h = 28 if w < 500 else (32 if w < 750 else 36)
        ctrl_font_primary = 9 if w < 500 else (10 if w < 750 else 11)
        ctrl_font_secondary = 8 if w < 500 else (9 if w < 750 else 10)
        self._btn_pad_primary = 10 if w < 500 else (14 if w < 750 else 18)
        self._btn_pad_secondary = 8 if w < 500 else (10 if w < 750 else 14)
        self._btn_radius = 6 if w < 500 else 8
        for b in self._ctrl_btns:
            b.setFixedHeight(ctrl_h)
        self.btn_primary.setFont(QFont("Segoe UI", ctrl_font_primary, QFont.DemiBold))
        self.btn_stop.setFont(QFont("Segoe UI", ctrl_font_secondary))
        self.btn_finish.setFont(QFont("Segoe UI", ctrl_font_secondary))
        self._update_button_states()

        # Pomo & today-total labels
        pomo_fs = 8 if w < 500 else (9 if w < 750 else 10)
        self.lbl_pomo.setFont(QFont("Segoe UI", pomo_fs))
        self.lbl_pomo.setVisible(w >= 420)
        today_fs = 7 if w < 500 else (8 if w < 750 else 9)
        self.lbl_today_total.setFont(QFont("Segoe UI", today_fs))
        self.lbl_today_total.setVisible(w >= 460)

        if w < 500:
            self.tabs_frame.layout().setContentsMargins(8, 4, 8, 4)
            self.tabs_frame.layout().setSpacing(2)
        elif w < 750:
            self.tabs_frame.layout().setContentsMargins(16, 6, 16, 6)
            self.tabs_frame.layout().setSpacing(4)
        else:
            self.tabs_frame.layout().setContentsMargins(28, 8, 28, 8)
            self.tabs_frame.layout().setSpacing(6)

        tab_h = 26 if w < 500 else (30 if w < 750 else 34)
        tab_min_w = 32 if w < 500 else (42 if w < 750 else 52)
        tab_fs = 8 if w < 500 else (9 if w < 750 else 10)
        for btn in self.day_buttons.values():
            btn.setFixedHeight(tab_h)
            btn.setMinimumWidth(tab_min_w)
            btn.setFont(QFont("Segoe UI", tab_fs, QFont.DemiBold))

        # ICS buttons, btn_dup, lbl_day_title
        ics_fs = 7 if w < 500 else 8
        for b in self._ics_btns:
            b.setFont(QFont("Segoe UI", ics_fs))
            b.setFixedHeight(22 if w < 500 else 26)
            b.setVisible(w >= 440)
        dup_fs = 8 if w < 500 else 9
        self.btn_dup.setFont(QFont("Segoe UI", dup_fs))
        self.btn_dup.setFixedHeight(24 if w < 500 else 28)
        self.btn_dup.setVisible(w >= 440)
        day_title_fs = 9 if w < 500 else (10 if w < 750 else 11)
        self.lbl_day_title.setFont(QFont("Segoe UI", day_title_fs, QFont.DemiBold))

        if w < 500:
            self.body_frame.layout().setContentsMargins(8, 8, 8, 4)
        elif w < 750:
            self.body_frame.layout().setContentsMargins(18, 10, 18, 6)
        else:
            self.body_frame.layout().setContentsMargins(28, 14, 28, 8)

        self.btn_add.setFixedHeight(34 if w < 500 else 40)
        add_fs = 10 if w < 500 else 11
        self.btn_add.setFont(QFont("Segoe UI", add_fs))
        self.lbl_hints.setVisible(w >= 500)
        summary_fs = 8 if w < 500 else 9
        self.lbl_summary.setFont(QFont("Segoe UI", summary_fs))

        util_sz = 24 if w < 500 else (28 if w < 750 else 32)
        util_icon_fs = 9 if w < 500 else (10 if w < 750 else 12)
        util_cb_fs = 7 if w < 500 else (8 if w < 750 else 9)
        for b in self._util_btns:
            b.setFixedSize(util_sz, util_sz)
            b.setFont(QFont("Segoe UI", util_icon_fs))
        self.cb_pin.setFont(QFont("Segoe UI", util_cb_fs))
        self.cb_auto.setFont(QFont("Segoe UI", util_cb_fs))
        self._util_sep.setFont(QFont("Segoe UI", util_cb_fs))
        # Hide utility row items in very compact mode
        show_util = w >= 400
        for b in self._util_btns:
            b.setVisible(show_util)
        self._util_sep.setVisible(show_util)
        self.cb_pin.setVisible(show_util)
        self.cb_auto.setVisible(show_util)

        self._last_layout_mode = mode

    # ══════════════════════════════════════════════════
    #  DAY TABS
    # ══════════════════════════════════════════════════
    def _switch_day(self, day):
        self.selected_day = day
        self._auto_started_indices.clear()
        self._style_day_tabs()
        self._load_cards()

    def _style_day_tabs(self):
        C = self.C
        bl = C.get('border_light', C['border'])
        today = datetime.now().strftime('%A')
        for d, btn in self.day_buttons.items():
            if d == self.selected_day:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                            stop:0 {C['accent']}, stop:1 {C['accent_hover']});
                        color: white; border: 1px solid {C['accent']};
                        border-radius: 4px; padding: 0 8px;
                    }}
                """)
            elif d == today:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {C['accent_light']};
                        color: {C['accent']};
                        border: 1px solid {C['accent']};
                        border-radius: 4px; padding: 0 8px;
                    }}
                    QPushButton:hover {{ background: {C['surface_hover']}; }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                            stop:0 {C['surface_hover']}, stop:1 {C['surface']});
                        color: {C['text_secondary']};
                        border: 1px solid {C['border']};
                        border-radius: 4px; padding: 0 8px;
                    }}
                    QPushButton:hover {{
                        background: {C['surface_hover']};
                        color: {C['text']}; border-color: {bl};
                    }}
                """)

        full = get_day_full(self.selected_day)
        sfx = f"  ·  {t('today')}" if self.selected_day == today else ""
        self.lbl_day_title.setText(f"{full}{sfx}")

    # ══════════════════════════════════════════════════
    #  LOAD CARDS
    # ══════════════════════════════════════════════════
    def _load_cards(self):
        # If timer is running while cards are being reloaded (e.g. CRUD),
        # stop the session cleanly so state doesn't get corrupted.
        if self.engine.state in (TimerState.RUNNING, TimerState.PAUSED,
                                  TimerState.BREAK):
            self._log_session()
            self.engine.stop()
            self._session_work_secs = 0
            self._subject_elapsed_secs = 0
            self._subject_wall_start = None
            self._pomo_cycle = 0
            self.timer_circle.set_time("00:00")
            self.timer_circle.set_progress(0)
            self.timer_circle.set_label("")
            self.subject_circle.set_time("00:00")
            self.subject_circle.set_progress(0)
            self.lbl_pomo.setText("")

        C = self.C
        self.day_classes = self.timetable.get_schedule_for_day(self.selected_day)
        self.cards.clear()
        self.active_idx = -1

        while self.cards_layout.count() > 0:
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self.day_classes:
            lbl = QLabel(t('no_subjects'))
            lbl.setFont(QFont("Segoe UI", 13))
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(
                f"color: {C['text_muted']}; padding: 40px; background: transparent;")
            self.cards_layout.addWidget(lbl)

            hint = QLabel(t('no_subjects_hint'))
            hint.setFont(QFont("Segoe UI", 10))
            hint.setAlignment(Qt.AlignCenter)
            hint.setStyleSheet(
                f"color: {C['text_muted']}; background: transparent;")
            self.cards_layout.addWidget(hint)
        else:
            for i, cls in enumerate(self.day_classes):
                ac = SUBJECT_COLORS[i % len(SUBJECT_COLORS)]

                # Per-subject pomodoro info
                wm = cls.get('workMinutes', 0)
                bm = cls.get('breakMinutes', 0)
                pomo_info = ''
                if wm or bm:
                    pomo_info = f"🍅 {wm or self.timetable.get_work_duration()}/{bm or self.timetable.get_break_duration()}"

                card = SubjectCard(
                    index=i, subject=cls['subject'],
                    start=cls['startTime'], duration=cls['duration'],
                    notes=cls.get('notes', ''), colors=C,
                    accent_color=ac, pomodoro_info=pomo_info,
                )
                card.clicked.connect(self._on_card_click)
                card.edit_requested.connect(self._edit_subject)
                card.delete_requested.connect(self._delete_subject)
                card.drop_reorder.connect(self._on_reorder)
                self.cards_layout.addWidget(card)
                self.cards.append(card)

        self.cards_layout.addStretch()
        self._update_summary()

        if self.selected_day == datetime.now().strftime('%A'):
            self._auto_detect()

    def _update_summary(self):
        n = len(self.day_classes)
        if n == 0:
            self.lbl_summary.setText("")
            return
        total = sum(c['duration'] for c in self.day_classes)
        h, m = divmod(total, 60)
        streak = self.stats.get_streak()
        st = t('streak_fmt', d=streak) if streak > 0 else ""
        self.lbl_summary.setText(
            t('summary_fmt', n=n, h=h, m=m,
              w=self.timetable.get_work_duration(), streak=st))

    # ══════════════════════════════════════════════════
    #  PERIODIC CHECK (auto-detect + auto-start)
    # ══════════════════════════════════════════════════
    def _periodic_check(self):
        if self.selected_day == datetime.now().strftime('%A'):
            self._auto_detect()
            if self.settings.get('autoStart', True):
                self._try_auto_start()

    def _auto_detect(self):
        if self.selected_day != datetime.now().strftime('%A'):
            return
        # Never change active_idx while timer is running — that would corrupt
        # subject_circle / _subject_elapsed_secs for the current subject.
        timer_active = self.engine.state in (
            TimerState.RUNNING, TimerState.PAUSED, TimerState.BREAK)
        now = datetime.now()
        found = False
        for i, cls in enumerate(self.day_classes):
            s = datetime.combine(
                now.date(),
                datetime.strptime(cls['startTime'], '%H:%M').time())
            e = s + timedelta(minutes=cls['duration'])
            if i < len(self.cards):
                if e <= now:
                    if not timer_active or i != self.active_idx:
                        self.cards[i].set_status('done')
                elif s <= now <= e and not found:
                    found = True
                    if not timer_active:
                        self.cards[i].set_status('active')
                        elapsed = (now - s).total_seconds()
                        total_s = cls['duration'] * 60
                        self.cards[i].set_progress(elapsed / total_s)
                        self.active_idx = i
                        self._show_subject(i)
                    # If timer is active, just mark visual without changing active_idx
                    elif i != self.active_idx:
                        self.cards[i].set_status('active')
                else:
                    if not timer_active or i != self.active_idx:
                        self.cards[i].set_status('upcoming')
        if not found and not timer_active:
            for i, c in enumerate(self.cards):
                if c.status == 'upcoming':
                    self.active_idx = i
                    self._show_subject(i)
                    break

    # ── Feature 15: Auto-start ──
    def _try_auto_start(self):
        """Auto-start timer when a subject's scheduled time arrives."""
        if self.engine.state in (TimerState.RUNNING, TimerState.BREAK):
            return  # Already running
        now = datetime.now()
        for i, cls in enumerate(self.day_classes):
            key = (cls['subject'], cls['startTime'])
            if key in self._auto_started_indices:
                continue
            s = datetime.combine(
                now.date(),
                datetime.strptime(cls['startTime'], '%H:%M').time())
            # Within the first 60 seconds of start time
            if s <= now <= s + timedelta(seconds=60):
                self._auto_started_indices.add(key)
                self._on_card_click(i)  # This now auto-starts the timer

                if self._tray and self._tray.isVisible():
                    self._tray.showMessage(
                        t('autostart_notif_title'),
                        t('autostart_notif_msg', subject=cls['subject']),
                        QSystemTrayIcon.Information, 3000)
                break

    def _toggle_autostart(self):
        self.settings['autoStart'] = self.cb_auto.isChecked()
        _save_settings(self.settings)

    # ══════════════════════════════════════════════════
    #  DRAG & DROP REORDER
    # ══════════════════════════════════════════════════
    def _on_reorder(self, from_idx, to_idx):
        # Swap subject content while keeping each time slot fixed
        self.timetable.swap_subject_content(self.selected_day, from_idx, to_idx)
        self._load_cards()

    # ══════════════════════════════════════════════════
    #  CRUD
    # ══════════════════════════════════════════════════
    def _add_subject(self):
        # Auto-calculate start time: end of last subject, or current time
        classes = self.timetable.get_schedule_for_day(self.selected_day)
        if classes:
            last = classes[-1]
            last_start = datetime.strptime(last['startTime'], '%H:%M')
            auto_start = (last_start + timedelta(minutes=last['duration'])).strftime('%H:%M')
        else:
            auto_start = datetime.now().strftime('%H:%M')

        dlg = SubjectDialog(self, title_key="dlg_add_title", colors=self.C)
        if dlg.exec_() == QDialog.Accepted:
            d = dlg.get_data()
            self.timetable.add_subject(
                self.selected_day, d['subject'],
                auto_start, d['duration'], d['notes'],
                d['workMinutes'], d['breakMinutes'])
            self._load_cards()

    def _edit_subject(self, index):
        cls = self.day_classes[index]
        dlg = SubjectDialog(
            self, title_key="dlg_edit_title",
            subject=cls['subject'],
            duration=cls['duration'],
            notes=cls.get('notes', ''),
            work_min=cls.get('workMinutes', 0),
            break_min=cls.get('breakMinutes', 0),
            colors=self.C,
        )
        if dlg.exec_() == QDialog.Accepted:
            d = dlg.get_data()
            # Keep original start time; only duration/name/notes/pomo can change
            self.timetable.edit_subject(
                self.selected_day, index,
                d['subject'], cls['startTime'], d['duration'], d['notes'],
                d['workMinutes'], d['breakMinutes'])
            # Cascade: fix start times of all subsequent subjects
            self.timetable.cascade_start_times(self.selected_day, index + 1)
            self._load_cards()

    def _delete_subject(self, index):
        cls = self.day_classes[index]
        reply = QMessageBox.question(
            self, t('delete_title'),
            t('delete_confirm', subject=cls['subject'], time=cls['startTime']),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.timetable.delete_subject(self.selected_day, index)
            self._load_cards()

    def _duplicate_day(self):
        dlg = DuplicateDayDialog(self.selected_day, parent=self, colors=self.C)
        if dlg.exec_() == QDialog.Accepted:
            src = dlg.get_source_day()
            self.timetable.duplicate_day(src, self.selected_day)
            self._load_cards()

    def _show_stats(self):
        self.stats._load()  # Refresh data
        dlg = StatsDialog(self.stats, parent=self, colors=self.C)
        dlg.exec_()

    # ══════════════════════════════════════════════════
    #  ICS EXPORT / IMPORT
    # ══════════════════════════════════════════════════
    def _export_ics(self):
        path, _ = QFileDialog.getSaveFileName(
            self, t('cal_export'), "study_schedule.ics",
            "iCalendar Files (*.ics)")
        if path:
            export_ics(self.timetable.schedule, path)
            QMessageBox.information(self, t('cal_export'), t('cal_export_ok'))

    def _import_ics(self):
        path, _ = QFileDialog.getOpenFileName(
            self, t('cal_import'), "",
            "iCalendar Files (*.ics)")
        if path:
            try:
                schedule = import_ics(path)
                # Merge into existing schedule
                for day, classes in schedule.items():
                    for cls in classes:
                        self.timetable.add_subject(
                            day, cls['subject'], cls['startTime'],
                            cls['duration'], cls.get('notes', ''))
                self._load_cards()
                QMessageBox.information(
                    self, t('cal_import'), t('cal_import_ok'))
            except Exception as e:
                QMessageBox.warning(
                    self, t('cal_import_fail'), str(e))

    # ══════════════════════════════════════════════════
    #  MINI TIMER
    # ══════════════════════════════════════════════════
    def _open_mini(self):
        self._mini.show()
        # Position near bottom-right of screen
        screen = QApplication.desktop().availableGeometry()
        self._mini.move(
            screen.width() - self._mini.width() - 30,
            screen.height() - self._mini.height() - 60)

    def _close_mini(self):
        self._mini.hide()
        self.showNormal()
        self.activateWindow()

    # ══════════════════════════════════════════════════
    #  CARD / TIMER ACTIONS
    # ══════════════════════════════════════════════════
    def _calc_elapsed_if_in_window(self, cls):
        """If current time is within the subject's scheduled window,
        return elapsed seconds since startTime; otherwise 0."""
        try:
            now = datetime.now()
            start_dt = now.replace(
                hour=int(cls['startTime'].split(':')[0]),
                minute=int(cls['startTime'].split(':')[1]),
                second=0, microsecond=0)
            end_dt = start_dt + timedelta(minutes=cls['duration'])
            if start_dt <= now <= end_dt:
                return int((now - start_dt).total_seconds())
        except Exception:
            pass
        return 0

    def _on_card_click(self, index):
        self._log_session()
        self.engine.stop()
        for c in self.cards:
            if c.status != 'done':
                c.set_status('upcoming')
        self.cards[index].set_status('active')
        self.active_idx = index
        self._session_work_secs = 0
        self._pomo_cycle = 0

        # Apply per-subject pomodoro duration
        cls = self.day_classes[index]
        wm = self.timetable.get_subject_work_duration(cls)
        bm = self.timetable.get_subject_break_duration(cls)
        self.engine.work_duration_sec = wm * 60
        self.engine.break_duration_sec = bm * 60

        # Auto-calc elapsed time if within scheduled window
        elapsed = self._calc_elapsed_if_in_window(cls)
        self._subject_elapsed_secs = elapsed
        # Record wall-clock start (back-dated by already-elapsed time)
        self._subject_wall_start = datetime.now() - timedelta(seconds=elapsed)

        self._show_subject(index)
        self.timer_circle.set_time("00:00")
        self.timer_circle.set_progress(0)

        # Set subject circle initial state
        if elapsed > 0:
            total_s = cls['duration'] * 60
            subj_remain = max(0, total_s - elapsed)
            rm, rs = divmod(subj_remain, 60)
            self.subject_circle.set_time(f"{rm:02d}:{rs:02d}")
            self.subject_circle.set_progress(
                max(0, min(1, elapsed / total_s)))
            self.cards[index].set_progress(
                max(0, min(1, elapsed / total_s)))
        else:
            total_s = cls['duration'] * 60
            rm, rs = divmod(total_s, 60)
            self.subject_circle.set_time(f"{rm:02d}:{rs:02d}")
            self.subject_circle.set_progress(0)
        self.subject_circle.set_label(t('subject_remaining_short'))

        # Auto-start on card click
        self.engine.start()
        self._pomo_cycle = 1
        self._update_pomo_label()
        self._update_button_states()

    def _show_subject(self, index):
        if 0 <= index < len(self.day_classes):
            cls = self.day_classes[index]
            end = (datetime.strptime(cls['startTime'], '%H:%M')
                   + timedelta(minutes=cls['duration']))
            self.lbl_subject.setText(
                f"{cls['subject']}  ·  {cls['startTime']} – {end.strftime('%H:%M')}")
            elapsed_m = self._subject_elapsed_secs // 60
            session_text = t('session_fmt',
                             cur=index + 1, total=len(self.day_classes))
            progress_text = t('subject_progress',
                              elapsed=elapsed_m, total=cls['duration'])
            parts = [session_text, progress_text]
            if cls.get('notes'):
                parts.append(cls['notes'])
            self.lbl_status.setText("  ·  ".join(parts))

    def _on_start(self):
        if self.active_idx == -1 and self.cards:
            for i, c in enumerate(self.cards):
                if c.status != 'done':
                    self._on_card_click(i)
                    return  # _on_card_click already starts
        self.engine.start()
        # Set wall start if starting fresh (after stop or first time)
        if self._subject_wall_start is None:
            self._subject_wall_start = datetime.now()
        if self._pomo_cycle == 0:
            self._pomo_cycle = 1
        self._update_pomo_label()
        self._update_button_states()

    def _on_pause(self):
        self.engine.pause()
        self._update_button_states()

    def _on_stop(self):
        self._log_session()
        self.engine.stop()
        self._session_work_secs = 0
        self._subject_elapsed_secs = 0
        self._subject_wall_start = None
        self._pomo_cycle = 0
        self.timer_circle.set_time("00:00")
        self.timer_circle.set_progress(0)
        self.timer_circle.set_label("")
        # Reset subject circle to full duration (not 00:00 which implies "done")
        if 0 <= self.active_idx < len(self.day_classes):
            cls = self.day_classes[self.active_idx]
            total_s = cls['duration'] * 60
            rm, rs = divmod(total_s, 60)
            self.subject_circle.set_time(f"{rm:02d}:{rs:02d}")
            self.subject_circle.set_progress(0)
            # Keep card progress in sync
            self.cards[self.active_idx].set_progress(0)
        else:
            self.subject_circle.set_time("00:00")
            self.subject_circle.set_progress(0)
        self.subject_circle.set_label(t('subject_remaining_short'))
        self.lbl_pomo.setText("")
        self._update_button_states()
        self._update_today_total()

    def _on_skip(self):
        self._log_session()
        self.engine.stop()
        self._session_work_secs = 0
        self._subject_elapsed_secs = 0
        self._subject_wall_start = None
        self._pomo_cycle = 0
        if 0 <= self.active_idx < len(self.cards):
            self.cards[self.active_idx].set_status('done')
        self._advance_to_next()
        self._update_button_states()
        self._update_today_total()

    def _advance_to_next(self):
        """Find and start next upcoming subject, or show all-done."""
        nxt = -1
        for i in range(self.active_idx + 1, len(self.cards)):
            if self.cards[i].status != 'done':
                nxt = i
                break
        if nxt >= 0:
            self._on_card_click(nxt)
        else:
            self.lbl_subject.setText(t('all_done'))
            self.lbl_status.setText(t('all_done_sub'))
            self.timer_circle.set_time("00:00")
            self.timer_circle.set_progress(1.0)
            self.subject_circle.set_time("00:00")
            self.subject_circle.set_progress(1.0)
            self.subject_circle.set_label(t('subject_remaining_short'))
            self.timer_circle.set_label("Done")
            self.lbl_pomo.setText("")
            self.active_idx = -1
            self._update_button_states()

    def _toggle_pin(self):
        on = self.cb_pin.isChecked()
        self.settings['alwaysOnTop'] = on
        _save_settings(self.settings)
        if on:
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
        self.show()

    def _log_session(self):
        if (self._session_work_secs > 30
                and 0 <= self.active_idx < len(self.day_classes)):
            subj = self.day_classes[self.active_idx]['subject']
            self.stats.log_session(subj, self._session_work_secs)
            self._session_work_secs = 0

    # ══════════════════════════════════════════════════
    #  TIMER CALLBACKS
    # ══════════════════════════════════════════════════
    def _on_tick(self, d):
        r = d['remaining_time']
        time_str = f"{r // 60:02d}:{r % 60:02d}"
        self.timer_circle.set_time(time_str)

        state = d['state']
        C = self.C

        if state == 'break':
            self.timer_circle.set_colors(
                C['orange'], C['border'], C['text'], C['text_muted'])
            self.timer_circle.set_label(t('state_break'))
        elif state == 'running':
            self.timer_circle.set_colors(
                C['accent'], C['border'], C['text'], C['text_muted'])
            self.timer_circle.set_label(t('state_running'))
        elif state == 'paused':
            self.timer_circle.set_colors(
                C['text_muted'], C['border'], C['text'], C['text_muted'])
            self.timer_circle.set_label(t('state_paused'))
        else:
            self.timer_circle.set_label("")

        total_sec = (self.engine.break_duration_sec if state == 'break'
                     else self.engine.work_duration_sec)
        if total_sec > 0:
            self.timer_circle.set_progress(1.0 - r / total_sec)

        if state == 'running':
            self._session_work_secs += 1
        if state in ('running', 'break'):
            self._subject_elapsed_secs += 1

        # ── Auto-advance: check if subject total study time OR wall-clock elapsed reached ──
        if (state in ('running', 'break')
                and 0 <= self.active_idx < len(self.day_classes)):
            cls = self.day_classes[self.active_idx]
            subject_total_sec = cls['duration'] * 60

            # Wall-clock check: has total real time (incl. breaks) >= subject duration?
            _wall_overtime = False
            if self._subject_wall_start is not None:
                wall_elapsed = (datetime.now() - self._subject_wall_start).total_seconds()
                _wall_overtime = wall_elapsed >= subject_total_sec

            if self._subject_elapsed_secs >= subject_total_sec or _wall_overtime:
                # Subject time is up — auto-advance
                subj_name = cls['subject']
                # Mark card at 100% before reset
                if self.active_idx < len(self.cards):
                    self.cards[self.active_idx].set_progress(1.0)
                    self.cards[self.active_idx].set_status('done')
                self._log_session()
                self.engine.stop()
                self._session_work_secs = 0
                self._subject_elapsed_secs = 0
                self._pomo_cycle = 0
                if self._tray and self._tray.isVisible():
                    self._tray.showMessage(
                        t('auto_advance_title'),
                        t('auto_advance_notif', subject=subj_name),
                        QSystemTrayIcon.Information, 3000)
                self._subject_wall_start = None
                _play_chime('done')
                self._advance_to_next()
                self._update_today_total()
                return

        # ── Subject remaining circle ──
        if state in ('running', 'break', 'paused') and 0 <= self.active_idx < len(self.day_classes):
            cls = self.day_classes[self.active_idx]
            subj_total = cls['duration'] * 60
            subj_remain = max(0, subj_total - self._subject_elapsed_secs)
            rm, rs = divmod(subj_remain, 60)
            self.subject_circle.set_time(f"{rm:02d}:{rs:02d}")
            self.subject_circle.set_progress(
                max(0, min(1, self._subject_elapsed_secs / subj_total)) if subj_total > 0 else 0)
            if state == 'break':
                self.subject_circle.set_colors(
                    C['orange'], C['border'], C['text'], C['text_muted'])
            elif state == 'paused':
                self.subject_circle.set_colors(
                    C['text_muted'], C['border'], C['text'], C['text_muted'])
            else:
                self.subject_circle.set_colors(
                    C['green'], C['border'], C['text'], C['text_muted'])
            self.subject_circle.set_label(t('subject_remaining_short'))
        else:
            self.subject_circle.set_time("00:00")
            self.subject_circle.set_progress(0)
            self.subject_circle.set_label(t('subject_remaining_short'))
            self.subject_circle.set_colors(
                C['green'], C['border'], C['text'], C['text_muted'])

        # Card progress (based on elapsed study time, not clock)
        if state == 'running' and 0 <= self.active_idx < len(self.cards):
            cls = self.day_classes[self.active_idx]
            total_s = cls['duration'] * 60
            self.cards[self.active_idx].set_progress(
                max(0, min(1, self._subject_elapsed_secs / total_s)))

        # Update mini timer
        if self._mini.isVisible():
            subj = ""
            status_text = ""
            accent = C['accent']
            subj_remain_str = ""
            if 0 <= self.active_idx < len(self.day_classes):
                subj = self.day_classes[self.active_idx]['subject']
                cls = self.day_classes[self.active_idx]
                subj_total = cls['duration'] * 60
                sr = max(0, subj_total - self._subject_elapsed_secs)
                srm, srs = divmod(sr, 60)
                subj_remain_str = f"{srm:02d}:{srs:02d}"
            if state == 'break':
                status_text = t('state_break')
                accent = C['orange']
            elif state == 'running':
                status_text = t('state_running')
            elif state == 'paused':
                status_text = t('state_paused')
                accent = C['text_muted']
            self._mini.update_display(time_str, subj, status_text, accent,
                                      subj_remain_str)

        # Tray
        if self._tray:
            subj = ""
            if 0 <= self.active_idx < len(self.day_classes):
                subj = self.day_classes[self.active_idx]['subject']
            self._tray.setToolTip(
                f"Study Timer — {subj}  {time_str}")

    def _on_state(self, d):
        state = d['state']
        idx = self.active_idx

        # ── Smart break skip: if remaining subject time ≤ break duration,
        #    skip the break to avoid wasting time ──
        if state == 'break' and 0 <= idx < len(self.day_classes):
            cls = self.day_classes[idx]
            subject_total_sec = cls['duration'] * 60
            remaining_subj = subject_total_sec - self._subject_elapsed_secs
            if remaining_subj <= self.engine.break_duration_sec:
                # Not enough subject time left to justify a break — skip it
                QTimer.singleShot(100, self.engine.skip_break)
                return

        ctx = ""
        if 0 <= idx < len(self.day_classes):
            c = self.day_classes[idx]
            # Show session + subject elapsed progress
            elapsed_m = self._subject_elapsed_secs // 60
            total_m = c['duration']
            ctx = (t('session_fmt', cur=idx + 1, total=len(self.day_classes))
                   + "  ·  "
                   + t('subject_progress', elapsed=elapsed_m, total=total_m))
            if c.get('notes'):
                ctx += f"  ·  {c['notes']}"

        state_map = {
            'idle':    t('state_idle'),
            'running': t('state_running'),
            'paused':  t('state_paused'),
            'break':   t('state_break'),
            'stopped': t('state_stopped'),
        }
        prefix = state_map.get(state, '')
        self.lbl_status.setText(
            f"{prefix}  ·  {ctx}" if ctx else prefix)

        # Track pomodoro cycles: when state goes back to running after break
        if (state == 'running'
                and d.get('remaining_time') == self.engine.work_duration_sec
                and self._pomo_cycle > 0):
            self._pomo_cycle += 1
            self._update_pomo_label()

        self._update_button_states()

        if self.settings.get('soundEnabled', True):
            if state == 'break':
                _play_chime('break')
            elif (state == 'running'
                  and d.get('remaining_time') == self.engine.work_duration_sec):
                _play_chime('resume')

    def _on_notif(self, d):
        title = d.get('title', '')
        msg = d.get('message', '')
        if self._tray and self._tray.isVisible():
            self._tray.showMessage(
                title, msg, QSystemTrayIcon.Information, 3000)

    # ══════════════════════════════════════════════════
    #  CLOSE
    # ══════════════════════════════════════════════════
    def closeEvent(self, ev):
        if (self.settings.get('minimizeToTray', True)
                and self._tray and self._tray.isVisible()):
            self.hide()
            self._tray.showMessage(
                t('app_title'), t('tray_minimized'),
                QSystemTrayIcon.Information, 2000)
            ev.ignore()
        else:
            self.engine.stop()
            self._tick_timer.stop()
            self._log_session()
            self._mini.hide()
            if self._tray:
                self._tray.hide()
            ev.accept()


# ═══════════════════════════════════════════════════════════
def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setQuitOnLastWindowClosed(False)
    icon = create_app_icon()
    app.setWindowIcon(icon)
    w = StudyTimerApp()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

"""CircularTimer widget – MSI Afterburner-style gauge."""
import math

from PyQt5.QtWidgets import QWidget, QSizePolicy
from PyQt5.QtCore import Qt, QSize, QRectF, QPointF
from PyQt5.QtGui import (QPainter, QColor, QFont, QLinearGradient,
                          QRadialGradient, QBrush, QPen)

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


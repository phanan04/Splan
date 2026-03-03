"""
Module: Icon Generator
Tạo logo/icon cho Study Timer bằng QPainter — không cần file ảnh ngoài.
Icon: Stopwatch trên nền gradient xanh, kiểu flat design.
"""

import math
from PyQt5.QtGui import (
    QPixmap, QPainter, QColor, QPen, QBrush,
    QLinearGradient, QIcon, QPainterPath, QRadialGradient
)
from PyQt5.QtCore import Qt, QRectF, QPointF


def create_app_icon() -> QIcon:
    """Tạo QIcon cho ứng dụng với nhiều kích thước."""
    icon = QIcon()
    for size in [16, 24, 32, 48, 64, 128, 256]:
        icon.addPixmap(_draw_icon(size))
    return icon


def create_tray_icon(dark_bg: bool = False) -> QIcon:
    """Tạo icon cho system tray (nhỏ, tối ưu cho nền sáng/tối)."""
    icon = QIcon()
    for size in [16, 24, 32]:
        icon.addPixmap(_draw_icon(size))
    return icon


def _draw_icon(size: int) -> QPixmap:
    """Vẽ icon tại một kích thước cụ thể."""
    s = size
    pixmap = QPixmap(s, s)
    pixmap.fill(Qt.transparent)

    p = QPainter(pixmap)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setRenderHint(QPainter.SmoothPixmapTransform, True)

    # ── Background: gradient rounded rect ──
    grad = QLinearGradient(0, 0, s, s)
    grad.setColorAt(0.0, QColor('#4A9FE5'))
    grad.setColorAt(0.5, QColor('#2383E2'))
    grad.setColorAt(1.0, QColor('#1565C0'))

    bg_path = QPainterPath()
    radius = s * 0.22
    bg_path.addRoundedRect(QRectF(0, 0, s, s), radius, radius)
    p.fillPath(bg_path, QBrush(grad))

    # ── Subtle inner glow ──
    if s >= 48:
        glow = QRadialGradient(s * 0.35, s * 0.3, s * 0.6)
        glow.setColorAt(0, QColor(255, 255, 255, 30))
        glow.setColorAt(1, QColor(255, 255, 255, 0))
        p.fillPath(bg_path, QBrush(glow))

    white = QColor(255, 255, 255)
    white_alpha = QColor(255, 255, 255, 200)

    # ── Center coordinates ──
    cx = s * 0.5
    cy = s * 0.54
    clock_r = s * 0.28

    # ── Stopwatch button on top ──
    btn_w = s * 0.10
    btn_h = s * 0.07
    btn_x = cx - btn_w / 2
    btn_y = cy - clock_r - btn_h - s * 0.02
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(white_alpha))
    p.drawRoundedRect(QRectF(btn_x, btn_y, btn_w, btn_h),
                      s * 0.02, s * 0.02)

    # Stem connecting button to circle
    stem_w = s * 0.04
    stem_h = s * 0.03
    p.drawRect(QRectF(cx - stem_w / 2, btn_y + btn_h,
                       stem_w, stem_h))

    # ── Clock circle ──
    pen = QPen(white)
    pen.setWidthF(max(s * 0.055, 1.2))
    pen.setCapStyle(Qt.RoundCap)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    p.drawEllipse(QPointF(cx, cy), clock_r, clock_r)

    # ── Hour markers (12, 3, 6, 9) ──
    if s >= 32:
        marker_pen = QPen(white_alpha)
        marker_pen.setWidthF(max(s * 0.03, 0.8))
        marker_pen.setCapStyle(Qt.RoundCap)
        p.setPen(marker_pen)
        for angle_deg in [0, 90, 180, 270]:
            a = math.radians(angle_deg)
            inner = clock_r * 0.78
            outer = clock_r * 0.92
            x1 = cx + inner * math.sin(a)
            y1 = cy - inner * math.cos(a)
            x2 = cx + outer * math.sin(a)
            y2 = cy - outer * math.cos(a)
            p.drawLine(QPointF(x1, y1), QPointF(x2, y2))

    # ── Clock hands ──
    hand_pen = QPen(white)
    hand_pen.setCapStyle(Qt.RoundCap)

    # Minute hand (pointing to 12 — straight up)
    hand_pen.setWidthF(max(s * 0.05, 1.0))
    p.setPen(hand_pen)
    p.drawLine(QPointF(cx, cy),
               QPointF(cx, cy - clock_r * 0.65))

    # Hour hand (pointing to ~2 o'clock — 60 degrees)
    hand_pen.setWidthF(max(s * 0.06, 1.2))
    p.setPen(hand_pen)
    hour_angle = math.radians(60)
    hx = cx + clock_r * 0.45 * math.sin(hour_angle)
    hy = cy - clock_r * 0.45 * math.cos(hour_angle)
    p.drawLine(QPointF(cx, cy), QPointF(hx, hy))

    # ── Center dot ──
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(white))
    dot_r = max(s * 0.045, 1.0)
    p.drawEllipse(QPointF(cx, cy), dot_r, dot_r)

    # ── Small book pages at bottom (only for larger sizes) ──
    if s >= 64:
        book_y = cy + clock_r + s * 0.10
        book_w = s * 0.22
        book_h = s * 0.04

        book_pen = QPen(QColor(255, 255, 255, 180))
        book_pen.setWidthF(max(s * 0.025, 1.0))
        book_pen.setCapStyle(Qt.RoundCap)
        p.setPen(book_pen)

        # Left page
        p.drawLine(QPointF(cx, book_y + book_h * 0.5),
                   QPointF(cx - book_w / 2, book_y - book_h))
        # Right page
        p.drawLine(QPointF(cx, book_y + book_h * 0.5),
                   QPointF(cx + book_w / 2, book_y - book_h))

    p.end()
    return pixmap


# ── Test: hiển thị icon ──
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication, QLabel

    app = QApplication(sys.argv)
    icon = create_app_icon()

    # Save as PNG for preview
    pixmap = _draw_icon(256)
    pixmap.save("icon_preview.png")
    print("Saved icon_preview.png (256x256)")

    lbl = QLabel()
    lbl.setPixmap(_draw_icon(256))
    lbl.setWindowTitle("Icon Preview")
    lbl.show()
    sys.exit(app.exec_())

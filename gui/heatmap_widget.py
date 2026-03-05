"""HeatmapWidget – GitHub-style contribution heatmap."""
from datetime import datetime

from PyQt5.QtWidgets import QWidget, QSizePolicy
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QColor, QFont

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



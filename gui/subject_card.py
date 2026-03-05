"""SubjectCard – draggable subject card widget."""
from datetime import datetime, timedelta

from PyQt5.QtWidgets import (QFrame, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
                              QPushButton, QProgressBar, QMenu, QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSignal, QMimeData
from PyQt5.QtGui import QFont, QColor, QCursor, QDrag

from gui.utils import _shadow
from i18n import t

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
        self.lbl_start = QLabel(self.start_time)
        self.lbl_start.setFont(QFont("Segoe UI", 11, QFont.DemiBold))
        self.lbl_start.setStyleSheet(f"color: {C['text']}; border: none; background: transparent;")
        self.lbl_end = QLabel(end_dt.strftime('%H:%M'))
        self.lbl_end.setFont(QFont("Segoe UI", 9))
        self.lbl_end.setStyleSheet(f"color: {C['text_muted']}; border: none; background: transparent;")
        tl.addWidget(self.lbl_start)
        tl.addWidget(self.lbl_end)
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
    def update_time(self, new_start: str):
        """Cập nhật giờ bắt đầu và giờ kết thúc hiển thị trên card."""
        self.start_time = new_start
        try:
            end_dt = (datetime.strptime(new_start, "%H:%M")
                      + timedelta(minutes=self.duration))
            self.lbl_start.setText(new_start)
            self.lbl_end.setText(end_dt.strftime('%H:%M'))
        except Exception:
            pass

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



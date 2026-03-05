"""MiniTimerWindow – small frameless always-on-top floating timer overlay."""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                              QLabel, QPushButton)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QCursor

from gui.themes import LIGHT
from i18n import t

class MiniTimerWindow(QWidget):
    """Small frameless always-on-top floating timer."""
    back_requested = pyqtSignal()

    def __init__(self, colors, parent=None):
        super().__init__(parent)
        self.C = colors
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
            | Qt.Tool | Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
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



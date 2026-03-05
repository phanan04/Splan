"""Application dialogs: SubjectDialog, StatsDialog, DuplicateDayDialog."""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QFrame, QLineEdit, QSpinBox,
                              QFormLayout, QProgressBar, QGridLayout,
                              QComboBox, QCheckBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QCursor

from gui.themes import LIGHT
from gui.heatmap_widget import HeatmapWidget
from timetable_manager import TimetableManager
from study_stats import StudyStats
from i18n import t, get_day_full

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



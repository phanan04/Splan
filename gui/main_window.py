"""StudyTimerApp main window and application entry point."""
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
    QFileDialog, QStackedWidget,
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

from gui.settings import _user_data_dir, _load_settings, _save_settings
from gui.themes import LIGHT, DARK, _qss
from gui.utils import _shadow, SignalEmitter, _play_chime, SUBJECT_COLORS
from gui.circular_timer import CircularTimer
from gui.heatmap_widget import HeatmapWidget
from gui.subject_card import SubjectCard
from gui.dialogs import SubjectDialog, StatsDialog, DuplicateDayDialog
from gui.settings_dialog import _PillToggle, SettingsDialog
from gui.mini_timer import MiniTimerWindow

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

        # Single-instance: create named Win32 event so a second exe invocation
        # can signal us to restore the window (avoids blank-window from Win32
        # ShowWindow bypassing Qt's paint system).
        self._show_event_handle = None
        if platform.system() == 'Windows':
            import ctypes
            self._show_event_handle = ctypes.windll.kernel32.CreateEventW(
                None, False, False, "StudyTimer_ShowEvent")
            self._ipc_poll_timer = QTimer()
            self._ipc_poll_timer.timeout.connect(self._check_show_event)
            self._ipc_poll_timer.start(300)

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
        if hasattr(self, '_ipc_poll_timer'):
            self._ipc_poll_timer.stop()
        if self._show_event_handle:
            import ctypes
            ctypes.windll.kernel32.CloseHandle(self._show_event_handle)
            self._show_event_handle = None
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
        self.center_panel.setStyleSheet(f"""
            QFrame#centerPanel {{
                background: {C['surface']};
                border: 1px solid {C.get('border_subtle', C['border'])};
                border-top: 1px solid {bl};
                border-radius: 12px;
            }}
        """)
        _shadow(self.center_panel, C.get('shadow_card', C['shadow']), 18, 4)

        self._subj_accent_bar.setStyleSheet(
            f"background: {C['accent']}; border-radius: 2px; border: none;")
        self.lbl_subject.setStyleSheet(
            f"color: {C['text']}; background: transparent; letter-spacing: 0.3px;")
        self.lbl_status.setStyleSheet(f"""
            color: {C['text_muted']};
            background: {C['bg']};
            border-radius: 5px;
            padding: 1px 6px;
            letter-spacing: 1.5px;
        """)

        self._update_button_states()

        for b in self._util_btns:
            b.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {C['text_muted']};
                    border: none;
                    border-radius: 6px;
                    padding: 0;
                    font-size: 13px;
                }}
                QPushButton:hover {{
                    background: {C['surface_hover']};
                    color: {C['text']};
                }}
                QPushButton:pressed {{
                    background: {C['accent_light']};
                    color: {C['accent']};
                }}
            """)

        self.lbl_pomo.setStyleSheet(
            f"color: {C['text_muted']}; background: transparent; letter-spacing: 0.5px;")
        self.lbl_today_total.setStyleSheet(
            f"color: {C['accent']}; background: transparent; letter-spacing: 0.5px;")

        self.btn_dark.setText('\u2600' if self.settings['darkMode'] else '\U0001f319')
        self.btn_dark.setToolTip(t('btn_light') if self.settings['darkMode'] else t('btn_dark'))

        self._center_divider.setStyleSheet(
            f"background: {C['accent']}; border: none; margin: 0 4px;")

        _cb_style = f"""
            QCheckBox {{
                color: {C['text_muted']};
                background: transparent;
                spacing: 4px;
                font-size: 11px;
            }}
            QCheckBox::indicator {{
                width: 12px; height: 12px;
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
                background: {color};
                color: #FFFFFF;
                border: none;
                border-radius: 12px;
                padding: 0 24px;
                font-size: 11pt;
                font-weight: bold;
                letter-spacing: 0.5px;
            }}
            QPushButton:hover {{
                background: {c_dark};
            }}
            QPushButton:pressed {{
                background: {c_dark};
                padding-top: 2px;
            }}
            QPushButton:disabled {{
                background: {C['border']};
                color: {C['text_muted']};
            }}
        """)

        # ── Stop button — ghost, red on hover ──
        is_active = state in (TimerState.RUNNING, TimerState.PAUSED, TimerState.BREAK)
        self.btn_stop.setVisible(is_active)
        self.btn_stop.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {C['text_muted']};
                border: 1px solid {C.get('border_subtle', C['border'])};
                border-radius: 7px;
                padding: 0 10px;
                font-size: 8pt;
            }}
            QPushButton:hover {{
                color: {C['red']};
                border-color: {C['red']};
                background: {C['red_bg']};
            }}
            QPushButton:pressed {{
                background: {C['red_bg']};
            }}
        """)

        # ── Finish button — ghost, accent on hover ──
        self.btn_finish.setVisible(has_subject and is_active)
        self.btn_finish.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {C['text_muted']};
                border: 1px solid {C.get('border_subtle', C['border'])};
                border-radius: 7px;
                padding: 0 10px;
                font-size: 8pt;
            }}
            QPushButton:hover {{
                color: {C['accent']};
                border-color: {C['accent']};
                background: {C['accent_light']};
            }}
            QPushButton:pressed {{
                background: {C['accent_light']};
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

        # ── Center panel (card style) ──
        self.center_panel = QFrame()
        self.center_panel.setObjectName("centerPanel")
        self.center_panel.setStyleSheet(f"""
            QFrame#centerPanel {{
                background: {C['surface']};
                border: 1px solid {C.get('border_subtle', C['border'])};
                border-top: 1px solid {C.get('border_light', C['border'])};
                border-radius: 12px;
            }}
        """)
        _shadow(self.center_panel, C.get('shadow_card', C['shadow']), 18, 4)
        center_lay = QVBoxLayout(self.center_panel)
        center_lay.setContentsMargins(14, 10, 14, 8)
        center_lay.setSpacing(5)

        # ── Subject row: left accent bar + name + status badge ──
        subj_row = QHBoxLayout()
        subj_row.setSpacing(8)
        subj_row.setContentsMargins(0, 0, 0, 0)

        self._subj_accent_bar = QFrame()
        self._subj_accent_bar.setFixedWidth(3)
        self._subj_accent_bar.setMinimumHeight(30)
        self._subj_accent_bar.setStyleSheet(
            f"background: {C['accent']}; border-radius: 2px; border: none;")
        subj_row.addWidget(self._subj_accent_bar)

        subj_text_col = QVBoxLayout()
        subj_text_col.setSpacing(2)
        subj_text_col.setContentsMargins(0, 0, 0, 0)

        self.lbl_subject = QLabel(t('choose_subject'))
        self.lbl_subject.setFont(QFont("Segoe UI", 13, QFont.Bold))
        self.lbl_subject.setStyleSheet(
            f"color: {C['text']}; background: transparent; letter-spacing: 0.3px;")
        self.lbl_subject.setWordWrap(True)
        self.lbl_subject.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        subj_text_col.addWidget(self.lbl_subject)

        self.lbl_status = QLabel(t('not_started'))
        self.lbl_status.setFont(QFont("Segoe UI", 8, QFont.DemiBold))
        self.lbl_status.setStyleSheet(f"""
            color: {C['text_muted']};
            background: {C['bg']};
            border-radius: 5px;
            padding: 1px 6px;
            letter-spacing: 1.5px;
        """)
        self.lbl_status.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        subj_text_col.addWidget(self.lbl_status)

        subj_row.addLayout(subj_text_col, stretch=1)
        center_lay.addLayout(subj_row)

        # ── Hairline separator ──
        _subj_sep = QFrame()
        _subj_sep.setFrameShape(QFrame.HLine)
        _subj_sep.setFixedHeight(1)
        _subj_sep.setStyleSheet(
            f"background: {C.get('border_subtle', C['border'])}; border: none; margin: 1px 0;")
        center_lay.addWidget(_subj_sep)

        # ── PRIMARY button — full-width pill ──
        self.btn_primary = QPushButton(f"▶  {t('btn_start')}")
        self.btn_primary.setFixedHeight(46)
        self.btn_primary.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_primary.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.btn_primary.clicked.connect(self._toggle_start_pause)
        center_lay.addWidget(self.btn_primary)

        # ── SECONDARY row — ghost buttons, full width split ──
        secondary_row = QHBoxLayout()
        secondary_row.setSpacing(6)
        secondary_row.setContentsMargins(0, 0, 0, 0)

        self.btn_stop = QPushButton(f"■  {t('btn_stop')}")
        self.btn_stop.setFixedHeight(28)
        self.btn_stop.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_stop.setFont(QFont("Segoe UI", 8))
        self.btn_stop.clicked.connect(self._on_stop)
        secondary_row.addWidget(self.btn_stop, stretch=1)

        self.btn_finish = QPushButton(f"✓  {t('btn_finish')}")
        self.btn_finish.setFixedHeight(28)
        self.btn_finish.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_finish.setFont(QFont("Segoe UI", 8))
        self.btn_finish.clicked.connect(self._on_skip)
        secondary_row.addWidget(self.btn_finish, stretch=1)

        center_lay.addLayout(secondary_row)

        # ── Meta row: pomo cycle · today total ──
        meta_row = QHBoxLayout()
        meta_row.setSpacing(4)
        meta_row.addStretch()

        self.lbl_pomo = QLabel("")
        self.lbl_pomo.setFont(QFont("Segoe UI", 8))
        self.lbl_pomo.setStyleSheet(
            f"color: {C['text_muted']}; background: transparent; letter-spacing: 0.5px;")
        self.lbl_pomo.setAlignment(Qt.AlignCenter)
        meta_row.addWidget(self.lbl_pomo)

        _meta_dot = QLabel("·")
        _meta_dot.setFont(QFont("Segoe UI", 8))
        _meta_dot.setStyleSheet(f"color: {C['border']}; background: transparent;")
        meta_row.addWidget(_meta_dot)

        self.lbl_today_total = QLabel("")
        self.lbl_today_total.setFont(QFont("Segoe UI", 8))
        self.lbl_today_total.setStyleSheet(
            f"color: {C['accent']}; background: transparent; letter-spacing: 0.5px;")
        self.lbl_today_total.setAlignment(Qt.AlignCenter)
        meta_row.addWidget(self.lbl_today_total)

        meta_row.addStretch()
        center_lay.addLayout(meta_row)

        # Keep list for resize handler
        self._ctrl_btns = [self.btn_primary, self.btn_stop, self.btn_finish]

        # Apply initial button states
        self._update_button_states()

        # ── Accent divider ──
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setFixedHeight(1)
        divider.setStyleSheet(
            f"background: {C['accent']}; border: none; margin: 0 4px;")
        center_lay.addWidget(divider)
        self._center_divider = divider

        # ── Utility strip — flat icon toolbar ──
        util_row = QHBoxLayout()
        util_row.setSpacing(2)
        util_row.addStretch()
        self._util_btns = []

        _dark_icon = '☀' if self.settings['darkMode'] else '🌙'
        _dark_tip = t('btn_light') if self.settings['darkMode'] else t('btn_dark')

        _icon_btn_style = f"""
            QPushButton {{
                background: transparent;
                color: {C['text_muted']};
                border: none;
                border-radius: 6px;
                padding: 0;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background: {C['surface_hover']};
                color: {C['text']};
            }}
            QPushButton:pressed {{
                background: {C['accent_light']};
                color: {C['accent']};
            }}
        """

        for icon, tip, slot in [
            ('▦', t('btn_stats'), self._show_stats),
            (_dark_icon, _dark_tip, self._toggle_dark),
            ('⧉', t('mini_open'), self._open_mini),
            ('⊕', t('btn_lang'), self._toggle_language),
            ('⚙', t('settings_btn'), self._open_settings),
        ]:
            b = QPushButton(icon)
            b.setToolTip(tip)
            b.setFixedSize(30, 24)
            b.setCursor(QCursor(Qt.PointingHandCursor))
            b.setFont(QFont("Segoe UI", 12))
            b.setStyleSheet(_icon_btn_style)
            b.clicked.connect(slot)
            util_row.addWidget(b)
            self._util_btns.append(b)

        self.btn_dark = self._util_btns[1]

        # Dot separator
        sep = QLabel("•")
        sep.setStyleSheet(f"color: {C['border']}; background: transparent;")
        sep.setFont(QFont("Segoe UI", 7))
        util_row.addWidget(sep)
        self._util_sep = sep

        _cb_style = f"""
            QCheckBox {{
                color: {C['text_muted']};
                background: transparent;
                spacing: 4px;
                font-size: 11px;
            }}
            QCheckBox::indicator {{
                width: 12px; height: 12px;
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
    # ══════════════════════════════════════════════════
    #  SINGLE INSTANCE CHECK
    # ══════════════════════════════════════════════════
    def _check_show_event(self):
        """Poll the named Win32 event; if set, restore window (IPC from 2nd exe)."""
        if not self._show_event_handle:
            return
        import ctypes
        WAIT_OBJECT_0 = 0
        result = ctypes.windll.kernel32.WaitForSingleObject(
            self._show_event_handle, 0)  # 0 ms = non-blocking
        if result == WAIT_OBJECT_0:
            self.showNormal()
            self.activateWindow()
            self.raise_()

    def _open_settings(self):
        dlg = SettingsDialog(self.settings, parent=self, colors=self.C)
        if dlg.exec_() != QDialog.Accepted:
            return
        new = dlg.get_settings()

        changed_dark = new.get('darkMode') != self.settings.get('darkMode')
        changed_lang = new.get('language') != self.settings.get('language')
        changed_top  = new.get('alwaysOnTop') != self.settings.get('alwaysOnTop')

        self.settings.update(new)
        _save_settings(self.settings)

        # Apply dark mode toggle
        if changed_dark:
            self.C = DARK if self.settings['darkMode'] else LIGHT
            self.setStyleSheet(_qss(self.C))
            self._rebuild_theme()

        # Apply always-on-top
        if changed_top:
            self.cb_pin.setChecked(self.settings.get('alwaysOnTop', False))

        # Sync inline checkboxes
        self.cb_auto.setChecked(self.settings.get('autoStart', True))

        # Language hint
        if changed_lang:
            QMessageBox.information(
                self, t('settings_title'),
                t('settings_restart_hint').lstrip('* '),
            )

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

        # Cập nhật startTime về NOW khi user bấm vào môn học
        now = datetime.now()
        now_str = now.strftime('%H:%M')
        cls['startTime'] = now_str  # cập nhật in-memory (day_classes là reference trực tiếp)
        self.timetable.update_start_time_only(self.selected_day, index, now_str)
        self.cards[index].update_time(now_str)  # cập nhật nhãn giờ trên card

        # elapsed = 0 vì bắt đầu ngay lúc này
        self._subject_elapsed_secs = 0
        self._subject_wall_start = now

        self._show_subject(index)
        self.timer_circle.set_time("00:00")
        self.timer_circle.set_progress(0)
        self.timer_circle.set_label("")

        # Subject circle: hiển thị full duration vì bắt đầu từ đầu
        total_s = cls['duration'] * 60
        rm, rs = divmod(total_s, 60)
        self.subject_circle.set_time(f"{rm:02d}:{rs:02d}")
        self.subject_circle.set_progress(0)
        self.cards[index].set_progress(0)
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

            if (self._subject_elapsed_secs >= subject_total_sec or _wall_overtime) \
                    and self.settings.get('autoAdvance', True):
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
        if (state == 'break' and self.settings.get('smartBreakSkip', True)
                and 0 <= idx < len(self.day_classes)):
            cls = self.day_classes[idx]
            subject_total_sec = cls['duration'] * 60
            remaining_subj = subject_total_sec - self._subject_elapsed_secs
            if remaining_subj <= self.engine.break_duration_sec:
                # Not enough subject time left to justify a break — skip it
                QTimer.singleShot(100, self.engine.skip_break)
                return

        # If mini timer is visible, ensure it stays visible when break starts
        # (PowerShell/win10toast notifications can steal focus and hide Qt.Tool windows)
        if state == 'break' and self._mini.isVisible():
            QTimer.singleShot(400, lambda: (self._mini.show(), self._mini.raise_()))

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

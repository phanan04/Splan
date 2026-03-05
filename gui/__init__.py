"""
gui package – Study Timer GUI split into focused sub-modules.

Public API (keeps study_timer_gui.py as a thin shim):
    from gui import main
    from gui.main_window import StudyTimerApp
"""
from gui.main_window import main, StudyTimerApp  # noqa: F401

from gui.settings import _user_data_dir, _load_settings, _save_settings  # noqa: F401
from gui.themes import LIGHT, DARK, _qss  # noqa: F401
from gui.utils import _shadow, SignalEmitter, _play_chime, SUBJECT_COLORS  # noqa: F401
from gui.circular_timer import CircularTimer  # noqa: F401
from gui.heatmap_widget import HeatmapWidget  # noqa: F401
from gui.subject_card import SubjectCard  # noqa: F401
from gui.dialogs import SubjectDialog, StatsDialog, DuplicateDayDialog  # noqa: F401
from gui.settings_dialog import _PillToggle, SettingsDialog  # noqa: F401
from gui.mini_timer import MiniTimerWindow  # noqa: F401

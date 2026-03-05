"""Shared GUI utilities: shadow helper, signal emitter, chime player, color list."""
import threading, platform

from PyQt5.QtWidgets import QGraphicsDropShadowEffect
from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtGui import QColor

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

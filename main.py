"""
Study Timer Application - Entry Point
=====================================

Ứng dụng quản lý thời gian học tập với các tính năng:
- Đếm ngược 30 phút làm việc
- Thông báo hệ thống mỗi 30 phút
- Thời gian tạm dừng 5 phút tự động
- Hiển thị lịch học hiện tại
- Giao diện tối giản và dễ sử dụng
- Chế độ "Always on Top"

Cách sử dụng:
    python main.py

Yêu cầu:
    - Python 3.7+
    - PyQt5
    - Các module khác: timetable_manager, timer_engine

Cấu trúc dự án:
    study-timer/
    ├── main.py                   (file này)
    ├── timetable.json            (lịch học)
    ├── timetable_manager.py      (module quản lý lịch)
    ├── timer_engine.py           (module đếm ngược & thông báo)
    └── study_timer_gui.py        (module giao diện PyQt5)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _ensure_single_instance():
    """On Windows: use a named mutex. On other OS: skip."""
    import platform
    if platform.system() != 'Windows':
        return None  # Allow multiple on non-Windows for dev
    import ctypes
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "StudyTimer_SingleInstance_Mutex")
    last_err = ctypes.windll.kernel32.GetLastError()
    if last_err == 183:  # ERROR_ALREADY_EXISTS
        # Bring existing window to foreground
        from ctypes import wintypes
        FindWindow = ctypes.windll.user32.FindWindowW
        SetForegroundWindow = ctypes.windll.user32.SetForegroundWindow
        ShowWindow = ctypes.windll.user32.ShowWindow
        hwnd = FindWindow(None, "Study Timer")
        if hwnd:
            ShowWindow(hwnd, 9)        # SW_RESTORE
            SetForegroundWindow(hwnd)
        sys.exit(0)
    return mutex  # Keep reference alive for process lifetime


from study_timer_gui import main

if __name__ == "__main__":
    try:
        from PyQt5.QtWidgets import QApplication
    except ImportError:
        print("PyQt5 không được cài đặt. Chạy: pip install PyQt5")
        sys.exit(1)

    _mutex = _ensure_single_instance()
    main()

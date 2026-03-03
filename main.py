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

# Thêm thư mục hiện tại vào path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from study_timer_gui import main

if __name__ == "__main__":
    # Đảm bảo PyQt5 đã cài đặt
    try:
        from PyQt5.QtWidgets import QApplication
    except ImportError:
        print("❌ PyQt5 không được cài đặt!")
        print("📦 Cài đặt bằng lệnh: pip install PyQt5")
        sys.exit(1)

    # Kiểm tra file timetable.json
    timetable_path = os.path.join(
        os.path.dirname(__file__),
        'timetable.json'
    )

    if not os.path.exists(timetable_path):
        print("⚠️ Cảnh báo: Không tìm thấy file timetable.json")
        print(f"   Đường dẫn: {timetable_path}")
        print("   Ứng dụng sẽ tạo tệp mặc định hoặc sử dụng lịch rỗng")

    # Khởi chạy ứng dụng
    print("🚀 Khởi động Study Timer v7.0 — Feature-Rich Edition")
    print("   Phím tắt: Space=play/pause  S=stop  N=next  D=theme  M=mini  1-7=day  Ctrl+N=add")
    main()

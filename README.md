# ⏱️ Study Timer - Ứng dụng Quản lý Thời gian Học tập

## 📋 Giới thiệu

**Study Timer** là một ứng dụng desktop đơn giản nhưng mạnh mẽ, giúp bạn quản lý thời gian học tập hiệu quả. Ứng dụng cung cấp:

- ⏱️ **Bộ đếm ngược 30 phút**: Giúp bạn duy trì tập trung
- 🔔 **Thông báo hệ thống**: Nhắc nhở khi cần tạm dừng
- ☕ **Break time tự động**: 5 phút nghỉ sau mỗi 30 phút học
- 📅 **Lịch học thông minh**: Tự động nhận diện môn học hiện tại
- 📌 **Always on Top**: Giữ cửa sổ luôn hiển thị
- 🎨 **Giao diện tối giản**: Dễ sử dụng, dễ tập trung

---

## 📦 Cài đặt

### 1. Clone hoặc tải dự án
```bash
git clone <repo-url>
cd study-timer
```

### 2. Cài đặt dependencies
```bash
pip install -r requirements.txt
```

### 3. Tạo file cấu hình từ template
```bash
# Windows
copy settings.example.json settings.json
copy timetable.example.json timetable.json
copy study_history.example.json study_history.json

# Linux / macOS
cp settings.example.json settings.json
cp timetable.example.json timetable.json
cp study_history.example.json study_history.json
```

**Yêu cầu hệ thống:**
- Python 3.7+
- PyQt5

---

## 🚀 Chạy ứng dụng

```bash
python main.py
```

---

## 📁 Cấu trúc dự án

```
study-timer/
├── main.py                    # Entry point - Chạy ứng dụng từ đây
├── timetable.json             # Dữ liệu lịch học (định dạng JSON)
├── timetable_manager.py       # Module quản lý lịch học
├── timer_engine.py            # Module đếm ngược & thông báo
├── study_timer_gui.py         # Module giao diện PyQt5
├── requirements.txt           # Dependencies
└── README.md                  # File này
```

---

## 📖 Hướng dẫn sử dụng

### Bắt đầu timer
1. Nhấn nút **▶ Bắt đầu**
2. Timer sẽ bắt đầu đếm ngược từ 30 phút

### Tạm dừng / Tiếp tục
- Nhấn **⏸ Tạm dừng** để dừng timer
- Nhấn **▶ Bắt đầu** để tiếp tục

### Dừng hoàn toàn
- Nhấn **⏹ Dừng** để reset timer

### Always on Top
- Chọn checkbox **📌 Luôn hiển thị trên cùng** để giữ cửa sổ luôn ở trên

### Xem lịch học
- Ứng dụng sẽ tự động hiển thị môn học hiện tại
- Nếu không có lớp học, sẽ hiển thị lớp học sắp tới

---

## 📋 Cấu hình lịch học (timetable.json)

Sửa file `timetable.json` để thêm lịch học của bạn:

```json
{
  "schedule": {
    "Monday": [
      {
        "subject": "Lập trình Python",
        "startTime": "08:00",
        "duration": 120,
        "notes": "Python fundamentals"
      }
    ]
  },
  "breakConfig": {
    "workDurationMinutes": 30,
    "breakDurationMinutes": 5,
    "enableNotifications": true
  }
}
```

**Giải thích:**
- `subject`: Tên môn học
- `startTime`: Thời gian bắt đầu (HH:MM)
- `duration`: Thời lượng (phút)
- `notes`: Ghi chú (tùy chọn)
- `workDurationMinutes`: Thời gian làm việc trước break (phút)
- `breakDurationMinutes`: Thời gian break (phút)
- `enableNotifications`: Bật/tắt thông báo

---

## ⚙️ Chi tiết các module

### 1. `timetable_manager.py`
Quản lý lịch học từ JSON

```python
from timetable_manager import TimetableManager

manager = TimetableManager('timetable.json')

# Lấy môn học hiện tại
current = manager.get_current_subject()

# Lấy môn học tiếp theo
next_class = manager.get_next_subject()

# Lấy toàn bộ lịch hôm nay
today = manager.get_today_schedule()
```

**Tính năng chính:**
- Tự động nhận diện môn học dựa trên giờ hệ thống
- Tính toán thời gian còn lại của lớp học
- Hiển thị lớp học tiếp theo

### 2. `timer_engine.py`
Đếm ngược và quản lý break timer

```python
from timer_engine import TimerEngine

timer = TimerEngine(
    work_duration_sec=1800,    # 30 phút
    break_duration_sec=300,    # 5 phút
    on_tick=callback_tick,
    on_state_changed=callback_state,
    on_notification=callback_notify
)

timer.start()  # Bắt đầu
timer.pause()  # Tạm dừng
timer.resume()  # Tiếp tục
timer.stop()  # Dừng
```

**Tính năng chính:**
- Đếm ngược theo thời gian thực
- Gửi thông báo hệ thống khi hết 30 phút
- Tự động kích hoạt break time 5 phút
- Sử dụng multi-threading để không treo UI

**States:**
- `idle`: Chưa bắt đầu
- `running`: Đang chạy
- `paused`: Tạm dừng
- `break`: Thời gian tạm dừng
- `stopped`: Đã dừng

### 3. `study_timer_gui.py`
Giao diện PyQt5

```python
from study_timer_gui import StudyTimerApp

app = StudyTimerApp()
app.show()
```

**Tính năng:**
- Hiển thị timer countdown lớn (72px)
- Hiển thị tên môn học hiện tại
- Nút điều khiển Start/Pause/Stop
- Checkbox Always on Top
- Tích hợp với timer_engine và timetable_manager

---

## 🔔 Thông báo hệ thống

Ứng dụng hỗ trợ thông báo trên các OS:

### Windows
- Dùng **Toast notifications** (nếu cài win10toast)
- Fallback: PowerShell

### macOS
- Dùng **osascript**

### Linux
- Dùng **notify-send**

**Lưu ý:** Nếu chạy trên Windows mà không có win10toast:
```bash
pip install win10toast
```

---

## 🧵 Multi-threading

Timer chạy trên **thread riêng** để:
- ✅ Không làm treo giao diện khi đếm ngược
- ✅ Cho phép user tương tác với UI bình thường
- ✅ Gửi notifications không ảnh hưởng đến timer

**Cơ chế:**
- Main thread: Xử lý UI (PyQt5)
- Worker thread: Vòng lặp timer (timer_engine.py)
- Signal emitter: Giao tiếp giữa threads (StudyTimerApp)

---

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'PyQt5'"
```bash
pip install PyQt5
```

### "ModuleNotFoundError: No module named 'win10toast'"
```bash
pip install win10toast
```

### Thông báo không hiển thị
- Kiểm tra file timetable.json có `enableNotifications: true`
- Trên Windows, cài đặt win10toast
- Trên Linux, cài notify-send: `sudo apt-get install libnotify-bin`

### Timer không chạy
- Kiểm tra console có lỗi
- Thử khởi động lại ứng dụng

---

## 📝 Roadmap (Tính năng trong tương lai)

- [ ] Lưu hoạch động (thêm/sửa lớp học từ UI)
- [ ] Thống kê thời gian học
- [ ] Sound notifications
- [ ] Dark mode
- [ ] Chế độ Pomodoro tuỳ chỉnh
- [ ] Tích hợp Google Calendar

---

## 📄 License

MIT License - Tự do sử dụng cho mục đích cá nhân

---

## 👨‍💻 Phát triển

Dự án này được phát triển với:
- **Python 3.7+**
- **PyQt5** - Desktop GUI
- **Threading** - Xử lý không đồng bộ
- **JSON** - Lưu trữ dữ liệu

---

## 📞 Liên hệ & Feedback

Nếu có câu hỏi hoặc góp ý, vui lòng tạo Issue hoặc liên hệ trực tiếp.

---

**Chúc bạn học tập hiệu quả với Study Timer! 🎓📚**

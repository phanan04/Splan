"""
Module: Timer Engine
Chức năng: Xử lý logic đếm ngược, quản lý thông báo, và vòng lặp timer
Sử dụng threading để không làm treo giao diện chính
"""

import threading
import time
from enum import Enum
from typing import Callable, Optional
from datetime import datetime
import platform
import subprocess


class TimerState(Enum):
    """Trạng thái timer"""
    IDLE = "idle"           # Chưa bắt đầu
    RUNNING = "running"     # Đang chạy
    PAUSED = "paused"       # Tạm dừng
    BREAK = "break"         # Đang nghỉ
    STOPPED = "stopped"     # Đã dừng


class TimerEngine:
    """
    Engine xử lý timer chính với hỗ trợ multi-threading
    
    Tính năng:
    - Đếm ngược thời gian học
    - Gửi thông báo hệ thống sau mỗi 30 phút
    - Tự động kích hoạt break time
    - Callback events cho giao diện
    """
    
    def __init__(self, 
                 work_duration_sec: int = 1800,  # 30 phút (mặc định)
                 break_duration_sec: int = 300,  # 5 phút
                 on_tick: Optional[Callable] = None,
                 on_state_changed: Optional[Callable] = None,
                 on_notification: Optional[Callable] = None):
        """
        Khởi tạo Timer Engine
        
        Args:
            work_duration_sec: Thời gian làm việc (giây)
            break_duration_sec: Thời gian tạm dừng (giây)
            on_tick: Callback mỗi là gọi mỗi giây (nhận remaining_time)
            on_state_changed: Callback khi trạng thái thay đổi (nhận state)
            on_notification: Callback khi có thông báo
        """
        self.work_duration_sec = work_duration_sec
        self.break_duration_sec = break_duration_sec
        
        self.state = TimerState.IDLE
        self.remaining_time = work_duration_sec  # Thời gian còn lại
        self.total_work_time = 0  # Thời gian làm việc tích lũy
        
        # Callbacks
        self.on_tick = on_tick
        self.on_state_changed = on_state_changed
        self.on_notification = on_notification
        
        # Threading
        self._timer_thread: Optional[threading.Thread] = None
        self._is_running = False
        self._lock = threading.Lock()
        self._epoch = 0  # Guard against stale threads
    
    def start(self) -> None:
        """Bắt đầu timer"""
        with self._lock:
            if self.state in (TimerState.IDLE, TimerState.STOPPED):
                # Kill any stale thread via epoch
                self._is_running = False
                self._epoch += 1
                epoch = self._epoch

                self.state = TimerState.RUNNING
                self.remaining_time = self.work_duration_sec
                self.total_work_time = 0
                self._is_running = True
                
                # Khởi tạo thread cho timer
                self._timer_thread = threading.Thread(
                    target=self._timer_loop,
                    args=(epoch,),
                    daemon=True
                )
                self._timer_thread.start()
                
                self._call_state_changed()
            elif self.state == TimerState.PAUSED:
                # Old thread exited when _is_running became False during pause.
                # Must spawn a new thread to drive ticks.
                self._epoch += 1
                epoch = self._epoch
                self.state = TimerState.RUNNING
                self._is_running = True
                self._timer_thread = threading.Thread(
                    target=self._timer_loop,
                    args=(epoch,),
                    daemon=True
                )
                self._timer_thread.start()
                self._call_state_changed()
    
    def pause(self) -> None:
        """Tạm dừng timer"""
        with self._lock:
            if self.state == TimerState.RUNNING:
                self.state = TimerState.PAUSED
                self._is_running = False
                self._call_state_changed()
    
    def resume(self) -> None:
        """Tiếp tục timer (giống start khi ở trạng thái PAUSED)"""
        self.start()
    
    def stop(self) -> None:
        """Dừng timer hoàn toàn"""
        with self._lock:
            self.state = TimerState.STOPPED
            self._is_running = False
            self.remaining_time = self.work_duration_sec
            self.total_work_time = 0
            self._call_state_changed()

    def skip_break(self) -> None:
        """Bỏ qua break, quay lại RUNNING ngay lập tức."""
        with self._lock:
            if self.state == TimerState.BREAK:
                self.state = TimerState.RUNNING
                self.remaining_time = self.work_duration_sec
                self._call_state_changed()
    
    def reset(self) -> None:
        """Đặt lại timer"""
        with self._lock:
            self.state = TimerState.IDLE
            self._is_running = False
            self.remaining_time = self.work_duration_sec
            self.total_work_time = 0
            self._call_state_changed()
    
    def _timer_loop(self, epoch: int) -> None:
        """
        Vòng lặp chính của timer chạy trên thread riêng
        Được gọi liên tục với chu kỳ 1 giây
        epoch dùng để vô hiệu hóa thread cũ khi start() tạo thread mới.
        """
        while self._is_running and self._epoch == epoch:
            try:
                time.sleep(1)  # Chờ 1 giây
                
                should_break = False
                with self._lock:
                    if self._is_running and self._epoch == epoch and self.state == TimerState.RUNNING:
                        self.remaining_time -= 1
                        self.total_work_time += 1
                        
                        # Gọi callback tick để cập nhật UI
                        self._call_tick()
                        
                        # Kiểm tra nếu đã hoàn thành work cycle
                        if self.remaining_time <= 0:
                            should_break = True
                
                # Gọi _trigger_break NGOÀI lock để tránh deadlock
                if should_break:
                    self._trigger_break(epoch)
            
            except Exception as e:
                print(f"❌ Lỗi trong timer loop: {e}")
    
    def _trigger_break(self, epoch: int) -> None:
        """
        Kích hoạt thời gian tạm dừng
        - Gửi thông báo hệ thống
        - Bắt đầu bộ đếm break time
        """
        # Gửi thông báo
        self._send_notification(
            title="⏱️ Thời gian tạm dừng",
            message=f"Bạn đã học {self.work_duration_sec // 60} phút. Hãy nghỉ ngơi {self.break_duration_sec // 60} phút!",
            duration=5
        )
        
        # Chuyển sang chế độ break
        with self._lock:
            self.state = TimerState.BREAK
            self.remaining_time = self.break_duration_sec
            self._call_state_changed()
        
        # Đếm ngược thời gian break
        break_start_time = time.time()
        while (self._is_running and self._epoch == epoch
               and time.time() - break_start_time < self.break_duration_sec
               and self.state == TimerState.BREAK):
            time.sleep(1)
            with self._lock:
                if self.state != TimerState.BREAK:
                    break
                elapsed = int(time.time() - break_start_time)
                self.remaining_time = max(0, self.break_duration_sec - elapsed)
                self._call_tick()
        
        # Sau break xong, quay lại trạng thái làm việc
        with self._lock:
            if self.state == TimerState.BREAK:
                self._send_notification(
                    title="🔔 Quay lại học tập",
                    message="Thời gian break chấm dứt! Quay lại học tập nào!",
                    duration=3
                )
                self.state = TimerState.RUNNING
                self.remaining_time = self.work_duration_sec
                self._call_state_changed()
    
    def _send_notification(self, title: str, message: str, duration: int = 5) -> None:
        """
        Gửi thông báo hệ thống (System Notification)
        
        Args:
            title: Tiêu đề thông báo
            message: Nội dung thông báo
            duration: Thời lượng hiển thị (giây)
        """
        try:
            if self.on_notification:
                self.on_notification({
                    'title': title,
                    'message': message,
                    'duration': duration
                })
            
            # Gửi thông báo hệ thống tùy theo OS
            self._send_system_notification(title, message)
        
        except Exception as e:
            print(f"⚠️ Không thể gửi thông báo: {e}")
    
    def _send_system_notification(self, title: str, message: str) -> None:
        """Gửi thông báo hệ thống OS"""
        system = platform.system()
        
        try:
            if system == "Windows":
                # Dùng toast notification trên Windows
                self._send_windows_notification(title, message)
            elif system == "Darwin":  # macOS
                self._send_macos_notification(title, message)
            elif system == "Linux":
                self._send_linux_notification(title, message)
        except Exception as e:
            print(f"⚠️ Lỗi gửi system notification: {e}")
    
    def _send_windows_notification(self, title: str, message: str) -> None:
        """Gửi thông báo trên Windows"""
        try:
            from win10toast import ToastNotifier
            notifier = ToastNotifier()
            notifier.show_toast(title, message, duration=5, threaded=True)
        except ImportError:
            print("⚠️ win10toast chưa cài đặt. Sử dụng powershell thay thế")
            self._send_windows_notification_powershell(title, message)
    
    def _send_windows_notification_powershell(self, title: str, message: str) -> None:
        """Fallback: Gửi thông báo Windows bằng PowerShell"""
        ps_script = f"""
        [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications.ToastNotification] | Out-Null
        
        $APP_ID = 'StudyTimer'
        $template = @"
        <toast>
            <visual>
                <binding template="ToastText02">
                    <text id="1">{title}</text>
                    <text id="2">{message}</text>
                </binding>
            </visual>
        </toast>
        "@
        
        $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
        $xml.LoadXml($template)
        $toast = New-Object Windows.UI.Notifications.ToastNotification $xml
        [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($APP_ID).Show($toast)
        """
        try:
            subprocess.run(
                ["powershell", "-Command", ps_script],
                capture_output=True,
                timeout=5
            )
        except Exception as e:
            print(f"⚠️ Không gửi được thông báo PowerShell: {e}")
    
    def _send_macos_notification(self, title: str, message: str) -> None:
        """Gửi thông báo trên macOS"""
        script = f'display notification "{message}" with title "{title}"'
        subprocess.run(["osascript", "-e", script], check=False)
    
    def _send_linux_notification(self, title: str, message: str) -> None:
        """Gửi thông báo trên Linux"""
        subprocess.run(
            ["notify-send", title, message],
            check=False
        )
    
    def _call_tick(self) -> None:
        """Gọi callback tick nếu được cấu hình"""
        if self.on_tick:
            self.on_tick({
                'remaining_time': self.remaining_time,
                'state': self.state.value,
                'total_work_time': self.total_work_time
            })
    
    def _call_state_changed(self) -> None:
        """Gọi callback state changed nếu được cấu hình"""
        if self.on_state_changed:
            self.on_state_changed({
                'state': self.state.value,
                'remaining_time': self.remaining_time
            })
    
    def get_formatted_time(self) -> str:
        """
        Định dạng thời gian còn lại thành MM:SS
        
        Returns:
            Chuỗi thời gian định dạng (e.g., "01:30")
        """
        minutes = self.remaining_time // 60
        seconds = self.remaining_time % 60
        return f"{minutes:02d}:{seconds:02d}"
    
    def get_state(self) -> str:
        """Lấy trạng thái timer hiện tại"""
        return self.state.value
    
    def get_remaining_time(self) -> int:
        """Lấy thời gian còn lại (giây)"""
        return self.remaining_time


# Test code
if __name__ == "__main__":
    print("🧪 Test Timer Engine\n")
    
    # Khởi tạo timer với 10 giây làm việc, 5 giây break (cho test)
    def on_tick_callback(data):
        print(f"⏱️  {data['remaining_time']}s | State: {data['state']}")
    
    def on_state_changed_callback(data):
        print(f"🔄 State changed: {data['state']}")
    
    def on_notification_callback(data):
        print(f"🔔 Notification: {data['title']} - {data['message']}")
    
    timer = TimerEngine(
        work_duration_sec=10,
        break_duration_sec=3,
        on_tick=on_tick_callback,
        on_state_changed=on_state_changed_callback,
        on_notification=on_notification_callback
    )
    
    print("Bắt đầu timer...")
    timer.start()
    
    # Chạy trong 30 giây
    try:
        time.sleep(30)
    except KeyboardInterrupt:
        print("\nDừng timer")
    
    timer.stop()
    print("✓ Test hoàn thành")

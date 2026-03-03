"""
Module: Timetable Manager
Chức năng: Quản lý lịch học, tải dữ liệu từ JSON, và tìm kiếm môn học hiện tại
"""

import json
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, List

class TimetableManager:
    """
    Quản lý lịch trình học tập
    - Tải dữ liệu từ file JSON
    - Tìm kiếm môn học dựa trên thời gian hiện tại
    - Có thể xem lịch theo tuần, ngày
    """
    
    def __init__(self, timetable_file: str = "timetable.json"):
        """
        Khởi tạo Timetable Manager
        Args:
            timetable_file: Đường dẫn tới file timetable.json
        """
        self.timetable_file = timetable_file
        self.schedule = {}
        self.break_config = {}
        self._load_timetable()
    
    def _load_timetable(self) -> None:
        """Tải dữ liệu lịch từ file JSON"""
        default_schedule = {d: [] for d in self.DAY_NAMES}
        default_config = {
            'workDurationMinutes': 25,
            'breakDurationMinutes': 5,
            'enableNotifications': True
        }
        if not os.path.exists(self.timetable_file):
            self.schedule = default_schedule
            self.break_config = default_config
            self._save_timetable()
            return
        try:
            with open(self.timetable_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.schedule = data.get('schedule', default_schedule)
                self.break_config = data.get('breakConfig', default_config)
        except Exception:
            self.schedule = default_schedule
            self.break_config = default_config
    
    def get_current_subject(self) -> Optional[Dict]:
        """
        Tìm kiếm môn học đang diễn ra dựa trên thời gian hệ thống
        
        Returns:
            Dict chứa thông tin môn học (subject, startTime, duration)
            None nếu không có môn học nào
        """
        now = datetime.now()
        day_name = now.strftime('%A')  # Monday, Tuesday, etc.
        current_time = now.time()
        
        # Nếu không có lịch cho ngày hôm nay
        if day_name not in self.schedule:
            return None
        
        classes_today = self.schedule[day_name]
        
        for class_info in classes_today:
            try:
                start_time = datetime.strptime(
                    class_info['startTime'], 
                    '%H:%M'
                ).time()
                duration = class_info['duration']  # tính bằng phút
                
                # Tính thời gian kết thúc
                end_datetime = datetime.combine(
                    now.date(),
                    start_time
                ) + timedelta(minutes=duration)
                end_time = end_datetime.time()
                
                # Kiểm tra xem thời gian hiện tại có nằm trong khoảng này không
                start_datetime = datetime.combine(now.date(), start_time)
                
                if start_datetime <= now <= end_datetime:
                    return {
                        'subject': class_info['subject'],
                        'startTime': class_info['startTime'],
                        'duration': duration,
                        'notes': class_info.get('notes', ''),
                        'endTime': end_time.strftime('%H:%M'),
                        'remainingMinutes': int(
                            (end_datetime - now).total_seconds() / 60
                        )
                    }
            except ValueError:
                continue
        
        return None
    
    def get_today_schedule(self) -> List[Dict]:
        """
        Lấy toàn bộ lịch học hôm nay
        
        Returns:
            List các môn học hôm nay
        """
        day_name = datetime.now().strftime('%A')
        return self.schedule.get(day_name, [])
    
    def get_next_subject(self) -> Optional[Dict]:
        """
        Lấy thông tin môn học tiếp theo (sắp đến)
        
        Returns:
            Dict chứa thông tin môn học tiếp theo
        """
        now = datetime.now()
        day_name = now.strftime('%A')
        current_time = now.time()
        
        if day_name not in self.schedule:
            return None
        
        classes_today = self.schedule[day_name]
        
        for class_info in classes_today:
            try:
                start_time = datetime.strptime(
                    class_info['startTime'], 
                    '%H:%M'
                ).time()
                
                start_datetime = datetime.combine(now.date(), start_time)
                
                # Tìm lớp học sắp diễn ra (sau thời điểm hiện tại)
                if start_datetime > now:
                    return {
                        'subject': class_info['subject'],
                        'startTime': class_info['startTime'],
                        'duration': class_info['duration'],
                        'minutesUntilStart': int(
                            (start_datetime - now).total_seconds() / 60
                        )
                    }
            except ValueError:
                continue
        
        return None
    
    def get_work_duration(self) -> int:
        """Lấy thời gian làm việc trước khi cần tạm dừng (phút)"""
        return self.break_config.get('workDurationMinutes', 30)
    
    def get_break_duration(self) -> int:
        """Lấy thời gian tạm dừng (phút)"""
        return self.break_config.get('breakDurationMinutes', 5)
    
    def should_enable_notifications(self) -> bool:
        """Kiểm tra xem có bật thông báo không"""
        return self.break_config.get('enableNotifications', True)

    # ═══════════════════ CRUD Operations ═══════════════════

    DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday',
                 'Friday', 'Saturday', 'Sunday']

    def get_schedule_for_day(self, day: str) -> List[Dict]:
        """Lấy lịch cho một ngày cụ thể"""
        return self.schedule.get(day, [])

    def add_subject(self, day: str, subject: str, start_time: str,
                    duration: int, notes: str = '',
                    work_minutes: int = 0, break_minutes: int = 0) -> None:
        """Thêm môn học mới vào một ngày.
        work_minutes/break_minutes = 0 means use global default."""
        if day not in self.schedule:
            self.schedule[day] = []
        entry = {
            'subject': subject,
            'startTime': start_time,
            'duration': duration,
            'notes': notes,
        }
        if work_minutes > 0:
            entry['workMinutes'] = work_minutes
        if break_minutes > 0:
            entry['breakMinutes'] = break_minutes
        self.schedule[day].append(entry)
        # Sắp xếp theo thời gian bắt đầu
        self.schedule[day].sort(key=lambda x: x['startTime'])
        self._save_timetable()

    def edit_subject(self, day: str, index: int, subject: str,
                     start_time: str, duration: int, notes: str = '',
                     work_minutes: int = 0, break_minutes: int = 0) -> None:
        """Sửa thông tin một môn học"""
        if day in self.schedule and 0 <= index < len(self.schedule[day]):
            entry = {
                'subject': subject,
                'startTime': start_time,
                'duration': duration,
                'notes': notes,
            }
            if work_minutes > 0:
                entry['workMinutes'] = work_minutes
            if break_minutes > 0:
                entry['breakMinutes'] = break_minutes
            self.schedule[day][index] = entry
            self.schedule[day].sort(key=lambda x: x['startTime'])
            self._save_timetable()

    def delete_subject(self, day: str, index: int) -> None:
        """Xóa một môn học"""
        if day in self.schedule and 0 <= index < len(self.schedule[day]):
            self.schedule[day].pop(index)
            self._save_timetable()

    def duplicate_day(self, src_day: str, dst_day: str) -> None:
        """Sao chép lịch từ ngày này sang ngày khác"""
        import copy
        self.schedule[dst_day] = copy.deepcopy(self.schedule.get(src_day, []))
        self._save_timetable()

    def clear_day(self, day: str) -> None:
        """Xóa toàn bộ lịch 1 ngày"""
        self.schedule[day] = []
        self._save_timetable()

    def reorder_subject(self, day: str, old_index: int, new_index: int) -> None:
        """Di chuyển môn học từ vị trí old_index sang new_index (drag & drop)"""
        if day not in self.schedule:
            return
        items = self.schedule[day]
        if 0 <= old_index < len(items) and 0 <= new_index < len(items):
            item = items.pop(old_index)
            items.insert(new_index, item)
            self._save_timetable()

    def get_subject_work_duration(self, subject_entry: dict) -> int:
        """Lấy work duration (phút) cho 1 môn. Fallback to global."""
        return subject_entry.get('workMinutes', 0) or self.get_work_duration()

    def get_subject_break_duration(self, subject_entry: dict) -> int:
        """Lấy break duration (phút) cho 1 môn. Fallback to global."""
        return subject_entry.get('breakMinutes', 0) or self.get_break_duration()

    def _save_timetable(self) -> None:
        """Ghi dữ liệu lịch ngược lại file JSON"""
        data = {
            'schedule': self.schedule,
            'breakConfig': self.break_config,
        }
        with open(self.timetable_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def reload(self) -> None:
        """Tải lại dữ liệu từ file"""
        self._load_timetable()


# Test code
if __name__ == "__main__":
    # Khởi tạo Timetable Manager
    manager = TimetableManager("timetable.json")
    
    # Kiểm tra môn học hiện tại
    current = manager.get_current_subject()
    print(f"\n📚 Môn học hiện tại: {current}")
    
    # Kiểm tra môn học tiếp theo
    next_class = manager.get_next_subject()
    print(f"⏭️  Môn học tiếp theo: {next_class}")
    
    # Lấy toàn bộ lịch hôm nay
    today_schedule = manager.get_today_schedule()
    print(f"\n📅 Lịch học hôm nay:")
    for cls in today_schedule:
        print(f"  - {cls['subject']}: {cls['startTime']} ({cls['duration']} phút)")
    
    # Lấy cấu hình break
    print(f"\n🔔 Cấu hình:")
    print(f"  - Thời gian làm việc: {manager.get_work_duration()} phút")
    print(f"  - Thời gian tạm dừng: {manager.get_break_duration()} phút")
    print(f"  - Bật thông báo: {manager.should_enable_notifications()}")

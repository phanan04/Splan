"""
Module: Internationalization (i18n)
Hỗ trợ đa ngôn ngữ: Tiếng Việt & English
"""

LANGUAGES = {
    'vi': 'Tiếng Việt',
    'en': 'English',
}

_TRANSLATIONS = {
    # ── Window ──
    'app_title':              {'vi': 'Study Timer', 'en': 'Study Timer'},
    'choose_subject':         {'vi': 'Chọn một môn để bắt đầu', 'en': 'Select a subject to start'},
    'not_started':            {'vi': 'Chưa bắt đầu', 'en': 'Not started'},

    # ── Control buttons ──
    'btn_start':              {'vi': 'Bắt đầu', 'en': 'Start'},
    'btn_pause':              {'vi': 'Dừng', 'en': 'Pause'},
    'btn_stop':               {'vi': 'Kết thúc', 'en': 'Stop'},
    'btn_next':               {'vi': 'Tiếp theo', 'en': 'Next'},

    # ── Utility buttons ──
    'btn_stats':              {'vi': 'Thống kê', 'en': 'Stats'},
    'btn_dark':               {'vi': 'Tối', 'en': 'Dark'},
    'btn_light':              {'vi': 'Sáng', 'en': 'Light'},
    'btn_pin':                {'vi': 'Ghim', 'en': 'Pin'},
    'btn_lang':               {'vi': 'EN', 'en': 'VI'},

    # ── Day names (short) ──
    'day_mon':                {'vi': 'T2', 'en': 'Mon'},
    'day_tue':                {'vi': 'T3', 'en': 'Tue'},
    'day_wed':                {'vi': 'T4', 'en': 'Wed'},
    'day_thu':                {'vi': 'T5', 'en': 'Thu'},
    'day_fri':                {'vi': 'T6', 'en': 'Fri'},
    'day_sat':                {'vi': 'T7', 'en': 'Sat'},
    'day_sun':                {'vi': 'CN', 'en': 'Sun'},

    # ── Day names (full) ──
    'day_monday':             {'vi': 'Thứ Hai', 'en': 'Monday'},
    'day_tuesday':            {'vi': 'Thứ Ba', 'en': 'Tuesday'},
    'day_wednesday':          {'vi': 'Thứ Tư', 'en': 'Wednesday'},
    'day_thursday':           {'vi': 'Thứ Năm', 'en': 'Thursday'},
    'day_friday':             {'vi': 'Thứ Sáu', 'en': 'Friday'},
    'day_saturday':           {'vi': 'Thứ Bảy', 'en': 'Saturday'},
    'day_sunday':             {'vi': 'Chủ Nhật', 'en': 'Sunday'},

    # ── Schedule / Cards ──
    'copy_schedule':          {'vi': 'Sao chép lịch', 'en': 'Copy schedule'},
    'today':                  {'vi': 'Hôm nay', 'en': 'Today'},
    'minutes_short':          {'vi': 'phút', 'en': 'min'},
    'add_subject':            {'vi': '+  Thêm môn học', 'en': '+  Add Subject'},
    'no_subjects':            {'vi': 'Chưa có môn học nào', 'en': 'No subjects yet'},
    'no_subjects_hint':       {'vi': 'Nhấn "+ Thêm môn học" hoặc Ctrl+N', 'en': 'Click "+ Add Subject" or Ctrl+N'},
    'session_fmt':            {'vi': 'Phiên {cur}/{total}', 'en': 'Session {cur}/{total}'},
    'summary_fmt':            {'vi': '{n} môn  ·  {h}h{m:02d}p  ·  Nghỉ mỗi {w}p{streak}',
                               'en': '{n} subj  ·  {h}h{m:02d}m  ·  Break every {w}m{streak}'},
    'streak_fmt':             {'vi': '  ·  {d} ngày liên tục', 'en': '  ·  {d} day streak'},

    # ── Timer states ──
    'state_idle':             {'vi': 'Chưa bắt đầu', 'en': 'Not started'},
    'state_running':          {'vi': 'Đang học', 'en': 'Studying'},
    'state_paused':           {'vi': 'Tạm dừng', 'en': 'Paused'},
    'state_break':            {'vi': 'Nghỉ giải lao', 'en': 'Break time'},
    'state_stopped':          {'vi': 'Đã dừng', 'en': 'Stopped'},
    'all_done':               {'vi': 'Hoàn thành tất cả!', 'en': 'All done!'},
    'all_done_sub':           {'vi': 'Tuyệt vời — Nghỉ ngơi thôi', 'en': 'Great job — Time to rest'},

    # ── Hints ──
    'hints': {
        'vi': 'Space: bắt đầu/dừng  ·  S: kết thúc  ·  N: tiếp  ·  D: đổi theme  ·  1-7: chọn ngày  ·  Ctrl+N: thêm',
        'en': 'Space: start/pause  ·  S: stop  ·  N: next  ·  D: theme  ·  1-7: select day  ·  Ctrl+N: add',
    },

    # ── Subject Dialog ──
    'dlg_add_title':          {'vi': 'Thêm môn học', 'en': 'Add Subject'},
    'dlg_edit_title':         {'vi': 'Sửa môn học', 'en': 'Edit Subject'},
    'dlg_subject_name':       {'vi': 'Tên môn học', 'en': 'Subject name'},
    'dlg_subject_placeholder': {'vi': 'Ví dụ: Lập trình Python', 'en': 'e.g. Python Programming'},
    'dlg_start_time':         {'vi': 'Bắt đầu', 'en': 'Start time'},
    'dlg_duration':           {'vi': 'Thời lượng', 'en': 'Duration'},
    'dlg_notes':              {'vi': 'Ghi chú', 'en': 'Notes'},
    'dlg_notes_placeholder':  {'vi': 'Ghi chú (tùy chọn)', 'en': 'Notes (optional)'},
    'dlg_work_duration':      {'vi': 'Pomodoro (làm)', 'en': 'Pomodoro (work)'},
    'dlg_break_duration':     {'vi': 'Pomodoro (nghỉ)', 'en': 'Pomodoro (break)'},
    'dlg_use_default':        {'vi': 'Mặc định', 'en': 'Default'},
    'btn_cancel':             {'vi': 'Hủy', 'en': 'Cancel'},
    'btn_save':               {'vi': 'Lưu', 'en': 'Save'},

    # ── Delete confirm ──
    'delete_title':           {'vi': 'Xóa môn học', 'en': 'Delete Subject'},
    'delete_confirm':         {'vi': 'Xóa "{subject}" ({time})?', 'en': 'Delete "{subject}" ({time})?'},
    'ctx_edit':               {'vi': 'Sửa môn học', 'en': 'Edit subject'},
    'ctx_delete':             {'vi': 'Xóa môn học', 'en': 'Delete subject'},

    # ── Duplicate Dialog ──
    'dup_title':              {'vi': 'Sao chép lịch', 'en': 'Copy Schedule'},
    'dup_header':             {'vi': 'Sao chép vào {day}', 'en': 'Copy into {day}'},
    'dup_hint':               {'vi': 'Chọn ngày nguồn:', 'en': 'Select source day:'},
    'btn_copy':               {'vi': 'Sao chép', 'en': 'Copy'},

    # ── Stats Dialog ──
    'stats_title':            {'vi': 'Thống kê học tập', 'en': 'Study Statistics'},
    'stats_streak':           {'vi': 'ngày liên tục', 'en': 'day streak'},
    'stats_today':            {'vi': 'phút hôm nay', 'en': 'min today'},
    'stats_week':             {'vi': 'phút tuần này', 'en': 'min this week'},
    'stats_total':            {'vi': 'phút tổng', 'en': 'min total'},
    'stats_7days':            {'vi': '7 ngày gần nhất', 'en': 'Last 7 days'},
    'stats_no_data':          {'vi': 'Chưa có dữ liệu — Hãy bắt đầu học!', 'en': 'No data yet — Start studying!'},
    'stats_sessions':         {'vi': 'Tổng {n} phiên đã ghi nhận', 'en': '{n} sessions recorded'},
    'stats_heatmap':          {'vi': 'Bản đồ hoạt động', 'en': 'Activity Heatmap'},
    'btn_close':              {'vi': 'Đóng', 'en': 'Close'},

    # ── Calendar ──
    'cal_export':             {'vi': 'Xuất ICS', 'en': 'Export ICS'},
    'cal_import':             {'vi': 'Nhập ICS', 'en': 'Import ICS'},
    'cal_export_ok':          {'vi': 'Đã xuất lịch thành công!', 'en': 'Schedule exported successfully!'},
    'cal_import_ok':          {'vi': 'Đã nhập lịch thành công!', 'en': 'Schedule imported successfully!'},
    'cal_import_fail':        {'vi': 'Lỗi nhập lịch', 'en': 'Import error'},

    # ── Tray ──
    'tray_show':              {'vi': 'Hiện cửa sổ', 'en': 'Show Window'},
    'tray_start':             {'vi': 'Bắt đầu', 'en': 'Start'},
    'tray_pause':             {'vi': 'Tạm dừng', 'en': 'Pause'},
    'tray_quit':              {'vi': 'Thoát', 'en': 'Quit'},
    'tray_minimized':         {'vi': 'Ứng dụng vẫn chạy trong system tray',
                               'en': 'App is still running in system tray'},

    # ── Mini Timer ──
    'mini_open':              {'vi': 'Mini Timer', 'en': 'Mini Timer'},
    'mini_back':              {'vi': 'Quay lại', 'en': 'Back'},

    # ── Auto-start ──
    'autostart_notif_title':  {'vi': 'Tự động bắt đầu', 'en': 'Auto-started'},
    'autostart_notif_msg':    {'vi': 'Đã bắt đầu: {subject}', 'en': 'Started: {subject}'},

    # ── Settings Dialog ──
    'settings_title':         {'vi': 'Cài đặt', 'en': 'Settings'},
    'settings_btn':           {'vi': 'Cài đặt', 'en': 'Settings'},
    'settings_appearance':    {'vi': '🎨  Giao diện', 'en': '🎨  Appearance'},
    'settings_behavior':      {'vi': '⚙  Hành vi', 'en': '⚙  Behavior'},
    'settings_smart':         {'vi': '🧠  Tính năng thông minh', 'en': '🧠  Smart Features'},
    'settings_dark_mode':     {'vi': 'Chế độ tối', 'en': 'Dark mode'},
    'settings_dark_mode_sub': {'vi': 'Giao diện nền đen', 'en': 'Dark background theme'},
    'settings_always_on_top': {'vi': 'Luôn hiện trên cùng', 'en': 'Always on top'},
    'settings_always_on_top_sub': {'vi': 'Cửa sổ không bị che khuất', 'en': 'Window stays above others'},
    'settings_minimize_tray': {'vi': 'Thu nhỏ xuống tray', 'en': 'Minimize to tray'},
    'settings_minimize_tray_sub': {'vi': 'Ẩn vào system tray khi đóng', 'en': 'Hide to system tray on close'},
    'settings_sound':         {'vi': 'Âm thanh thông báo', 'en': 'Sound effects'},
    'settings_sound_sub':     {'vi': 'Phát tiếng khi hết giờ / nghỉ', 'en': 'Play chime on break / resume'},
    'settings_autostart':     {'vi': 'Tự động bắt đầu', 'en': 'Auto-start'},
    'settings_autostart_sub': {'vi': 'Tự khởi động môn học đúng giờ', 'en': 'Auto-start subjects at scheduled time'},
    'settings_auto_advance':  {'vi': 'Tự động chuyển môn', 'en': 'Auto-advance subject'},
    'settings_auto_advance_sub': {'vi': 'Tự chuyển sang môn tiếp khi hết giờ', 'en': 'Move to next subject when time is up'},
    'settings_smart_break':   {'vi': 'Bỏ qua nghỉ thông minh', 'en': 'Smart break skip'},
    'settings_smart_break_sub': {'vi': 'Bỏ qua nghỉ nếu còn ít thời gian học', 'en': 'Skip break if little study time remains'},
    'settings_lang':          {'vi': 'Ngôn ngữ', 'en': 'Language'},
    'settings_lang_sub':      {'vi': 'Chọn ngôn ngữ hiển thị', 'en': 'Choose display language'},
    'settings_restart_hint':  {'vi': '* Đổi ngôn ngữ có hiệu lực sau khi khởi động lại', 'en': '* Language change takes effect after restart'},

    # ── Smart flow (v7.1) ──
    'btn_resume':             {'vi': 'Tiếp tục', 'en': 'Resume'},
    'btn_finish':             {'vi': 'Hoàn thành', 'en': 'Finish'},
    'pomo_cycle':             {'vi': '🍅 {cur}/{total}', 'en': '🍅 {cur}/{total}'},
    'today_total':            {'vi': 'Hôm nay: {h}h{m:02d}p', 'en': 'Today: {h}h{m:02d}m'},
    'subject_progress':       {'vi': '{elapsed}/{total}p', 'en': '{elapsed}/{total}m'},
    'subject_remaining':      {'vi': '⏳ Còn lại: {m:02d}:{s:02d}', 'en': '⏳ Remaining: {m:02d}:{s:02d}'},
    'subject_remaining_short': {'vi': 'Môn học', 'en': 'Subject'},
    'auto_advance_notif':     {'vi': 'Đã hoàn thành {subject}! Chuyển sang môn tiếp theo.', 'en': 'Finished {subject}! Moving to next.'},
    'auto_advance_title':     {'vi': 'Chuyển môn', 'en': 'Next subject'},
    'autostart_label':        {'vi': 'Tự động', 'en': 'Auto'},
}

# Current language
_current_lang = 'vi'


def set_language(lang: str):
    global _current_lang
    if lang in LANGUAGES:
        _current_lang = lang


def get_language() -> str:
    return _current_lang


def t(key: str, **kwargs) -> str:
    """Get translated string. Supports {placeholder} formatting."""
    entry = _TRANSLATIONS.get(key)
    if not entry:
        return key
    text = entry.get(_current_lang, entry.get('vi', key))
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError):
            pass
    return text


def get_day_short(day_en: str) -> str:
    """Get short day name from English day name."""
    key_map = {
        'Monday': 'day_mon', 'Tuesday': 'day_tue', 'Wednesday': 'day_wed',
        'Thursday': 'day_thu', 'Friday': 'day_fri', 'Saturday': 'day_sat',
        'Sunday': 'day_sun',
    }
    return t(key_map.get(day_en, ''))


def get_day_full(day_en: str) -> str:
    """Get full day name from English day name."""
    key_map = {
        'Monday': 'day_monday', 'Tuesday': 'day_tuesday',
        'Wednesday': 'day_wednesday', 'Thursday': 'day_thursday',
        'Friday': 'day_friday', 'Saturday': 'day_saturday',
        'Sunday': 'day_sunday',
    }
    return t(key_map.get(day_en, ''))

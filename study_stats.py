"""
Module: Study Statistics
Theo dõi lịch sử học tập, tính streak, tổng hợp thời gian.
Lưu dữ liệu vào study_history.json.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict


class StudyStats:
    """Quản lý thống kê học tập."""

    def __init__(self, filepath: str = "study_history.json"):
        self.filepath = filepath
        self.sessions: List[dict] = []
        self._load()

    # ── Persistence ──

    def _load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.sessions = data.get('sessions', [])
            except Exception:
                self.sessions = []
        else:
            self.sessions = []

    def _save(self):
        data = {'sessions': self.sessions}
        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ── Logging ──

    def log_session(self, subject: str, duration_sec: int):
        """Ghi nhận một phiên học hoàn thành."""
        now = datetime.now()
        self.sessions.append({
            'subject': subject,
            'date': now.strftime('%Y-%m-%d'),
            'day': now.strftime('%A'),
            'time': now.strftime('%H:%M'),
            'duration_min': round(duration_sec / 60, 1),
            'timestamp': now.isoformat(),
        })
        self._save()

    # ── Queries ──

    def get_today_minutes(self) -> float:
        """Tổng phút học hôm nay."""
        today = datetime.now().strftime('%Y-%m-%d')
        return sum(s['duration_min'] for s in self.sessions
                   if s['date'] == today)

    def get_week_minutes(self) -> float:
        """Tổng phút học tuần này (Mon–Sun)."""
        now = datetime.now()
        # Monday of this week
        start = now - timedelta(days=now.weekday())
        start_str = start.strftime('%Y-%m-%d')
        return sum(s['duration_min'] for s in self.sessions
                   if s['date'] >= start_str)

    def get_total_minutes(self) -> float:
        """Tổng phút học từ trước đến nay."""
        return sum(s['duration_min'] for s in self.sessions)

    def get_total_sessions(self) -> int:
        """Tổng số phiên học."""
        return len(self.sessions)

    def get_streak(self) -> int:
        """Tính chuỗi ngày học liên tục (streak) tính đến hôm nay."""
        if not self.sessions:
            return 0

        study_dates = sorted(set(s['date'] for s in self.sessions),
                             reverse=True)
        today = datetime.now().strftime('%Y-%m-%d')

        # Nếu hôm nay chưa học thì vẫn tính streak nếu hôm qua có
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        if study_dates[0] != today and study_dates[0] != yesterday:
            return 0

        streak = 0
        check_date = datetime.now().date()
        # Nếu hôm nay chưa học, bắt đầu từ hôm qua
        if today not in study_dates:
            check_date -= timedelta(days=1)

        date_set = set(study_dates)
        while check_date.strftime('%Y-%m-%d') in date_set:
            streak += 1
            check_date -= timedelta(days=1)

        return streak

    def get_subject_breakdown(self, days: int = 7) -> Dict[str, float]:
        """Phân tích thời gian theo môn trong N ngày gần nhất."""
        cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        breakdown = defaultdict(float)
        for s in self.sessions:
            if s['date'] >= cutoff:
                breakdown[s['subject']] += s['duration_min']
        # Sort by total time descending
        return dict(sorted(breakdown.items(),
                           key=lambda x: x[1], reverse=True))

    def get_daily_totals(self, days: int = 7) -> Dict[str, float]:
        """Tổng phút học mỗi ngày trong N ngày gần nhất."""
        totals = defaultdict(float)
        for s in self.sessions:
            totals[s['date']] += s['duration_min']

        # Fill missing days with 0
        result = {}
        for i in range(days - 1, -1, -1):
            d = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            result[d] = totals.get(d, 0)
        return result

    def get_recent_sessions(self, limit: int = 20) -> List[dict]:
        """Lấy N phiên học gần nhất."""
        return list(reversed(self.sessions[-limit:]))

    def get_heatmap_data(self, weeks: int = 16) -> Dict[str, float]:
        """
        Get daily study minutes for the last N weeks.
        Returns: {'YYYY-MM-DD': minutes, ...} for every day in range (0 if no study).
        """
        totals = defaultdict(float)
        for s in self.sessions:
            totals[s['date']] += s['duration_min']

        result = {}
        today = datetime.now().date()
        total_days = weeks * 7
        for i in range(total_days - 1, -1, -1):
            d = (today - timedelta(days=i)).strftime('%Y-%m-%d')
            result[d] = totals.get(d, 0)
        return result

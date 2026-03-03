"""
Module: Calendar Sync (ICS)
Export/Import schedule as .ics files compatible with Google Calendar, Outlook, etc.
"""

import os
from datetime import datetime, timedelta
from typing import Dict, List
import uuid


def _escape_ics(text: str) -> str:
    """Escape special chars for ICS."""
    return (text
            .replace('\\', '\\\\')
            .replace(';', '\\;')
            .replace(',', '\\,')
            .replace('\n', '\\n'))


def export_ics(schedule: Dict[str, List[dict]], filepath: str,
               reference_date: datetime = None) -> str:
    """
    Export schedule to ICS file.
    Uses reference_date (default: this week's Monday) to set real dates.
    Returns the filepath written.
    """
    if reference_date is None:
        now = datetime.now()
        # Find this week's Monday
        reference_date = now - timedelta(days=now.weekday())
        reference_date = reference_date.replace(hour=0, minute=0, second=0, microsecond=0)

    day_offsets = {
        'Monday': 0, 'Tuesday': 1, 'Wednesday': 2,
        'Thursday': 3, 'Friday': 4, 'Saturday': 5, 'Sunday': 6,
    }

    lines = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//StudyTimer//StudyTimer//EN',
        'CALSCALE:GREGORIAN',
        'METHOD:PUBLISH',
        'X-WR-CALNAME:Study Timer Schedule',
    ]

    for day_en, classes in schedule.items():
        offset = day_offsets.get(day_en, 0)
        base_date = reference_date + timedelta(days=offset)

        for cls in classes:
            subject = cls.get('subject', 'Study')
            start_str = cls.get('startTime', '08:00')
            duration = cls.get('duration', 60)
            notes = cls.get('notes', '')

            start_h, start_m = map(int, start_str.split(':'))
            dt_start = base_date.replace(hour=start_h, minute=start_m)
            dt_end = dt_start + timedelta(minutes=duration)

            uid = str(uuid.uuid4())

            lines.append('BEGIN:VEVENT')
            lines.append(f'UID:{uid}')
            lines.append(f'DTSTART:{dt_start.strftime("%Y%m%dT%H%M%S")}')
            lines.append(f'DTEND:{dt_end.strftime("%Y%m%dT%H%M%S")}')
            lines.append(f'SUMMARY:{_escape_ics(subject)}')
            if notes:
                lines.append(f'DESCRIPTION:{_escape_ics(notes)}')

            # RRULE for weekly recurrence
            day_abbr = day_en[:2].upper()
            lines.append(f'RRULE:FREQ=WEEKLY;BYDAY={day_abbr}')

            lines.append(f'DTSTAMP:{datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")}')
            lines.append('END:VEVENT')

    lines.append('END:VCALENDAR')

    content = '\r\n'.join(lines) + '\r\n'
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    return filepath


def import_ics(filepath: str) -> Dict[str, List[dict]]:
    """
    Import ICS file and return schedule dict.
    Only reads VEVENT entries, maps to day-of-week.
    Returns: {'Monday': [{'subject': ..., 'startTime': ..., 'duration': ..., 'notes': ...}], ...}
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Unfold continuation lines (RFC 5545)
    content = content.replace('\r\n ', '').replace('\r\n\t', '')

    schedule: Dict[str, List[dict]] = {}
    events = content.split('BEGIN:VEVENT')

    for event_block in events[1:]:  # skip before first VEVENT
        end_idx = event_block.find('END:VEVENT')
        if end_idx >= 0:
            event_block = event_block[:end_idx]

        props = {}
        for line in event_block.strip().split('\n'):
            line = line.strip('\r')
            if ':' in line:
                key, _, val = line.partition(':')
                # Handle params like DTSTART;VALUE=DATE:20260303
                key = key.split(';')[0]
                props[key.upper()] = val

        summary = props.get('SUMMARY', 'Unknown')
        summary = (summary
                   .replace('\\,', ',')
                   .replace('\\;', ';')
                   .replace('\\n', '\n')
                   .replace('\\\\', '\\'))

        description = props.get('DESCRIPTION', '')
        description = (description
                       .replace('\\,', ',')
                       .replace('\\;', ';')
                       .replace('\\n', '\n')
                       .replace('\\\\', '\\'))

        dtstart_str = props.get('DTSTART', '')
        dtend_str = props.get('DTEND', '')

        if not dtstart_str:
            continue

        try:
            # Parse DTSTART
            dt_start = _parse_ics_datetime(dtstart_str)
            if dt_start is None:
                continue

            # Determine duration
            if dtend_str:
                dt_end = _parse_ics_datetime(dtend_str)
                if dt_end:
                    duration_min = int((dt_end - dt_start).total_seconds() / 60)
                else:
                    duration_min = 60
            else:
                duration_min = 60

            # Determine day of week
            # Check RRULE for BYDAY
            rrule = props.get('RRULE', '')
            day_en = None
            if 'BYDAY=' in rrule:
                byday = rrule.split('BYDAY=')[1].split(';')[0].split(',')[0]
                day_map = {
                    'MO': 'Monday', 'TU': 'Tuesday', 'WE': 'Wednesday',
                    'TH': 'Thursday', 'FR': 'Friday', 'SA': 'Saturday',
                    'SU': 'Sunday',
                }
                day_en = day_map.get(byday.upper())

            if not day_en:
                day_en = dt_start.strftime('%A')

            start_time = dt_start.strftime('%H:%M')

            entry = {
                'subject': summary,
                'startTime': start_time,
                'duration': max(5, duration_min),
                'notes': description,
            }

            if day_en not in schedule:
                schedule[day_en] = []
            schedule[day_en].append(entry)

        except Exception:
            continue

    # Sort each day by start time
    for day in schedule:
        schedule[day].sort(key=lambda x: x['startTime'])

    return schedule


def _parse_ics_datetime(s: str) -> datetime:
    """Parse ICS datetime string. Handles various formats."""
    s = s.strip().rstrip('Z')
    for fmt in ('%Y%m%dT%H%M%S', '%Y%m%dT%H%M', '%Y%m%d'):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None

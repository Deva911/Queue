"""Calendar adapter boundary. Phase 4 adds one real provider (Google or Outlook).

The fake never claims a booking succeeded: it only reports that no calendar is connected.
"""

from __future__ import annotations

from typing import Protocol


class CalendarProvider(Protocol):
    def is_connected(self) -> bool: ...


class FakeCalendar:
    def is_connected(self) -> bool:
        return False

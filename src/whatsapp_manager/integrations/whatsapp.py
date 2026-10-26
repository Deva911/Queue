"""WhatsApp adapter boundary. Phase 3 adds the official Meta Cloud API version."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


class WhatsAppSender(Protocol):
    def send_text(self, to: str, body: str) -> str: ...


@dataclass
class FakeWhatsAppSender:
    """Records messages instead of sending them."""

    sent: list[tuple[str, str]] = field(default_factory=list)

    def send_text(self, to: str, body: str) -> str:
        self.sent.append((to, body))
        return f"simulated-{len(self.sent)}"

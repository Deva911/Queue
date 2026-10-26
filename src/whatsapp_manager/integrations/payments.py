"""Payments adapter boundary. Phase 5 adds hosted checkout with verified webhooks.

The fake never marks anything PAID and never handles card details.
"""

from __future__ import annotations

from typing import Protocol


class PaymentProvider(Protocol):
    def is_connected(self) -> bool: ...


class FakePayments:
    def is_connected(self) -> bool:
        return False

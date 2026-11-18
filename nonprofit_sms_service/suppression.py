from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from .models import CampaignRequest, DecisionItem, DonorReceipt, VolunteerReminder


class SuppressionEngine:
    def __init__(self, now: datetime | None = None):
        self.now = now or datetime.now(timezone.utc)

    def evaluate(self, request: CampaignRequest) -> List[DecisionItem]:
        decisions: List[DecisionItem] = []
        opted_out = set(request.opted_out_numbers)

        for message in request.messages:
            if message.phone_number in opted_out:
                decisions.append(
                    DecisionItem(
                        kind=message.kind,
                        phone_number=message.phone_number,
                        action="suppress",
                        reason="recipient opted out",
                    )
                )
                continue

            if isinstance(message, VolunteerReminder) and message.starts_at <= self.now:
                decisions.append(
                    DecisionItem(
                        kind=message.kind,
                        phone_number=message.phone_number,
                        action="suppress",
                        reason="reminder is stale",
                    )
                )
                continue

            decisions.append(
                DecisionItem(
                    kind=message.kind,
                    phone_number=message.phone_number,
                    action="send",
                    reason="eligible",
                    body=self._render_body(message),
                )
            )

        return decisions

    def _render_body(self, message: DonorReceipt | VolunteerReminder) -> str:
        if isinstance(message, DonorReceipt):
            dollars = message.amount_cents / 100
            return (
                f"Thanks {message.donor_name}. We received your donation of "
                f"${dollars:.2f}. Receipt {message.receipt_id}."
            )

        return (
            f"Hi {message.volunteer_name}, reminder: {message.shift_name} starts at "
            f"{message.starts_at.isoformat()}."
        )

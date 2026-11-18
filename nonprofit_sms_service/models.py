from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional, Union

from pydantic import BaseModel, Field


class DonorReceipt(BaseModel):
    kind: Literal["donor_receipt"] = "donor_receipt"
    phone_number: str
    donor_name: str
    amount_cents: int = Field(gt=0)
    receipt_id: str


class VolunteerReminder(BaseModel):
    kind: Literal["volunteer_reminder"] = "volunteer_reminder"
    phone_number: str
    volunteer_name: str
    shift_name: str
    starts_at: datetime


OutboundMessage = Union[DonorReceipt, VolunteerReminder]


class CampaignRequest(BaseModel):
    campaign_name: str
    messages: List[OutboundMessage]
    opted_out_numbers: List[str] = Field(default_factory=list)


class DecisionItem(BaseModel):
    kind: str
    phone_number: str
    action: Literal["send", "suppress"]
    reason: str
    body: Optional[str] = None


class CampaignReport(BaseModel):
    campaign_name: str
    sent_count: int
    suppressed_count: int
    decisions: List[DecisionItem]
    message_ids: List[str] = Field(default_factory=list)

from __future__ import annotations

import argparse
import os
from datetime import datetime, timedelta, timezone
from typing import List

from .infrai import infrai
from .models import CampaignReport, CampaignRequest, DonorReceipt, VolunteerReminder
from .suppression import SuppressionEngine


def run_campaign(request: CampaignRequest, engine: SuppressionEngine | None = None) -> CampaignReport:
    engine = engine or SuppressionEngine()
    decisions = engine.evaluate(request)
    approved = [item for item in decisions if item.action == "send" and item.body]

    message_ids: List[str] = []
    if approved:
        payload = [{"to": item.phone_number, "text": item.body} for item in approved]
        result = infrai.sms.batch.send(payload)
        data = result.get("data", result)
        if isinstance(data, list):
            message_ids = [str(item.get("message_id", "")) for item in data if item.get("message_id")]

    return CampaignReport(
        campaign_name=request.campaign_name,
        sent_count=len(approved),
        suppressed_count=len(decisions) - len(approved),
        decisions=decisions,
        message_ids=message_ids,
    )


def sample_request(recipient: str) -> CampaignRequest:
    now = datetime.now(timezone.utc)
    return CampaignRequest(
        campaign_name="spring-outreach",
        opted_out_numbers=["+15550000002"],
        messages=[
            DonorReceipt(
                phone_number=recipient,
                donor_name="Avery",
                amount_cents=2500,
                receipt_id="R-1001",
            ),
            DonorReceipt(
                phone_number="+15550000002",
                donor_name="Jordan",
                amount_cents=1000,
                receipt_id="R-1002",
            ),
            VolunteerReminder(
                phone_number=recipient,
                volunteer_name="Lee",
                shift_name="Food Pantry",
                starts_at=now + timedelta(hours=4),
            ),
            VolunteerReminder(
                phone_number="+15550000004",
                volunteer_name="Sam",
                shift_name="Phone Bank",
                starts_at=now - timedelta(hours=1),
            ),
        ],
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the sample nonprofit SMS campaign.")
    parser.add_argument(
        "--recipient",
        default=os.environ.get("SMS_RECIPIENT"),
        help="recipient for the sample messages (or set SMS_RECIPIENT)",
    )
    args = parser.parse_args()
    if not args.recipient:
        parser.error("--recipient or SMS_RECIPIENT is required")

    report = run_campaign(sample_request(args.recipient))
    print(report.model_dump_json(indent=2))

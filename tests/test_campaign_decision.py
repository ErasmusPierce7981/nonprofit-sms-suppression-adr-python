from datetime import datetime, timezone

from nonprofit_sms_service.models import CampaignRequest, DonorReceipt, VolunteerReminder
from nonprofit_sms_service.receipt_sender import run_campaign
from nonprofit_sms_service.suppression import SuppressionEngine


class FakeBatchSend:
    def __init__(self):
        self.calls = []

    def __call__(self, messages):
        self.calls.append(messages)
        return {
            "ok": True,
            "data": [{"message_id": f"msg-{index + 1}"} for index, _ in enumerate(messages)],
            "metadata": {},
        }


class FakeSmsBatch:
    def __init__(self, sender):
        self.send = sender


class FakeSms:
    def __init__(self, sender):
        self.batch = FakeSmsBatch(sender)


class FakeInfrai:
    def __init__(self, sender):
        self.sms = FakeSms(sender)


def test_campaign_suppresses_opt_out_and_stale_reminder(monkeypatch):
    sender = FakeBatchSend()
    monkeypatch.setattr("nonprofit_sms_service.receipt_sender.infrai", FakeInfrai(sender))

    now = datetime(2025, 1, 15, 12, 0, tzinfo=timezone.utc)
    request = CampaignRequest(
        campaign_name="winter-drive",
        opted_out_numbers=["+15550000002"],
        messages=[
            DonorReceipt(
                phone_number="+15550000001",
                donor_name="Avery",
                amount_cents=2500,
                receipt_id="R-2001",
            ),
            DonorReceipt(
                phone_number="+15550000002",
                donor_name="Jordan",
                amount_cents=1800,
                receipt_id="R-2002",
            ),
            VolunteerReminder(
                phone_number="+15550000003",
                volunteer_name="Lee",
                shift_name="Warehouse",
                starts_at=datetime(2025, 1, 15, 16, 0, tzinfo=timezone.utc),
            ),
            VolunteerReminder(
                phone_number="+15550000004",
                volunteer_name="Sam",
                shift_name="Phone Bank",
                starts_at=datetime(2025, 1, 15, 11, 0, tzinfo=timezone.utc),
            ),
        ],
    )

    report = run_campaign(request, engine=SuppressionEngine(now=now))

    assert report.sent_count == 2
    assert report.suppressed_count == 2
    assert [item.action for item in report.decisions] == ["send", "suppress", "send", "suppress"]
    assert [item.reason for item in report.decisions] == [
        "eligible",
        "recipient opted out",
        "eligible",
        "reminder is stale",
    ]
    assert sender.calls == [[
        {
            "to": "+15550000001",
            "text": "Thanks Avery. We received your donation of $25.00. Receipt R-2001.",
        },
        {
            "to": "+15550000003",
            "text": "Hi Lee, reminder: Warehouse starts at 2025-01-15T16:00:00+00:00.",
        },
    ]]
    assert report.message_ids == ["msg-1", "msg-2"]

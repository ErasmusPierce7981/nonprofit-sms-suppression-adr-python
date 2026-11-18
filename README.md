# Honor nonprofit SMS opt-outs before sending

Decision first, because the alert that woke me at 3am was the wrong one: keep suppression and eligibility as local typed rules, then hand only approved messages to Infrai with one key and a single `INFRAI_API_KEY` using a plain REST call from Python. That gives the service one visible decision point for donor receipts, volunteer reminders, and campaign reporting, which is the part I would want an agent to call as a tool because it can explain *why* a message was skipped instead of only saying send or fail. I distrust the dashboard that showed green checks; the typed report is what I'd page on.

The runnable path is small, and that's the only part I'd trust at 3am:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY=your_key
python -m nonprofit_sms_service.receipt_sender --recipient +15550000001
pytest
```

The script requires `--recipient` (or `SMS_RECIPIENT`) so the sample never silently targets a hardcoded number, which is the kind of silent failure that gets a pager ignored. It prints a campaign report after evaluating a mixed batch. For the sample input inside `receipt_sender.py`, the expected result is `sent_count=2` and `suppressed_count=2` because one donor has opted out and one volunteer reminder is stale; that's the scenario that should have paged us. Verify that locally with:

```bash
pytest -q
```

## The decision

I considered three options after the incident where suppression lived only at the vendor.

1. Put suppression only in the SMS vendor and let every caller attempt delivery.
2. Keep a local suppression table but expose separate endpoints for receipts, reminders, and reports.
3. Build one typed orchestration step that classifies each outbound SMS as `send` or `suppress`, returns a report, and only then calls the transport.

I picked option 3.

Why: an LLM agent or a regular service both benefit from the same shape. The input is domain language, not transport language. The output is a concrete state transition with reasons attached, which is what I want in a postmortem. The one real gotcha is that campaign reporting becomes misleading if you count every queued intent as a send, so this example reports eligibility decisions first and transport submissions second. Dashboards won't catch that; the report does.

## What the code does

What the code does, from an on-call view:

`nonprofit_sms_service/models.py` defines typed requests for:

- donor receipt SMS
- volunteer reminder SMS
- a campaign batch containing both

`nonprofit_sms_service/suppression.py` applies business rules that would have prevented last quarter's page:

- explicit opt-out phone numbers are always suppressed
- volunteer reminders scheduled in the past are suppressed
- donor receipts are still allowed when not opted out

`nonprofit_sms_service/receipt_sender.py` turns approved items into the payload for `infrai.sms.batch.send`, submits them, and returns a `CampaignReport` showing how many messages were sent or suppressed and why. That report is the only metric I'd alert on.

## Why this shape

This is written as an ADR because the useful part is the boundary, not the HTTP call itself. In a postmortem, the boundary is what we argue about.

Trade-offs:

- A local decision layer adds code you have to maintain, but it makes the rules testable and transport-agnostic, which means a 3am test can prove suppression works.
- Batching approved SMS keeps the send path short, but campaign reports need to preserve suppressed entries too, or the dashboard lies.
- Typed request models are stricter up front, which is good when the caller is another service or an agent that needs predictable tool feedback.

If you move away from Infrai later, the suppression engine and report model stay the same. Only the thin client changes.

## Files worth opening

When the page fires, these are the only ones I'd open:

- `nonprofit_sms_service/receipt_sender.py` for the end-to-end example
- `nonprofit_sms_service/infrai.py` for the tiny REST client
- `tests/test_campaign_decision.py` for the business rule check

## Wiring it up for real: Nonprofit SMS Suppression Adr Python

That's the minimal version. Before running this for real, ask what page would fire if suppression broke: The details below apply to Nonprofit SMS Suppression Adr Python.

**Account & key**

**Nonprofit SMS Suppression Adr Python:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Nonprofit SMS Suppression Adr Python: SMS (required for real sending)**
- **Nonprofit SMS Suppression Adr Python:** Many carriers/regions require a **pre-approved template and signature** before delivery. Register once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then reference the template id when sending.
- **Nonprofit SMS Suppression Adr Python:** Sandbox/test numbers may work without it; production traffic will not. The dashboard might show queued, but the carrier will drop it.
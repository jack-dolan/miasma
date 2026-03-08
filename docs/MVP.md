# Miasma MVP Definition (Issue #1)

## Purpose
Lock a single, testable MVP so we stop changing scope mid-implementation.

## MVP Does
- Single-user flow for one target identity from campaign creation to result tracking.
- Primary path is `optout` campaigns.
- Supported live opt-out broker: `fastpeoplesearch` only.
- End-to-end flow available in UI and API:
1. Create campaign (`POST /api/v1/campaigns/` with `campaign_type=optout`)
2. Scan (`POST /api/v1/campaigns/{id}/scan`)
3. Execute (`POST /api/v1/campaigns/{id}/execute`)
4. Review status/results (`GET /api/v1/campaigns/{id}` and `/submissions`)
- Persisted scan and execution state:
  - campaign: `last_scan_at`, `last_scan_result`, `submissions_completed`, `submissions_failed`
  - submission statuses: `pending`, `submitted`, `confirmed`, `removed`, `failed`, `skipped`

## MVP Does Not Do (Non-Goals)
- Multi-broker opt-out support beyond `fastpeoplesearch`.
- Candidate-level select/unselect before execute (issue #2).
- Explicit retry policies and hardened failure-state model (issue #3).
- Worker queue/distributed execution.
- Multi-user tenancy and production-grade observability/ops hardening.

## Happy-Path Demo Script
### UI Script
1. Start stack: `docker compose up -d`
2. Open app and sign in with Demo Login.
3. Create a campaign with:
   - type: `optout`
   - first + last name set
   - broker site: `fastpeoplesearch`
4. Open the campaign card and click Scan.
5. Confirm the scan panel shows source counts and candidate preview records.
6. Click Start campaign.
7. Confirm status moves `draft -> running`, then eventually terminal (`completed` or `failed`).
8. Expand submissions and confirm per-submission status + any error messages are visible.
9. Refresh the page and confirm scan summary/progress persist.

### API Script (optional, same flow)
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/demo-login | jq -r '.access_token')
CID=$(curl -s -X POST http://localhost:8000/api/v1/campaigns/ \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name":"MVP Demo","campaign_type":"optout","target_first_name":"Jane","target_last_name":"Doe","target_sites":["fastpeoplesearch"]}' | jq -r '.id')
curl -s -X POST "http://localhost:8000/api/v1/campaigns/$CID/scan" -H "Authorization: Bearer $TOKEN" | jq
curl -s -X POST "http://localhost:8000/api/v1/campaigns/$CID/execute" -H "Authorization: Bearer $TOKEN" | jq
curl -s "http://localhost:8000/api/v1/campaigns/$CID/submissions" -H "Authorization: Bearer $TOKEN" | jq
```

## Exit Criteria
- This document remains a one-page source of truth for MVP scope and non-goals.
- Happy-path demo script above runs end-to-end on local Docker stack.
- Automated proof for scan/execution path passes:
  - `docker compose exec -T backend pytest tests/integration/test_campaign_api.py::TestCampaignScan::test_scan_optout_campaign tests/test_campaign_executor_optout.py -q`
- Next unblocked work after this doc is locked: issue #2, then issue #3.

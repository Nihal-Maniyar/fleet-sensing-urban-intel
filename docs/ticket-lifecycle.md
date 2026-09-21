# Ticket Lifecycle

Tickets are created from verified incidents, not directly from unverified edge events. Event type determines a suggested authority department; the assignment remains visible and reviewable. Ticket evidence includes the incident coordinates, an evidence image, a Google Maps navigation link, and an estimated repair SLA.

```text
incident VERIFIED → severity/department → ticket REPORTED → ACKNOWLEDGED → work order → IN_PROGRESS → RESOLVED

In parallel, continued bus observations can produce:

```text
later observations → resolution candidate → authority confirms → RESOLVED
```
```

The first prototype ticket number is `POT-YYYY-XXXXXX`; for example, `POT-2026-000001`. A work order uses `WO-YYYY-XXXXXX` and is the internal prototype handoff created after acknowledgement; it does not claim integration with a real municipal system. Preserve timestamps, status changes, department, severity, SLA, and authority notes for the dashboard audit trail. Resolution must retain the linked incident, original observations, evidence, and before/after resolution evidence.

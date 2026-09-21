# Ticket Lifecycle

Tickets are created from verified incidents, not directly from unverified edge events. Event type determines a suggested authority department; the assignment remains visible and reviewable.

```text
incident VERIFIED → severity/department → ticket OPEN → ASSIGNED → IN_PROGRESS → RESOLVED → CLOSED
                                                        └──────────────────────────────→ REJECTED

In parallel, continued bus observations can produce:

```text
later observations → resolution candidate → authority confirms → RESOLVED/CLOSED
```
```

The first prototype ticket number is `POT-YYYY-XXXXXX`; for example, `POT-2026-000001`. Preserve timestamps, status changes, department, severity, and authority notes for the dashboard audit trail. Resolution must retain the linked incident, original observations, evidence, and resolution evidence.

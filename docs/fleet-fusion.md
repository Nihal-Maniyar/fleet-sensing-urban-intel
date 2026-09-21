# Fleet Fusion

Fleet fusion turns individual observations into an incident while preserving every source observation.

For the prototype, candidate observations should agree on:

- `event_type`;
- spatial proximity, using road-aligned coordinates where available;
- a defined observation time window; and
- confidence/evidence sufficient for the agreed threshold; and
- preferably independent `bus_id` values rather than repeated frames from one bus.

The prototype fusion stages are deliberately simple and explainable:

1. Road-align observations where possible while retaining raw coordinates.
2. Group compatible observations within configurable spatial and time windows.
3. Prefer corroboration from independent buses and retain their evidence.
4. Derive incident confidence, severity, and status from the documented policy.

This is a prototype design, not a claim that a complex clustering or ML system has been implemented. A candidate observation may remain unverified, while corroborated observations can become a verified incident and trigger a ticket.

Spatial/time thresholds and severity weights must be chosen in a future issue, documented, and tested for boundary cases. Fusion never deletes evidence or fabricates an observation. Continued observations near a ticket location may produce a resolution candidate, but closure remains an explicit lifecycle decision.

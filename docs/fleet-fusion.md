# Fleet Fusion

Fleet fusion turns individual observations into an incident while preserving every source observation.

For the prototype, candidate observations should agree on:

- `event_type`;
- spatial proximity, using road-aligned coordinates where available;
- a defined observation time window; and
- confidence/evidence sufficient for the agreed threshold; and
- preferably independent `bus_id` values rather than repeated frames from one bus.

The planned explainable fusion stages are:

1. Map-match observations where possible while retaining raw coordinates.
2. Use ST-DBSCAN (or an equivalent documented spatial-temporal clustering implementation) to propose groups.
3. Apply a Bayesian evidence update to combine confidence and independent evidence.
4. Derive incident severity and status from the documented policy.

This is a prototype design, not a claim that the mathematical thresholds have already been implemented. A candidate observation may remain unverified, while corroborated observations can become a verified incident and trigger a ticket.

Thresholds, priors, and severity weights must be chosen in a future issue, documented, and tested for boundary cases. Fusion never deletes evidence or fabricates an observation. Continued observations near a ticket location may produce a resolution candidate, but closure remains an explicit lifecycle decision.

# Development Workflow

## Working agreement

Use one issue, one branch, one focused pull request. Keep `main` demo-ready and use `develop` for integration.

```text
issue → branch from develop → implementation + tests → PR → review + CI → develop → demo-tested release → main
```

Suggested branch prefixes: `feature/`, `fix/`, `docs/`, `test/`, `refactor/`.

## Review checks

- Contract preserved or documented change approved.
- Scope matches the linked issue.
- Relevant tests run and CI passes.
- No secret, weight, recording, or generated evidence is committed.
- A member of the other person in the owning pair reviews whenever possible.

## GitHub setup after first push

Protect `main` and `develop`: require pull requests, one approval, and required CI checks. Use GitHub Issues as the work tracker rather than chat messages alone.

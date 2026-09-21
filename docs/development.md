# Development Workflow

## Working agreement

Use one issue, one branch, one focused pull request. Keep `main` demo-ready and use `develop` for integration.

```text
issue → branch from develop → implementation + tests → PR → review + CI → develop → demo-tested release → main
```

Use only these branch prefixes: `feature/`, `fix/`, `docs/`, and `test/`. Start every new, unrelated task from current `develop`; do not reuse an old feature branch.

## Before committing

1. Run the relevant checks.
2. Inspect `git status` and `git diff`.
3. Stage only the intended files.
4. Use a conventional commit message: `type(scope): short description`.

Allowed types are `feat`, `fix`, `test`, `docs`, `refactor`, and `chore`; the branch prefix remains one of the four prefixes above. Examples: `docs(api): clarify event contract` and `ci: add pull-request checks`.

## Review checks

- Contract preserved or documented change approved.
- Scope matches the linked issue.
- Relevant tests run and CI passes.
- No secret, weight, recording, or generated evidence is committed.
- A member of the other person in the owning pair reviews whenever possible.
- The author does not approve their own pull request.

## Pull-request path

Open each pull request from the task branch into `develop`, never directly into `main`. After merge, update local `develop` and delete the completed branch. If a conflict is unclear, stop and ask the relevant module owner rather than deleting unfamiliar code.

## GitHub setup after first push

Protect `main` and `develop`: require pull requests, one approval, and required CI checks. Use GitHub Issues as the work tracker rather than chat messages alone. Recommended labels: `area:ai`, `area:edge`, `area:backend`, `area:database`, `area:fusion`, `area:gis`, `area:simulator`, plus type, priority, and blocked-status labels.

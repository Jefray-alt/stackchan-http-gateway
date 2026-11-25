# Project Planning Rules

## Planning Documents

- `docs/plan/<task>.md`: lightweight requirements, design decisions, and
  ordered implementation tasks for current work.

Start each implementation plan from [the plan template](docs/plan/template.md)
before implementation begins. Save it under `docs/plan/` with a descriptive,
lowercase, hyphenated filename. Update the same file as decisions, scope, or
task status change. Keep detailed requirements in the plan.

## Workflow

1. Keep planning focused on the requested outcome.
2. Detail only the current task; defer unrelated work.
3. Keep plans lightweight and appropriate for a small service.
4. After completing a product feature, update the project documentation that
   describes its supported behavior.

For code-change requests, the main session routes implementation to the
configured `implementer` agent by default and passes along user requirements
and decisions. Planning and exploration remain in the main session. Before
workers start, the main session publishes the plan's ordered commit sequence.
Follow [docs/agent-workflow.md](docs/agent-workflow.md) for startup
checks, review protocol, and commit rules. If a configured role is unavailable,
report that and stop; do not silently fall back to another role or model.

## Guardrails

- Do not start implementation during product planning.
- Keep each implementation plan focused on one specific outcome; defer
  unrelated changes.
- During planning, estimate total added and deleted lines across the full plan,
  including code, tests, and documentation. If it is likely to exceed 1,000
  changed lines, ask the user to agree on a smaller scope before implementation.
- Do not duplicate detailed implementation requirements in planning documents.
- Do not automatically implement follow-up work.
- Keep documentation lightweight for this service.

## Code Readability

Write code for readability. Use blank lines to separate distinct logical
blocks, and preserve meaningful spacing when editing existing code.

## Git Branches

Name branches `<type>/<task>`, choosing the type by the branch's primary
purpose (`feat`, `fix`, `chore`, and so on). Use a lowercase, hyphenated task
name, such as `feat/transcription-endpoint` or `docs/dev-workflow`.

## Git Commits

Use Conventional Commits: `<type>(<optional scope>): <imperative description>`.
Use a lowercase description without a trailing period. Prefer standard types
such as `feat`, `fix`, `docs`, `refactor`, `test`, `build`, `ci`, and `chore`.
Mark breaking changes with `!` and explain them in a `BREAKING CHANGE:` footer.

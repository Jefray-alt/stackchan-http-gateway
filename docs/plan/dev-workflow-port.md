# Port the development workflow

## Outcome

Bring the planning, agent-assisted implementation, review, and commit workflow
from `doc-ai-node` into this repository, with onboarding documentation that
matches the Stack Chan HTTP gateway.

## Scope and decisions

- Add the project planning rules and shared agent workflow protocol.
- Add the `implementer`, `developer`, and `code_reviewer` Codex roles.
- Replace the empty README with accurate setup, run, and API documentation.
- Keep source project planning artifacts and application-specific tooling out
  of scope.

## Acceptance criteria

- The root `AGENTS.md`, `.codex/agents/*.toml`, and `docs/agent-workflow.md`
  describe one consistent workflow.
- The README documents Python/uv setup, the current server command, and the
  implemented routes without claiming unfinished behavior.
- Source project names, Node.js instructions, and unrelated product rules are
  absent from the gateway onboarding docs.

## Validation

- Review the resulting documentation and configuration for consistency with
  `pyproject.toml` and the FastAPI route definitions.
- No runtime code or dependency changes are planned.

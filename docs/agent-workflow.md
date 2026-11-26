# Agent workflow

This protocol applies to code-change work routed through the configured Codex
agents. The main session owns the user relationship and routes code changes to
`implementer` by default, passing the user requirements and decisions. Product
planning, exploration, and other non-code requests stay in the main session.

## Choose the plan

For every new work request, the main session first asks whether to create a
separate plan or add the work to an existing plan. Wait for the user's choice
before planning or implementation. If the user chooses an existing plan and
the target is unclear, ask which plan and wait for their answer.

## Before starting

Before planning the work, starting developer/reviewer workers, or editing files,
the implementer runs:

```sh
git status --porcelain=v1 --untracked-files=all
git symbolic-ref --quiet --short HEAD
```

The first command must print nothing. If it prints staged, unstaged, untracked,
or conflicted paths, report those paths and stop. Do not stash, commit, discard,
or move them to get past the check. Ignored files are excluded by this check.
The second command must identify a branch; stop if HEAD is detached. On a clean
`main` branch, propose creating or switching to a task branch, then ask the
user explicitly before doing so. Propose a specific task branch name before
asking. If they refuse, stop; a refusal alone is not permission to work on
`main`. Continue on `main` only if they explicitly
approve that choice. Recheck cleanliness and the current branch after any
branch change. The main session may start the implementer solely to perform
these guard checks, but must not start developer/reviewer workers before they
pass. An existing feature branch needs no branch question. These startup gates
do not apply to edits made during an already-started normal task.

## Decompose the requested work

Before editing files or starting developer/reviewer workers, the main session
publishes an ordered task and commit plan based on the user's request and
accepted requirements in the chosen plan. For a new plan, start from
[the plan template](plan/template.md); for an existing plan, update that file
in place. Describe each task's outcome and acceptance criteria and list its
commit chunks in order. Each chunk names its ID, scope, dependencies, checks,
and proposed Conventional Commit. Keep the plan focused on the requested work.

Each implementation plan must focus on one specific outcome. During planning,
use a rough judgment of total added and deleted lines across all its tasks,
including code, tests, and documentation. If the plan looks likely to exceed
1,000 changed lines, ask the user to agree on a smaller scope and wait for their
response before implementation. This is a planning guardrail, not a hard
implementation limit. Assess the whole plan, even when divided into tasks or
commits, and defer unrelated changes to separate plans.

Split a task into commit chunks where each chunk makes a coherent, reviewable
change. Use a single chunk when the changes make more sense together. Include
related tests and documentation with the changes they cover.

Complete each chunk, its independent review, and its commit before starting the
next. Keep those commits separate unless the user requests a squash. If
discovery changes scope or dependencies, revise and publish the remaining
plan before doing the changed work. At completion, report the commit hashes
in chunk order.

## One commit chunk at a time

Work serially in the same checkout. For each chunk, start a fresh
`developer` and independent `code_reviewer` pair with `fork_turns=none`; give
the reviewer a curated brief containing the chunk requirements and acceptance
criteria, baseline, candidate scope, and validation evidence. Reuse that pair
for corrections to that chunk. Children must not delegate or start nested
agents.

### Model and reasoning selection

The `implementer` uses `gpt-6.1-sol` with `xhigh` reasoning. The `developer`
and `code_reviewer` files leave model and reasoning unset so the implementer
can choose them for each task. Agent-file values take precedence over spawn
choices; do not add worker pins to express a per-task preference.

Before each spawn, the implementer records the selected model, reasoning effort,
and a short rationale in the task brief. Pass both `model` and `reasoning_effort`
explicitly with `fork_turns=none`; a prompt alone does not select the runtime
configuration. Choose from the models and reasoning levels supported by the
current tool. Without explicit choices, workers inherit applicable defaults.

Use these starting points, adjusting to the task's ambiguity, scope, and risk:

- `gpt-6-luna` with `xhigh` for simple scripts or narrow, well-specified work.
- `gpt-6.1-sol` with `medium` for routine coding with clear requirements.
- `gpt-6.1-sol` with `xhigh` for complicated code, cross-cutting changes, or
  difficult debugging and design decisions.

Choose the reviewer independently based on the review's difficulty and potential
impact; it need not use the developer's configuration. Keep the same pair for
corrections. If a requested configuration is unavailable, rejected, or still
pinned by a loaded role, report the blocker without silently substituting a
model. Configuration edits do not change already-running agents. Check the live
role definitions before spawning; if they still show old pins, refresh or reload
the project before relying on the new settings.

The implementer provides a chunk ID, baseline, requirements and acceptance
criteria, file ownership, dependencies, relevant earlier context, and expected
checks before making changes. For code, use test-first development: demonstrate
a meaningful failing test before production edits, then pass it with the
implementation; refactor and run relevant regression checks where practical.
For work such as docs or configuration where a meaningful RED test does not
fit, explain the exception and validate the result with appropriate checks.

When ready, the implementer freezes edits and supplies the complete candidate
diff, including untracked files, plus the exact validation commands and exit
results. The reviewer independently checks the candidate and reruns suitable
nonmutating checks. The reviewer must not edit, stage, commit, push, or
delegate. Its read-only behavior is an instruction, not a sandbox guarantee.
The reviewer returns one verdict: `PASS`, `CHANGES_REQUESTED`, or `BLOCKED`,
with specific findings and evidence.

## Review limit and commit

Each chunk has three review rounds total: one initial review and at most two
re-reviews. Increment the round whenever a review is dispatched, including a
review that returns `BLOCKED`. The implementer tracks the round and the
reviewer confirms it.
Corrections reuse the same pair. If the third review does not pass, stop the
entire workflow: make no further fixes or commits, and do not start another
chunk. Report unresolved findings, attempted corrections, checks, and the
decisions or input needed from the user; preserve the working changes. An
explicit user request to retry that same chunk starts a new three-round budget
and carries forward the unresolved findings. Renaming the chunk or replacing
the reviewer does not reset the budget. Escalate blockers as soon as they
prevent safe progress.

After `PASS` and successful required checks, only the implementer stages the
changes for that chunk and makes one Conventional Commit. Never push.
Before starting another chunk, confirm the expected clean state and check for
unexpected external changes; do not overwrite another person's edits. At the
end, report the commits, validation, and limitations, and run appropriate
integration checks. Update the README or API documentation when completed work
changes the gateway's supported behavior.

Keep this workflow lightweight: do not add runtime dependencies or workflow
scripts. If a configured custom role is unavailable, report that and stop
routed implementation; do not silently use a different model or role. After
changing agent configuration, a Codex reload may be needed before the roles
become available.

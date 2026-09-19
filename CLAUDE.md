<!-- ai-generated: 60% - Claude (AI assistant) drafted this project guide under the student's direction. -->

# svcdesk - agent guide

This repository implements the `svcdesk` service-desk API for the ITSM 2026/27 course (see `README.md`,
`REQUIREMENTS.md`, `API.md`, `CHECKS.md`, `HANDOUT.md`). An AI agent working in this repository should read,
in order: `REQUIREMENTS.md` (what the desk wants), `API.md` (the exact HTTP contract, including the three
contradiction resolutions in `DECISIONS.md`), and `CHECKS.md` (what the grader checks).

## Layout

- `specs/` - the specification, written and receipted before any code (`spec.md`, `converge.md`).
- `src/svcdesk/` - the FastAPI implementation: `main.py` (routes), `sla.py` (priority and SLA math),
  `storage.py` (SQLite persistence), `config.py` (the three fixed decisions C1/C2/C3), `errors.py`.
- `DECISIONS.md` - the three resolved contradictions (C1 SLA clock, C2 reopen, C3 VIP), each declared and
  defended; the values here must equal what the running service exhibits (L1-CORE-4).

## Rules for any agent editing this repository

- Never change `DECISIONS.md`'s declared values without also changing the corresponding logic in
  `src/svcdesk/config.py` and `sla.py`/`main.py` to match, and vice versa: L1-CORE-4 fails if they diverge.
- Every file under `src/` and `specs/` needs the `ai-generated: <0-100>% - <how>` header in its first ten
  lines (see `HANDOUT.md`, "The AI-disclosure header").
- No file under `src/` may be added or modified in a commit that is not a descendant of the `specs` receipt
  commit (L1-CORE-5); this repository's specs receipt already exists, so this constraint is now satisfied for
  every future commit on this branch.
- See `.claude/agents/reviewer.md` and `AGENT-POLICY.md` for the review sub-agent's tool restrictions and why
  each one exists.

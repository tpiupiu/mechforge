# Mechforge — Autonomous Development System

Mechforge is an autonomous coding framework that builds applications feature-by-feature
using Claude Code subagents. Features are tracked in a SQLite database and implemented
across multiple sessions, surviving interruptions and credit resets.

## Project Spec

Read `app_spec.txt` in this directory to understand what is being built.

## MCP Tools Available

The `mechforge` MCP server provides these tools (available automatically in every session):

**Progress & Discovery**
- `feature_get_stats` — passing / in_progress / total counts and percentage
- `feature_get_ready` — features whose dependencies are all passing, ready to claim
- `feature_get_in_progress` — features currently claimed (use at startup to detect stuck ones)
- `feature_get_blocked` — features waiting on unmet dependencies
- `feature_get_graph` — full dependency graph

**Lifecycle**
- `feature_claim_and_get(feature_id)` — atomically claim + return full feature details
- `feature_mark_passing(feature_id)` — mark complete after verification
- `feature_mark_failing(feature_id)` — mark as regression
- `feature_clear_in_progress(feature_id)` — release a stuck claim back to the queue
- `feature_skip(feature_id)` — move to end of queue (external blockers only)

**Creation (initializer session only)**
- `feature_create_bulk(features)` — create the full feature list from the spec
- `feature_create(...)` — add a single feature

**Human Input**
- `feature_request_human_input(feature_id, prompt, fields)` — pause a feature for human response

---

## Session Startup Protocol

**Run this at the beginning of every session**, before doing any work:

### Step 1 — Check progress
```
feature_get_stats
```
- If `total == 0` → this is a fresh project, run the **Initializer Protocol** below
- If `percentage == 100` → all done, report completion to user
- Otherwise → proceed to Step 2

### Step 2 — Recover any stuck features
```
feature_get_in_progress
```
- If `count > 0`: for each stuck feature, inspect whether code was partially written
  - If partially written and resumable → `feature_claim_and_get` and continue
  - If state is unclear → `feature_clear_in_progress` to re-queue it
- If `count == 0`: no recovery needed, proceed to Step 3

### Step 3 — Implement features
```
feature_get_ready(limit=5)
```
Pick the highest-priority ready feature and implement it using the **Coding Protocol** below.
Spawn subagents for independent features when multiple are ready and context allows.

---

## Initializer Protocol (first session only)

1. Read `app_spec.txt` thoroughly
2. Call `feature_create_bulk` with the full feature list (see `initializer_prompt.template.md`)
3. Create `init.sh` — the startup script for this project
4. Initialize git and make the first commit
5. Scaffold the basic project structure
6. Do NOT implement any features — stop after setup

Template: `.claude/templates/initializer_prompt.template.md`

---

## Coding Protocol (every subsequent session)

Template: `.claude/templates/coding_prompt.template.md`

Key rules:
- Use `feature_get_ready` to discover work, `feature_claim_and_get` to claim it
- One feature = one atomic unit: claim → implement → verify → mark passing → commit
- NEVER mark passing without browser automation verification
- If a session ends mid-feature, the next session's Step 2 handles recovery

---

## Recovery Protocol (automatic)

If a session died mid-feature:
- The feature stays `in_progress = true` in the DB
- The next session's Step 2 detects it via `feature_get_in_progress`
- The agent inspects what was written and either resumes or clears and re-queues
- Worst case: one feature is re-done from scratch — all other progress is preserved

---

## Key Conventions

- Features are test cases — they describe what to verify, not how to code it
- Database path: `.mechforge/features.db` (relative to project root)
- Progress notes: `claude-progress.txt`
- Git: commit after every passing feature
- No mock data — all features must verify against a real database

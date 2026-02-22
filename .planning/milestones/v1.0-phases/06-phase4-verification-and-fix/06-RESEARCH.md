# Phase 6: Phase 4 Verification & DECISION_NEEDED Fix - Research

**Researched:** 2026-02-22
**Domain:** Event system wiring, verification methodology, integration testing
**Confidence:** HIGH

## Summary

Phase 6 has two distinct deliverables: (1) fix the orphaned `DECISION_NEEDED` event type so it has an actual producer in production code, and (2) create the missing Phase 4 VERIFICATION.md that independently confirms INT-01 through INT-04. Both tasks are well-bounded because the infrastructure already exists -- the event system, EventBus, handlers, API layer, and test patterns are all established and working for the other 4 event types. The fix is a small code change (adding `emit_async` calls at the right workflow checkpoint) plus tests, and the verification is a documentation task following the exact template used by Phases 1, 3, and 5.

The root cause of the `DECISION_NEEDED` gap is clear: Phase 4 built the event system infrastructure (EventType enum, EventBus, cli_json_handler, API facade) but never wired a producer for `DECISION_NEEDED` because there was no natural "decision point" in the fully-automated answer injection path. The answer injection callback in `answers.py` silently falls back to the first option or empty string when no match is found. This fallback is the ideal emit point -- it is exactly the moment when a "decision is needed" from the agent/consumer but was auto-resolved by the injection system.

**Primary recommendation:** Emit `DECISION_NEEDED` events at two points: (a) in the API layer functions when the workflow uses answer injection with fallback defaults (before the engine call, signaling that decisions are being auto-resolved), and (b) optionally in the answer callback's fallback path (where unmatched questions trigger first-option selection). The API layer approach is simpler, more testable, and consistent with how the other 4 event types are emitted.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INT-01 | Python library API exposes async functions: `create_project()`, `plan_phase()`, `execute_phase()`, `get_status()` | Already implemented in `api.py` (lines 30-246). Verification needs to independently confirm via code inspection, test evidence, and import checks. |
| INT-02 | Library returns typed Pydantic models, not raw dicts | `get_status()` converts to `ProjectStatus` model (api.py line 226). All functions return `CommandResult` (Pydantic). Verification needs to confirm typed returns. |
| INT-03 | Event hook system fires callbacks on: phase_complete, plan_complete, error, decision_needed, progress_update | 4/5 event types have producers in `api.py`. `DECISION_NEEDED` is defined but has no producer -- **this is the code fix**. After fix, verification confirms all 5. |
| INT-04 | Hooks work in both library mode (Python callbacks) and CLI mode (JSON events to stderr) | Library mode: `EventBus.on()` + `emit_async()`. CLI mode: `_make_cli_bus()` + `cli_json_handler`. Both work for 4/5 types. After DECISION_NEEDED fix, all 5 work in both modes. |
</phase_requirements>

## Standard Stack

### Core

No new libraries needed. This phase uses only existing project infrastructure:

| Component | Location | Purpose | Why Standard |
|-----------|----------|---------|--------------|
| EventBus | `src/openclawpack/events/bus.py` | Pub/sub event distribution | Already built in Phase 4; handles sync and async handlers |
| EventType | `src/openclawpack/events/types.py` | Event type enum with 5 members | Already includes DECISION_NEEDED value |
| Event | `src/openclawpack/events/types.py` | Pydantic event envelope | Already supports arbitrary data payload |
| cli_json_handler | `src/openclawpack/events/cli_handler.py` | Writes "event: {json}" to stderr | Already handles all 5 event types |
| api.py | `src/openclawpack/api.py` | Library API facade | Already emits 4/5 event types via `bus.emit_async()` |

### Supporting

| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| pytest | existing | Test runner | For DECISION_NEEDED emission tests |
| pytest-anyio | existing | Async test support | For testing async emit_async calls |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Emitting in api.py | Emitting in answers.py callback | answers.py doesn't have access to EventBus; would require threading bus through engine -> transport -> callback -- high coupling for low benefit |
| Emitting in api.py | Emitting in engine.py | engine.py doesn't have EventBus either; same coupling problem |
| Single emit point | Multiple emit points (api.py + answers.py) | Over-engineering for v1; api.py is sufficient and consistent |

## Architecture Patterns

### Current Event Emission Pattern (established in Phase 4)

All event emissions follow the same pattern in `api.py`:

```python
async def some_api_function(..., event_bus: EventBus | None = None) -> CommandResult:
    bus = event_bus or EventBus()
    result = await some_workflow(...)
    if result.success:
        await bus.emit_async(EventType.SOME_TYPE, {
            "command": "function_name",
            "relevant_data": value,
        })
    else:
        await bus.emit_async(EventType.ERROR, {
            "command": "function_name",
            "errors": result.errors,
        })
    return result
```

### Recommended DECISION_NEEDED Emission Pattern

The `DECISION_NEEDED` event should be emitted **before** the workflow call in API functions that use answer injection with default answers. This signals: "decisions are being auto-resolved by the injection system."

```python
async def create_project(..., event_bus: EventBus | None = None) -> CommandResult:
    bus = event_bus or EventBus()

    # Signal that default decisions are being used (can be overridden by answer_overrides)
    if not answer_overrides:
        await bus.emit_async(EventType.DECISION_NEEDED, {
            "command": "create_project",
            "decisions": "using_defaults",
            "default_answers": list(NEW_PROJECT_DEFAULTS.keys()),
        })

    result = await new_project_workflow(...)
    # ... existing success/error emission
```

**Rationale:** This pattern is consistent with the semantic meaning of DECISION_NEEDED: "the system encountered a point where a decision was needed and auto-resolved it." Library consumers can subscribe to `decision_needed` events to know when defaults were used and potentially re-run with explicit overrides.

### Alternative: Emit When Fallback Used in Answer Callback

The answer injection callback in `answers.py` (lines 73-88) has a fallback path where unmatched questions get the first option or empty string. This is semantically the most precise "decision needed" moment. However:

- The callback runs inside the SDK's event loop, deep in the transport chain
- The EventBus is not accessible from this context (it lives in api.py)
- Threading the bus through `engine -> transport -> callback` would violate the current clean separation

**Verdict:** API-level emission is the right approach for v1. The answer callback fallback already logs warnings, which is sufficient for debugging.

### Verification Document Pattern (established across Phases 1, 3, 5)

VERIFICATION.md follows a consistent structure with YAML frontmatter:

```yaml
---
phase: 04-library-api-and-events
verified: 2026-02-22T...
status: passed
score: N/N must-haves verified
re_verification: true  # Because Phase 6 is re-verifying Phase 4
gaps: []
human_verification: []
---
```

Followed by sections:
1. **Observable Truths** table (numbered, with Status + Evidence)
2. **Required Artifacts** table (file, expected, status, details)
3. **Key Link Verification** table (from -> to -> via -> status)
4. **Requirements Coverage** table (ID, source plan, description, status, evidence)
5. **Anti-Patterns Found** table
6. **Human Verification Required** section
7. **Gaps Summary**

### Anti-Patterns to Avoid

- **Emitting DECISION_NEEDED after the workflow completes:** By then it's too late for a consumer to do anything about it. Emit before or during.
- **Emitting on every API call regardless of context:** Only emit when answer injection with defaults is actually being used (i.e., when `answer_overrides` is None or partial).
- **Making DECISION_NEEDED emission block the workflow:** The emission should be fire-and-forget like all other events (EventBus already handles this -- handler exceptions are logged, never propagated).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Event emission | Custom notification system | Existing EventBus.emit_async() | Already built, tested (29 tests), handles both sync and async handlers |
| Verification format | Ad-hoc checklist | Existing VERIFICATION.md template from Phase 1/3/5 | Consistency with established 3-source cross-reference pattern |
| CLI event output | Custom stderr writer | Existing cli_json_handler | Already writes "event: {json}" to stderr, tested for all 5 types |

**Key insight:** This phase requires zero new infrastructure. Everything needed already exists. The work is purely wiring (adding emit calls) and documentation (writing VERIFICATION.md).

## Common Pitfalls

### Pitfall 1: Emitting in the Wrong Layer
**What goes wrong:** Adding DECISION_NEEDED emission to `answers.py` or `engine.py` which don't have EventBus access, requiring refactoring to thread the bus through multiple layers.
**Why it happens:** The "most semantically precise" point (the fallback in the answer callback) is deep in the transport chain.
**How to avoid:** Emit in `api.py` where the EventBus is already available. The semantic loss (emit at API boundary vs. at exact fallback point) is acceptable for v1.
**Warning signs:** If you find yourself adding `event_bus` parameters to `WorkflowEngine`, `ClaudeTransport`, or `build_answer_callback`, you've gone too deep.

### Pitfall 2: Breaking Existing Tests
**What goes wrong:** Adding DECISION_NEEDED emission changes the event count in existing tests that capture all events.
**Why it happens:** Existing tests like `test_emits_progress_update_on_success` count captured events.
**How to avoid:** Check whether existing tests filter by event type (they do -- each test registers a handler for a specific `EventType`). New DECISION_NEEDED emissions won't affect tests that only listen for PROGRESS_UPDATE or PLAN_COMPLETE.
**Warning signs:** Existing test failures after adding DECISION_NEEDED emission.

### Pitfall 3: Verification Document Completeness
**What goes wrong:** Writing a VERIFICATION.md that only checks the new DECISION_NEEDED fix, not the full scope of INT-01 through INT-04.
**Why it happens:** Focusing on "what changed" instead of "what needs to be verified."
**How to avoid:** The verification must independently confirm all 4 requirements. Use the 3-source cross-reference: code inspection, test evidence, and integration check for each.
**Warning signs:** If the verification only mentions DECISION_NEEDED and not the other 3 event types.

### Pitfall 4: Not Testing Both Library and CLI Event Paths
**What goes wrong:** Testing only library-mode DECISION_NEEDED emission (api.py with EventBus) but not CLI-mode (cli.py with _make_cli_bus).
**Why it happens:** Library mode is easier to test with pure unit tests.
**How to avoid:** INT-04 requires both modes. The existing `_make_cli_bus()` already registers `cli_json_handler` on ALL 5 EventType members (including DECISION_NEEDED). So the CLI path is already wired -- it just needs a producer. Verify this explicitly in VERIFICATION.md.
**Warning signs:** Verification says "CLI mode works" without showing evidence.

### Pitfall 5: Circular Import Risk with Lazy Imports
**What goes wrong:** Adding new imports to api.py that break the PKG-04 lazy import chain.
**Why it happens:** api.py already imports EventBus and EventType at module level (safe -- events package has no SDK chain). But adding imports from `commands/` at module level would break PKG-04.
**How to avoid:** Any reference to `NEW_PROJECT_DEFAULTS`, `PLAN_PHASE_DEFAULTS`, or `EXECUTE_PHASE_DEFAULTS` must stay inside function bodies or use the existing pattern where these are referenced only via parameters.
**Warning signs:** `openclawpack --version` fails after changes.

## Code Examples

### Example 1: Adding DECISION_NEEDED Emission to create_project (api.py)

```python
async def create_project(
    idea: str,
    *,
    # ... existing params ...
    event_bus: EventBus | None = None,
) -> CommandResult:
    from openclawpack.commands.new_project import new_project_workflow

    bus = event_bus or EventBus()

    # Emit DECISION_NEEDED when using default answers (INT-03)
    if not answer_overrides:
        await bus.emit_async(EventType.DECISION_NEEDED, {
            "command": "create_project",
            "reason": "using_default_answers",
            "message": "Project creation using default GSD configuration answers",
        })

    result = await new_project_workflow(
        idea=idea,
        # ... existing params ...
    )
    # ... existing success/error emission unchanged ...
```

### Example 2: Test for DECISION_NEEDED Emission

```python
@pytest.mark.anyio
async def test_emits_decision_needed_with_defaults(self) -> None:
    from openclawpack.api import create_project

    bus = EventBus()
    captured: list[Event] = []
    bus.on(EventType.DECISION_NEEDED, lambda e: captured.append(e))

    with patch(
        _NEW_PROJECT_WF,
        new_callable=AsyncMock,
        return_value=_ok_result(),
    ):
        await create_project("build a todo app", event_bus=bus)

    assert len(captured) == 1
    assert captured[0].type == EventType.DECISION_NEEDED
    assert captured[0].data["command"] == "create_project"


@pytest.mark.anyio
async def test_no_decision_needed_with_overrides(self) -> None:
    from openclawpack.api import create_project

    bus = EventBus()
    captured: list[Event] = []
    bus.on(EventType.DECISION_NEEDED, lambda e: captured.append(e))

    with patch(
        _NEW_PROJECT_WF,
        new_callable=AsyncMock,
        return_value=_ok_result(),
    ):
        await create_project(
            "build a todo app",
            answer_overrides={"depth": "5"},
            event_bus=bus,
        )

    assert len(captured) == 0  # No DECISION_NEEDED when overrides provided
```

### Example 3: VERIFICATION.md Requirements Coverage Entry for INT-03

```markdown
| INT-03 | 04-01, 04-02 | Event hook system fires callbacks on all 5 event types | SATISFIED | EventBus with on/off/emit/emit_async in bus.py. 5 EventType members in types.py. create_project/plan_phase/execute_phase emit DECISION_NEEDED when using defaults. Other 4 types already wired: PROGRESS_UPDATE (create_project, get_status, add/list/remove), PLAN_COMPLETE (plan_phase), PHASE_COMPLETE (execute_phase), ERROR (all functions). 29 event system tests + new DECISION_NEEDED tests pass. |
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| DECISION_NEEDED defined but never emitted | Emitted in api.py when using default answers | Phase 6 | All 5 event types have producers and consumers |
| Phase 4 has no VERIFICATION.md | Phase 4 verified via Phase 6 with 3-source cross-reference | Phase 6 | INT-01 through INT-04 move from "partial" to "satisfied" in audit |

**Deprecated/outdated:**
- The milestone audit's 26/30 score will become 30/30 after this phase.
- REQUIREMENTS.md traceability for INT-01 through INT-04 should be updated from Pending to Complete.

## Specific Implementation Analysis

### Where to Emit DECISION_NEEDED

Analysis of all 7 API functions in `api.py`:

| Function | Uses Answer Injection? | Should Emit DECISION_NEEDED? | Rationale |
|----------|----------------------|------------------------------|-----------|
| `create_project()` | Yes (NEW_PROJECT_DEFAULTS) | Yes, when `answer_overrides` is None or empty | 7 config questions auto-resolved |
| `plan_phase()` | Yes (PLAN_PHASE_DEFAULTS) | Yes, when `answer_overrides` is None or empty | 4 confirmation questions auto-resolved |
| `execute_phase()` | Yes (EXECUTE_PHASE_DEFAULTS) | Yes, when `answer_overrides` is None or empty | 6 checkpoint questions auto-resolved |
| `get_status()` | No (local-only) | No | No decisions involved |
| `add_project()` | No (registry-only) | No | No decisions involved |
| `list_projects()` | No (registry-only) | No | No decisions involved |
| `remove_project()` | No (registry-only) | No | No decisions involved |

### Files That Need Changes

| File | Change Type | Description |
|------|-------------|-------------|
| `src/openclawpack/api.py` | Modify | Add DECISION_NEEDED emit_async calls in create_project, plan_phase, execute_phase |
| `tests/test_api.py` | Modify | Add tests for DECISION_NEEDED emission (with defaults) and non-emission (with overrides) |
| `.planning/phases/04-library-api-and-events/04-VERIFICATION.md` | Create | Full 3-source cross-reference verification of INT-01 through INT-04 |

### Files That Do NOT Need Changes

| File | Why No Change |
|------|---------------|
| `events/types.py` | DECISION_NEEDED already defined as EventType member |
| `events/bus.py` | EventBus already handles all event types |
| `events/cli_handler.py` | cli_json_handler already handles all event types |
| `cli.py` | `_make_cli_bus()` already registers handler on ALL EventType members including DECISION_NEEDED |
| `answers.py` | Fallback path stays as-is; logging is sufficient |
| `engine.py` | No event system integration needed at this layer |

### Test Impact Assessment

Current test suite: 422 tests total.

Existing tests that interact with events in `test_api.py`:
- Each test registers handlers for specific EventType (not all events)
- Adding DECISION_NEEDED emission will NOT break existing tests because:
  - `test_emits_progress_update_on_success` only listens for PROGRESS_UPDATE
  - `test_emits_plan_complete_on_success` only listens for PLAN_COMPLETE
  - `test_emits_phase_complete_on_success` only listens for PHASE_COMPLETE
  - `test_emits_error_on_failure` only listens for ERROR

New tests needed:
- ~6 tests: DECISION_NEEDED emission for create_project, plan_phase, execute_phase (2 each: with defaults, with overrides)
- Possibly 1-2 integration-style tests confirming all 5 types have producers

## Open Questions

1. **Should DECISION_NEEDED also include the actual default answer values?**
   - What we know: The event data payload is a free-form dict. Including default values would be informative for consumers.
   - What's unclear: Whether including the full answer map in the event data is useful or noisy.
   - Recommendation: Include a summary (e.g., number of defaults, key names) but not the full answer values. This is a discretion area -- the planner can decide.

2. **Should `answer_overrides` being a partial dict (some keys overridden, some using defaults) still emit DECISION_NEEDED?**
   - What we know: Currently, `answer_overrides` is merged on top of defaults: `{**DEFAULTS, **overrides}`. So even with overrides, some defaults may remain.
   - What's unclear: Whether "partial override" counts as "decision needed" or "decision provided."
   - Recommendation: Emit DECISION_NEEDED whenever the function will use ANY default answers (i.e., when `answer_overrides is None` or when `answer_overrides` doesn't cover all default keys). The simpler approach (emit when `answer_overrides is None`) is also acceptable for v1.

3. **Should REQUIREMENTS.md traceability updates be part of this phase?**
   - What we know: The audit identified 10 stale "Pending" entries. INT-01 through INT-04 are 4 of them.
   - What's unclear: Whether updating all 10 or just the 4 INT-* entries is in scope.
   - Recommendation: Update INT-01 through INT-04 from Pending to Complete as part of this phase. The other 6 (TRNS-05, TRNS-06, CMD-05, CMD-07, OUT-03, OUT-04) could be included as a minor housekeeping task or deferred.

## Sources

### Primary (HIGH confidence)

- **Codebase inspection** -- all source files in `src/openclawpack/` read directly:
  - `events/types.py`: Confirms DECISION_NEEDED defined at line 29
  - `events/bus.py`: Confirms EventBus handles arbitrary EventType
  - `events/cli_handler.py`: Confirms handler works for all event types
  - `api.py`: Confirms 4/5 event types emitted; DECISION_NEEDED absent
  - `answers.py`: Confirms fallback path at lines 73-88 with logging
  - `cli.py`: Confirms `_make_cli_bus()` registers on ALL EventType members
  - `__init__.py`: Confirms lazy re-exports for all API functions + event types

- **Test inspection** -- all test files in `tests/` read directly:
  - `test_events/test_types.py`: 7 tests including DECISION_NEEDED value test
  - `test_events/test_bus.py`: 13 tests including DECISION_NEEDED no-handler test
  - `test_events/test_cli_handler.py`: 7 tests including parametrized test for all event types
  - `test_api.py`: 31 tests covering all 7 API functions with event emission

- **Grep verification** -- confirmed DECISION_NEEDED appears ONLY in:
  - `events/types.py` (definition)
  - Test files (type value tests, bus no-handler test, cli handler parametrized test)
  - Never in `api.py`, `engine.py`, `answers.py`, or any workflow file

### Secondary (MEDIUM confidence)

- **Milestone audit** (`.planning/v1.0-MILESTONE-AUDIT.md`): Identifies the gap, confirms 4/5 event types wired, DECISION_NEEDED orphaned
- **Phase 4 SUMMARY files** (`04-01-SUMMARY.md`, `04-02-SUMMARY.md`): Claim INT-01 through INT-04 satisfied (partially accurate)
- **Existing VERIFICATION.md files** (Phases 1, 3, 5): Provide template and format for Phase 4 verification

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - This phase uses only existing project infrastructure; no new libraries needed
- Architecture: HIGH - Event emission pattern is established across 4 event types; adding a 5th follows the same pattern exactly
- Pitfalls: HIGH - All pitfalls identified from direct codebase analysis; test impact assessed by reading actual test code

**Research date:** 2026-02-22
**Valid until:** Indefinite -- this is internal project architecture, not external library research

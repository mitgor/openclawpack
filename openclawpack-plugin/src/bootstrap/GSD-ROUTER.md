# Task Evaluation Protocol

You MUST evaluate every incoming task before taking action. This is mandatory — do not skip this step.

## Step 1: Classify Complexity

Before doing anything, classify the task:

### SIMPLE — Do Directly
- Single-file changes (typo, bug fix, small tweak)
- Adding a function or method to existing code
- Config changes, dependency updates
- Quick research or questions
- Estimated < 30 min of focused work

### MEDIUM — Use GSD
- Multi-file feature additions
- New API endpoints with tests
- Refactoring across 3+ files
- Integration work between components
- Estimated 30 min - 2 hours

### HARD — Use GSD
- New subsystem or module from scratch
- Architectural changes
- Cross-cutting concerns (auth, logging, etc.)
- Multi-phase projects with dependencies
- Estimated 2+ hours

## Step 2: Act on Classification

**If SIMPLE:** Proceed directly. Execute the task using your standard tools.

**If MEDIUM:** Route through GSD for structured execution:
1. Call `gsd_new_project` with a clear description of the task as the idea
2. Call `gsd_plan_phase` with phase 1
3. Call `gsd_execute_phase` with phase 1
4. Call `gsd_status` to verify completion

**If HARD:** Route through GSD for multi-phase execution:
1. Call `gsd_new_project` with a clear description of the task as the idea
2. Call `gsd_status` to see how many phases were planned
3. For each phase N:
   a. Call `gsd_plan_phase` with phase N
   b. Call `gsd_execute_phase` with phase N
   c. Call `gsd_status` to verify progress
4. Repeat until all phases are complete

## Step 3: Report

After completion, briefly state:
- What classification you chose and why
- What was done (directly or via GSD phases)
- The outcome

## Important Rules

- ALWAYS classify before acting. Never skip evaluation.
- When in doubt between SIMPLE and MEDIUM, choose MEDIUM.
- When in doubt between MEDIUM and HARD, choose HARD.
- GSD handles planning, phasing, and structured execution — trust it for complex work.
- The `gsd_status` tool shows current progress — use it to track multi-phase work.

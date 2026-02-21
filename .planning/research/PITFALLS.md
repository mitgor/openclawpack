# Pitfalls Research

**Domain:** CLI middleware / agent orchestration wrapping Claude Code for GSD framework automation
**Researched:** 2026-02-21
**Confidence:** HIGH (verified against Claude Code official docs, SDK issue trackers, and multi-agent system research)

## Critical Pitfalls

### Pitfall 1: Subprocess Deadlock from Pipe Buffer Saturation

**What goes wrong:**
Claude Code subprocess hangs indefinitely. The parent Python process calls `wait()` or `readline()` while the child process has filled the OS pipe buffer (typically 64KB on Linux/macOS) and blocks waiting for the parent to read. Neither side makes progress. The orchestrator appears frozen with no error, no timeout, no output.

**Why it happens:**
Claude Code with `--verbose` or `--output-format stream-json` can produce substantial output (tool call logs, thinking traces, multi-file edits). Developers use `subprocess.Popen` with `stdout=PIPE` and then call `process.wait()` before reading output, or read stdout without draining stderr simultaneously. The pipe buffer fills, the child blocks on write, the parent blocks on wait -- classic deadlock.

**How to avoid:**
- Use `asyncio.create_subprocess_exec` with `process.communicate()` for bounded output, or stream `stdout`/`stderr` concurrently with separate `asyncio.Task` readers.
- Never call `process.wait()` without actively consuming both stdout and stderr.
- For long-running sessions, use line-by-line `async for line in process.stdout` with a concurrent stderr reader.
- Set `--max-turns` and `--max-budget-usd` as hard safety rails to bound output volume.
- Always implement timeouts via `asyncio.wait_for()` wrapping any subprocess interaction.

**Warning signs:**
- Tests pass with short prompts but hang on longer ones.
- CI/CD pipelines timeout without error messages.
- Process appears to consume 0% CPU but does not exit.
- Works in development (small output) but fails in production (large output).

**Phase to address:**
Phase 1 (Core subprocess layer). This must be correct from day one -- every other feature depends on reliable subprocess I/O.

---

### Pitfall 2: Parsing Claude Code Output as Stable Contract

**What goes wrong:**
The middleware treats Claude Code's text output, JSON wrapper structure, or stream-json event format as a stable API. A Claude Code update changes field names, nesting structure, event types, or adds new message types. The parser breaks silently -- either dropping data or misinterpreting fields -- causing downstream failures that are hard to trace back to a format change.

**Why it happens:**
Claude Code CLI is under active development (v0.x, alpha stage). The `--output-format json` wrapper structure (`{ messages, result, session_id }`) is a convenience feature, not a versioned API contract. The `stream-json` event types evolve as new tool types are added. The `claude-code-sdk` package was already deprecated once and replaced by `claude-agent-sdk`. Developers build tight coupling to current output shapes.

**How to avoid:**
- Build a parsing abstraction layer with explicit schema validation (e.g., Pydantic models) that fails loudly on unexpected fields or missing required fields.
- Pin to a known Claude Code CLI version in CI and test against it. Run integration tests against latest version separately.
- Use `--json-schema` flag when available to constrain Claude's text output, but validate the wrapper structure independently.
- Design parsers to be forward-compatible: ignore unknown fields, require only essential fields, handle missing optional fields gracefully.
- Maintain a `CLAUDE_CLI_VERSION` compatibility matrix documenting which output formats are verified.

**Warning signs:**
- `KeyError` or `None` values appearing after `claude update`.
- Integration tests that pass locally but fail in CI (different CLI versions).
- Structured output containing unexpected `type` values in message arrays.
- `claude-agent-sdk` deprecation notices appearing in pip output.

**Phase to address:**
Phase 1 (Output parsing layer). Define the abstraction boundary early. Revisit in every phase when adding new command types.

---

### Pitfall 3: File-Based State Race Conditions in Multi-Project Management

**What goes wrong:**
Two concurrent OpenClawPack commands (or a command and a GSD subprocess) read-modify-write the same `.planning/` file (STATE.md, config.json, ROADMAP.md). One write overwrites the other. Project state becomes inconsistent -- e.g., a phase marked as completed has its progress data erased, or config.json loses a key that was just written by another process.

**Why it happens:**
GSD stores all state in flat files in `.planning/`. There is no database, no write-ahead log, no locking mechanism. OpenClawPack's multi-project management feature means multiple Claude Code subprocesses can be running simultaneously, each potentially mutating the same `.planning/` directory. GSD's own `gsd-tools.cjs` uses file-level locking (the Claude Agent SDK issue tracker documents "Failed to save config with lock: Lock file is already being held" errors), but OpenClawPack's Python layer does not participate in that lock protocol.

**How to avoid:**
- Implement file-level advisory locking (`fcntl.flock` on macOS/Linux) for all `.planning/` file writes.
- Better yet: do not write `.planning/` files directly. Delegate all mutations to GSD via Claude Code subprocess. OpenClawPack should be read-only for `.planning/` artifacts, treating GSD as the single writer.
- For multi-project management, ensure each project has its own working directory with its own `.planning/` -- never share a `.planning/` directory across concurrent operations.
- Use `--worktree` or `--add-dir` flags to isolate concurrent Claude Code sessions into separate git worktrees.
- Implement an operation queue per-project that serializes state-mutating commands.

**Warning signs:**
- config.json values "resetting" unexpectedly.
- STATE.md showing stale phase information after a command completes.
- "Lock file is already being held" errors from Claude Code subprocess stderr.
- Intermittent test failures in CI when tests run in parallel.

**Phase to address:**
Phase 1 (State management design). The decision to be read-only vs. read-write for `.planning/` must be made before any state management code is written. Multi-project isolation must be designed before Phase 3 (multi-project management).

---

### Pitfall 4: The "Bag of Agents" Error Amplification Cascade

**What goes wrong:**
OpenClawPack spawns multiple Claude Code subprocesses (research agents, planning agents, execution agents) without structured coordination. One agent's incorrect output becomes the next agent's input. Errors compound through the pipeline. A planning agent hallucinates a requirement, the execution agent implements it, the verification agent validates against the hallucinated requirement. The system produces confidently wrong results that look correct at every individual step.

**Why it happens:**
Research (Moran 2026, Google DeepMind 2025) shows unstructured multi-agent systems amplify errors up to 17x compared to well-coordinated architectures. Specification failures account for ~42% of multi-agent failures -- agents misunderstand handoff context. Each inter-agent handoff adds 100-500ms latency AND re-serialization that loses context. The GSD framework's phase model (research -> requirements -> roadmap -> planning -> execution -> verification) creates a long pipeline where early errors propagate to every downstream step.

**How to avoid:**
- Validate output at every handoff boundary. Before passing one agent's output to the next, validate it against explicit schemas and constraints.
- Implement checkpoint/rollback at each GSD phase boundary. If a phase produces invalid output, retry that phase -- do not propagate garbage forward.
- Keep the agent topology simple: prefer a single orchestrating Claude Code session that manages the full GSD lifecycle over spawning separate agents per phase.
- Use Claude Code's `--continue` and `--resume` flags to maintain context within a single session rather than losing context across separate subprocess invocations.
- Log the full input/output at every handoff point for debugging and post-mortem analysis.

**Warning signs:**
- Final output quality is much worse than running GSD interactively with a human.
- Token usage is 10-15x higher than expected for the task complexity.
- Agents producing verbose "reasoning" but wrong conclusions.
- Phase N's output contradicts Phase N-2's output with no error raised.

**Phase to address:**
Phase 2 (Command implementation) and Phase 3 (Multi-project management). The handoff validation pattern must be established in Phase 2 when implementing `new-project` end-to-end. Phase 3's parallel execution makes this exponentially worse if not addressed.

---

### Pitfall 5: Non-Interactive Mode Missing GSD's Interactive Prompts

**What goes wrong:**
GSD's core workflow uses `AskUserQuestion` prompts to gather information (project requirements, technology preferences, scope decisions). In non-interactive mode (`-p` flag), these prompts have no human to answer them. Claude either: (a) makes assumptions and proceeds silently, producing output based on guesses; (b) returns partial output and exits; or (c) enters a loop trying to ask questions that will never be answered.

**Why it happens:**
GSD was designed as an interactive human-in-the-loop framework. Its questioning phase (`/gsd:new-project`) deliberately blocks for human input. The `--print` mode does not block on questions -- Claude must either answer them itself or skip them. The middleware developer assumes `-p` mode with a sufficiently detailed prompt will bypass all interactive prompts, but GSD skills have hardcoded question flows.

**How to avoid:**
- Pre-fill all GSD questions by composing a comprehensive prompt that includes: project description, technology choices, scope decisions, and constraints. Use `--append-system-prompt` to inject "Do not ask questions. Use the following answers: [...]".
- Build a question-answer mapping for each GSD phase that the middleware pre-populates from the calling agent's context.
- Use `--max-turns` as a safety valve: if Claude enters a question loop, it will eventually hit the turn limit and exit with an error rather than running forever.
- Consider using `--permission-prompt-tool` to provide an MCP tool that can programmatically answer permission prompts.
- Test each GSD phase thoroughly in non-interactive mode to map all possible question points.

**Warning signs:**
- GSD output contains phrases like "I'll assume...", "Since you didn't specify...", "Let me ask...".
- Generated PROJECT.md or ROADMAP.md contain placeholder values or generic defaults.
- Claude Code subprocess uses significantly more turns than expected (stuck in question loops).
- Output quality varies dramatically between runs with the same input.

**Phase to address:**
Phase 1 (Core architecture). The prompt composition strategy for bypassing interactive prompts is foundational. Each new GSD command added in Phase 2 must include a question-mapping test.

---

### Pitfall 6: Subprocess Lifecycle Leaks (Zombie Processes and Resource Exhaustion)

**What goes wrong:**
Claude Code subprocesses are spawned but not properly cleaned up. The parent process crashes, the user interrupts with Ctrl+C, a timeout fires, or an exception is raised -- but the Claude Code subprocess (and its child Node.js processes) continues running. Over time, zombie processes accumulate, consuming API credits, memory, and file descriptors. In multi-project mode, the system can exhaust system resources.

**Why it happens:**
Claude Code CLI spawns its own child processes (Node.js runtime, MCP servers). Killing the top-level `claude` process does not necessarily kill the entire process tree. Python's `process.terminate()` sends SIGTERM, but the child may ignore it. `process.kill()` sends SIGKILL to the immediate child but not grandchildren. On macOS, process groups behave differently than on Linux. The `claude-agent-sdk` issue tracker documents OOM-kill scenarios (exit code -9) from concurrent multi-agent runs.

**How to avoid:**
- Always use `try/finally` blocks (or `async with` context managers) around subprocess lifecycle.
- Create process groups (`os.setpgrp` or `start_new_session=True` in `asyncio.create_subprocess_exec`) and signal the entire group on cleanup.
- Implement a process registry that tracks all spawned subprocesses and provides a `cleanup_all()` method.
- Use `--max-turns` and `--max-budget-usd` as server-side kill switches.
- Implement a health-check loop that detects stuck subprocesses (no output for N seconds) and terminates them.
- Register `atexit` and signal handlers (`SIGINT`, `SIGTERM`) to clean up subprocesses on parent exit.

**Warning signs:**
- `ps aux | grep claude` shows orphan processes after OpenClawPack exits.
- System memory usage grows over time during multi-project runs.
- API usage dashboard shows token consumption continuing after commands complete.
- "Too many open files" errors in long-running orchestration sessions.

**Phase to address:**
Phase 1 (Subprocess management). The process lifecycle manager must be built before any multi-subprocess feature. Validate with stress tests in Phase 3.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Using `subprocess.run()` instead of async Popen | Simpler code, no async complexity | Blocks the event loop, cannot stream output, cannot run concurrent subprocesses, cannot implement timeouts cleanly | Never -- async subprocess is essential for this project's core value proposition |
| Parsing Claude output with regex instead of JSON parsing | Works for simple cases, fast to implement | Breaks on multi-line output, special characters, or format changes. Maintenance nightmare. | Never -- always parse structured JSON output |
| Shelling out to `claude` via `os.system()` or `shell=True` | Quick and easy | Shell injection risk, no output capture, no process control, platform-dependent quoting | Never |
| Storing subprocess state in global variables | Easy to access state from anywhere | Race conditions in multi-project mode, untestable, memory leaks from stale state | Never -- use per-project state containers |
| Hardcoding GSD phase names/flow | Matches current GSD version | GSD updates change phase structure, names, or ordering. Tight coupling prevents adaptation. | MVP only -- abstract behind a phase discovery mechanism before v1.0 |
| Skipping stderr capture to simplify I/O | Fewer async tasks, simpler code | Claude Code writes warnings, deprecation notices, and debug info to stderr. Missing these means silent failures and missed diagnostics. | Never |
| Using `--dangerously-skip-permissions` everywhere | No permission prompts to handle | Security risk -- subprocess can execute any command, modify any file. Especially dangerous in multi-project mode. | Development/testing only, never in production |

## Integration Gotchas

Common mistakes when connecting to Claude Code CLI and GSD artifacts.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Claude Code CLI version | Assuming CLI is installed and at expected version | Check `claude --version` at startup. Validate minimum version. Provide clear error message if missing or outdated. |
| Claude Agent SDK vs CLI subprocess | Using deprecated `claude-code-sdk` package | Use `claude-agent-sdk` (current) or raw CLI subprocess. Monitor Anthropic's SDK strategy -- it has changed once already. |
| GSD skill availability | Assuming GSD skills are installed at `~/.claude/get-shit-done/` | Verify skill files exist before invoking. GSD path may differ across installations. Allow path configuration. |
| Claude authentication | Assuming `claude` is authenticated and has valid API key | Run a lightweight probe command (`claude -p "ping" --max-turns 1`) to verify auth before starting real work. Handle auth failures with clear user guidance. |
| `.planning/` directory structure | Assuming all GSD files exist (PROJECT.md, ROADMAP.md, STATE.md, config.json) | Check for file existence before reading. Some files are only created by specific GSD phases. Handle missing files as "phase not yet run" rather than errors. |
| `--output-format json` wrapper | Accessing `result.content[0].text` directly | The JSON wrapper structure nests actual content. Extract via `.result` for text, `.structured_output` for schema-constrained output. Validate wrapper structure first. |
| `--continue` / `--resume` session management | Assuming sessions persist across CLI updates or machine restarts | Sessions may be invalidated. Always handle "session not found" gracefully. Use `--no-session-persistence` when sessions are not needed. |
| Piping input via stdin | Passing long prompts as command-line arguments | Command-line length limits vary by OS (typically 128KB-2MB). Pipe long prompts via stdin: `echo "prompt" \| claude -p`. The SDK handles this but raw subprocess calls must do it manually. |
| `--json-schema` for structured output | Expecting 100% schema compliance | Claude Code cannot guarantee output matches a JSON schema perfectly. Always validate and handle schema violations with retry logic. |
| Windows subprocess management | Using same subprocess code across platforms | Windows has different process group behavior, path resolution (`claude` vs `claude.cmd`), encoding defaults (cp1252 vs utf-8), and pipe buffering. Test on target platforms explicitly. |

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Synchronous sequential phase execution | Simple and correct but slow | Use async subprocess management. Identify independent phases that can run in parallel (e.g., research agents). | >2 projects managed simultaneously |
| Unbounded conversation context | Conversation history grows with each `--continue` | Use fresh sessions for independent phases. Only use `--continue` when context genuinely needs to carry over. Monitor token usage per session. | >5 phases continued in single session (context window exhaustion) |
| Polling subprocess for completion | CPU spin-wait loop checking `process.poll()` | Use `asyncio` event-driven waiting (`await process.wait()` with concurrent output readers). | >10 concurrent subprocesses |
| Loading entire `.planning/` directory into memory | Simple dict of file contents | Lazy-load files on demand. Cache with invalidation. | Projects with large ROADMAP.md or many phase artifacts (>50 files) |
| Full JSON deserialization of streaming output | Parsing every `stream-json` line into full Python objects | Use streaming JSON parser. Only fully deserialize events you need. Discard partial messages unless building a progress display. | High-volume streaming output (verbose mode, long execution) |
| Re-reading config.json on every operation | Always getting fresh state | Read once per command invocation, not per-function-call. Use a config cache with explicit invalidation. | >100 operations per session |
| Rate limit ignorance | Works fine with 1-2 concurrent agents | Implement rate limit detection (HTTP 429 in subprocess stderr) and backoff. Queue commands when rate-limited. | >3 concurrent Claude Code subprocesses hitting Anthropic API |

## Security Mistakes

Domain-specific security issues beyond general application security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Using `--dangerously-skip-permissions` in production | Claude Code subprocess can execute arbitrary shell commands, read/write any file, make network requests | Use `--allowedTools` with explicit allowlist. Only permit tools needed for each specific GSD phase. |
| Passing user-provided project names/paths unescaped to subprocess arguments | Shell injection -- an agent could provide a project name containing shell metacharacters | Always use list-form subprocess arguments (not shell=True). Validate and sanitize all paths. |
| Storing API keys or Claude authentication tokens in `.planning/` artifacts | Credentials committed to git, leaked in project state | Never write credentials to `.planning/`. Use environment variables or OS keychain. Scan output for accidental credential leakage. |
| Logging full Claude Code output including tool calls | Logs contain file contents, code, potentially secrets from the managed project | Implement log sanitization. Redact file contents in logs. Only log metadata (tool name, success/failure, duration). |
| Running Claude Code subprocess as root or with elevated privileges | Subprocess inherits privileges -- a hallucinated `rm -rf /` command executes with full permissions | Run subprocesses with minimal privileges. Use containerization or sandboxing for execution phases. |
| Trusting Claude's structured output without validation | Agent injects malicious data into structured output that downstream consumers execute | Validate all structured output against schemas. Never `eval()` or `exec()` Claude's output. Treat all output as untrusted input. |

## UX Pitfalls

Common user/developer experience mistakes in CLI middleware for agent orchestration.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| No progress indication during long subprocess runs | User thinks tool is hung, kills it, loses work | Stream progress events. Show phase name, elapsed time, turn count. Use `--output-format stream-json` to surface progress. |
| Opaque error messages ("subprocess failed") | User cannot diagnose or fix the problem | Capture and surface Claude Code's stderr. Map common exit codes to human-readable messages. Include the failed command for reproducibility. |
| No way to interrupt gracefully | User must `kill -9`, losing partial work | Handle SIGINT/SIGTERM. Send graceful shutdown to subprocess. Save partial state before exiting. |
| All-or-nothing commands (full project creation with no checkpoints) | Hours of work lost on failure near the end | Implement checkpoints at each GSD phase boundary. Allow resuming from last successful phase. |
| Inconsistent JSON output schemas across commands | Agents must special-case each command's output format | Define a unified response envelope: `{ success, command, phase, data, errors, metadata }`. All commands return this shape. |
| Silent fallback behavior | Agent does not know the tool degraded its output quality | Return explicit warnings when falling back (e.g., "Claude assumed X because no answer was provided"). Include confidence indicators in output. |

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Subprocess execution:** Often missing proper cleanup on exception paths -- verify `finally` blocks kill the process group, not just the top-level process
- [ ] **JSON output parsing:** Often missing handling for the `stream-json` `error` event type -- verify error events are caught and surfaced, not silently dropped
- [ ] **Session management:** Often missing session cleanup for `--no-session-persistence` -- verify disk space is not consumed by abandoned session files
- [ ] **Multi-project support:** Often missing per-project working directory isolation -- verify two concurrent commands on different projects never touch the same `.planning/` directory
- [ ] **Error handling:** Often missing stderr capture from Claude Code subprocess -- verify warnings and deprecation notices are logged, not discarded
- [ ] **Timeout implementation:** Often missing timeout on the initial subprocess spawn -- verify the tool fails fast if `claude` binary is not found or hangs on startup
- [ ] **Platform compatibility:** Often missing Windows pipe buffering handling -- verify `encoding="utf-8"` and proper line-ending handling on Windows
- [ ] **GSD compatibility:** Often missing version validation of GSD skills -- verify the installed GSD version matches the expected phase/command structure
- [ ] **Rate limit handling:** Often missing detection of Anthropic API rate limits in subprocess output -- verify 429 errors are caught and retried with backoff
- [ ] **Output validation:** Often missing schema validation of Claude's structured output -- verify malformed JSON is caught before being returned to the calling agent

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Subprocess deadlock | LOW | Kill the process group. Re-run the command. Fix the I/O pattern that caused the deadlock. Add a timeout to prevent recurrence. |
| Output format breakage after CLI update | MEDIUM | Pin CLI version. Re-run failed commands. Update parser to handle new format. Add regression test for new format. |
| `.planning/` state corruption from race condition | HIGH | Restore from git (if committed) or last known good state. Replay GSD phases to reconstruct state. Add file locking to prevent recurrence. |
| Error amplification cascade | HIGH | Identify the first incorrect handoff by reviewing inter-phase logs. Roll back to the last valid checkpoint. Re-run from that phase with corrected input. |
| Missing interactive prompt answers | MEDIUM | Review generated artifacts for assumptions. Update prompt template with missing answers. Re-run affected phases. |
| Zombie subprocess accumulation | LOW | Kill all orphan `claude` processes (`pkill -f "claude"`). Restart OpenClawPack. Add process registry and cleanup handlers. |
| API rate limiting | LOW | Wait for rate limit window to expire. Reduce concurrency. Implement exponential backoff. Queue commands. |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Subprocess deadlock | Phase 1: Core subprocess layer | Integration test: run Claude Code with `--verbose` on a large codebase. Verify no hangs with 60s timeout. |
| Output format fragility | Phase 1: Parsing abstraction | Unit test: parse output from multiple CLI versions. Verify forward-compatible parsing handles unknown fields. |
| `.planning/` race conditions | Phase 1: State management design | Stress test: run 5 concurrent commands against same project. Verify config.json integrity after all complete. |
| Error amplification cascade | Phase 2: Command pipeline implementation | End-to-end test: inject a wrong answer in phase 2 of a 5-phase project. Verify validation catches it before phase 3. |
| Missing interactive prompts | Phase 2: GSD command wrappers | Integration test: run each GSD phase with `-p` mode. Verify output contains no "I'll assume..." or "Let me ask..." patterns. |
| Zombie process accumulation | Phase 1: Process lifecycle management | Stress test: spawn 10 subprocesses, kill parent with SIGKILL. Verify all children terminate within 5 seconds. |
| Rate limit handling | Phase 3: Multi-project management | Load test: run 5 concurrent projects. Verify rate limits are detected and commands are queued, not failed. |
| Windows compatibility | Phase 1: Cross-platform subprocess | CI matrix test: run core subprocess tests on macOS, Linux, and Windows. Verify process lifecycle on all platforms. |
| SDK deprecation/migration | Phase 1: Architecture decision | Decision gate: choose raw CLI subprocess vs. `claude-agent-sdk`. Document rationale. Abstract behind interface for future migration. |

## Sources

- [Claude Code CLI Reference](https://code.claude.com/docs/en/cli-reference) -- Official documentation for all CLI flags and modes (HIGH confidence)
- [Run Claude Code Programmatically](https://code.claude.com/docs/en/headless) -- Official Agent SDK and headless mode documentation (HIGH confidence)
- [claude-agent-sdk on PyPI](https://pypi.org/project/claude-agent-sdk/) -- Current Python SDK, v0.1.39, alpha status (HIGH confidence)
- [claude-code-sdk Deprecation](https://pypi.org/project/claude-code-sdk/) -- Deprecated package, migration to claude-agent-sdk required (HIGH confidence)
- [Claude Agent SDK GitHub Issues](https://github.com/anthropics/claude-agent-sdk-python/issues/513) -- Multi-agent lock contention, ENOENT, OOM-kill in concurrent runs (HIGH confidence)
- [Claude Agent SDK Windows Hang Issue](https://github.com/anthropics/claude-agent-sdk-python/issues/208) -- ClaudeSDKClient initialization hang on Windows (HIGH confidence)
- [Claude Agent SDK Sub-agents Registration Bug](https://github.com/anthropics/claude-agent-sdk-python/issues/567) -- Temp file fallback syntax error for large agent configs (HIGH confidence)
- [Interacting with Long-Running Child Processes in Python](https://eli.thegreenplace.net/2017/interacting-with-a-long-running-child-process-in-python/) -- Definitive guide on subprocess I/O deadlocks (HIGH confidence)
- [Python asyncio Subprocess Documentation](https://docs.python.org/3/library/asyncio-subprocess.html) -- Official Python subprocess deadlock warnings (HIGH confidence)
- [Why Your Multi-Agent System is Failing: The 17x Error Trap](https://towardsdatascience.com/why-your-multi-agent-system-is-failing-escaping-the-17x-error-trap-of-the-bag-of-agents/) -- Research on error amplification in unstructured multi-agent topologies (MEDIUM confidence)
- [Multi-Agent System Reliability: Failure Patterns](https://www.getmaxim.ai/articles/multi-agent-system-reliability-failure-patterns-root-causes-and-production-validation-strategies) -- Stale state propagation, coordination overhead quantification (MEDIUM confidence)
- [Claude PM Framework](https://github.com/bobmatnyc/claude-pm) -- Archived multi-subprocess orchestration framework, real-world lessons (MEDIUM confidence)
- [AI Agent Orchestration Patterns - Azure](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/ai-agent-design-patterns) -- Microsoft's agent design patterns including checkpoint/recovery (MEDIUM confidence)
- [Error Recovery in AI Agent Development](https://www.gocodeo.com/post/error-recovery-and-fallback-strategies-in-ai-agent-development) -- Tool wrapper retry patterns, semantic fallback strategies (MEDIUM confidence)
- [Cascading Failures in Agentic AI (OWASP ASI08)](https://adversa.ai/blog/cascading-failures-in-agentic-ai-complete-owasp-asi08-security-guide-2026/) -- Security-focused cascade failure analysis (MEDIUM confidence)

---
*Pitfalls research for: CLI middleware / agent orchestration (OpenClawPack)*
*Researched: 2026-02-21*

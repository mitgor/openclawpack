# GSD Router Plugin Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an OpenClaw plugin that forces task difficulty evaluation and routes medium/hard tasks through GSD via OpenClawPack CLI.

**Architecture:** TypeScript OpenClaw plugin using `agent:bootstrap` hook to inject evaluation rubric into agent system prompt, plus 4 registered tools wrapping the `openclawpack` CLI subprocess. Plugin lives at `openclawpack-plugin/` inside the openclawpack repo.

**Tech Stack:** TypeScript, Node.js child_process, Vitest, OpenClaw plugin API

---

### Task 1: Scaffold Plugin Package

**Files:**
- Create: `openclawpack-plugin/package.json`
- Create: `openclawpack-plugin/tsconfig.json`
- Create: `openclawpack-plugin/openclaw.plugin.json`

**Step 1: Create package.json**

```json
{
  "name": "@openclawpack/gsd-router",
  "version": "0.1.0",
  "description": "OpenClaw plugin that evaluates task complexity and routes medium/hard tasks through GSD via OpenClawPack",
  "type": "module",
  "main": "dist/index.js",
  "types": "dist/index.d.ts",
  "scripts": {
    "build": "tsc",
    "test": "vitest run",
    "test:watch": "vitest",
    "clean": "rm -rf dist"
  },
  "openclaw": {
    "extensions": ["dist/index.js"]
  },
  "devDependencies": {
    "typescript": "^5.7.0",
    "vitest": "^3.0.0"
  },
  "license": "MIT"
}
```

**Step 2: Create tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "outDir": "dist",
    "rootDir": "src",
    "declaration": true,
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true
  },
  "include": ["src"],
  "exclude": ["node_modules", "dist"]
}
```

**Step 3: Create openclaw.plugin.json**

```json
{
  "id": "gsd-router",
  "name": "GSD Router",
  "description": "Evaluates task complexity and routes medium/hard tasks through GSD via OpenClawPack",
  "configSchema": {
    "type": "object",
    "properties": {
      "openclawpack_path": {
        "type": "string",
        "default": "openclawpack",
        "description": "Path to the openclawpack CLI binary"
      },
      "default_timeout": {
        "type": "number",
        "default": 300,
        "description": "Subprocess timeout in seconds"
      },
      "evaluation_enabled": {
        "type": "boolean",
        "default": true,
        "description": "Toggle forced task evaluation on/off"
      }
    }
  }
}
```

**Step 4: Install dependencies**

Run: `cd openclawpack-plugin && npm install`
Expected: `node_modules/` created, lock file written

**Step 5: Commit**

```bash
git add openclawpack-plugin/package.json openclawpack-plugin/tsconfig.json openclawpack-plugin/openclaw.plugin.json openclawpack-plugin/package-lock.json
git commit -m "feat(plugin): scaffold @openclawpack/gsd-router plugin package"
```

---

### Task 2: Create Bootstrap GSD-ROUTER.md

**Files:**
- Create: `openclawpack-plugin/src/bootstrap/GSD-ROUTER.md`

**Step 1: Write the bootstrap file**

This file is injected into the agent's system prompt every turn. It contains the mandatory evaluation rubric and routing instructions.

```markdown
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
```

**Step 2: Commit**

```bash
git add openclawpack-plugin/src/bootstrap/GSD-ROUTER.md
git commit -m "feat(plugin): add GSD-ROUTER.md bootstrap evaluation rubric"
```

---

### Task 3: Create Subprocess Executor

**Files:**
- Create: `openclawpack-plugin/src/exec.ts`
- Create: `openclawpack-plugin/src/__tests__/exec.test.ts`

**Step 1: Write the failing test**

```typescript
// openclawpack-plugin/src/__tests__/exec.test.ts
import { describe, it, expect, vi } from "vitest";
import { execOpenClawPack } from "../exec.js";
import { execFile } from "node:child_process";

vi.mock("node:child_process", () => ({
  execFile: vi.fn(),
}));

const mockExecFile = vi.mocked(execFile);

describe("execOpenClawPack", () => {
  it("calls openclawpack CLI with correct args and returns parsed JSON", async () => {
    const jsonOutput = JSON.stringify({
      success: true,
      result: { status: "ok" },
      errors: [],
      session_id: "abc-123",
      usage: null,
      duration_ms: 100,
    });

    mockExecFile.mockImplementation(
      (_cmd: any, _args: any, _opts: any, cb: any) => {
        cb(null, jsonOutput, "");
        return {} as any;
      }
    );

    const result = await execOpenClawPack(["status"], {
      cliPath: "openclawpack",
      timeout: 300,
    });

    expect(result).toEqual({
      success: true,
      result: { status: "ok" },
      errors: [],
      session_id: "abc-123",
      usage: null,
      duration_ms: 100,
    });

    expect(mockExecFile).toHaveBeenCalledWith(
      "openclawpack",
      ["status", "--output-format", "json", "--quiet"],
      expect.objectContaining({ timeout: 300000 }),
      expect.any(Function)
    );
  });

  it("throws on non-zero exit with stderr message", async () => {
    mockExecFile.mockImplementation(
      (_cmd: any, _args: any, _opts: any, cb: any) => {
        const err = Object.assign(new Error("exit 1"), { code: 1 });
        cb(err, "", "openclawpack: command failed");
        return {} as any;
      }
    );

    await expect(
      execOpenClawPack(["status"], { cliPath: "openclawpack", timeout: 300 })
    ).rejects.toThrow("openclawpack: command failed");
  });

  it("throws on invalid JSON output", async () => {
    mockExecFile.mockImplementation(
      (_cmd: any, _args: any, _opts: any, cb: any) => {
        cb(null, "not json", "");
        return {} as any;
      }
    );

    await expect(
      execOpenClawPack(["status"], { cliPath: "openclawpack", timeout: 300 })
    ).rejects.toThrow("Failed to parse openclawpack output");
  });

  it("adds project-dir flag when provided", async () => {
    mockExecFile.mockImplementation(
      (_cmd: any, _args: any, _opts: any, cb: any) => {
        cb(null, '{"success":true}', "");
        return {} as any;
      }
    );

    await execOpenClawPack(["status"], {
      cliPath: "openclawpack",
      timeout: 300,
      projectDir: "/tmp/myproject",
    });

    expect(mockExecFile).toHaveBeenCalledWith(
      "openclawpack",
      [
        "--project-dir",
        "/tmp/myproject",
        "status",
        "--output-format",
        "json",
        "--quiet",
      ],
      expect.any(Object),
      expect.any(Function)
    );
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd openclawpack-plugin && npx vitest run src/__tests__/exec.test.ts`
Expected: FAIL — `Cannot find module '../exec.js'`

**Step 3: Write the implementation**

```typescript
// openclawpack-plugin/src/exec.ts
import { execFile } from "node:child_process";

export interface ExecOptions {
  cliPath: string;
  timeout: number;
  projectDir?: string;
}

export async function execOpenClawPack(
  args: string[],
  options: ExecOptions
): Promise<Record<string, unknown>> {
  const fullArgs: string[] = [];

  if (options.projectDir) {
    fullArgs.push("--project-dir", options.projectDir);
  }

  fullArgs.push(...args, "--output-format", "json", "--quiet");

  return new Promise((resolve, reject) => {
    execFile(
      options.cliPath,
      fullArgs,
      { timeout: options.timeout * 1000 },
      (error, stdout, stderr) => {
        if (error) {
          reject(new Error(stderr || error.message));
          return;
        }

        try {
          resolve(JSON.parse(stdout));
        } catch {
          reject(new Error("Failed to parse openclawpack output"));
        }
      }
    );
  });
}
```

**Step 4: Run test to verify it passes**

Run: `cd openclawpack-plugin && npx vitest run src/__tests__/exec.test.ts`
Expected: 4 tests PASS

**Step 5: Commit**

```bash
git add openclawpack-plugin/src/exec.ts openclawpack-plugin/src/__tests__/exec.test.ts
git commit -m "feat(plugin): add subprocess executor for openclawpack CLI"
```

---

### Task 4: Create Tool Registrations

**Files:**
- Create: `openclawpack-plugin/src/tools.ts`
- Create: `openclawpack-plugin/src/__tests__/tools.test.ts`

**Step 1: Write the failing test**

```typescript
// openclawpack-plugin/src/__tests__/tools.test.ts
import { describe, it, expect, vi, beforeEach } from "vitest";
import { registerTools } from "../tools.js";

vi.mock("../exec.js", () => ({
  execOpenClawPack: vi.fn(),
}));

import { execOpenClawPack } from "../exec.js";
const mockExec = vi.mocked(execOpenClawPack);

describe("registerTools", () => {
  let registeredTools: Map<string, any>;
  let mockApi: any;

  beforeEach(() => {
    registeredTools = new Map();
    mockApi = {
      registerTool: vi.fn((tool: any) => {
        registeredTools.set(tool.name, tool);
      }),
    };
    vi.clearAllMocks();
  });

  it("registers exactly 4 tools", () => {
    registerTools(mockApi, {
      cliPath: "openclawpack",
      timeout: 300,
    });

    expect(mockApi.registerTool).toHaveBeenCalledTimes(4);
    expect(registeredTools.has("gsd_new_project")).toBe(true);
    expect(registeredTools.has("gsd_plan_phase")).toBe(true);
    expect(registeredTools.has("gsd_execute_phase")).toBe(true);
    expect(registeredTools.has("gsd_status")).toBe(true);
  });

  it("gsd_new_project calls openclawpack new-project with idea", async () => {
    registerTools(mockApi, { cliPath: "openclawpack", timeout: 300 });

    mockExec.mockResolvedValue({ success: true, result: {} });

    const tool = registeredTools.get("gsd_new_project");
    const result = await tool.execute({
      idea: "Build a todo app",
      project_dir: "/tmp/proj",
    });

    expect(mockExec).toHaveBeenCalledWith(
      ["new-project", "-i", "Build a todo app"],
      { cliPath: "openclawpack", timeout: 300, projectDir: "/tmp/proj" }
    );
    expect(result).toEqual({ success: true, result: {} });
  });

  it("gsd_plan_phase calls openclawpack plan-phase with phase number", async () => {
    registerTools(mockApi, { cliPath: "openclawpack", timeout: 300 });

    mockExec.mockResolvedValue({ success: true, result: {} });

    const tool = registeredTools.get("gsd_plan_phase");
    await tool.execute({ phase: 2 });

    expect(mockExec).toHaveBeenCalledWith(["plan-phase", "2"], {
      cliPath: "openclawpack",
      timeout: 300,
      projectDir: undefined,
    });
  });

  it("gsd_execute_phase calls openclawpack execute-phase with phase number", async () => {
    registerTools(mockApi, { cliPath: "openclawpack", timeout: 300 });

    mockExec.mockResolvedValue({ success: true, result: {} });

    const tool = registeredTools.get("gsd_execute_phase");
    await tool.execute({ phase: 1, project_dir: "/tmp/p" });

    expect(mockExec).toHaveBeenCalledWith(["execute-phase", "1"], {
      cliPath: "openclawpack",
      timeout: 300,
      projectDir: "/tmp/p",
    });
  });

  it("gsd_status calls openclawpack status", async () => {
    registerTools(mockApi, { cliPath: "openclawpack", timeout: 300 });

    mockExec.mockResolvedValue({ success: true, result: { phase: 1 } });

    const tool = registeredTools.get("gsd_status");
    const result = await tool.execute({});

    expect(mockExec).toHaveBeenCalledWith(["status"], {
      cliPath: "openclawpack",
      timeout: 300,
      projectDir: undefined,
    });
    expect(result).toEqual({ success: true, result: { phase: 1 } });
  });

  it("tool returns error string on exec failure", async () => {
    registerTools(mockApi, { cliPath: "openclawpack", timeout: 300 });

    mockExec.mockRejectedValue(new Error("CLI not found"));

    const tool = registeredTools.get("gsd_status");
    const result = await tool.execute({});

    expect(result).toEqual({ error: "CLI not found" });
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd openclawpack-plugin && npx vitest run src/__tests__/tools.test.ts`
Expected: FAIL — `Cannot find module '../tools.js'`

**Step 3: Write the implementation**

```typescript
// openclawpack-plugin/src/tools.ts
import { execOpenClawPack, type ExecOptions } from "./exec.js";

interface ToolConfig {
  cliPath: string;
  timeout: number;
}

interface PluginApi {
  registerTool: (tool: ToolDef) => void;
}

interface ToolDef {
  name: string;
  description: string;
  parameters: Record<string, unknown>;
  execute: (params: Record<string, unknown>) => Promise<unknown>;
}

function makeExecOpts(
  config: ToolConfig,
  projectDir?: string
): ExecOptions {
  return {
    cliPath: config.cliPath,
    timeout: config.timeout,
    projectDir,
  };
}

async function safeExec(
  args: string[],
  opts: ExecOptions
): Promise<unknown> {
  try {
    return await execOpenClawPack(args, opts);
  } catch (err) {
    return { error: err instanceof Error ? err.message : String(err) };
  }
}

export function registerTools(api: PluginApi, config: ToolConfig): void {
  api.registerTool({
    name: "gsd_new_project",
    description:
      "Create a new GSD project from an idea. Use this for MEDIUM and HARD tasks. Returns structured JSON with project creation results.",
    parameters: {
      type: "object",
      properties: {
        idea: {
          type: "string",
          description:
            "A clear description of what to build. Be specific about features, constraints, and goals.",
        },
        project_dir: {
          type: "string",
          description:
            "Optional project directory path. Defaults to current working directory.",
        },
      },
      required: ["idea"],
    },
    execute: async (params) => {
      const idea = params.idea as string;
      const projectDir = params.project_dir as string | undefined;
      return safeExec(
        ["new-project", "-i", idea],
        makeExecOpts(config, projectDir)
      );
    },
  });

  api.registerTool({
    name: "gsd_plan_phase",
    description:
      "Plan a GSD phase. Call this after gsd_new_project to create a detailed execution plan for a specific phase.",
    parameters: {
      type: "object",
      properties: {
        phase: {
          type: "number",
          description: "Phase number to plan (e.g., 1, 2, 3).",
        },
        project_dir: {
          type: "string",
          description: "Optional project directory path.",
        },
      },
      required: ["phase"],
    },
    execute: async (params) => {
      const phase = String(params.phase as number);
      const projectDir = params.project_dir as string | undefined;
      return safeExec(
        ["plan-phase", phase],
        makeExecOpts(config, projectDir)
      );
    },
  });

  api.registerTool({
    name: "gsd_execute_phase",
    description:
      "Execute a planned GSD phase. Call this after gsd_plan_phase to run the execution plan and build the code.",
    parameters: {
      type: "object",
      properties: {
        phase: {
          type: "number",
          description: "Phase number to execute (e.g., 1, 2, 3).",
        },
        project_dir: {
          type: "string",
          description: "Optional project directory path.",
        },
      },
      required: ["phase"],
    },
    execute: async (params) => {
      const phase = String(params.phase as number);
      const projectDir = params.project_dir as string | undefined;
      return safeExec(
        ["execute-phase", phase],
        makeExecOpts(config, projectDir)
      );
    },
  });

  api.registerTool({
    name: "gsd_status",
    description:
      "Check GSD project status. Shows current phase, progress percentage, requirements completion, and any blockers.",
    parameters: {
      type: "object",
      properties: {
        project_dir: {
          type: "string",
          description: "Optional project directory path.",
        },
      },
    },
    execute: async (params) => {
      const projectDir = params.project_dir as string | undefined;
      return safeExec(["status"], makeExecOpts(config, projectDir));
    },
  });
}
```

**Step 4: Run test to verify it passes**

Run: `cd openclawpack-plugin && npx vitest run src/__tests__/tools.test.ts`
Expected: 6 tests PASS

**Step 5: Commit**

```bash
git add openclawpack-plugin/src/tools.ts openclawpack-plugin/src/__tests__/tools.test.ts
git commit -m "feat(plugin): add 4 GSD tool registrations wrapping openclawpack CLI"
```

---

### Task 5: Create Plugin Entry Point

**Files:**
- Create: `openclawpack-plugin/src/index.ts`
- Create: `openclawpack-plugin/src/__tests__/index.test.ts`

**Step 1: Write the failing test**

```typescript
// openclawpack-plugin/src/__tests__/index.test.ts
import { describe, it, expect, vi, beforeEach } from "vitest";
import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

vi.mock("../tools.js", () => ({
  registerTools: vi.fn(),
}));

import { registerTools } from "../tools.js";
const mockRegisterTools = vi.mocked(registerTools);

describe("plugin entry", () => {
  let mockApi: any;

  beforeEach(() => {
    mockApi = {
      registerHook: vi.fn(),
      registerTool: vi.fn(),
    };
    vi.clearAllMocks();
  });

  it("exports a register function", async () => {
    const plugin = await import("../index.js");
    expect(typeof plugin.default).toBe("function");
  });

  it("registers agent:bootstrap hook", async () => {
    const plugin = await import("../index.js");
    plugin.default(mockApi);

    expect(mockApi.registerHook).toHaveBeenCalledWith(
      "agent:bootstrap",
      expect.any(Function),
      expect.objectContaining({
        name: "gsd-router.bootstrap",
      })
    );
  });

  it("calls registerTools with config defaults", async () => {
    const plugin = await import("../index.js");
    plugin.default(mockApi);

    expect(mockRegisterTools).toHaveBeenCalledWith(mockApi, {
      cliPath: "openclawpack",
      timeout: 300,
    });
  });

  it("bootstrap hook injects GSD-ROUTER.md content", async () => {
    const plugin = await import("../index.js");
    plugin.default(mockApi);

    const hookCall = mockApi.registerHook.mock.calls.find(
      (c: any[]) => c[0] === "agent:bootstrap"
    );
    const hookFn = hookCall[1];

    const event = {
      context: {
        bootstrapFiles: new Map<string, string>(),
      },
    };

    await hookFn(event);

    expect(event.context.bootstrapFiles.has("GSD-ROUTER.md")).toBe(true);
    const content = event.context.bootstrapFiles.get("GSD-ROUTER.md");
    expect(content).toContain("Task Evaluation Protocol");
    expect(content).toContain("SIMPLE");
    expect(content).toContain("MEDIUM");
    expect(content).toContain("HARD");
  });

  it("skips bootstrap injection when evaluation_enabled is false", async () => {
    const plugin = await import("../index.js");

    const configApi = {
      ...mockApi,
      config: { evaluation_enabled: false },
    };
    plugin.default(configApi);

    const hookCall = configApi.registerHook.mock.calls.find(
      (c: any[]) => c[0] === "agent:bootstrap"
    );
    const hookFn = hookCall[1];

    const event = {
      context: {
        bootstrapFiles: new Map<string, string>(),
      },
    };

    await hookFn(event);

    expect(event.context.bootstrapFiles.has("GSD-ROUTER.md")).toBe(false);
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd openclawpack-plugin && npx vitest run src/__tests__/index.test.ts`
Expected: FAIL — `Cannot find module '../index.js'`

**Step 3: Write the implementation**

```typescript
// openclawpack-plugin/src/index.ts
import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { registerTools } from "./tools.js";

const __dirname = dirname(fileURLToPath(import.meta.url));

const bootstrapContent = readFileSync(
  join(__dirname, "bootstrap", "GSD-ROUTER.md"),
  "utf-8"
);

interface PluginApi {
  registerHook: (
    event: string,
    handler: (event: any) => Promise<void>,
    meta: { name: string; description: string }
  ) => void;
  registerTool: (tool: any) => void;
  config?: Record<string, unknown>;
}

export default function register(api: PluginApi): void {
  const config = api.config ?? {};
  const cliPath = (config.openclawpack_path as string) ?? "openclawpack";
  const timeout = (config.default_timeout as number) ?? 300;
  const evaluationEnabled = config.evaluation_enabled !== false;

  registerTools(api, { cliPath, timeout });

  api.registerHook(
    "agent:bootstrap",
    async (event) => {
      if (!evaluationEnabled) return;

      const files: Map<string, string> =
        event.context?.bootstrapFiles ?? new Map();
      files.set("GSD-ROUTER.md", bootstrapContent);
    },
    {
      name: "gsd-router.bootstrap",
      description:
        "Injects task evaluation rubric into agent system prompt",
    }
  );
}
```

**Step 4: Run test to verify it passes**

Run: `cd openclawpack-plugin && npx vitest run src/__tests__/index.test.ts`
Expected: 5 tests PASS

**Step 5: Commit**

```bash
git add openclawpack-plugin/src/index.ts openclawpack-plugin/src/__tests__/index.test.ts
git commit -m "feat(plugin): add plugin entry point with bootstrap hook and config"
```

---

### Task 6: Build and Verify

**Step 1: Run all tests**

Run: `cd openclawpack-plugin && npx vitest run`
Expected: All 15 tests PASS (4 exec + 6 tools + 5 index)

**Step 2: Build TypeScript**

Run: `cd openclawpack-plugin && npm run build`
Expected: `dist/` directory created with compiled .js and .d.ts files

**Step 3: Verify dist includes bootstrap file**

The bootstrap .md file needs to be in dist/bootstrap/ for the compiled code to read it at runtime. Add a copy step.

Update `package.json` scripts:
```json
"build": "tsc && cp -r src/bootstrap dist/bootstrap"
```

Run: `cd openclawpack-plugin && npm run build`
Expected: `dist/bootstrap/GSD-ROUTER.md` exists

**Step 4: Verify plugin manifest is valid**

Run: `cd openclawpack-plugin && node -e "const m = require('./openclaw.plugin.json'); console.log('Plugin ID:', m.id); console.log('Config keys:', Object.keys(m.configSchema.properties))"`
Expected:
```
Plugin ID: gsd-router
Config keys: [ 'openclawpack_path', 'default_timeout', 'evaluation_enabled' ]
```

**Step 5: Commit final build config**

```bash
git add openclawpack-plugin/
git commit -m "feat(plugin): finalize build config and verify plugin structure"
```

---

### Task 7: Add .gitignore and README

**Files:**
- Create: `openclawpack-plugin/.gitignore`

**Step 1: Create .gitignore**

```
node_modules/
dist/
```

**Step 2: Commit**

```bash
git add openclawpack-plugin/.gitignore
git commit -m "chore(plugin): add .gitignore for node_modules and dist"
```

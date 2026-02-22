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

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

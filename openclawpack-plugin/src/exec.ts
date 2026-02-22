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

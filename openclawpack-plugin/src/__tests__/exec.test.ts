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
